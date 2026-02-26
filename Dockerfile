FROM python:3.11-slim

# Install cron and other dependencies
RUN apt-get update && apt-get install -y \
    cron \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/session /app/src/web/static/uploads

# Set up cron job
COPY crontab /etc/cron.d/telegram-sync
RUN chmod 0644 /etc/cron.d/telegram-sync && \
    crontab /etc/cron.d/telegram-sync && \
    touch /var/log/cron.log

# Environment variables for cron
RUN printenv | grep -v "no_proxy" >> /etc/environment

EXPOSE 5000

# Default command runs the web app
CMD ["python", "-m", "src.web.app"]
