import sys
import asyncio
from typing import Optional, List, Any
from temporalio import activity

@activity.defn
async def run_etl(dry_run: bool = False, batch_size: int = 1000, incremental: bool = False, since: Optional[str] = None, reset: bool = False) -> Any:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    run_etl = getattr(etl_mod, "run_etl")
    return await asyncio.to_thread(run_etl, dry_run, batch_size, incremental, since, reset)

@activity.defn
async def prepare_etl(dry_run: bool = False, batch_size: int = 1000, incremental: bool = False, since: Optional[str] = None, reset: bool = False) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    prepare = getattr(etl_mod, "prepare_etl")
    return await asyncio.to_thread(prepare, dry_run, batch_size, incremental, since, reset)

@activity.defn
async def extract_messages(dry_run: bool = False, batch_size: int = 1000, incremental: bool = False, since: Optional[str] = None, reset: bool = False) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    prepare = getattr(etl_mod, "prepare_etl")
    return await asyncio.to_thread(prepare, dry_run, batch_size, incremental, since, reset)

@activity.defn
async def transform_messages(message_ids: List[int], batch_size: int = 1000) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    proc = getattr(etl_mod, "process_message_batch")

    def run_all():
        total = 0
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i+batch_size]
            res = proc(batch, batch_size)
            total += int(res.get('messages_written', 0))
        return {'messages_written': total}

    return await asyncio.to_thread(run_all)

@activity.defn
async def extract_users(dry_run: bool = False, incremental: bool = False, since: Optional[str] = None, reset: bool = False) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    prep = getattr(etl_mod, "prepare_etl")
    res = await asyncio.to_thread(prep, dry_run, 0, incremental, since, reset)
    return {'user_ids': res.get('affected_user_ids', []), 'new_max_id': res.get('new_max_id')}


@activity.defn
async def transform_users(user_ids: List[int], new_max_id: int = None) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    fin = getattr(etl_mod, "finalize_metadata")
    return await asyncio.to_thread(fin, [], user_ids, new_max_id)


@activity.defn
async def load_users() -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    ANALYTICS_DB = getattr(etl_mod, 'ANALYTICS_DB')
    ensure = getattr(etl_mod, 'ensure_target_schema')
    from sqlalchemy import create_engine, select
    engine = create_engine(ANALYTICS_DB)
    tables = ensure(engine)
    with engine.connect() as conn:
        res = conn.execute(select(tables['users'].c.id)).fetchall()
        return {'analytics_users_count': len(res)}


@activity.defn
async def extract_chats(dry_run: bool = False, incremental: bool = False, since: Optional[str] = None, reset: bool = False) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    prep = getattr(etl_mod, "prepare_etl")
    res = await asyncio.to_thread(prep, dry_run, 0, incremental, since, reset)
    return {'chat_ids': res.get('affected_chat_ids', []), 'new_max_id': res.get('new_max_id')}


@activity.defn
async def transform_chats(chat_ids: List[int], new_max_id: int = None) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    fin = getattr(etl_mod, "finalize_metadata")
    return await asyncio.to_thread(fin, chat_ids, [], new_max_id)


@activity.defn
async def load_chats() -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    ANALYTICS_DB = getattr(etl_mod, 'ANALYTICS_DB')
    ensure = getattr(etl_mod, 'ensure_target_schema')
    from sqlalchemy import create_engine, select
    engine = create_engine(ANALYTICS_DB)
    tables = ensure(engine)
    with engine.connect() as conn:
        res = conn.execute(select(tables['chats'].c.id)).fetchall()
        return {'analytics_chats_count': len(res)}


@activity.defn
async def extract_chat_members(dry_run: bool = False) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    prep = getattr(etl_mod, "prepare_etl")
    res = await asyncio.to_thread(prep, dry_run, 0, False, None, False)
    return {'chat_ids': res.get('affected_chat_ids', [])}


@activity.defn
async def transform_chat_members(chat_ids: List[int]) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    fin = getattr(etl_mod, "finalize_metadata")
    return await asyncio.to_thread(fin, chat_ids, [], None)


@activity.defn
async def load_chat_members() -> dict:
    return {'status': 'ok'}


@activity.defn
async def load_messages(affected_chat_ids: List[int], min_dt_iso: str, max_dt_iso: str, batch_size: int = 1000) -> dict:
    from importlib import import_module
    etl_mod = import_module("api.data.etl")
    fin = getattr(etl_mod, "finalize_daily_rollups")
    return await asyncio.to_thread(fin, affected_chat_ids, min_dt_iso, max_dt_iso, batch_size)