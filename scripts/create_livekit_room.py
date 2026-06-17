#!/usr/bin/env python3
"""Create a LiveKit room using credentials from .env. No CLI needed."""

import asyncio
import sys
from pathlib import Path

# Load .env from project root (parent of scripts/)
try:
    from dotenv import load_dotenv

    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env", override=False)
except Exception:
    pass

from livekit import api


async def main() -> None:
    room_name = (sys.argv[1] if len(sys.argv) > 1 else "my-voice-room").strip()
    if not room_name:
        room_name = "my-voice-room"
    async with api.LiveKitAPI() as lk_api:
        room = await lk_api.room.create_room(api.CreateRoomRequest(name=room_name))
    print(f"Created room: {room.name} (sid={room.sid})")


if __name__ == "__main__":
    asyncio.run(main())
