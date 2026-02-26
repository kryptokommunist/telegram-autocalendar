"""Telethon client wrapper for Telegram Auto-Calendar Bot."""

import asyncio
import threading
from pathlib import Path
from typing import Optional, AsyncIterator, Callable, Any
from telethon import TelegramClient
from telethon.tl.types import (
    Channel,
    Chat,
    User,
    Message,
)
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
)

from .config import Config


class TelegramClientManager:
    """
    Manages Telethon client with a dedicated event loop in a background thread.
    This solves the 'event loop must not change after connection' error.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._api_id, self._api_hash = Config.load_telegram_credentials()
        self._session_path = Config.get_session_path()

        # Create dedicated event loop and thread
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Client will be created in the dedicated loop
        self._client: Optional[TelegramClient] = None
        self._client_lock = threading.Lock()

        self._initialized = True

    def _run_loop(self):
        """Run the event loop in the background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_coroutine(self, coro) -> Any:
        """Run a coroutine in the dedicated event loop and wait for result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=120)  # 2 minute timeout

    async def _get_client(self) -> TelegramClient:
        """Get or create the Telegram client (must be called from dedicated loop)."""
        if self._client is None:
            self._client = TelegramClient(
                str(self._session_path),
                self._api_id,
                self._api_hash,
                loop=self._loop,
            )
        return self._client

    async def _ensure_connected(self) -> TelegramClient:
        """Ensure client is connected."""
        client = await self._get_client()
        if not client.is_connected():
            await client.connect()
        return client

    # ============ Public synchronous API ============

    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        async def _check():
            try:
                client = await self._ensure_connected()
                return await client.is_user_authorized()
            except Exception as e:
                print(f"Auth check error: {e}")
                return False
        return self._run_coroutine(_check())

    def send_code(self, phone_number: str) -> str:
        """Send verification code. Returns phone_code_hash."""
        async def _send():
            client = await self._ensure_connected()
            result = await client.send_code_request(phone_number)
            return result.phone_code_hash
        return self._run_coroutine(_send())

    def sign_in_with_code(self, phone_number: str, code: str, phone_code_hash: str) -> dict:
        """Sign in with verification code."""
        async def _sign_in():
            client = await self._ensure_connected()
            try:
                await client.sign_in(
                    phone=phone_number, code=code, phone_code_hash=phone_code_hash
                )
                return {"success": True}
            except SessionPasswordNeededError:
                return {"success": False, "needs_2fa": True}
            except PhoneCodeInvalidError:
                return {"success": False, "error": "Invalid code"}
            except PhoneCodeExpiredError:
                return {"success": False, "error": "Code expired"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self._run_coroutine(_sign_in())

    def sign_in_with_2fa(self, password: str) -> dict:
        """Sign in with 2FA password."""
        async def _sign_in():
            client = await self._ensure_connected()
            try:
                await client.sign_in(password=password)
                return {"success": True}
            except PasswordHashInvalidError:
                return {"success": False, "error": "Invalid password"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return self._run_coroutine(_sign_in())

    def get_me(self) -> Optional[dict]:
        """Get current user info."""
        async def _get():
            client = await self._ensure_connected()
            me = await client.get_me()
            if me:
                return {
                    "id": me.id,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "username": me.username,
                    "phone": me.phone,
                }
            return None
        return self._run_coroutine(_get())

    def get_dialogs(self) -> list[dict]:
        """Get all dialogs (groups and channels only)."""
        async def _get():
            client = await self._ensure_connected()
            dialogs = []

            async for dialog in client.iter_dialogs():
                entity = dialog.entity
                dialog_type = "unknown"

                if isinstance(entity, Channel):
                    dialog_type = "channel" if entity.broadcast else "supergroup"
                elif isinstance(entity, Chat):
                    dialog_type = "group"
                elif isinstance(entity, User):
                    dialog_type = "user"

                if dialog_type in ("group", "supergroup", "channel"):
                    dialogs.append({
                        "id": dialog.id,
                        "name": dialog.name,
                        "type": dialog_type,
                        "unread_count": dialog.unread_count,
                    })

            return dialogs
        return self._run_coroutine(_get())

    def get_group_info(self, chat_id: int) -> Optional[dict]:
        """Get detailed info about a group/channel."""
        async def _get():
            client = await self._ensure_connected()
            try:
                entity = await client.get_entity(chat_id)
                info = {
                    "id": chat_id,
                    "name": getattr(entity, "title", None) or getattr(entity, "first_name", "Unknown"),
                    "description": None,
                    "type": "group",
                }

                if isinstance(entity, Channel):
                    info["type"] = "channel" if entity.broadcast else "supergroup"
                    from telethon.tl.functions.channels import GetFullChannelRequest
                    full = await client(GetFullChannelRequest(entity))
                    info["description"] = full.full_chat.about
                elif isinstance(entity, Chat):
                    info["type"] = "group"

                return info
            except Exception as e:
                print(f"Error getting group info for {chat_id}: {e}")
                return None
        return self._run_coroutine(_get())

    def get_messages(self, chat_id: int, limit: int = 100, min_id: int = 0) -> list[dict]:
        """Get messages from a chat."""
        async def _get():
            client = await self._ensure_connected()
            messages = []

            async for message in client.iter_messages(chat_id, limit=limit, min_id=min_id):
                if message.text:
                    messages.append({
                        "id": message.id,
                        "chat_id": chat_id,
                        "text": message.text,
                        "date": message.date,
                        "has_photo": message.photo is not None,
                        "photo": message.photo,
                    })

            return messages
        return self._run_coroutine(_get())

    def download_message_image(self, photo, chat_id: int, message_id: int) -> Optional[str]:
        """Download image from a message photo."""
        if not photo:
            return None

        async def _download():
            client = await self._ensure_connected()
            uploads_path = Config.get_uploads_path()

            filename = f"{chat_id}_{message_id}.jpg"
            filepath = uploads_path / filename

            try:
                await client.download_media(photo, str(filepath))
                return f"/static/uploads/{filename}"
            except Exception as e:
                print(f"Error downloading image: {e}")
                return None
        return self._run_coroutine(_download())


def get_telegram_client() -> TelegramClientManager:
    """Get the singleton Telegram client manager."""
    return TelegramClientManager()
