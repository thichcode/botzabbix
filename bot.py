import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import time

from config import Config
from db import init_db, save_user
from commands.get_alerts import GetProblemsCommand
from commands.get_hosts import GetHostsCommand
from commands.get_graph import GetGraphCommand
from commands.dashboard import DashboardCommand
from commands.ask_ai import AskAiCommand
from commands.analyze import AnalyzeCommand
from commands.add_website import AddWebsiteCommand


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Add rotating file handler
import logging.handlers
file_handler = logging.handlers.RotatingFileHandler(
    'bot.log', maxBytes=10*1024*1024, backupCount=5
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("Bạn không có quyền sử dụng bot này.")
        return
    save_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f"Xin chào {user.first_name}! 👋\n"
        "Tôi là bot giám sát cảnh báo Zabbix.\n\n"
        "**Các lệnh có sẵn:**\n"
        "📊 `/getproblems` - Lấy problems mới nhất\n"
        "🖥️ `/gethosts` - Lấy danh sách hosts\n"
        "📈 `/graph <host/IP>` - Lấy biểu đồ hiệu suất\n"
        "🖼️ `/dashboard` - Chụp ảnh dashboard Zabbix\n"
        "🤖 `/ask <host/IP>` - Phân tích thông tin hệ thống với AI\n"
        "📊 `/analyze` - Phân tích và dự đoán xu hướng\n"
        "🌐 `/addwebsite <host> <url> [enabled]` - Thêm website cho host\n"
        "💚 `/health` - Kiểm tra trạng thái bot",
        parse_mode='Markdown'
    )

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check command"""
    user = update.effective_user
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return
    
    try:
        await update.message.reply_text("🔍 Đang kiểm tra trạng thái bot...")
        
        # Test Zabbix connection
        from zabbix import get_zabbix_api
        zapi = get_zabbix_api()
        version = zapi.api_version()
        
        # Test database connection
        from db import get_db_connection
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        
        # Test AI API if configured
        ai_status = "✅ Đã cấu hình" if Config.OPENWEBUI_API_URL and Config.OPENWEBUI_API_KEY else "❌ Chưa cấu hình"
        
        status_message = f"""💚 **Trạng thái Bot: HOẠT ĐỘNG BÌNH THƯỜNG**

🔗 **Kết nối Zabbix:** ✅ Hoạt động
📊 **Zabbix API Version:** {version}
🗄️ **Database:** ✅ Hoạt động
🤖 **AI Service:** {ai_status}

⏰ **Thời gian kiểm tra:** {time.strftime('%Y-%m-%d %H:%M:%S')}"""
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = f"""❌ **Trạng thái Bot: CÓ VẤN ĐỀ**

🔗 **Lỗi:** {str(e)}
⏰ **Thời gian:** {time.strftime('%Y-%m-%d %H:%M:%S')}

Vui lòng kiểm tra logs để biết thêm chi tiết."""
        
        await update.message.reply_text(error_message, parse_mode='Markdown')
        logger.error(f"Health check failed: {str(e)}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id not in Config.ADMIN_IDS:
        await query.edit_message_text("Bạn không có quyền sử dụng tính năng này.")
        return
    
    try:
        data = query.data
        
        if data.startswith("graph_"):
            # Format: graph_hostid_itemid_period
            parts = data.split("_")
            if len(parts) >= 4:
                hostid = parts[1]
                itemid = parts[2]
                period = int(parts[3])
                
                await query.edit_message_text("Đang tạo biểu đồ...")
                
                graph_command = GetGraphCommand()
                await graph_command.create_graph(update, hostid, itemid, period)
                
                # Xóa message "Đang tạo biểu đồ..."
                await query.edit_message_text("✅ Biểu đồ đã được tạo!")
        
        elif data.startswith("search_items_"):
            # Format: search_items_hostid
            hostid = data.split("_")[2]
            
            await query.edit_message_text("Tính năng tìm kiếm thêm items sẽ được phát triển trong phiên bản tiếp theo.")
    
    except Exception as e:
        logger.error(f"Error handling callback query: {str(e)}")
        await query.edit_message_text(f"Lỗi khi xử lý yêu cầu: {str(e)}")

def main() -> None:
    """Start the bot."""
    # Validate configuration
    config_errors = Config.validate()
    if config_errors:
        logger.error("Configuration errors:")
        for error in config_errors:
            logger.error(f"  - {error}")
        return
    
    # Initialize database
    init_db()
    
    # Create the Application and pass it your bot's token.
    # Configure proxy using Cloudflare Worker if provided
    application_builder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)

    if Config.USE_PROXY and Config.TELEGRAM_PROXY_URL:
        application_builder.proxy_url(Config.TELEGRAM_PROXY_URL)
        logger.info(f"Using proxy for Telegram connection: {Config.TELEGRAM_PROXY_URL}")
    else:
        logger.info("No proxy configured for Telegram connection.")
        
    application = application_builder.build()

    # Add handlers for commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(CommandHandler("getproblems", GetProblemsCommand().execute))
    application.add_handler(CommandHandler("gethosts", GetHostsCommand().execute))
    application.add_handler(CommandHandler("graph", GetGraphCommand().execute))
    application.add_handler(CommandHandler("dashboard", DashboardCommand().execute))
    application.add_handler(CommandHandler("ask", AskAiCommand().execute))
    application.add_handler(CommandHandler("analyze", AnalyzeCommand().execute))
    application.add_handler(CommandHandler("addwebsite", AddWebsiteCommand().execute))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Start the Bot
    logger.info("Starting bot...")
    
    # Start the Bot
    logger.info("Starting bot...")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}")
        raise

if __name__ == '__main__':
    main()
