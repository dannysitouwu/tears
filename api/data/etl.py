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
    target_engine = create_engine(ANALYTICS_DB)
    tables = ensure_target_schema(target_engine)

    # create a dedicated engine/session for source
    src_engine = create_engine(SRC_DB)
    SrcSession = sessionmaker(autocommit=False, autoflush=False, bind=src_engine)
    src_db = SrcSession()
    try:
        def fmt_exact(n: int) -> str:
            return f"{n:,}"

        def fmt_num(n: int) -> str:
            if n < 1000:
                return str(n)
            if n < 100_000:
                if n % 1000 == 0:
                    return f"{n // 1000}k"
                v = n / 1000
                s = f"{v:.3f}".rstrip('0').rstrip('.')
                return f"{s}k"
            return fmt_exact(n)

        PROGRESS_STEP = 1000

        target_is_postgres = target_engine.dialect.name == 'postgresql'

        def get_watermark(conn):
            res = conn.execute(select(tables['etl_state'].c.value).where(tables['etl_state'].c.key == 'messages_max_id')).fetchone()
            return int(res[0]) if res and res[0] else 0

        def set_watermark(conn, val: int):
            conn.execute(tables['etl_state'].delete().where(tables['etl_state'].c.key == 'messages_max_id'))
            conn.execute(tables['etl_state'].insert(), [{'key': 'messages_max_id', 'value': str(val)}])

        with target_engine.begin() as conn:
            if reset:
                print('Resetting ETL state')
                conn.execute(tables['etl_state'].delete())

            last_max_id = 0
            if incremental:
                last_max_id = get_watermark(conn)

            msg_query = src_db.query(models.Message).order_by(models.Message.id)
            if since:
                try:
                    since_dt = datetime.fromisoformat(since)
                    msg_query = msg_query.filter(models.Message.created_at >= since_dt)
                except Exception:
                    print('warning: could not parse --since, ignoring')
            if incremental and last_max_id:
                msg_query = msg_query.filter(models.Message.id > last_max_id)

            messages_to_process = msg_query.all()
            if not messages_to_process:
                print('No new messages to process')
                return

            new_max_id = max(m.id for m in messages_to_process)

            affected_chat_ids = list({m.chat_id for m in messages_to_process})
            affected_user_ids = list({m.user_id for m in messages_to_process})

            print(f'Found {len(messages_to_process)} messages for {len(affected_chat_ids)} chats and {len(affected_user_ids)} users')

            chat_rows = []
            since_30d = datetime.utcnow() - timedelta(days=30)
            for chat_id in affected_chat_ids:
                member_count = src_db.query(func.count(models.ChatMember.id)).filter(models.ChatMember.chat_id == chat_id).scalar() or 0
                message_count = src_db.query(func.count(models.Message.id)).filter(models.Message.chat_id == chat_id).scalar() or 0
                first_message = src_db.query(func.min(models.Message.created_at)).filter(models.Message.chat_id == chat_id).scalar()
                last_message = src_db.query(func.max(models.Message.created_at)).filter(models.Message.chat_id == chat_id).scalar()
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

            msg_rows_all = []
            for m in messages_to_process:
                content_length = len(m.content) if m.content else 0
                word_count = len(m.content.split()) if m.content else 0
                msg_rows_all.append({'id': m.id, 'chat_id': m.chat_id, 'user_id': m.user_id, 'content': m.content, 'content_length': content_length, 'word_count': word_count, 'created_at': m.created_at})

            print(f"Prepared {fmt_num(len(msg_rows_all))} messages for insert")

            # summary of actions
            print(f"Will write {len(chat_rows)} chat rows, {len(user_rows)} user rows, {len(msg_rows_all)} messages (batches of {batch_size})")

            if dry_run:
                print('Dry-run mode: no changes will be written to target')
            else:
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

                    if msg_rows_all:
                        total_written = 0
                        for i in range(0, len(msg_rows_all), batch_size):
                            batch = msg_rows_all[i:i+batch_size]
                            stmt = pg_insert(tables['messages']).values(batch)
                            update_dict = {c.name: getattr(stmt.excluded, c.name) for c in tables['messages'].columns if c.name != 'id'}
                            conn.execute(stmt.on_conflict_do_update(index_elements=['id'], set_=update_dict))
                            total_written += len(batch)
                            if PROGRESS_STEP and total_written % PROGRESS_STEP == 0:
                                print(f"{fmt_num(total_written)} messages written")
                        if PROGRESS_STEP and total_written and total_written % PROGRESS_STEP != 0:
                            print(f"{fmt_num(total_written)} messages written")
                else:
                    if chat_rows:
                        ids = [r['id'] for r in chat_rows]
                        conn.execute(tables['chats'].delete().where(tables['chats'].c.id.in_(ids)))
                        conn.execute(tables['chats'].insert(), chat_rows)

                    if user_rows:
                        ids = [r['id'] for r in user_rows]
                        conn.execute(tables['users'].delete().where(tables['users'].c.id.in_(ids)))
                        conn.execute(tables['users'].insert(), user_rows)

                    total_written = 0
                    for i in range(0, len(msg_rows_all), batch_size):
                        batch = msg_rows_all[i:i+batch_size]
                        ids = [r['id'] for r in batch]
                        conn.execute(tables['messages'].delete().where(tables['messages'].c.id.in_(ids)))
                        conn.execute(tables['messages'].insert(), batch)
                        total_written += len(batch)
                        if PROGRESS_STEP and total_written % PROGRESS_STEP == 0:
                            print(f"{fmt_num(total_written)} messages written")
                    if PROGRESS_STEP and total_written and total_written % PROGRESS_STEP != 0:
                        print(f"{fmt_num(total_written)} messages written")

                set_watermark(conn, new_max_id)

            min_dt = min((m['created_at'] for m in msg_rows_all)) if msg_rows_all else None
            max_dt = max((m['created_at'] for m in msg_rows_all)) if msg_rows_all else None
            if min_dt and max_dt and affected_chat_ids:
                min_date = min_dt.date()
                max_date = max_dt.date()
                daily_q = src_db.query(func.date(models.Message.created_at).label('d'), models.Message.chat_id,
                                        func.count().label('messages'), func.count(distinct(models.Message.user_id)).label('active_users'))
                daily_q = daily_q.filter(models.Message.chat_id.in_(affected_chat_ids), models.Message.created_at >= datetime.combine(min_date, datetime.min.time()), models.Message.created_at <= datetime.combine(max_date, datetime.max.time()))
                daily_q = daily_q.group_by(func.date(models.Message.created_at), models.Message.chat_id)
                daily_rows = []
                for row in daily_q.all():
                    daily_rows.append({'date': row[0], 'chat_id': row[1], 'messages': int(row[2] or 0), 'active_users': int(row[3] or 0)})

                print(f"Prepared {fmt_num(len(daily_rows))} daily rollup rows for {len(affected_chat_ids)} chats")

                if not dry_run:
                    if target_is_postgres and daily_rows:
                        from sqlalchemy.dialects.postgresql import insert as pg_insert
                        total_daily = 0
                        for i in range(0, len(daily_rows), batch_size):
                            batch = daily_rows[i:i+batch_size]
                            stmt = pg_insert(tables['chat_daily']).values(batch)
                            update_dict = {c.name: getattr(stmt.excluded, c.name) for c in tables['chat_daily'].columns}
                            conn.execute(stmt.on_conflict_do_update(index_elements=['date', 'chat_id'], set_=update_dict))
                            total_daily += len(batch)
                        print(f"Wrote {fmt_num(total_daily)} daily rows")
                    else:
                        if daily_rows:
                            for r in daily_rows:
                                conn.execute(tables['chat_daily'].delete().where(and_(tables['chat_daily'].c.date == r['date'], tables['chat_daily'].c.chat_id == r['chat_id'])))
                            conn.execute(tables['chat_daily'].insert(), daily_rows)
                            print(f"Wrote {fmt_num(len(daily_rows))} daily rows")

    finally:
        src_db.close()
    print('ETL finished')

def main():
    parser = argparse.ArgumentParser(description='ETL to analytics DB')
    parser.add_argument('--dry-run', action='store_true', help='Compute and print actions without writing to target')
    parser.add_argument('--batch-size', type=int, default=500, help='Batch size for message inserts')
    parser.add_argument('--incremental', action='store_true', help='Only process new messages since last ETL run')
    parser.add_argument('--since', type=str, default=None, help='ISO datetime lower bound for messages (e.g. 2025-01-01T00:00:00)')
    parser.add_argument('--reset', action='store_true', help='Reset ETL state (clear watermark)')
    args = parser.parse_args()
    run_etl(dry_run=args.dry_run, batch_size=args.batch_size, incremental=args.incremental, since=args.since, reset=args.reset)

if __name__ == '__main__':
    main()