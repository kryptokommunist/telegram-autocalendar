"""Flask application entry point for Telegram Auto-Calendar Bot."""

import asyncio
from flask import Flask

from .routes import register_routes
from ..config import Config

app = Flask(__name__)
app.secret_key = "telegram-autocalendar-secret-key-change-in-production"

# Ensure uploads directory exists
Config.get_uploads_path()

# Register all routes
register_routes(app)


def run():
    """Run the Flask application."""
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    run()
