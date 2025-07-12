import asyncio
import logging
import time
from datetime import datetime, timedelta
from db import cleanup_old_data, get_db_connection
from config import Config

logger = logging.getLogger(__name__)

class DatabaseScheduler:
    """Scheduler for database maintenance tasks"""
    
    def __init__(self):
        self.running = False
        self.cleanup_interval = 24 * 60 * 60  # 24 hours in seconds
        
    async def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info("Database scheduler started")
        
        while self.running:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in database scheduler: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Database scheduler stopped")
    
    async def _perform_cleanup(self):
        """Perform database cleanup"""
        try:
            logger.info("Starting database cleanup...")
            start_time = time.time()
            
            cleanup_old_data()
            
            # Get database statistics
            stats = await self._get_database_stats()
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"Database cleanup completed in {duration:.2f}s. Stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
    
    async def _get_database_stats(self):
        """Get database statistics"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Count alerts
                cursor.execute("SELECT COUNT(*) FROM alerts")
                alert_count = cursor.fetchone()[0]
                
                # Count users
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                user_count = cursor.fetchone()[0]
                
                # Count error patterns
                cursor.execute("SELECT COUNT(*) FROM error_patterns")
                pattern_count = cursor.fetchone()[0]
                
                # Get database size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                
                return {
                    "alerts": alert_count,
                    "active_users": user_count,
                    "error_patterns": pattern_count,
                    "db_size_mb": round(db_size / (1024 * 1024), 2)
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {"error": str(e)}

# Global scheduler instance
scheduler = DatabaseScheduler()

async def start_scheduler():
    """Start the database scheduler"""
    await scheduler.start()

def stop_scheduler():
    """Stop the database scheduler"""
    asyncio.create_task(scheduler.stop()) 