from fastapi import FastAPI, Request, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from athena_logging import get_logger

from athena_settings import settings

from views import telegram_router

logger = get_logger(__name__)

app = FastAPI()

LOCALHOST_WHITELIST = [f'http://localhost:{i}' for i in range(3000, 4000)]
CORS_WHITELIST = settings.CORS_WHITELIST + LOCALHOST_WHITELIST

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_WHITELIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=['Access-Control-Allow-Origin',
                    'Access-Control-Allow-Headers',
                    'Access-Control-Allow-Methods']
)




app.include_router(telegram_router)

