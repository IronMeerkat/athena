import asyncio
from utils import BaseState, store, vectorstore
import time
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from athena_logging import get_logger
from utils.memory_engine import store_conversation_async

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
    conversation_pairs = []

    # First pass: Archive to vector store and extract conversation pairs
    messages = state.interesting_messages
    for idx, msg in enumerate(messages):
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

        # Extract conversation pairs for memory storage
        if isinstance(msg, HumanMessage):
            # Look for the next AI message to form a conversation pair
            for next_idx in range(idx + 1, len(messages)):
                next_msg = messages[next_idx]
                if isinstance(next_msg, AIMessage):
                    conversation_pairs.append({
                        "user_message": msg.content,
                        "assistant_message": next_msg.content,
                        "user_id": str(state.session_id),
                        "timestamp": timestamp_ms
                    })
                    break

    # Store to vector store (existing functionality)
    vectorstore.add_texts(texts, metadatas=metadatas)

    # Batch store conversations to memory (NEW: replaces real-time storage)
    if conversation_pairs:
        logger.info(f"Storing {len(conversation_pairs)} conversation pairs to memory during archiving")
        try:
            # Process all conversations in parallel using thread pool (much more efficient)
            tasks = []
            for pair in conversation_pairs:
                task = store_conversation_async(
                    pair["user_message"],
                    pair["assistant_message"],
                    pair["user_id"]
                )
                tasks.append(task)

            # Execute all memory storage operations in parallel
            await asyncio.gather(*tasks)
            logger.info(f"Successfully batch-stored {len(conversation_pairs)} conversations to memory")
        except Exception as e:
            logger.exception(f"Failed to batch store conversations to memory: {e}")

    logger.info(f"Archived {len(texts)} messages and {len(conversation_pairs)} conversations for session {state.session_id}")

