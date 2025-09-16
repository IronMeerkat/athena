from fastapi import APIRouter, Depends, Request, Body, HTTPException
from fastapi.responses import Response
from fastapi import status

from dependencies.authentication import telegram_webhook_authentication
from utils import send_celery_task



telegram_router = APIRouter(
    prefix="/api/telegram",
    dependencies=[Depends(telegram_webhook_authentication)]
)


@telegram_router.post("/")
async def telegram_webhook(data: dict = Body(...)):
    message = data.get("message") or data.get("edited_message")
    if not message:
        raise HTTPException(status_code=400, detail="Message not found")

    text = message['text']
    chat_id = message['chat']['id']

    send_celery_task("telegram_agent_task", telegram_chat_id=chat_id, text=text)

    return Response(status=status.HTTP_200_OK)
