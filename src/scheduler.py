"""Scheduler for processing Telegram messages and extracting events."""

import asyncio
import sys
from datetime import datetime

from . import database as db
from .telegram_client import get_telegram_client
from .llm_processor import process_message_for_event


async def process_new_messages():
    """
    Process new messages from all Telegram groups/channels.
    This is the main function called by cron.
    """
    print(f"\n{'='*60}")
    print(f"Starting sync at {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    client = get_telegram_client()

    try:
        # Connect and check auth
        is_authenticated = await client.connect()
        if not is_authenticated:
            print("ERROR: Not authenticated. Please complete auth via web UI first.")
            db.update_sync_status("error", error_message="Not authenticated")
            return

        # Update sync status
        db.update_sync_status("running")

        # Get all dialogs (groups and channels)
        dialogs = await client.get_dialogs()
        print(f"Found {len(dialogs)} groups/channels to process\n")

        db.set_sync_progress(
            groups_total=len(dialogs),
            groups_scanned=0,
            messages_processed=0,
            events_found=0,
        )

        total_messages = 0
        total_events = 0

        for i, dialog in enumerate(dialogs, 1):
            chat_id = dialog["id"]
            chat_name = dialog["name"]
            chat_type = dialog["type"]

            print(f"[{i}/{len(dialogs)}] Processing: {chat_name} ({chat_type})")

            # Get group info for context
            group_info = await client.get_group_info(chat_id)
            chat_description = group_info.get("description") if group_info else None

            # Save/update group metadata
            db.save_telegram_group(
                chat_id=chat_id,
                chat_name=chat_name,
                chat_description=chat_description,
                chat_type=chat_type,
            )

            # Get last processed message ID for incremental processing
            last_id = db.get_last_processed_id(chat_id) or 0

            # Fetch new messages
            message_count = 0
            event_count = 0

            async for msg in client.get_messages(chat_id, limit=100, min_id=last_id):
                message_count += 1
                total_messages += 1

                # Download image if present
                image_path = None
                if msg["has_photo"]:
                    image_path = await client.download_message_image(
                        msg["message_obj"], chat_id
                    )

                # Process message for event extraction
                event_id = await process_message_for_event(
                    message_id=msg["id"],
                    chat_id=chat_id,
                    chat_name=chat_name,
                    message_text=msg["text"],
                    chat_description=chat_description,
                    chat_type=chat_type,
                    image_path=image_path,
                )

                if event_id:
                    event_count += 1
                    total_events += 1
                    print(f"  -> Found event: ID {event_id}")

            print(f"   Processed {message_count} messages, found {event_count} events")

            # Update progress
            db.set_sync_progress(
                groups_total=len(dialogs),
                groups_scanned=i,
                messages_processed=total_messages,
                events_found=total_events,
            )

        # Mark sync as complete
        db.update_sync_status("completed")

        print(f"\n{'='*60}")
        print(f"Sync completed at {datetime.now().isoformat()}")
        print(f"Total: {total_messages} messages processed, {total_events} events found")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"ERROR during sync: {e}")
        db.update_sync_status("error", error_message=str(e))
        raise
    finally:
        await client.disconnect()


def main():
    """Entry point for the scheduler."""
    asyncio.run(process_new_messages())


if __name__ == "__main__":
    main()
