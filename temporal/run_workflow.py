import asyncio
import uuid
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from temporalio.client import Client
from temporal.workflows import ETLWorkflow

async def main():
    temporal_addr = os.getenv("TEMPORAL_LOCAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    client = await Client.connect(temporal_addr, namespace=namespace)

    workflow_id = f"etl-workflow-{uuid.uuid4()}"
    task_queue = os.getenv("ETL_TASK_QUEUE", "etl-task-queue")

    print(f"Starting ETL workflow (id={workflow_id}) on {temporal_addr} task_queue={task_queue}")
    result = await client.execute_workflow(
        ETLWorkflow.run,
        args=[False, 500, False, None, False],
        id=workflow_id,
        task_queue=task_queue,
    )
    print(f"Workflow result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
