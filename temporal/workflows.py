from datetime import timedelta
from typing import Optional
from temporalio import workflow
from .activities import run_etl_activity

@workflow.defn
class ETLWorkflow:
    @workflow.run
    async def run(self, dry_run: bool = False, batch_size: int = 500, incremental: bool = False, since: Optional[str] = None, reset: bool = False):
        result = await workflow.execute_activity(
            run_etl_activity,
            args=[dry_run, batch_size, incremental, since, reset],
            start_to_close_timeout=timedelta(minutes=30),
        )
        return result
