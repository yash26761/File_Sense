-- FileSense Audit Database Schema
CREATE TABLE IF NOT EXISTS scan_history (
    scan_id SERIAL PRIMARY KEY,
    folder_path TEXT NOT NULL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_files INT NOT NULL,
    total_bytes BIGINT NOT NULL,
    duplicate_groups INT DEFAULT 0,
    recoverable_bytes BIGINT DEFAULT 0
);
