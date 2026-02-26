-- Telegram Auto-Calendar Database Schema

-- Categories table (LLM-generated, grows dynamically)
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial categories
INSERT INTO categories (name, description) VALUES
    ('Tech & Startup', 'Technology meetups, hackathons, startup events'),
    ('Networking', 'Professional networking, business mixers'),
    ('Social', 'Casual hangouts, parties, social gatherings'),
    ('Sports & Fitness', 'Sports events, fitness classes, outdoor activities'),
    ('Arts & Culture', 'Art exhibitions, concerts, theater, cultural events'),
    ('Education', 'Workshops, courses, lectures, learning events'),
    ('Food & Drink', 'Food festivals, tastings, restaurant openings'),
    ('Music & Nightlife', 'Concerts, DJ sets, club events'),
    ('Community', 'Local community events, volunteer opportunities'),
    ('Conference', 'Large conferences, summits, industry events');

-- Events table (enhanced)
CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    chat_name VARCHAR(255),
    event_title VARCHAR(500) NOT NULL,
    event_start DATETIME,
    event_end DATETIME,
    event_location VARCHAR(500),
    city VARCHAR(100),
    country VARCHAR(100),
    event_description TEXT,
    event_description_full TEXT,
    event_link VARCHAR(1000),
    ticket_price VARCHAR(100),
    organizer VARCHAR(255),
    category_id INT,
    image_path VARCHAR(500),
    original_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_message (message_id, chat_id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Indexes for filtering
CREATE INDEX idx_events_category ON events(category_id);
CREATE INDEX idx_events_start ON events(event_start);
CREATE INDEX idx_events_city ON events(city);
CREATE INDEX idx_events_country ON events(country);

-- Processed messages tracking (avoid reprocessing)
CREATE TABLE processed_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_processed (message_id, chat_id)
);

-- Telegram groups/channels metadata
CREATE TABLE telegram_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    chat_name VARCHAR(255),
    chat_description TEXT,
    chat_type ENUM('group', 'supergroup', 'channel') DEFAULT 'group',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Auth state for web-based Telegram auth
CREATE TABLE auth_state (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(50),
    phone_code_hash VARCHAR(255),
    status ENUM('pending_code', 'pending_2fa', 'authenticated') DEFAULT 'pending_code',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Sync status tracking
CREATE TABLE sync_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    status ENUM('idle', 'running', 'completed', 'error') DEFAULT 'idle',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    groups_total INT DEFAULT 0,
    groups_scanned INT DEFAULT 0,
    messages_processed INT DEFAULT 0,
    events_found INT DEFAULT 0,
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert initial sync status row
INSERT INTO sync_status (status) VALUES ('idle');

-- Table to track which groups are enabled for scanning
CREATE TABLE selected_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT TRUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- User settings
CREATE TABLE user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default setting for group selection completed
INSERT INTO user_settings (setting_key, setting_value) VALUES ('groups_configured', 'false');
