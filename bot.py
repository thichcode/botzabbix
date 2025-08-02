import os
import logging
import datetime
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
from config import Config
from db import init_db, cleanup_old_data
from commands.dashboard import DashboardCommand
from commands.get_alerts import GetAlertsCommand
from commands.get_hosts import GetHostsCommand
from commands.get_graph import GetGraphCommand
from commands.ask_ai import AskAICommand
from commands.analyze import AnalyzeCommand
from commands.add_website import AddWebsiteCommand
from commands.start import StartCommand
from commands.help import HelpCommand
from utils import setup_secure_logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Setup secure logging to mask sensitive data
setup_secure_logging()

def main() -> None:
    """Start the bot."""
    # Load environment variables
    load_dotenv()

    # Validate configuration
    errors = Config.validate()
    if errors:
        for error in errors:
            logger.error(error)
        return

    # Initialize database
    init_db()

    # Log safe configuration info
    safe_config = Config.get_safe_config_info()
    logger.info("Bot configuration loaded successfully")
    logger.info(f"Zabbix URL: {safe_config['zabbix_url']}")
    logger.info(f"Zabbix User: {safe_config['zabbix_user']}")
    logger.info(f"Zabbix Auth Method: {'Token' if safe_config['zabbix_token'] else 'Username/Password'}")
    logger.info(f"Admin IDs: {safe_config['admin_ids']}")
    logger.info(f"Host Groups: {safe_config['host_groups']}")

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", StartCommand().execute))
    application.add_handler(CommandHandler("help", HelpCommand().execute))
    application.add_handler(CommandHandler("dashboard", DashboardCommand().execute))
    application.add_handler(CommandHandler("getalerts", GetAlertsCommand().execute))
    application.add_handler(CommandHandler("gethosts", GetHostsCommand().execute))
    application.add_handler(CommandHandler("getgraph", GetGraphCommand().execute))
    application.add_handler(CommandHandler("ask", AskAICommand().execute))
    application.add_handler(CommandHandler("analyze", AnalyzeCommand().execute))
    application.add_handler(CommandHandler("addwebsite", AddWebsiteCommand().execute))

    # Schedule daily cleanup
    job_queue = application.job_queue
    job_queue.run_daily(cleanup_old_data, time=datetime.time(hour=1, minute=0))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
