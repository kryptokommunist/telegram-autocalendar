"""Flask routes for Telegram Auto-Calendar Bot."""

import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify

from .. import database as db
from ..telegram_client import get_telegram_client


def register_routes(app: Flask):
    """Register all routes with the Flask app."""

    # ============ Page Routes ============

    @app.route("/")
    def index():
        """Main event calendar view."""
        return render_template("index.html")

    @app.route("/auth")
    def auth_page():
        """Telegram authentication wizard."""
        return render_template("auth.html")

    @app.route("/event/<int:event_id>")
    def event_detail(event_id: int):
        """Single event detail page."""
        event = db.get_event_by_id(event_id)
        if not event:
            return "Event not found", 404
        return render_template("event.html", event=event)

    # ============ API Routes ============

    @app.route("/api/events")
    def api_events():
        """Get events with optional filters."""
        category_id = request.args.get("category_id", type=int)
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        chat_id = request.args.get("chat_id", type=int)
        price_type = request.args.get("price_type")
        max_price = request.args.get("max_price", type=float)
        city = request.args.get("city")
        country = request.args.get("country")
        event_type = request.args.get("event_type")
        search = request.args.get("search")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Parse dates
        date_from_dt = None
        date_to_dt = None
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                pass
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
            except ValueError:
                pass

        events = db.get_events(
            category_id=category_id,
            date_from=date_from_dt,
            date_to=date_to_dt,
            chat_id=chat_id,
            price_type=price_type,
            max_price=max_price,
            city=city,
            country=country,
            event_type=event_type,
            search=search,
            limit=limit,
            offset=offset,
        )

        # Get total count with same filters (for pagination info)
        total_count = db.get_events_count(
            category_id=category_id,
            date_from=date_from_dt,
            date_to=date_to_dt,
            chat_id=chat_id,
            price_type=price_type,
            max_price=max_price,
            city=city,
            country=country,
            event_type=event_type,
            search=search,
        )

        # Serialize datetime objects
        for event in events:
            for key in ["event_start", "event_end", "created_at"]:
                if event.get(key):
                    event[key] = event[key].isoformat()

        return jsonify({
            "events": events,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        })

    @app.route("/api/events/<int:event_id>")
    def api_event_detail(event_id: int):
        """Get single event detail."""
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404

        # Serialize datetime objects
        for key in ["event_start", "event_end", "created_at"]:
            if event.get(key):
                event[key] = event[key].isoformat()

        return jsonify(event)

    @app.route("/api/events/<int:event_id>/ical")
    def api_event_ical(event_id: int):
        """Get event as iCal file for calendar apps."""
        from flask import Response

        event = db.get_event_by_id(event_id)
        if not event:
            return "Event not found", 404

        # Build location string
        location_parts = []
        if event.get("event_location"):
            location_parts.append(event["event_location"])
        if event.get("city"):
            location_parts.append(event["city"])
        if event.get("country"):
            location_parts.append(event["country"])
        location = ", ".join(location_parts)

        # Format dates for iCal (YYYYMMDDTHHMMSSZ)
        def format_ical_date(dt):
            if not dt:
                return None
            return dt.strftime("%Y%m%dT%H%M%SZ")

        start_date = format_ical_date(event.get("event_start"))
        if not start_date:
            return "Event has no start date", 400

        # Default to 2 hour duration if no end date
        end_dt = event.get("event_end")
        if not end_dt and event.get("event_start"):
            from datetime import timedelta
            end_dt = event["event_start"] + timedelta(hours=2)
        end_date = format_ical_date(end_dt)

        # Escape special characters
        def escape_ical(s):
            if not s:
                return ""
            return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = f"event-{event_id}@telegram-autocalendar"

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Telegram Auto-Calendar//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{start_date}",
            f"DTEND:{end_date}",
            f"SUMMARY:{escape_ical(event.get('event_title', 'Event'))}",
        ]

        if location:
            lines.append(f"LOCATION:{escape_ical(location)}")
        if event.get("event_description"):
            lines.append(f"DESCRIPTION:{escape_ical(event['event_description'])}")
        if event.get("event_link"):
            lines.append(f"URL:{event['event_link']}")

        lines.extend(["END:VEVENT", "END:VCALENDAR"])

        ical_content = "\r\n".join(lines)

        # Check if this is for download or direct open
        download = request.args.get("download", "false").lower() == "true"

        response = Response(ical_content, mimetype="text/calendar")
        if download:
            response.headers["Content-Disposition"] = f"attachment; filename=event-{event_id}.ics"
        # Without Content-Disposition, browser/OS may open Calendar app directly
        return response

    @app.route("/api/categories")
    def api_categories():
        """Get all categories with event counts."""
        categories = db.get_all_categories()
        return jsonify(categories)

    @app.route("/api/groups")
    def api_groups():
        """Get groups that have events (for filtering)."""
        groups = db.get_groups_with_events()
        return jsonify(groups)

    @app.route("/api/locations")
    def api_locations():
        """Get distinct cities and countries for filtering."""
        cities = db.get_distinct_cities()
        countries = db.get_distinct_countries()
        return jsonify({
            "cities": cities,
            "countries": countries,
        })

    @app.route("/api/status")
    def api_status():
        """Get auth status and sync info."""
        try:
            client = get_telegram_client()
            is_authenticated = client.is_authenticated()

            user_info = None
            if is_authenticated:
                user_info = client.get_me()
        except Exception as e:
            print(f"Error checking auth status: {e}")
            is_authenticated = False
            user_info = None

        sync_status = db.get_sync_status()

        # Serialize datetime objects in sync_status
        for key in ["started_at", "completed_at", "updated_at"]:
            if sync_status.get(key):
                sync_status[key] = sync_status[key].isoformat()

        return jsonify({
            "authenticated": is_authenticated,
            "user": user_info,
            "sync": sync_status,
        })

    # ============ Auth Routes ============

    @app.route("/api/auth/phone", methods=["POST"])
    def api_auth_phone():
        """Start auth flow by sending code to phone."""
        data = request.get_json()
        phone_number = data.get("phone_number")

        if not phone_number:
            return jsonify({"error": "Phone number required"}), 400

        try:
            client = get_telegram_client()
            phone_code_hash = client.send_code(phone_number)
            db.save_auth_state(phone_number, phone_code_hash, "pending_code")
            return jsonify({"success": True, "message": "Code sent"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/auth/code", methods=["POST"])
    def api_auth_code():
        """Submit verification code."""
        data = request.get_json()
        code = data.get("code")

        if not code:
            return jsonify({"error": "Code required"}), 400

        auth_state = db.get_auth_state()
        if not auth_state:
            return jsonify({"error": "No pending auth. Start with phone number."}), 400

        try:
            client = get_telegram_client()
            result = client.sign_in_with_code(
                auth_state["phone_number"],
                code,
                auth_state["phone_code_hash"],
            )

            if result.get("success"):
                db.clear_auth_state()
                return jsonify({"success": True, "message": "Authenticated successfully"})
            elif result.get("needs_2fa"):
                db.update_auth_status("pending_2fa")
                return jsonify({"success": False, "needs_2fa": True})
            else:
                return jsonify({"error": result.get("error", "Unknown error")}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/auth/2fa", methods=["POST"])
    def api_auth_2fa():
        """Submit 2FA password."""
        data = request.get_json()
        password = data.get("password")

        if not password:
            return jsonify({"error": "Password required"}), 400

        try:
            client = get_telegram_client()
            result = client.sign_in_with_2fa(password)

            if result.get("success"):
                db.clear_auth_state()
                return jsonify({"success": True, "message": "Authenticated successfully"})
            else:
                return jsonify({"error": result.get("error", "Unknown error")}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ============ Sync Routes ============

    @app.route("/api/sync", methods=["POST"])
    def api_sync():
        """Trigger manual sync."""
        sync_status = db.get_sync_status()
        force = request.args.get("force", "false").lower() == "true"

        # Allow restart if sync is stale (stuck)
        if sync_status.get("status") == "running" and not force:
            return jsonify({"error": "Sync already running"}), 400

        # If forcing restart of a stale sync, reset status first
        if sync_status.get("status") in ("running", "stale") and force:
            db.reset_sync_status()

        # Import here to avoid circular imports
        from ..scheduler import run_sync_in_thread

        # Run sync in background thread
        thread = threading.Thread(target=run_sync_in_thread)
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "Sync started"})

    @app.route("/api/sync/status")
    def api_sync_status():
        """Get current sync status."""
        sync_status = db.get_sync_status()

        # Serialize datetime objects
        for key in ["started_at", "completed_at", "updated_at"]:
            if sync_status.get(key):
                sync_status[key] = sync_status[key].isoformat()

        return jsonify(sync_status)

    # ============ Settings Routes ============

    @app.route("/settings")
    def settings_page():
        """Settings page for group management."""
        return render_template("settings.html")

    @app.route("/setup")
    def setup_page():
        """Initial setup page for group selection."""
        return render_template("setup.html")

    @app.route("/api/settings/groups")
    def api_settings_groups():
        """Get all groups with selection status."""
        try:
            # Get groups from database
            groups = db.get_selected_groups()

            # Also get telegram groups info to merge
            tg_groups = db.get_all_telegram_groups()
            tg_map = {g["chat_id"]: g for g in tg_groups}

            # Merge data
            result = []
            for g in groups:
                chat_id = g["chat_id"]
                tg = tg_map.get(chat_id, {})
                result.append({
                    "chat_id": chat_id,
                    "chat_name": g.get("chat_name") or tg.get("chat_name") or f"Group {chat_id}",
                    "chat_type": g.get("chat_type") or tg.get("chat_type") or "group",
                    "enabled": g["enabled"],
                    "is_new": False,  # Could track this with timestamps
                })

            # Stats
            enabled_count = sum(1 for g in result if g["enabled"])
            total_events = len(db.get_events(limit=10000))

            return jsonify({
                "groups": result,
                "stats": {
                    "total_groups": len(result),
                    "enabled_groups": enabled_count,
                    "total_events": total_events,
                    "total_messages": 0,  # Could query processed_messages
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/groups", methods=["POST"])
    def api_settings_groups_save():
        """Save group selections."""
        data = request.get_json()
        groups = data.get("groups", [])

        try:
            db.bulk_set_groups(groups)
            db.mark_groups_configured()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/groups/refresh", methods=["POST"])
    def api_settings_groups_refresh():
        """Refresh groups from Telegram."""
        try:
            client = get_telegram_client()
            if not client.is_authenticated():
                return jsonify({"error": "Not authenticated"}), 401

            # Get dialogs from Telegram
            dialogs = client.get_dialogs()

            # Save group metadata
            for dialog in dialogs:
                db.save_telegram_group(
                    chat_id=dialog["id"],
                    chat_name=dialog["name"],
                    chat_description=None,
                    chat_type=dialog["type"],
                )

            # Sync available groups
            chat_ids = [d["id"] for d in dialogs]
            result = db.sync_available_groups(chat_ids)

            return jsonify({
                "success": True,
                "new_count": result["new_count"],
                "removed_count": result["removed_count"],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/groups/new")
    def api_settings_new_groups():
        """Get newly added groups that haven't been reviewed."""
        groups = db.get_new_unselected_groups()
        return jsonify({"groups": groups})

    @app.route("/api/settings/configured")
    def api_settings_configured():
        """Check if initial group setup is complete."""
        return jsonify({
            "configured": db.is_groups_configured()
        })
