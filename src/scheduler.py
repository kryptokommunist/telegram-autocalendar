"""Scheduler for processing Telegram messages and extracting events."""

import asyncio
import sys
from datetime import datetime

from . import database as db
from .telegram_client import get_telegram_client
from .llm_processor import process_message_for_event


def log(msg):
    """Print with flush for Docker logs."""
    print(msg, flush=True)


def process_new_messages():
    """
    Process new messages from all Telegram groups/channels.
    This is the main function called by cron or manual sync.
    """
    log(f"\n{'='*60}")
    log(f"Starting sync at {datetime.now().isoformat()}")
    log(f"{'='*60}\n")

    client = get_telegram_client()

    try:
        # Check auth
        log("Checking authentication...")
        if not client.is_authenticated():
            log("ERROR: Not authenticated. Please complete auth via web UI first.")
            db.update_sync_status("error", error_message="Not authenticated")
            return

        log("Authentication OK")

        # Update sync status
        db.update_sync_status("running")

        # Get all dialogs (groups and channels)
        log("Fetching dialogs (groups and channels)...")
        all_dialogs = client.get_dialogs()

        # Get enabled groups
        enabled_ids = set(db.get_enabled_group_ids())

        if not enabled_ids:
            log("No groups are enabled for scanning. Configure groups in Settings.")
            db.update_sync_status("completed")
            return

        # Filter to only enabled groups
        dialogs = [d for d in all_dialogs if d["id"] in enabled_ids]
        log(f"Found {len(all_dialogs)} total groups, {len(dialogs)} enabled for scanning\n")

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

            log(f"[{i}/{len(dialogs)}] Processing: {chat_name} ({chat_type})")

            try:
                # Get group info for context
                group_info = client.get_group_info(chat_id)
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
                messages = client.get_messages(chat_id, limit=100, min_id=last_id)
                message_count = 0
                event_count = 0

                for msg in messages:
                    message_count += 1
                    total_messages += 1

                    # Download image if present
                    image_path = None
                    if msg.get("has_photo") and msg.get("photo"):
                        image_path = client.download_message_image(
                            msg["photo"], chat_id, msg["id"]
                        )

                    # Process message for event extraction (this is async)
                    try:
                        event_id = asyncio.run(process_message_for_event(
                            message_id=msg["id"],
                            chat_id=chat_id,
                            chat_name=chat_name,
                            message_text=msg["text"],
                            chat_description=chat_description,
                            chat_type=chat_type,
                            image_path=image_path,
                            message_date=msg.get("date"),
                        ))

                        if event_id:
                            event_count += 1
                            total_events += 1
                            log(f"  -> Found event: ID {event_id}")
                    except Exception as e:
                        log(f"  -> Error processing message {msg['id']}: {e}")

                log(f"   Processed {message_count} messages, found {event_count} events")

            except Exception as e:
                log(f"   Error processing group: {e}")

            # Update progress
            db.set_sync_progress(
                groups_total=len(dialogs),
                groups_scanned=i,
                messages_processed=total_messages,
                events_found=total_events,
            )

        # Mark sync as complete
        db.update_sync_status("completed")

        log(f"\n{'='*60}")
        log(f"Sync completed at {datetime.now().isoformat()}")
        log(f"Total: {total_messages} messages processed, {total_events} events found")
        log(f"{'='*60}\n")

    except Exception as e:
        log(f"ERROR during sync: {e}")
        import traceback
        traceback.print_exc()
        db.update_sync_status("error", error_message=str(e))


def run_sync_in_thread():
    """Run sync in a thread (for web UI trigger)."""
    process_new_messages()


def main():
    """Entry point for the scheduler (cron job)."""
    process_new_messages()


if __name__ == "__main__":
    main()
