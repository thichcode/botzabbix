import sqlite3
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from config import Config

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

@contextmanager
def get_db_connection(db_path=Config.DB_PATH):
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=Config.DB_TIMEOUT)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Database connection error: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

def init_db(db_path=Config.DB_PATH):
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            
            c.execute('''CREATE TABLE IF NOT EXISTS alerts
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          trigger_id TEXT,
                          host TEXT,
                          description TEXT,
                          priority INTEGER,
                          timestamp INTEGER,
                          status TEXT,
                          resolution TEXT,
                          analysis TEXT)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS error_patterns
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          pattern TEXT,
                          description TEXT,
                          solution TEXT,
                          frequency INTEGER,
                          last_updated INTEGER)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY,
                          username TEXT,
                          first_name TEXT,
                          last_name TEXT,
                          join_date INTEGER,
                          is_active BOOLEAN DEFAULT 1)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS host_websites
                         (host TEXT PRIMARY KEY,
                          website_url TEXT,
                          screenshot_enabled BOOLEAN DEFAULT 1)''')
            
            conn.commit()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def save_user(user_id: int, username: str, first_name: str, last_name: str) -> bool:
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO users 
                         (id, username, first_name, last_name, join_date, is_active)
                         VALUES (?, ?, ?, ?, ?, 1)''',
                      (user_id, username, first_name, last_name, int(time.time())))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        return False

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def remove_user(user_id: int) -> bool:
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error removing user: {str(e)}")
        return False

def save_alert(trigger_id, host, description, priority, timestamp) -> bool:
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO alerts 
                         (trigger_id, host, description, priority, timestamp)
                         VALUES (?, ?, ?, ?, ?)''',
                      (trigger_id, host, description, priority, timestamp))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving alert: {e}")
        return False

def add_host_website(host: str, url: str, enabled: bool) -> bool:
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO host_websites (host, website_url, screenshot_enabled)
                         VALUES (?, ?, ?)''', (host, url, enabled))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error inserting host website: {e}")
        return False

def get_host_website(host: str) -> Optional[tuple]:
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT website_url, screenshot_enabled FROM host_websites WHERE host = ?', (host,))
            return c.fetchone()
    except Exception as e:
        logger.error(f"Error fetching host website: {e}")
        return None

def cleanup_old_data():
    try:
        cutoff_time = int(time.time()) - Config.DATA_RETENTION_PERIOD
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_time,))
            alerts_deleted = c.rowcount
            c.execute('DELETE FROM error_patterns WHERE last_updated < ?', (cutoff_time,))
            patterns_deleted = c.rowcount
            conn.commit()
            logger.info(f"Cleaned up {alerts_deleted} old alerts and {patterns_deleted} old patterns")
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
