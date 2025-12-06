import asyncio
import os
import sys
import pathlib

from temporalio.client import Client
from temporalio.worker import Worker

from temporal.workflows import ETLWorkflow
from temporal.activities import run_etl

async def main():
    temporal_addr = os.getenv("TEMPORAL_LOCAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    print(f"Connecting to Temporal at {temporal_addr} (namespace={namespace})")
    client = await Client.connect(temporal_addr, namespace=namespace)

    task_queue = os.getenv("ETL_TASK_QUEUE", "etl-task-queue")
    print(f"Starting worker for task queue {task_queue}")

    worker = Worker(client, task_queue=task_queue, workflows=[ETLWorkflow], activities=[run_etl])
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped")