import sqlite3
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = 'zabbix_alerts.db'
DB_TIMEOUT = 10
DATA_RETENTION_PERIOD = 90 * 24 * 60 * 60

class DatabaseError(Exception):
    pass

@contextmanager
def get_db_connection(db_path=DB_PATH):
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=DB_TIMEOUT)
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

def init_db(db_path=DB_PATH):
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

def save_user(user_id: int, username: str, first_name: str, last_name: str, db_path=DB_PATH) -> bool:
    try:
        with get_db_connection(db_path) as conn:
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

def get_user(user_id: int, db_path=DB_PATH) -> Optional[Dict[str, Any]]:
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def remove_user(user_id: int, db_path=DB_PATH):
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error removing user: {str(e)}")
        return False

def save_alert(trigger_id, host, description, priority, timestamp, db_path=DB_PATH):
    try:
        with get_db_connection(db_path) as conn:
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

def save_problem(problem_id, host, description, priority, timestamp, severity, db_path=DB_PATH):
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO alerts 
                         (trigger_id, host, description, priority, timestamp, status)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (problem_id, host, description, priority, timestamp, severity))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving problem: {e}")
        return False

def add_error_pattern(pattern: str, db_path=DB_PATH) -> bool:
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO error_patterns 
                         (pattern, description, solution, frequency, last_updated)
                         VALUES (?, NULL, NULL, 0, ?)''',
                      (pattern, int(time.time())))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding error pattern: {e}")
        return False

def get_error_patterns(db_path=DB_PATH) -> list:
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT pattern FROM error_patterns')
            return [row['pattern'] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error getting error patterns: {e}")
        return []

def remove_error_pattern(pattern: str, db_path=DB_PATH) -> bool:
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM error_patterns WHERE pattern = ?', (pattern,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error removing error pattern: {e}")
        return False

def cleanup_old_data(db_path=DB_PATH, retention_period=DATA_RETENTION_PERIOD):
    try:
        cutoff_time = int(time.time()) - retention_period
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_time,))
            alerts_deleted = c.rowcount
            c.execute('DELETE FROM error_patterns WHERE last_updated < ?', (cutoff_time,))
            patterns_deleted = c.rowcount
            conn.commit()
            logger.info(f"Cleaned up {alerts_deleted} old alerts and {patterns_deleted} old patterns")
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
