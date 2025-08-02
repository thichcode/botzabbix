import logging
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only

logger = logging.getLogger(__name__)

class StartCommand:
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show welcome message and available commands"""
        try:
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name
            
            # Check if user is admin
            from config import Config
            is_admin = user_id in Config.ADMIN_IDS
            
            welcome_message = f"""
🤖 **Chào mừng {user_name}!**

Đây là bot Telegram để giám sát và quản lý Zabbix, tích hợp với AI để phân tích và dự đoán.

📋 **Các lệnh có sẵn:**

**Cho mọi người dùng:**
• `/start` - Hiển thị hướng dẫn này
• `/help` - Hiển thị hướng dẫn sử dụng chi tiết
• `/dashboard` - Chụp ảnh dashboard Zabbix

"""

            if is_admin:
                admin_commands = """
**Chỉ dành cho Admin:**
• `/getalerts` - Xem problems mới nhất được lọc theo host groups
• `/gethosts` - Liệt kê các host đang giám sát
• `/getgraph <host/IP>` - Lấy biểu đồ hiệu suất với gợi ý items
• `/ask <host/IP>` - Phân tích thông tin hệ thống với AI
• `/analyze` - Phân tích problems và dự đoán vấn đề hệ thống
• `/addwebsite` - Thêm website để chụp ảnh

**Quản lý người dùng:**
• `/users` - Xem danh sách người dùng bot
• `/removeuser` - Xóa người dùng khỏi bot
"""
                welcome_message += admin_commands
            
            welcome_message += """
💡 **Lưu ý:**
• Sử dụng `/help` để xem hướng dẫn chi tiết cho từng lệnh
• Bot tự động dọn dẹp dữ liệu cũ sau 3 tháng
• Hỗ trợ chụp ảnh dashboard và phân tích AI

🔧 **Hỗ trợ:**
Nếu cần hỗ trợ, vui lòng liên hệ admin.
"""
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý lệnh start: {str(e)}")
            await update.message.reply_text("Có lỗi xảy ra khi xử lý lệnh. Vui lòng thử lại sau.") 