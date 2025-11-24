import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models
from app.database import SessionLocal

SRC_DB = os.getenv('SRC_DATABASE_URL', os.getenv('DATABASE_URL'))
ANALYTICS_DB = os.getenv('ANALYTICS_DATABASE_URL', os.getenv('ANALYTICS_DB_URL', 'sqlite:///./analytics.db'))

if not SRC_DB:
    raise SystemExit("SRC_DATABASE_URL or DATABASE_URL must be set to run the ETL — refusing to run with default sqlite. Export SRC_DATABASE_URL and try again.")


def ensure_target_schema(engine):
    meta = MetaData()
    chats = Table('analytics_chats', meta,
                  Column('id', Integer, primary_key=True),
                  Column('name', String(128)),
                  Column('is_private', Boolean),
                  Column('created_at', DateTime),
                  Column('member_count', Integer),
                  Column('message_count', Integer),
                  )
    messages = Table('analytics_messages', meta,
                     Column('id', Integer, primary_key=True),
                     Column('chat_id', Integer),
                     Column('user_id', Integer),
                     Column('content', Text),
                     Column('created_at', DateTime),
                     )
    meta.create_all(engine)
    return chats, messages


def run_etl():
    print('ETL: source=', SRC_DB, 'target=', ANALYTICS_DB)
    target_engine = create_engine(ANALYTICS_DB)
    chats_table, messages_table = ensure_target_schema(target_engine)

    src_db = SessionLocal()
    try:
        # aggregate chat stats
        chat_stats = src_db.query(
            models.Chat.id,
            models.Chat.name,
            models.Chat.is_private,
            models.Chat.created_at,
            func.count(models.ChatMember.id).label('member_count'),
            func.count(models.Message.id).label('message_count')
        ).outerjoin(models.ChatMember, models.Chat.id == models.ChatMember.chat_id)
        chat_stats = chat_stats.outerjoin(models.Message, models.Chat.id == models.Message.chat_id)
        chat_stats = chat_stats.group_by(models.Chat.id).all()

        # write to target
        with target_engine.begin() as conn:
            # clear existing analytics tables
            conn.execute(messages_table.delete())
            conn.execute(chats_table.delete())

            # insert chats
            chat_rows = []
            for row in chat_stats:
                chat_rows.append({'id': row[0], 'name': row[1], 'is_private': row[2], 'created_at': row[3], 'member_count': row[4], 'message_count': row[5]})
            if chat_rows:
                conn.execute(chats_table.insert(), chat_rows)

            # copy messages
            messages = src_db.query(models.Message).all()
            msg_rows = []
            for m in messages:
                msg_rows.append({'id': m.id, 'chat_id': m.chat_id, 'user_id': m.user_id, 'content': m.content, 'created_at': m.created_at})
            if msg_rows:
                conn.execute(messages_table.insert(), msg_rows)

    finally:
        src_db.close()
    print('ETL finished')


if __name__ == '__main__':
    run_etl()
