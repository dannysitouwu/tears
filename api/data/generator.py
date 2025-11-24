import os
import random
import argparse
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy import select
from app import models
from app.database import SessionLocal, engine
from app.security import hash_password

fake = Faker()

DEFAULT_MIN_USERS = 100
BATCH_SIZE = 500


def chunked(iterable, size):
    it = iter(iterable)
    while True:
        chunk = []
        try:
            for _ in range(size):
                chunk.append(next(it))
        except StopIteration:
            if chunk:
                yield chunk
            break
        yield chunk


def ensure_users(db: Session, min_users: int):
    existing = db.query(models.User).count()
    created = 0
    if existing >= min_users:
        return existing
    to_create = min_users - existing
    objs = []
    for i in range(to_create):
        username = f"faker_{fake.user_name()}_{random.randint(1000,9999)}"
        email = f"{username}@example.com"
        pw = hash_password("change-me")
        u = models.User(username=username, display_name=fake.name(), email=email, password_hash=pw)
        objs.append(u)
    for chunk in chunked(objs, BATCH_SIZE):
        db.bulk_save_objects(chunk)
        db.commit()
    return db.query(models.User).count()


def create_chats(db: Session, count: int):
    objs = []
    for i in range(count):
        name = fake.sentence(nb_words=3)[:128]
        is_private = random.random() < 0.1
        objs.append(models.Chat(name=name, is_private=is_private))
    for chunk in chunked(objs, BATCH_SIZE):
        db.bulk_save_objects(chunk)
        db.commit()
    return db.query(models.Chat).count()


def create_chat_members(db: Session, target_count: int):
    chat_ids = [c[0] for c in db.query(models.Chat.id).all()]
    user_ids = [u[0] for u in db.query(models.User.id).all()]
    if not chat_ids or not user_ids:
        return 0
    created = 0
    objs = []
    seen = set()
    while created < target_count:
        chat_id = random.choice(chat_ids)
        user_id = random.choice(user_ids)
        key = (chat_id, user_id)
        if key in seen:
            continue
        seen.add(key)
        role = 'member'
        # small chance of owner
        if random.random() < 0.01:
            role = 'owner'
        objs.append(models.ChatMember(chat_id=chat_id, user_id=user_id, role=role))
        created += 1
        if len(objs) >= BATCH_SIZE:
            db.bulk_save_objects(objs)
            db.commit()
            objs = []
    if objs:
        db.bulk_save_objects(objs)
        db.commit()
    return db.query(models.ChatMember).count()


def create_messages(db: Session, target_count: int):
    chat_ids = [c[0] for c in db.query(models.Chat.id).all()]
    # We'll try to pick senders from chat_members to keep consistency
    member_rows = db.query(models.ChatMember.chat_id, models.ChatMember.user_id).all()
    if not chat_ids or not member_rows:
        return 0
    pair_list = [(r[0], r[1]) for r in member_rows]
    created = 0
    objs = []
    while created < target_count:
        chat_id, user_id = random.choice(pair_list)
        content = fake.paragraph(nb_sentences=2)
        objs.append(models.Message(chat_id=chat_id, user_id=user_id, content=content))
        created += 1
        if len(objs) >= BATCH_SIZE:
            db.bulk_save_objects(objs)
            db.commit()
            objs = []
    if objs:
        db.bulk_save_objects(objs)
        db.commit()
    return db.query(models.Message).count()


def main():
    parser = argparse.ArgumentParser(description='Populate DB with fake chats/members/messages')
    parser.add_argument('--chats', type=int, default=5000)
    parser.add_argument('--members', type=int, default=5000)
    parser.add_argument('--messages', type=int, default=5000)
    parser.add_argument('--min-users', type=int, default=DEFAULT_MIN_USERS,
                        help='Ensure at least this many users exist (will create simple placeholder users if needed)')
    args = parser.parse_args()

    print('Starting faker populate...')
    db = SessionLocal()
    try:
        ucount = ensure_users(db, args.min_users)
        print(f'Users in DB: {ucount}')
        ccount_before = db.query(models.Chat).count()
        print(f'Chats before: {ccount_before}')
        create_chats(db, args.chats)
        print(f'Chats after: {db.query(models.Chat).count()}')
        create_chat_members(db, args.members)
        print(f'Chat members after: {db.query(models.ChatMember).count()}')
        create_messages(db, args.messages)
        print(f'Messages after: {db.query(models.Message).count()}')
        print('Done')
    finally:
        db.close()


if __name__ == '__main__':
    main()
