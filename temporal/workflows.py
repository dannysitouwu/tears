from datetime import timedelta
from typing import Optional, List, Any
from temporalio import workflow
from .activities import (
    # messages
    extract_messages,
    transform_messages,
    load_messages,
    # users
    extract_users,
    transform_users,
    load_users,
    # chats
    extract_chats,
    transform_chats,
    load_chats,
    # chat members
    extract_chat_members,
    transform_chat_members,
    load_chat_members,
)

@workflow.defn
class ETLWorkflow:
    @workflow.run
    async def run(self, dry_run: bool = False, batch_size: int = 500, incremental: bool = False, since: Optional[str] = None, reset: bool = False) -> dict:
        prep = await workflow.execute_activity(
            extract_messages,
            args=[dry_run, batch_size, incremental, since, reset],
            start_to_close_timeout=timedelta(minutes=10),
        )

        total_messages = int(prep.get('total_messages', 0))
        if total_messages == 0:
            return {
                'messages': 0,
                'chats': 0,
                'users': 0,
                'daily_rows': 0,
            }

        message_ids: List[int] = prep.get('message_ids', [])
        affected_chat_ids: List[int] = prep.get('affected_chat_ids', [])
        affected_user_ids: List[int] = prep.get('affected_user_ids', [])
        min_dt_iso = prep.get('min_dt')
        max_dt_iso = prep.get('max_dt')
        new_max_id = prep.get('new_max_id')

        # messages
        transform_res = await workflow.execute_activity(
            transform_messages,
            args=[message_ids, batch_size],
            start_to_close_timeout=timedelta(minutes=30),
        )
        messages_written = int(transform_res.get('messages_written', 0))

        load_msg_res = await workflow.execute_activity(
            load_messages,
            args=[affected_chat_ids, min_dt_iso, max_dt_iso, batch_size],
            start_to_close_timeout=timedelta(minutes=15),
        )

        # users
        users_prep = await workflow.execute_activity(
            extract_users,
            args=[dry_run, incremental, since, reset],
            start_to_close_timeout=timedelta(minutes=5),
        )
        user_ids: List[int] = users_prep.get('user_ids', [])
        users_res = await workflow.execute_activity(
            transform_users,
            args=[user_ids, new_max_id],
            start_to_close_timeout=timedelta(minutes=10),
        )
        load_users_res = await workflow.execute_activity(
            load_users,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # chats
        chats_prep = await workflow.execute_activity(
            extract_chats,
            args=[dry_run, incremental, since, reset],
            start_to_close_timeout=timedelta(minutes=5),
        )
        chat_ids: List[int] = chats_prep.get('chat_ids', [])
        chats_res = await workflow.execute_activity(
            transform_chats,
            args=[chat_ids, new_max_id],
            start_to_close_timeout=timedelta(minutes=10),
        )
        load_chats_res = await workflow.execute_activity(
            load_chats,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # chat members
        cm_prep = await workflow.execute_activity(
            extract_chat_members,
            args=[dry_run],
            start_to_close_timeout=timedelta(minutes=5),
        )
        cm_ids: List[int] = cm_prep.get('chat_ids', [])
        cm_res = await workflow.execute_activity(
            transform_chat_members,
            args=[cm_ids],
            start_to_close_timeout=timedelta(minutes=10),
        )
        load_cm_res = await workflow.execute_activity(
            load_chat_members,
            start_to_close_timeout=timedelta(minutes=5),
        )

        return {
            'messages': messages_written,
            'chats': int(chats_res.get('chats_written', 0)),
            'users': int(users_res.get('users_written', 0)),
            'daily_rows': int(load_msg_res.get('daily_rows_written', 0) if isinstance(load_msg_res, dict) else 0),
            'min_dt': min_dt_iso,
            'max_dt': max_dt_iso,
        }