import hashlib
from athena_settings import settings
from athena_celery import shared_task
from langchain_postgres import PGEngine, PGVectorStore
from langchain_postgres.v2.indexes import DistanceStrategy
from langchain_core.documents import Document
from langchain.embeddings import init_embeddings
from django.apps import apps
from typing import Any, Dict
from api.agents.telegram import telegram_agent


from api.integrations.telegram import send_telegram_message
from api.models import Chat, ChatMessage

from .notifications import send_fcm_message

from athena_logging import get_logger

logger = get_logger(__name__)


def _vec_dsn() -> str:
    base = settings.DATABASE_URL
    return f"{base}?options=-c%20search_path=rag,public"

def _vectorstore() -> PGVectorStore:
    engine = PGEngine.from_connection_string(_vec_dsn())
    emb = init_embeddings("openai:text-embedding-3-small")
    return PGVectorStore.create_sync(
        engine=engine,
        embedding_service=emb,
        table_name="docs",
        schema_name="rag",
        distance_strategy=DistanceStrategy.EUCLIDEAN,
    )

def _chunk(text: str, max_chars=1200, overlap=150):
    # trivial chunker; swap for RecursiveCharacterTextSplitter if you prefer
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+max_chars])
        i += max_chars - overlap
    return chunks

def _chunk_id(doc_pk: str, ix: int, content: str) -> str:
    # deterministic ID so re-embeds replace; short hash avoids collisions on edits
    h = hashlib.blake2s(content.encode("utf-8"), digest_size=6).hexdigest()
    return f"{doc_pk}:{ix}:{h}"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def embed_doc_task(self, doc_pk: str):
    Doc = apps.get_model("app", "Doc")
    doc = Doc.objects.select_related().get(pk=doc_pk)

    # assemble metadata from your RBAC base model
    # md = {
    #     "doc_id": str(doc.pk),
    #     "org_id": str(getattr(doc, "org_id", "")) or None,
    #     "owner_id": str(getattr(doc, "owner_id", "")) or None,
    #     "min_role": int(getattr(doc, "min_role", 0)),
    #     "title": doc.title,
    # }

    vs = _vectorstore()

    # remove any prior chunks for this doc (deterministic id prefix)
    # we don't have a 'delete by metadata' API, so compute prior-id patterns locally:
    # simplest approach: delete by known ids after re-chunk; otherwise do a small SQL where doc_id = ...
    chunks = _chunk(doc.text)
    ids = [_chunk_id(str(doc.pk), i, c) for i, c in enumerate(chunks)]

    # Proactively delete those ids to avoid duplicates on schema changes
    vs.delete(ids=ids)  # safe even if none exist

    docs = [
        Document(page_content=c) for c in chunks
    ]
    vs.add_documents(docs, ids=ids)  # embeds + inserts

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def delete_doc_task(self, doc_pk: str):
    # If you persisted chunk IDs somewhere, delete by that list.
    # Otherwise, do a cleanup by metadata with raw SQL via engine (doc_id column).
    engine = PGEngine.from_connection_string(_vec_dsn())
    with engine.connection() as conn:
        conn.execute(f'DELETE FROM rag.docs WHERE doc_id = %s', [doc_pk])

@shared_task
def example_background_task(x: int, y: int) -> int:
    """
    A trivial example task that adds two numbers together.

    This function exists solely to illustrate how to define a task.  In a
    real application you might perform I/O, long‑running computations or
    other work here.
    """
    return x + y


@shared_task(name="gateway.dispatch_push")
def dispatch_push(token: str, title: str, body: str, source: str, result: Dict[str, Any]=None) -> None:
    """
    Dispatch a push payload to Android frontends.
    """

    try:
        send_fcm_message(token, title, body, source, result)
    except Exception as e:
        logger.exception(f"Error sending FCM message, data: {token} {title} {body} from {source}")


@shared_task(name="recieved.telegram")
def recieved_telegram(chat_id: str, text: str) -> None:
    """
    Recieved a message from Telegram.
    """
    logger.debug(f"Recieved a message from Telegram: {text} in chat {chat_id}")
    chat = Chat.objects.get(id=chat_id)
    chat.messages.create(
        role=ChatMessage.ROLE_ASSISTANT,
        content=text,
    )
    chat.save(update_fields=["updated_at"])
    send_telegram_message(chat.telegram_chat_id, text)