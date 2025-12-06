import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Text, Float
from datetime import datetime, timedelta
from sqlalchemy import select, func, distinct, and_
from sqlalchemy.orm import Session, sessionmaker
from app import models
import argparse

SRC_DB = os.getenv('SRC_DATABASE_URL', os.getenv('DATABASE_URL'))
ANALYTICS_DB = os.getenv('ANALYTICS_DATABASE_URL', os.getenv('ANALYTICS_DB_URL', 'sqlite:///./analytics.db'))

if not SRC_DB:
    raise SystemExit("SRC_DATABASE_URL or DATABASE_URL must be set to run the ETL — refusing to run with default sqlite. Export SRC_DATABASE_URL and try again.")

def ensure_target_schema(engine):
    meta = MetaData()
    chats = Table('chat_metrics', meta,
                  Column('id', Integer, primary_key=True),
                  Column('name', String(128)),
                  Column('is_private', Boolean),
                  Column('created_at', DateTime),
                  Column('member_count', Integer),
                  Column('message_count', Integer),
                  Column('first_message_at', DateTime),
                  Column('last_message_at', DateTime),
                  Column('active_users_30d', Integer),
                  Column('avg_messages_per_user', Float),
                  )

    users = Table('user_metrics', meta,
                  Column('id', Integer, primary_key=True),
                  Column('username', String(64)),
                  Column('email', String(256)),
                  Column('created_at', DateTime),
                  Column('last_active_at', DateTime),
                  Column('message_count', Integer),
                  Column('chat_count', Integer),
                  )

    messages = Table('analytics_messages', meta,
                     Column('id', Integer, primary_key=True),
                     Column('chat_id', Integer),
                     Column('user_id', Integer),
                     Column('content', Text),
                     Column('content_length', Integer),
                     Column('word_count', Integer),
                     Column('created_at', DateTime),
                     )

    chat_daily = Table('chat_daily', meta,
                       Column('date', DateTime, primary_key=True),
                       Column('chat_id', Integer, primary_key=True),
                       Column('messages', Integer),
                       Column('active_users', Integer),
                       )

    etl_state = Table('etl_state', meta,
                      Column('key', String(64), primary_key=True),
                      Column('value', String(256)),
                      )
    meta.create_all(engine)
    return {
        'chats': chats,
        'messages': messages,
        'users': users,
        'chat_daily': chat_daily,
        'etl_state': etl_state,
    }

def run_etl(dry_run: bool = False, batch_size: int = 500, incremental: bool = False, since: str = None, reset: bool = False):
    print('ETL: source=', SRC_DB, 'target=', ANALYTICS_DB, 'dry_run=', dry_run, 'batch_size=', batch_size, 'incremental=', incremental, 'since=', since, 'reset=', reset)

    prep = prepare_etl(dry_run=dry_run, batch_size=batch_size, incremental=incremental, since=since, reset=reset)
    total_messages = int(prep.get('total_messages', 0))
    if total_messages == 0:
        print('No new messages to process')
        return {
            'messages': 0,
            'chats': 0,
            'users': 0,
            'daily_rows': 0,
        }

    message_ids = prep.get('message_ids', [])
    affected_chat_ids = prep.get('affected_chat_ids', [])
    affected_user_ids = prep.get('affected_user_ids', [])
    min_dt = prep.get('min_dt')
    max_dt = prep.get('max_dt')
    new_max_id = prep.get('new_max_id')

    messages_written = 0
    if not dry_run:
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i+batch_size]
            res = process_message_batch(batch, batch_size)
            messages_written += int(res.get('messages_written', 0))

    meta_res = finalize_metadata(affected_chat_ids, affected_user_ids, new_max_id)

    daily_res = finalize_daily_rollups(affected_chat_ids, min_dt, max_dt, batch_size)

    summary = {
        'messages': messages_written,
        'chats': int(meta_res.get('chats_written', 0)),
        'users': int(meta_res.get('users_written', 0)),
        'daily_rows': int(daily_res.get('daily_rows_written', 0)),
        'min_dt': min_dt,
        'max_dt': max_dt,
    }
    print('ETL finished')
    return summary

def main():
    parser = argparse.ArgumentParser(description='ETL to analytics DB')
    parser.add_argument('--dry-run', action='store_true', help='Compute and print actions without writing to target')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size for message inserts')
    parser.add_argument('--incremental', action='store_true', help='Only process new messages since last ETL run')
    parser.add_argument('--since', type=str, default=None, help='ISO datetime lower bound for messages (e.g. 2025-01-01T00:00:00)')
    parser.add_argument('--reset', action='store_true', help='Reset ETL state (clear watermark)')
    args = parser.parse_args()
    run_etl(dry_run=args.dry_run, batch_size=args.batch_size, incremental=args.incremental, since=args.since, reset=args.reset)

def prepare_etl(dry_run: bool = False, batch_size: int = 500, incremental: bool = False, since: str = None, reset: bool = False):
    target_engine = create_engine(ANALYTICS_DB)
    tables = ensure_target_schema(target_engine)
    src_engine = create_engine(SRC_DB)
    SrcSession = sessionmaker(autocommit=False, autoflush=False, bind=src_engine)
    src_db = SrcSession()
    try:
        with target_engine.begin() as conn:
            if reset:
                conn.execute(tables['etl_state'].delete())

            last_max_id = 0
            if incremental:
                res = conn.execute(select(tables['etl_state'].c.value).where(tables['etl_state'].c.key == 'messages_max_id')).fetchone()
                last_max_id = int(res[0]) if res and res[0] else 0

            msg_query = src_db.query(models.Message).order_by(models.Message.id)
            if since:
                try:
                    since_dt = datetime.fromisoformat(since)
                    msg_query = msg_query.filter(models.Message.created_at >= since_dt)
                except Exception:
                    print('warning: could not parse --since, ignoring')
            if incremental and last_max_id:
                msg_query = msg_query.filter(models.Message.id > last_max_id)

            messages = msg_query.all()
            message_ids = [m.id for m in messages]
            if not message_ids:
                return {'total_messages': 0, 'message_ids': [], 'affected_chat_ids': [], 'affected_user_ids': [], 'min_dt': None, 'max_dt': None, 'new_max_id': None}

            new_max_id = max(message_ids)
            affected_chat_ids = list({m.chat_id for m in messages})
            affected_user_ids = list({m.user_id for m in messages})

            if not incremental and not since:
                try:
                    all_chats = src_db.query(models.Chat).all()
                    affected_chat_ids = [c.id for c in all_chats]
                    all_users = src_db.query(models.User).all()
                    affected_user_ids = [u.id for u in all_users]
                except Exception:
                    pass
            min_dt = min((m.created_at for m in messages)) if messages else None
            max_dt = max((m.created_at for m in messages)) if messages else None

            return {
                'total_messages': len(message_ids),
                'message_ids': message_ids,
                'affected_chat_ids': affected_chat_ids,
                'affected_user_ids': affected_user_ids,
                'min_dt': min_dt.isoformat() if min_dt else None,
                'max_dt': max_dt.isoformat() if max_dt else None,
                'new_max_id': int(new_max_id),
            }
    finally:
        src_db.close()


def process_message_batch(message_ids: list, batch_size: int = 500):
    if not message_ids:
        return {'messages': 0}
    target_engine = create_engine(ANALYTICS_DB)
    tables = ensure_target_schema(target_engine)
    src_engine = create_engine(SRC_DB)
    SrcSession = sessionmaker(autocommit=False, autoflush=False, bind=src_engine)
    src_db = SrcSession()
    try:
        # fetch messages by ids
        msgs = src_db.query(models.Message).filter(models.Message.id.in_(message_ids)).all()

        msg_rows = []
        for m in msgs:
            content_length = len(m.content) if m.content else 0
            word_count = len(m.content.split()) if m.content else 0
            msg_rows.append({'id': m.id, 'chat_id': m.chat_id, 'user_id': m.user_id, 'content': m.content, 'content_length': content_length, 'word_count': word_count, 'created_at': m.created_at})

        total_written = 0
        with target_engine.begin() as conn:
            target_is_postgres = target_engine.dialect.name == 'postgresql'
            if target_is_postgres:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                for i in range(0, len(msg_rows), batch_size):
                    batch = msg_rows[i:i+batch_size]
                    stmt = pg_insert(tables['messages']).values(batch)
                    update_dict = {c.name: getattr(stmt.excluded, c.name) for c in tables['messages'].columns if c.name != 'id'}
                    conn.execute(stmt.on_conflict_do_update(index_elements=['id'], set_=update_dict))
                    total_written += len(batch)
            else:
                for i in range(0, len(msg_rows), batch_size):
                    batch = msg_rows[i:i+batch_size]
                    ids = [r['id'] for r in batch]
                    conn.execute(tables['messages'].delete().where(tables['messages'].c.id.in_(ids)))
                    conn.execute(tables['messages'].insert(), batch)
                    total_written += len(batch)

        return {'messages': total_written}
    finally:
        src_db.close()


def finalize_metadata(affected_chat_ids: list, affected_user_ids: list, new_max_id: int):
    target_engine = create_engine(ANALYTICS_DB)
    tables = ensure_target_schema(target_engine)
    src_engine = create_engine(SRC_DB)
    SrcSession = sessionmaker(autocommit=False, autoflush=False, bind=src_engine)
    src_db = SrcSession()
    try:
        chat_rows = []
        for chat_id in affected_chat_ids:
            member_count = src_db.query(func.count(models.ChatMember.id)).filter(models.ChatMember.chat_id == chat_id).scalar() or 0
            message_count = src_db.query(func.count(models.Message.id)).filter(models.Message.chat_id == chat_id).scalar() or 0
            first_message = src_db.query(func.min(models.Message.created_at)).filter(models.Message.chat_id == chat_id).scalar()
            last_message = src_db.query(func.max(models.Message.created_at)).filter(models.Message.chat_id == chat_id).scalar()
            since_30d = datetime.utcnow() - timedelta(days=30)
            active_30d = src_db.query(func.count(distinct(models.Message.user_id))).filter(models.Message.chat_id == chat_id, models.Message.created_at >= since_30d).scalar() or 0
            distinct_users = src_db.query(func.count(distinct(models.Message.user_id))).filter(models.Message.chat_id == chat_id).scalar() or 0
            avg_msgs = (message_count / distinct_users) if distinct_users else 0.0
            chat_obj = src_db.query(models.Chat).filter(models.Chat.id == chat_id).first()
            chat_rows.append({'id': chat_id, 'name': chat_obj.name if chat_obj else None, 'is_private': chat_obj.is_private if chat_obj else None, 'created_at': chat_obj.created_at if chat_obj else None, 'member_count': int(member_count), 'message_count': int(message_count), 'first_message_at': first_message, 'last_message_at': last_message, 'active_users_30d': int(active_30d), 'avg_messages_per_user': float(avg_msgs)})

        user_rows = []
        for user_id in affected_user_ids:
            message_count = src_db.query(func.count(models.Message.id)).filter(models.Message.user_id == user_id).scalar() or 0
            chat_count = src_db.query(func.count(distinct(models.Message.chat_id))).filter(models.Message.user_id == user_id).scalar() or 0
            last_active = src_db.query(func.max(models.Message.created_at)).filter(models.Message.user_id == user_id).scalar()
            user_obj = src_db.query(models.User).filter(models.User.id == user_id).first()
            user_rows.append({'id': user_id, 'username': user_obj.username if user_obj else None, 'email': user_obj.email if user_obj else None, 'created_at': user_obj.created_at if user_obj else None, 'last_active_at': last_active, 'message_count': int(message_count), 'chat_count': int(chat_count)})

        with target_engine.begin() as conn:
            target_is_postgres = target_engine.dialect.name == 'postgresql'
            if target_is_postgres:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                if chat_rows:
                    stmt = pg_insert(tables['chats']).values(chat_rows)
                    update_dict = {c.name: getattr(stmt.excluded, c.name) for c in tables['chats'].columns if c.name != 'id'}
                    conn.execute(stmt.on_conflict_do_update(index_elements=['id'], set_=update_dict))
                if user_rows:
                    stmt = pg_insert(tables['users']).values(user_rows)
                    update_dict = {c.name: getattr(stmt.excluded, c.name) for c in tables['users'].columns if c.name != 'id'}
                    conn.execute(stmt.on_conflict_do_update(index_elements=['id'], set_=update_dict))
                # set watermark
                conn.execute(tables['etl_state'].delete().where(tables['etl_state'].c.key == 'messages_max_id'))
                conn.execute(tables['etl_state'].insert(), [{'key': 'messages_max_id', 'value': str(new_max_id)}])
            else:
                if chat_rows:
                    ids = [r['id'] for r in chat_rows]
                    conn.execute(tables['chats'].delete().where(tables['chats'].c.id.in_(ids)))
                    conn.execute(tables['chats'].insert(), chat_rows)
                if user_rows:
                    ids = [r['id'] for r in user_rows]
                    conn.execute(tables['users'].delete().where(tables['users'].c.id.in_(ids)))
                    conn.execute(tables['users'].insert(), user_rows)
                conn.execute(tables['etl_state'].delete().where(tables['etl_state'].c.key == 'messages_max_id'))
                conn.execute(tables['etl_state'].insert(), [{'key': 'messages_max_id', 'value': str(new_max_id)}])

        return {
            'chats': len(chat_rows),
            'users': len(user_rows),
        }
    finally:
        src_db.close()


def finalize_daily_rollups(affected_chat_ids: list, min_dt_iso: str, max_dt_iso: str, batch_size: int = 500):
    if not affected_chat_ids or not min_dt_iso or not max_dt_iso:
        return {'daily_rows': 0}
    min_date = datetime.fromisoformat(min_dt_iso).date()
    max_date = datetime.fromisoformat(max_dt_iso).date()
    target_engine = create_engine(ANALYTICS_DB)
    tables = ensure_target_schema(target_engine)
    src_engine = create_engine(SRC_DB)
    SrcSession = sessionmaker(autocommit=False, autoflush=False, bind=src_engine)
    src_db = SrcSession()
    try:
        daily_q = src_db.query(func.date(models.Message.created_at).label('d'), models.Message.chat_id,
                                func.count().label('messages'), func.count(distinct(models.Message.user_id)).label('active_users'))
        daily_q = daily_q.filter(models.Message.chat_id.in_(affected_chat_ids), models.Message.created_at >= datetime.combine(min_date, datetime.min.time()), models.Message.created_at <= datetime.combine(max_date, datetime.max.time()))
        daily_q = daily_q.group_by(func.date(models.Message.created_at), models.Message.chat_id)
        daily_rows = []
        for row in daily_q.all():
            daily_rows.append({'date': row[0], 'chat_id': row[1], 'messages': int(row[2] or 0), 'active_users': int(row[3] or 0)})

        total_daily = 0
        with target_engine.begin() as conn:
            target_is_postgres = target_engine.dialect.name == 'postgresql'
            if target_is_postgres and daily_rows:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                for i in range(0, len(daily_rows), batch_size):
                    batch = daily_rows[i:i+batch_size]
                    stmt = pg_insert(tables['chat_daily']).values(batch)
                    update_dict = {c.name: getattr(stmt.excluded, c.name) for c in tables['chat_daily'].columns}
                    conn.execute(stmt.on_conflict_do_update(index_elements=['date', 'chat_id'], set_=update_dict))
                    total_daily += len(batch)
            else:
                if daily_rows:
                    for r in daily_rows:
                        conn.execute(tables['chat_daily'].delete().where(and_(tables['chat_daily'].c.date == r['date'], tables['chat_daily'].c.chat_id == r['chat_id'])))
                    conn.execute(tables['chat_daily'].insert(), daily_rows)
                    total_daily = len(daily_rows)

        return {'daily_rows': total_daily}
    finally:
        src_db.close()

if __name__ == '__main__':
    main()