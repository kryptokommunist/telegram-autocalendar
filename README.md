# Telegram Auto-Calendar

Automatically extract events from Telegram groups and channels and display them in a beautiful web interface.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Automatic Event Extraction**: Uses Claude AI to intelligently parse Telegram messages and extract event details
- **Multi-Group Support**: Monitor multiple Telegram groups and channels simultaneously
- **Smart Deduplication**: Same event posted in multiple groups is automatically deduplicated
- **Rich Filtering**: Filter events by date, category, location, price, and event type
- **Event Types**: Supports single events, multi-day events, recurring events, and course series
- **Beautiful UI**: Modern, responsive web interface inspired by Luma
- **Stale Sync Detection**: Automatically detects and allows restart of interrupted syncs

## Screenshots

The web interface displays events in a clean card-based layout with:
- Date and time
- Location (city, country, venue)
- Price information
- Category badges
- Event type indicators
- Direct links to original Telegram messages

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram API credentials (get from https://my.telegram.org)
- Claude API access (via Anthropic or compatible proxy)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/kryptokommunist/telegram-autocalendar.git
   cd telegram-autocalendar
   ```

2. **Create secrets file**
   ```bash
   cat > .secrets << EOF
   api_id
   YOUR_TELEGRAM_API_ID
   api_hash
   YOUR_TELEGRAM_API_HASH
   EOF
   ```

3. **Configure environment** (optional)

   Edit `docker-compose.yml` to set:
   - `GENAI_PROXY_URL`: Your Claude API endpoint
   - `GENAI_API_KEY`: Your API key
   - `MYSQL_PASSWORD`: Database password

4. **Start the application**
   ```bash
   docker-compose up -d
   ```

5. **Open the web interface**

   Navigate to http://localhost:5050

6. **Authenticate with Telegram**

   Go to http://localhost:5050/auth and complete the Telegram authentication flow

7. **Configure groups**

   Go to http://localhost:5050/settings to select which groups to monitor

## Architecture

```
telegram-autocalendar/
├── src/
│   ├── config.py          # Configuration management
│   ├── database.py        # MySQL database operations
│   ├── telegram_client.py # Telethon wrapper for Telegram API
│   ├── llm_processor.py   # Claude AI event extraction
│   ├── scheduler.py       # Sync job runner
│   └── web/
│       ├── app.py         # Flask application
│       ├── routes.py      # API endpoints
│       ├── templates/     # Jinja2 templates
│       └── static/        # CSS, JS, uploads
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/events` | GET | List events with filters |
| `/api/events/<id>` | GET | Get single event details |
| `/api/categories` | GET | List all categories |
| `/api/groups` | GET | List groups with events |
| `/api/locations` | GET | Get distinct cities/countries |
| `/api/sync` | POST | Trigger manual sync |
| `/api/sync/status` | GET | Get sync progress |
| `/api/status` | GET | Get auth and sync status |

### Event Filters

The `/api/events` endpoint supports:
- `category_id`: Filter by category
- `date_from`, `date_to`: Date range filter
- `chat_id`: Filter by source group
- `price_type`: `free` or `paid`
- `max_price`: Maximum price filter
- `city`, `country`: Location filters
- `event_type`: `single`, `multiday`, `recurring`, or `series`
- `limit`, `offset`: Pagination

## Event Extraction

The LLM processor extracts:
- **Title**: Brief descriptive event title
- **Date/Time**: Start and end times (handles relative dates like "this Saturday")
- **Location**: Venue, city, and country
- **Price**: Free, paid, or price range
- **Organizer**: Event host/organizer
- **Category**: Auto-categorized (reuses existing categories when possible)
- **Event Type**: Single, multi-day, recurring, or series
- **Description**: 1-2 sentence summary
- **Link**: Registration or info URL

## Sync Behavior

- **Incremental**: Only processes new messages since last sync
- **Cron**: Automatic sync every 30 minutes (configurable)
- **Manual**: Trigger sync from web UI
- **Stale Detection**: Syncs stuck for >5 minutes can be force-restarted

## Development

### Running locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up MySQL database
mysql -u root -e "CREATE DATABASE telegram_events"
mysql -u root telegram_events < schema.sql

# Run the web server
python -m src.web.app
```

### Running tests

```bash
pytest tests/
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MYSQL_HOST` | `mysql` | Database host |
| `MYSQL_USER` | `telegram_user` | Database user |
| `MYSQL_PASSWORD` | `telegram_events_pass` | Database password |
| `MYSQL_DATABASE` | `telegram_events` | Database name |
| `GENAI_PROXY_URL` | - | Claude API endpoint |
| `GENAI_API_KEY` | - | Claude API key |
| `GENAI_MODEL` | `claude-sonnet-4-20250514` | Model to use |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Claude](https://anthropic.com/claude) - AI for event extraction
