"""Configuration management for Telegram Auto-Calendar Bot."""

import os
from pathlib import Path


class Config:
    """Application configuration."""

    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    SECRETS_FILE = BASE_DIR / ".secrets"
    SESSION_DIR = BASE_DIR / "session"
    UPLOADS_DIR = BASE_DIR / "src" / "web" / "static" / "uploads"

    # Telegram API credentials (loaded from .secrets file)
    TELEGRAM_API_ID: int = None
    TELEGRAM_API_HASH: str = None

    # MySQL configuration
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "telegram_events_pass")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "telegram_events")

    # GenAI Proxy configuration
    GENAI_PROXY_URL = os.getenv(
        "GENAI_PROXY_URL", "http://host.docker.internal:9988/anthropic/v1/messages"
    )
    GENAI_API_KEY = os.getenv(
        "GENAI_API_KEY", "sk-aB1cD2eF3gH4jK5lM6nP7qR8sT9uV0wX1yZ2bC3nM4pK5sL6"
    )
    GENAI_MODEL = os.getenv("GENAI_MODEL", "anthropic--claude-4.5-opus")

    # Session file path
    SESSION_NAME = "telegram_session"

    @classmethod
    def load_telegram_credentials(cls) -> tuple[int, str]:
        """Load Telegram API credentials from .secrets file."""
        if cls.TELEGRAM_API_ID and cls.TELEGRAM_API_HASH:
            return cls.TELEGRAM_API_ID, cls.TELEGRAM_API_HASH

        secrets_path = cls.SECRETS_FILE
        if not secrets_path.exists():
            raise FileNotFoundError(f"Secrets file not found: {secrets_path}")

        content = secrets_path.read_text()
        lines = content.strip().split("\n")

        api_id = None
        api_hash = None

        for i, line in enumerate(lines):
            if "api_id" in line.lower():
                # Next line contains the value
                if i + 1 < len(lines):
                    api_id = int(lines[i + 1].strip())
            elif "api_hash" in line.lower():
                if i + 1 < len(lines):
                    api_hash = lines[i + 1].strip()

        if not api_id or not api_hash:
            raise ValueError("Could not parse API credentials from .secrets file")

        cls.TELEGRAM_API_ID = api_id
        cls.TELEGRAM_API_HASH = api_hash

        return api_id, api_hash

    @classmethod
    def get_session_path(cls) -> Path:
        """Get the path for Telethon session file."""
        cls.SESSION_DIR.mkdir(parents=True, exist_ok=True)
        return cls.SESSION_DIR / cls.SESSION_NAME

    @classmethod
    def get_uploads_path(cls) -> Path:
        """Get the path for uploaded images."""
        cls.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        return cls.UPLOADS_DIR

    @classmethod
    def get_mysql_config(cls) -> dict:
        """Get MySQL connection configuration."""
        return {
            "host": cls.MYSQL_HOST,
            "user": cls.MYSQL_USER,
            "password": cls.MYSQL_PASSWORD,
            "database": cls.MYSQL_DATABASE,
        }
