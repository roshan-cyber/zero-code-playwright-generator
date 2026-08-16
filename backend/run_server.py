import asyncio
import sys

if sys.platform == "win32":
    # Windows 3.8+ defaults to ProactorEventLoop, but ensure it is set before any loop creation
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)