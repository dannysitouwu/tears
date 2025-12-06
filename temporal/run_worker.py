import asyncio
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
try:
    from dotenv import load_dotenv
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")
except Exception:
    repo_root = pathlib.Path(__file__).resolve().parents[1]

from temporalio.client import Client
from temporalio.worker import Worker

from temporal.workflows import ETLWorkflow
from temporal.activities import (
    run_etl,
    prepare_etl,
    extract_messages,
    transform_messages,
    load_messages,
    extract_users,
    transform_users,
    load_users,
    extract_chats,
    transform_chats,
    load_chats,
    extract_chat_members,
    transform_chat_members,
    load_chat_members,
)

async def main():
    temporal_addr = os.getenv("TEMPORAL_LOCAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    if not os.getenv("SRC_DATABASE_URL") and not os.getenv("DATABASE_URL"):
        print(
            "Warning: `SRC_DATABASE_URL` or `DATABASE_URL` is not set. "
            "Importing the ETL module will fail. Create a `.env` with these "
            "values or export them before running the worker."
        )
    client = await Client.connect(temporal_addr, namespace=namespace)

    task_queue = os.getenv("ETL_TASK_QUEUE", "etl-task-queue")
    print(f"Worker connecting to {temporal_addr}, task queue {task_queue}")

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[ETLWorkflow],
        activities=[
            run_etl,
            # activities
            prepare_etl,
            extract_messages,
            transform_messages,
            load_messages,
            extract_users,
            transform_users,
            load_users,
            extract_chats,
            transform_chats,
            load_chats,
            extract_chat_members,
            transform_chat_members,
            load_chat_members,
        ],
    )
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped")