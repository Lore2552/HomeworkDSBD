CREATE TABLE IF NOT EXISTS flights (
    id SERIAL PRIMARY KEY,
    icao24 VARCHAR(24) NOT NULL,
    callsign VARCHAR(20),
    origin_country VARCHAR(100),
    time_position INTEGER,
    last_contact INTEGER,
    longitude FLOAT,
    latitude FLOAT,
    baro_altitude FLOAT,
    on_ground BOOLEAN,
    velocity FLOAT,
    true_track FLOAT,
    vertical_rate FLOAT,
    sensors INTEGER[],
    geo_altitude FLOAT,
    squawk VARCHAR(20),
    spi BOOLEAN,
    position_source INTEGER,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indice per ricerche geografiche veloci
CREATE INDEX idx_flights_location ON flights (longitude, latitude);
CREATE INDEX idx_flights_collected_at ON flights (collected_at);

CREATE TABLE IF NOT EXISTS user_airports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    airport_code VARCHAR(10) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, airport_code)
);

CREATE TABLE IF NOT EXISTS collection_log (
    id SERIAL PRIMARY KEY,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    flights_count INTEGER,
    status VARCHAR(50),
    error_message TEXT
);
