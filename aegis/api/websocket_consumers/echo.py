"""Echo WebSocket consumer.

Moved from `api/consumers.py` as part of consumer organization.
"""

from channels.generic.websocket import AsyncWebsocketConsumer


class EchoConsumer(AsyncWebsocketConsumer):
    """A simple WebSocket consumer that echoes received messages."""

    async def connect(self) -> None:
        # Accept the incoming WebSocket connection.  In a real application
        # you should perform authentication here.
        await self.accept()
        await self.send(text_data="Echo server connected. Send a message to receive it back.")

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is not None:
            await self.send(text_data=f"Echo: {text_data}")
        elif bytes_data is not None:
            await self.send(bytes_data=bytes_data)

        else:
            await self.send(text_data="acknowledged")

    async def disconnect(self, close_code: int) -> None:
        # Called when the socket closes.  Perform any cleanup here.
        pass


