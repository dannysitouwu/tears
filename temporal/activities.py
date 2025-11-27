import sys
import asyncio
from typing import Optional
from temporalio import activity

@activity.defn
async def run_etl_activity(dry_run: bool = False, batch_size: int = 500, incremental: bool = False, since: Optional[str] = None, reset: bool = False):
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    run_etl = getattr(etl_mod, "run_etl")
    return await asyncio.to_thread(run_etl, dry_run, batch_size, incremental, since, reset)