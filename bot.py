import os
import logging
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
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
