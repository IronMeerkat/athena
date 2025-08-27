from __future__ import annotations

import uvicorn

from athena_server.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "athena_server.server.app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
