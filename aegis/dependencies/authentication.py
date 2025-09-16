from typing import Tuple

from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi import Body, Header
from sqlalchemy import select

from athena_settings import settings
from athena_models import User, db_session

token_header = Header(..., alias="X-Telegram-Bot-Api-Secret-Token")

async def telegram_webhook_authentication(req: Request, tg_token: str = token_header, data: dict = Body(...)):
    if tg_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret key")

    message = data.get("message") or data.get("edited_message")

    tg_user_id = message['from']['id']

    stmt = select(User).where(User.telegram_user_id == tg_user_id)

    async with db_session() as session:
        user = await session.execute(stmt)
        user = user.scalar()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    req.state.user = user