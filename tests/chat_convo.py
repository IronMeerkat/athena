import asyncio
import json
import uuid
from typing import Optional
import websockets

WS_BASE = "ws://localhost:8000"


async def ws_journaling_conversation(session_id: Optional[str] = None):
    if websockets is None:
        print("websockets not installed; run `pip install websockets`.\nSkipping.")
        return
    sid = session_id or str(uuid.uuid4())
    url = f"{WS_BASE}/ws/journal/{sid}"
    print("Connecting to:", url)

    async def ainput(prompt: str = "") -> str:
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: input(prompt))

    async with websockets.connect(url) as ws:
        print("Type 'quit' to end the conversation.")

        async def receiver():
            while True:
                try:
                    incoming = await ws.recv()
                except Exception as e:
                    print("Connection closed:", e)
                    break
                try:
                    obj = json.loads(incoming)
                except Exception:
                    print("<-", incoming)
                    continue
                data = obj.get("data") if isinstance(obj, dict) else None
                if isinstance(data, dict):
                    if "text" in data and data["text"]:
                        print("Athena:", data["text"])
                    elif "history_snapshot" in data:
                        msgs = data["history_snapshot"].get("messages", [])
                        if msgs:
                            last = msgs[-1]
                            if isinstance(last, dict) and last.get("role") == "assistant":
                                print("Athena:", last.get("content"))
                            else:
                                print("<- history_snapshot:", data["history_snapshot"])
                    else:
                        print("<-", obj)
                else:
                    print("<-", obj)

        recv_task = asyncio.create_task(receiver())
        try:
            while True:
                user = await ainput("You: ")
                if user.strip().lower() in {"quit", "exit"}:
                    break
                msg = {"type": "message", "user_message": user}
                await ws.send(json.dumps(msg))
            await ws.close()
        finally:
            await asyncio.sleep(0.2)
            recv_task.cancel()
            try:
                await recv_task
            except Exception:
                pass

# To run in Jupyter:
# To run in Jupyter:
# await ws_journaling_conversation()

# To run as a script:
if __name__ == "__main__":
    asyncio.run(ws_journaling_conversation())
