"""Telethon client wrapper for Telegram Auto-Calendar Bot."""

import asyncio
from pathlib import Path
from typing import Optional, AsyncIterator
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    Channel,
    Chat,
    User,
    Message,
    MessageMediaPhoto,
)
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
)

from .config import Config


class TelegramClientWrapper:
    """Wrapper around Telethon client for easier use."""

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._api_id, self._api_hash = Config.load_telegram_credentials()
        self._session_path = Config.get_session_path()

    async def _get_client(self) -> TelegramClient:
        """Get or create the Telegram client."""
        if self.client is None:
            self.client = TelegramClient(
                str(self._session_path),
                self._api_id,
                self._api_hash,
            )
        return self.client

    async def connect(self) -> bool:
        """Connect to Telegram."""
        client = await self._get_client()
        await client.connect()
        return await client.is_user_authorized()

    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client:
            await self.client.disconnect()

    async def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        try:
            client = await self._get_client()
            await client.connect()
            return await client.is_user_authorized()
        except Exception:
            return False

    async def send_code(self, phone_number: str) -> str:
        """Send verification code to phone number. Returns phone_code_hash."""
        client = await self._get_client()
        await client.connect()
        result = await client.send_code_request(phone_number)
        return result.phone_code_hash

    async def sign_in_with_code(
        self, phone_number: str, code: str, phone_code_hash: str
    ) -> dict:
        """
        Sign in with verification code.
        Returns dict with 'success', 'needs_2fa', or 'error'.
        """
        client = await self._get_client()
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

    async def sign_in_with_2fa(self, password: str) -> dict:
        """Sign in with 2FA password."""
        client = await self._get_client()
        try:
            await client.sign_in(password=password)
            return {"success": True}
        except PasswordHashInvalidError:
            return {"success": False, "error": "Invalid password"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_me(self) -> Optional[dict]:
        """Get current user info."""
        client = await self._get_client()
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

    async def get_dialogs(self) -> list[dict]:
        """Get all dialogs (chats, groups, channels)."""
        client = await self._get_client()
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

            # Only include groups and channels, not private chats
            if dialog_type in ("group", "supergroup", "channel"):
                dialogs.append(
                    {
                        "id": dialog.id,
                        "name": dialog.name,
                        "type": dialog_type,
                        "unread_count": dialog.unread_count,
                    }
                )

        return dialogs

    async def get_group_info(self, chat_id: int) -> Optional[dict]:
        """Get detailed info about a group/channel."""
        client = await self._get_client()
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
                # Get full channel info for description
                full = await client(
                    __import__("telethon.tl.functions.channels", fromlist=["GetFullChannelRequest"]).GetFullChannelRequest(entity)
                )
                info["description"] = full.full_chat.about
            elif isinstance(entity, Chat):
                info["type"] = "group"

            return info
        except Exception as e:
            print(f"Error getting group info for {chat_id}: {e}")
            return None

    async def get_messages(
        self,
        chat_id: int,
        limit: int = 100,
        min_id: int = 0,
    ) -> AsyncIterator[dict]:
        """
        Get messages from a chat.
        Use min_id to get only messages newer than that ID.
        """
        client = await self._get_client()
        async for message in client.iter_messages(
            chat_id, limit=limit, min_id=min_id
        ):
            if message.text:  # Only text messages
                yield {
                    "id": message.id,
                    "chat_id": chat_id,
                    "text": message.text,
                    "date": message.date,
                    "has_photo": message.photo is not None,
                    "message_obj": message,  # Keep for downloading media
                }

    async def download_message_image(self, message: Message, chat_id: int) -> Optional[str]:
        """Download image from a message if present. Returns relative path."""
        if not message.photo:
            return None

        client = await self._get_client()
        uploads_path = Config.get_uploads_path()

        filename = f"{chat_id}_{message.id}.jpg"
        filepath = uploads_path / filename

        try:
            await client.download_media(message.photo, str(filepath))
            return f"/static/uploads/{filename}"
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None


# Singleton instance
_client_instance: Optional[TelegramClientWrapper] = None


def get_telegram_client() -> TelegramClientWrapper:
    """Get the singleton Telegram client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = TelegramClientWrapper()
    return _client_instance


async def run_with_client(coro):
    """Helper to run async code with the client."""
    client = get_telegram_client()
    try:
        await client.connect()
        return await coro
    finally:
        await client.disconnect()
