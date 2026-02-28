"""LLM processor for event extraction using Claude via GenAI Proxy."""

import json
import re
from datetime import datetime
from typing import Optional
import httpx

from .config import Config
from . import database as db


def get_existing_categories() -> str:
    """Get formatted list of existing categories for the LLM prompt."""
    categories = db.get_all_categories()
    if not categories:
        return "No existing categories yet."

    return "\n".join(f"- {cat['name']}" for cat in categories)


def build_extraction_prompt(
    message_text: str,
    chat_name: str,
    chat_description: Optional[str],
    chat_type: str,
    message_date: Optional[datetime] = None,
) -> str:
    """Build the prompt for event extraction."""
    categories = get_existing_categories()
    # Use message date as reference for relative dates, fall back to now if unknown
    reference_date = message_date if message_date else datetime.now()
    reference_date_str = reference_date.strftime("%Y-%m-%d")
    message_date_str = message_date.strftime("%Y-%m-%d %H:%M") if message_date else "Unknown"

    return f"""You are an event extraction assistant. Analyze the following Telegram message
and determine if it announces an event (meetup, party, conference, workshop, etc.).

SOURCE CONTEXT:
- Group/Channel name: {chat_name}
- Group/Channel description: {chat_description or 'Not available'}
- Type: {chat_type}
- Message posted on: {message_date_str}

EXISTING CATEGORIES (prefer these, but create new if none fit):
{categories}

EVENT TYPE definitions:
- "single": One-time event on a single day (class, workshop, party, meetup)
- "multiday": Continuous event spanning multiple days (retreat, festival, conference)
- "recurring": Repeats on an ongoing basis (every Thursday yoga, weekly meditation)
- "series": Limited course/program over a set period (4-week course, 3-month training)

Return JSON only, no other text:
- If NOT an event: {{"is_event": false}}
- If IS an event:
{{
  "is_event": true,
  "event_title": "Brief descriptive title",
  "event_start": "YYYY-MM-DDTHH:MM:SS or null if unclear",
  "event_end": "YYYY-MM-DDTHH:MM:SS or null",
  "event_location": "Venue name and address or null",
  "city": "City name where event takes place (e.g., 'Berlin', 'New York') or null",
  "country": "Country name (e.g., 'Germany', 'USA') or null",
  "event_link": "URL for registration/info or null",
  "ticket_price": "Price info (e.g., 'Free', '$25', '10-50 EUR') or null",
  "organizer": "Event organizer/host name or null",
  "category": "Best matching category name (existing or new)",
  "event_type": "single, multiday, recurring, or series",
  "event_description": "1-2 sentence summary"
}}

CRITICAL: Interpret ALL relative dates (e.g., "this Friday", "next week", "tomorrow") relative to the MESSAGE DATE ({reference_date_str}), NOT today's date.
For example, if the message was posted on 2026-01-15 and says "this Saturday", the event is on 2026-01-17.

Message:
{message_text}"""


async def extract_event(
    message_text: str,
    chat_name: str,
    chat_description: Optional[str] = None,
    chat_type: str = "group",
    message_date: Optional[datetime] = None,
) -> Optional[dict]:
    """
    Extract event information from a message using Claude.
    Returns parsed event data or None if not an event.
    """
    prompt = build_extraction_prompt(
        message_text, chat_name, chat_description, chat_type, message_date
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                Config.GENAI_PROXY_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": Config.GENAI_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": Config.GENAI_MODEL,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

            if response.status_code != 200:
                print(f"LLM API error: {response.status_code} - {response.text}")
                return None

            result = response.json()

            # Extract text from response
            content = result.get("content", [])
            if not content:
                return None

            text = content[0].get("text", "")

            # Parse JSON from response
            # Handle potential markdown code blocks
            text = text.strip()
            if text.startswith("```"):
                # Remove markdown code block
                text = re.sub(r"^```(?:json)?\n?", "", text)
                text = re.sub(r"\n?```$", "", text)

            event_data = json.loads(text)

            if not event_data.get("is_event"):
                return None

            return event_data

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None
    except httpx.TimeoutException:
        print("LLM request timed out")
        return None
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string from LLM response."""
    if not dt_str:
        return None

    try:
        # Try ISO format first
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    # Try other common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    return None


async def process_message_for_event(
    message_id: int,
    chat_id: int,
    chat_name: str,
    message_text: str,
    chat_description: Optional[str] = None,
    chat_type: str = "group",
    image_path: Optional[str] = None,
    message_date: Optional[datetime] = None,
) -> Optional[int]:
    """
    Process a message and save as event if applicable.
    Returns event ID if saved, None otherwise.
    """
    # Skip if already processed
    if db.is_message_processed(message_id, chat_id):
        return None

    # Extract event using LLM
    event_data = await extract_event(
        message_text, chat_name, chat_description, chat_type, message_date
    )

    # Mark as processed regardless of result
    db.mark_message_processed(message_id, chat_id)

    if not event_data:
        return None

    # Get or create category
    category_name = event_data.get("category")
    category_id = db.get_or_create_category(category_name) if category_name else None

    # Parse dates
    event_start = parse_datetime(event_data.get("event_start"))
    event_end = parse_datetime(event_data.get("event_end"))

    # Validate event_type
    event_type = event_data.get("event_type")
    if event_type not in ("single", "multiday", "recurring", "series"):
        event_type = None

    # Save event
    event_id = db.save_event(
        message_id=message_id,
        chat_id=chat_id,
        chat_name=chat_name,
        event_title=event_data.get("event_title", "Untitled Event"),
        event_start=event_start,
        event_end=event_end,
        event_location=event_data.get("event_location"),
        city=event_data.get("city"),
        country=event_data.get("country"),
        event_description=event_data.get("event_description"),
        event_description_full=message_text,
        event_link=event_data.get("event_link"),
        ticket_price=event_data.get("ticket_price"),
        organizer=event_data.get("organizer"),
        event_type=event_type,
        category_id=category_id,
        image_path=image_path,
        original_message=message_text,
    )

    return event_id
