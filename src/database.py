"""MySQL database operations for Telegram Auto-Calendar Bot."""

import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from .config import Config


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = mysql.connector.connect(**Config.get_mysql_config())
        yield conn
    finally:
        if conn and conn.is_connected():
            conn.close()


def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """Execute a query and optionally fetch results."""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
        cursor.close()
        return result


# ============ Categories ============

def get_all_categories() -> list[dict]:
    """Get all categories with event counts."""
    query = """
        SELECT c.id, c.name, c.description, COUNT(e.id) as event_count
        FROM categories c
        LEFT JOIN events e ON c.id = e.category_id
        GROUP BY c.id, c.name, c.description
        ORDER BY c.name
    """
    return execute_query(query, fetch=True)


def get_or_create_category(name: str) -> int:
    """Get category ID by name, creating it if it doesn't exist."""
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        # Check if exists
        cursor.execute("SELECT id FROM categories WHERE name = %s", (name,))
        row = cursor.fetchone()

        if row:
            category_id = row["id"]
        else:
            # Create new category
            cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
            conn.commit()
            category_id = cursor.lastrowid

        cursor.close()
        return category_id


# ============ Events ============

def save_event(
    message_id: int,
    chat_id: int,
    chat_name: str,
    event_title: str,
    event_start: Optional[datetime],
    event_end: Optional[datetime],
    event_location: Optional[str],
    city: Optional[str],
    country: Optional[str],
    event_description: Optional[str],
    event_description_full: Optional[str],
    event_link: Optional[str],
    ticket_price: Optional[str],
    organizer: Optional[str],
    category_id: Optional[int],
    image_path: Optional[str],
    original_message: str,
) -> int:
    """Save an event to the database."""
    query = """
        INSERT INTO events (
            message_id, chat_id, chat_name, event_title, event_start, event_end,
            event_location, city, country, event_description, event_description_full,
            event_link, ticket_price, organizer, category_id, image_path, original_message
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            event_title = VALUES(event_title),
            event_start = VALUES(event_start),
            event_end = VALUES(event_end),
            event_location = VALUES(event_location),
            city = VALUES(city),
            country = VALUES(country),
            event_description = VALUES(event_description),
            event_description_full = VALUES(event_description_full),
            event_link = VALUES(event_link),
            ticket_price = VALUES(ticket_price),
            organizer = VALUES(organizer),
            category_id = VALUES(category_id),
            image_path = VALUES(image_path)
    """
    return execute_query(
        query,
        (
            message_id,
            chat_id,
            chat_name,
            event_title,
            event_start,
            event_end,
            event_location,
            city,
            country,
            event_description,
            event_description_full,
            event_link,
            ticket_price,
            organizer,
            category_id,
            image_path,
            original_message,
        ),
    )


def get_events(
    category_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    chat_id: Optional[int] = None,
    price_type: Optional[str] = None,
    max_price: Optional[float] = None,
    city: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get events with optional filters."""
    query = """
        SELECT e.*, c.name as category_name
        FROM events e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params = []

    if category_id:
        query += " AND e.category_id = %s"
        params.append(category_id)

    if date_from:
        query += " AND e.event_start >= %s"
        params.append(date_from)

    if date_to:
        query += " AND e.event_start <= %s"
        params.append(date_to)

    if chat_id:
        query += " AND e.chat_id = %s"
        params.append(chat_id)

    if price_type == "free":
        query += " AND (e.ticket_price IS NULL OR LOWER(e.ticket_price) LIKE '%free%')"
    elif price_type == "paid":
        query += " AND e.ticket_price IS NOT NULL AND LOWER(e.ticket_price) NOT LIKE '%free%'"

    if max_price is not None:
        # Filter by max price - extract numeric value from ticket_price
        # This handles formats like "$25", "25 EUR", "10-50 EUR" (uses first number)
        query += """ AND (
            e.ticket_price IS NULL
            OR LOWER(e.ticket_price) LIKE '%free%'
            OR CAST(REGEXP_SUBSTR(e.ticket_price, '[0-9]+\\.?[0-9]*') AS DECIMAL(10,2)) <= %s
        )"""
        params.append(max_price)

    if city:
        query += " AND LOWER(e.city) = LOWER(%s)"
        params.append(city)

    if country:
        query += " AND LOWER(e.country) = LOWER(%s)"
        params.append(country)

    query += " ORDER BY e.event_start ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    return execute_query(query, tuple(params), fetch=True)


def get_distinct_cities() -> list[str]:
    """Get list of distinct cities with events."""
    query = """
        SELECT DISTINCT city FROM events
        WHERE city IS NOT NULL AND city != ''
        ORDER BY city
    """
    results = execute_query(query, fetch=True)
    return [r["city"] for r in results]


def get_distinct_countries() -> list[str]:
    """Get list of distinct countries with events."""
    query = """
        SELECT DISTINCT country FROM events
        WHERE country IS NOT NULL AND country != ''
        ORDER BY country
    """
    results = execute_query(query, fetch=True)
    return [r["country"] for r in results]


def get_event_by_id(event_id: int) -> Optional[dict]:
    """Get a single event by ID."""
    query = """
        SELECT e.*, c.name as category_name
        FROM events e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.id = %s
    """
    results = execute_query(query, (event_id,), fetch=True)
    return results[0] if results else None


def get_upcoming_events(days: int = 30) -> list[dict]:
    """Get upcoming events within the next N days."""
    query = """
        SELECT e.*, c.name as category_name
        FROM events e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.event_start >= NOW()
        AND e.event_start <= DATE_ADD(NOW(), INTERVAL %s DAY)
        ORDER BY e.event_start ASC
    """
    return execute_query(query, (days,), fetch=True)


# ============ Processed Messages ============

def is_message_processed(message_id: int, chat_id: int) -> bool:
    """Check if a message has already been processed."""
    query = "SELECT 1 FROM processed_messages WHERE message_id = %s AND chat_id = %s"
    results = execute_query(query, (message_id, chat_id), fetch=True)
    return len(results) > 0


def mark_message_processed(message_id: int, chat_id: int):
    """Mark a message as processed."""
    query = """
        INSERT IGNORE INTO processed_messages (message_id, chat_id)
        VALUES (%s, %s)
    """
    execute_query(query, (message_id, chat_id))


def get_last_processed_id(chat_id: int) -> Optional[int]:
    """Get the last processed message ID for a chat."""
    query = """
        SELECT MAX(message_id) as last_id
        FROM processed_messages
        WHERE chat_id = %s
    """
    results = execute_query(query, (chat_id,), fetch=True)
    return results[0]["last_id"] if results and results[0]["last_id"] else None


# ============ Telegram Groups ============

def save_telegram_group(
    chat_id: int, chat_name: str, chat_description: Optional[str], chat_type: str
):
    """Save or update telegram group metadata."""
    query = """
        INSERT INTO telegram_groups (chat_id, chat_name, chat_description, chat_type)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            chat_name = VALUES(chat_name),
            chat_description = VALUES(chat_description),
            chat_type = VALUES(chat_type)
    """
    execute_query(query, (chat_id, chat_name, chat_description, chat_type))


def get_telegram_group(chat_id: int) -> Optional[dict]:
    """Get telegram group metadata."""
    query = "SELECT * FROM telegram_groups WHERE chat_id = %s"
    results = execute_query(query, (chat_id,), fetch=True)
    return results[0] if results else None


def get_all_telegram_groups() -> list[dict]:
    """Get all telegram groups."""
    query = "SELECT * FROM telegram_groups ORDER BY chat_name"
    return execute_query(query, fetch=True)


def get_groups_with_events() -> list[dict]:
    """Get only groups that have events and are enabled for scanning."""
    query = """
        SELECT DISTINCT tg.chat_id, tg.chat_name, tg.chat_type, COUNT(e.id) as event_count
        FROM telegram_groups tg
        INNER JOIN events e ON tg.chat_id = e.chat_id
        INNER JOIN selected_groups sg ON tg.chat_id = sg.chat_id AND sg.enabled = TRUE
        GROUP BY tg.chat_id, tg.chat_name, tg.chat_type
        HAVING COUNT(e.id) > 0
        ORDER BY tg.chat_name
    """
    return execute_query(query, fetch=True)


# ============ Auth State ============

def get_auth_state() -> Optional[dict]:
    """Get the current auth state."""
    query = "SELECT * FROM auth_state ORDER BY id DESC LIMIT 1"
    results = execute_query(query, fetch=True)
    return results[0] if results else None


def save_auth_state(
    phone_number: str, phone_code_hash: str, status: str = "pending_code"
):
    """Save auth state for Telegram authentication."""
    # Clear old states first
    execute_query("DELETE FROM auth_state")

    query = """
        INSERT INTO auth_state (phone_number, phone_code_hash, status)
        VALUES (%s, %s, %s)
    """
    execute_query(query, (phone_number, phone_code_hash, status))


def update_auth_status(status: str):
    """Update the auth status."""
    query = "UPDATE auth_state SET status = %s, updated_at = NOW()"
    execute_query(query, (status,))


def clear_auth_state():
    """Clear auth state after successful authentication."""
    execute_query("DELETE FROM auth_state")


# ============ Sync Status ============

def get_sync_status() -> dict:
    """Get the current sync status."""
    query = "SELECT * FROM sync_status ORDER BY id DESC LIMIT 1"
    results = execute_query(query, fetch=True)
    return results[0] if results else {"status": "idle"}


def update_sync_status(
    status: str,
    groups_total: int = None,
    groups_scanned: int = None,
    messages_processed: int = None,
    events_found: int = None,
    error_message: str = None,
):
    """Update sync status."""
    query = "UPDATE sync_status SET status = %s, updated_at = NOW()"
    params = [status]

    if status == "running":
        query = """
            UPDATE sync_status SET
                status = %s,
                started_at = NOW(),
                completed_at = NULL,
                error_message = NULL,
                updated_at = NOW()
        """
        params = [status]
    elif status in ("completed", "error"):
        query = """
            UPDATE sync_status SET
                status = %s,
                completed_at = NOW(),
                updated_at = NOW()
        """
        params = [status]

    if groups_total is not None:
        query = query.replace("updated_at = NOW()", "groups_total = %s, updated_at = NOW()")
        params.append(groups_total)

    if groups_scanned is not None:
        query = query.replace("updated_at = NOW()", "groups_scanned = %s, updated_at = NOW()")
        params.append(groups_scanned)

    if messages_processed is not None:
        query = query.replace("updated_at = NOW()", "messages_processed = %s, updated_at = NOW()")
        params.append(messages_processed)

    if events_found is not None:
        query = query.replace("updated_at = NOW()", "events_found = %s, updated_at = NOW()")
        params.append(events_found)

    if error_message is not None:
        query = query.replace("updated_at = NOW()", "error_message = %s, updated_at = NOW()")
        params.append(error_message)

    execute_query(query, tuple(params))


def set_sync_progress(groups_total: int, groups_scanned: int, messages_processed: int, events_found: int):
    """Update sync progress counters."""
    query = """
        UPDATE sync_status SET
            groups_total = %s,
            groups_scanned = %s,
            messages_processed = %s,
            events_found = %s,
            updated_at = NOW()
    """
    execute_query(query, (groups_total, groups_scanned, messages_processed, events_found))


def reset_sync_status():
    """Reset sync status to idle."""
    query = """
        UPDATE sync_status SET
            status = 'idle',
            groups_total = 0,
            groups_scanned = 0,
            messages_processed = 0,
            events_found = 0,
            error_message = NULL,
            updated_at = NOW()
    """
    execute_query(query)


# ============ Selected Groups ============

def get_selected_groups() -> list[dict]:
    """Get all groups with their selection status."""
    query = """
        SELECT sg.chat_id, sg.enabled, sg.added_at,
               tg.chat_name, tg.chat_description, tg.chat_type
        FROM selected_groups sg
        LEFT JOIN telegram_groups tg ON sg.chat_id = tg.chat_id
        ORDER BY tg.chat_name
    """
    return execute_query(query, fetch=True)


def get_enabled_group_ids() -> list[int]:
    """Get list of chat_ids that are enabled for scanning."""
    query = "SELECT chat_id FROM selected_groups WHERE enabled = TRUE"
    results = execute_query(query, fetch=True)
    return [r["chat_id"] for r in results]


def set_group_enabled(chat_id: int, enabled: bool):
    """Enable or disable a group for scanning."""
    query = """
        INSERT INTO selected_groups (chat_id, enabled)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)
    """
    execute_query(query, (chat_id, enabled))


def bulk_set_groups(group_selections: list[dict]):
    """Bulk update group selections. Each dict has chat_id and enabled."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for group in group_selections:
            cursor.execute(
                """
                INSERT INTO selected_groups (chat_id, enabled)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)
                """,
                (group["chat_id"], group["enabled"])
            )
        conn.commit()
        cursor.close()


def sync_available_groups(available_chat_ids: list[int]):
    """
    Sync available groups from Telegram.
    - Add new groups as disabled (user must explicitly enable)
    - Keep existing selections
    - Mark removed groups (but don't delete to preserve history)
    Returns: dict with 'new' and 'removed' group counts
    """
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)

        # Get currently tracked groups
        cursor.execute("SELECT chat_id, enabled FROM selected_groups")
        existing = {row["chat_id"]: row["enabled"] for row in cursor.fetchall()}

        existing_ids = set(existing.keys())
        available_ids = set(available_chat_ids)

        # New groups (in Telegram but not in our DB)
        new_ids = available_ids - existing_ids
        # Removed groups (in our DB but no longer in Telegram)
        removed_ids = existing_ids - available_ids

        # Add new groups as disabled by default
        for chat_id in new_ids:
            cursor.execute(
                "INSERT INTO selected_groups (chat_id, enabled) VALUES (%s, FALSE)",
                (chat_id,)
            )

        conn.commit()
        cursor.close()

        return {
            "new_count": len(new_ids),
            "removed_count": len(removed_ids),
            "new_ids": list(new_ids),
            "removed_ids": list(removed_ids),
        }


def is_group_selected(chat_id: int) -> bool:
    """Check if a group is enabled for scanning."""
    query = "SELECT enabled FROM selected_groups WHERE chat_id = %s"
    results = execute_query(query, (chat_id,), fetch=True)
    return results[0]["enabled"] if results else False


def get_new_unselected_groups() -> list[dict]:
    """Get groups that were recently added but not yet reviewed by user."""
    query = """
        SELECT sg.chat_id, sg.added_at, tg.chat_name, tg.chat_type
        FROM selected_groups sg
        LEFT JOIN telegram_groups tg ON sg.chat_id = tg.chat_id
        WHERE sg.enabled = FALSE
        AND sg.added_at > (
            SELECT COALESCE(MAX(updated_at), '1970-01-01')
            FROM user_settings WHERE setting_key = 'groups_configured'
        )
        ORDER BY sg.added_at DESC
    """
    return execute_query(query, fetch=True)


# ============ User Settings ============

def get_setting(key: str) -> Optional[str]:
    """Get a user setting value."""
    query = "SELECT setting_value FROM user_settings WHERE setting_key = %s"
    results = execute_query(query, (key,), fetch=True)
    return results[0]["setting_value"] if results else None


def set_setting(key: str, value: str):
    """Set a user setting value."""
    query = """
        INSERT INTO user_settings (setting_key, setting_value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
    """
    execute_query(query, (key, value))


def is_groups_configured() -> bool:
    """Check if user has completed initial group configuration."""
    value = get_setting("groups_configured")
    return value == "true"


def mark_groups_configured():
    """Mark that user has completed initial group configuration."""
    set_setting("groups_configured", "true")
