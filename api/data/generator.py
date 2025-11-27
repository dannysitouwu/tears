import os
import random
import argparse
import sys
import pathlib
import time
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    from backports.zoneinfo import ZoneInfo  # type: ignore
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy import select
from app import models
from app.database import SessionLocal, engine
from app.security import hash_password

fake = Faker()

DEFAULT_MIN_USERS = 0
BATCH_SIZE = 500
DEFAULT_PROGRESS_STEP = 1000
TZ = ZoneInfo('America/Costa_Rica')
START_DATE = datetime(2025, 1, 1, tzinfo=TZ)

PROGRESS_STEP = DEFAULT_PROGRESS_STEP
NUM_FORMAT = 'responsive'
NUM_THRESHOLD = 100_000


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
    # compute one hashed password and reuse to avoid problems with Argon2
    hashed_pw = hash_password("change-me")
    for i in range(to_create):
        username = f"faker_{fake.user_name()}_{random.randint(1000,9999)}"
        email = f"{username}@example.com"
        created_at = random_datetime(START_DATE, datetime.now(TZ))
        u = models.User(username=username, display_name=fake.name(), email=email, password_hash=hashed_pw, created_at=created_at)
        objs.append(u)
    created_progress = 0
    for chunk in chunked(objs, BATCH_SIZE):
        db.bulk_save_objects(chunk)
        db.commit()
        created_progress += len(chunk)
        if PROGRESS_STEP and created_progress % PROGRESS_STEP == 0:
            print(f"{fmt_num(created_progress)} users created")
    if PROGRESS_STEP and created_progress and created_progress % PROGRESS_STEP != 0:
        print(f"{fmt_num(created_progress)} users created")
    return db.query(models.User).count()


def create_chats(db: Session, count: int):
    objs = []
    created = 0
    for i in range(count):
        name = fake.sentence(nb_words=3)[:128]
        is_private = random.random() < 0.1
        created_at = random_datetime(START_DATE, datetime.now(TZ))
        objs.append(models.Chat(name=name, is_private=is_private, created_at=created_at))
        created += 1
        if PROGRESS_STEP and created % PROGRESS_STEP == 0:
            print(f"{fmt_num(created)} chats created")
    for chunk in chunked(objs, BATCH_SIZE):
        db.bulk_save_objects(chunk)
        db.commit()
    # final progress if needed
    if PROGRESS_STEP and created and created % PROGRESS_STEP != 0:
        print(f"{fmt_num(created)} chats created")
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
        joined_at = random_datetime(START_DATE, datetime.now(TZ))
        objs.append(models.ChatMember(chat_id=chat_id, user_id=user_id, role=role, joined_at=joined_at))
        created += 1
        if PROGRESS_STEP and created % PROGRESS_STEP == 0:
            print(f"{fmt_num(created)} chat-members created")
        if len(objs) >= BATCH_SIZE:
            db.bulk_save_objects(objs)
            db.commit()
            objs = []
    if objs:
        db.bulk_save_objects(objs)
        db.commit()
    if PROGRESS_STEP and created and created % PROGRESS_STEP != 0:
        print(f"{fmt_num(created)} chat-members created")
    return db.query(models.ChatMember).count()


def create_messages(db: Session, target_count: int):
    chat_ids = [c[0] for c in db.query(models.Chat.id).all()]
    member_rows = db.query(models.ChatMember.chat_id, models.ChatMember.user_id).all()
    if not chat_ids or not member_rows:
        return 0
    pair_list = [(r[0], r[1]) for r in member_rows]
    created = 0
    objs = []
    while created < target_count:
        chat_id, user_id = random.choice(pair_list)
        content = fake.paragraph(nb_sentences=2)
        created_at = random_datetime(START_DATE, datetime.now(TZ))
        objs.append(models.Message(chat_id=chat_id, user_id=user_id, content=content, created_at=created_at))
        created += 1
        if PROGRESS_STEP and created % PROGRESS_STEP == 0:
            print(f"{fmt_num(created)} messages created")
        if len(objs) >= BATCH_SIZE:
            db.bulk_save_objects(objs)
            db.commit()
            objs = []
    if objs:
        db.bulk_save_objects(objs)
        db.commit()
    if PROGRESS_STEP and created and created % PROGRESS_STEP != 0:
        print(f"{fmt_num(created)} messages created")
    return db.query(models.Message).count()


def fmt_exact(n: int) -> str:
    return f"{n:,}"


def fmt_num(n: int) -> str:
    mode = (NUM_FORMAT or 'responsive').lower()
    if mode == 'comma':
        return fmt_exact(n)
    if mode == 'compact':
        if n < 1000:
            return str(n)
        if n % 1000 == 0:
            return f"{n // 1000}k"
        v = n / 1000
        s = f"{v:.3f}".rstrip('0').rstrip('.')
        return f"{s}k"
    # responsive
    if n < 1000:
        return str(n)
    if n < NUM_THRESHOLD:
        if n % 1000 == 0:
            return f"{n // 1000}k"
        v = n / 1000
        s = f"{v:.3f}".rstrip('0').rstrip('.')
        return f"{s}k"
    return fmt_exact(n)


def random_datetime(start: datetime, end: datetime) -> datetime:
    delta = end - start
    if delta.total_seconds() <= 0:
        return start
    rnd = random.random()
    return start + timedelta(seconds=int(rnd * delta.total_seconds()))


def main():
    global BATCH_SIZE, PROGRESS_STEP
    parser = argparse.ArgumentParser(description='Populate DB with fake chats/members/messages')
    parser.add_argument('--chats', type=int, default=0, help='number of chats to create')
    parser.add_argument('--members', type=int, default=0, help='number of chat members to create')
    parser.add_argument('--messages', type=int, default=0, help='number of messages to create')
    parser.add_argument('--min-users', type=int, default=DEFAULT_MIN_USERS,
                        help='Ensure at least this many users exist (will create simple placeholder users if needed)')
    parser.add_argument('--seed', type=int, default=None, help='random seed for reproducible data')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help='batch size for bulk inserts')
    parser.add_argument('--progress-step', type=int, default=DEFAULT_PROGRESS_STEP, help='print progress every N items')
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
        fake.seed_instance(args.seed)
    BATCH_SIZE = args.batch_size
    PROGRESS_STEP = args.progress_step

    print('Starting faker...')
    db = SessionLocal()
    start_time = time.time()
    try:
        # before counts
        users_before = db.query(models.User).count()
        chats_before = db.query(models.Chat).count()
        members_before = db.query(models.ChatMember).count()
        messages_before = db.query(models.Message).count()

        if args.min_users and args.min_users > 0:
            ensure_users(db, args.min_users)

        if args.chats > 0:
            create_chats(db, args.chats)
        if args.members > 0:
            create_chat_members(db, args.members)
        if args.messages > 0:
            create_messages(db, args.messages)

        # after counts
        users_after = db.query(models.User).count()
        chats_after = db.query(models.Chat).count()
        members_after = db.query(models.ChatMember).count()
        messages_after = db.query(models.Message).count()
        duration = time.time() - start_time

        # summary
        print('\nSummary:')
        print(f"  users_before: {fmt_num(users_before)}")
        print(f"  users_after:  {fmt_num(users_after)}")
        print(f"  chats_before: {fmt_num(chats_before)}")
        print(f"  chats_after:  {fmt_num(chats_after)}")
        print(f"  members_before: {fmt_num(members_before)}")
        print(f"  members_after:  {fmt_num(members_after)}")
        print(f"  messages_before: {fmt_num(messages_before)}")
        print(f"  messages_after:  {fmt_num(messages_after)}")
        print(f"  duration: {int(duration)}s")
    finally:
        db.close()


if __name__ == '__main__':
    main()
