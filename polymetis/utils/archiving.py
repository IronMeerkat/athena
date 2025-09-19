import asyncio
from utils import BaseState, store, vectorstore
import time
from langchain_core.messages import BaseMessage
from athena_logging import get_logger

logger = get_logger(__name__)

async def should_archive(message: BaseMessage, namespace: str):

    if len(message.content) < 140:
        return False

    condition_1 = store.asearch(namespace,
        filter={"text": message.content},
        limit=1)

    condition_2 = store.asearch(namespace,
        query=message.content,
        filter={"role": message.type},  # Only compare with same message type
        limit=1)  # Get top 3 similar messages to check for redundancy

    return not any(await asyncio.gather(condition_1, condition_2))



async def archive_thread(state: BaseState, namespace: str= 'global'):
    texts = []
    metadatas = []
    for idx, msg in enumerate(state.interesting_messages):
        if not await should_archive(msg, namespace):
            continue
        timestamp_ms = int(time.time() * 1000)
        metadata = {
            "agent": namespace,
            "role": msg.type,
            "session_id": state.session_id,
            "ts": timestamp_ms,
        }
        await store.aput(
            namespace=namespace,
            key=f"{namespace}:{state.session_id}:{timestamp_ms}:{idx}",
            value={**metadata, "text": msg.content}
        )
        texts.append(msg.content)
        metadatas.append(metadata)
    vectorstore.add_texts(texts, metadatas=metadatas)
    logger.info(f"Archived {len(texts)} messages for session {state.session_id}")

