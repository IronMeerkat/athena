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
        await self.send_text("Echo server connected. Send a message to receive it back.")

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is not None:
            # Echo the text back to the client.  You could also broadcast
            # the message to a group or perform other logic here.
            await self.send_text(f"Echo: {text_data}")
        elif bytes_data is not None:
            # If a binary message is received, we do nothing in this stub.
            pass

    async def disconnect(self, close_code: int) -> None:
        # Called when the socket closes.  Perform any cleanup here.
        pass


