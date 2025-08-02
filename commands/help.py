import logging
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only

logger = logging.getLogger(__name__)

class HelpCommand:
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed help information"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            from config import Config
            is_admin = user_id in Config.ADMIN_IDS
            
            help_message = """
📚 **HƯỚNG DẪN SỬ DỤNG BOT ZABBIX**

🤖 **Giới thiệu:**
Bot này giúp bạn giám sát và quản lý hệ thống Zabbix thông qua Telegram, tích hợp với AI để phân tích và dự đoán vấn đề.

📋 **LỆNH CHO MỌI NGƯỜI DÙNG:**

**/start** - Hiển thị menu chính và danh sách lệnh
**/help** - Hiển thị hướng dẫn chi tiết này
**/dashboard** - Chụp ảnh dashboard Zabbix hiện tại

"""
            
            if is_admin:
                admin_help = """
🔐 **LỆNH CHỈ DÀNH CHO ADMIN:**

**📊 Giám sát hệ thống:**
• `/getalerts` - Xem 10 problems mới nhất được lọc theo host groups
• `/gethosts` - Liệt kê tất cả host đang giám sát và trạng thái
• `/getgraph <host/IP>` - Tạo biểu đồ hiệu suất cho host cụ thể

**🤖 Phân tích AI:**
• `/ask <host/IP>` - Phân tích thông tin hệ thống với AI
  - Thu thập dữ liệu CPU, RAM, Disk, Network
  - Đưa ra đánh giá và khuyến nghị tối ưu hóa
  - Dự đoán xu hướng sử dụng tài nguyên

• `/analyze` - Phân tích problems và dự đoán vấn đề
  - Phân tích problems trong 3 ngày qua
  - Xác định hosts có vấn đề nghiêm trọng
  - Tìm mối quan hệ phụ thuộc giữa hosts
  - Dự đoán vấn đề có thể xảy ra tiếp theo

**🌐 Quản lý website:**
• `/addwebsite` - Thêm website để chụp ảnh

**👥 Quản lý người dùng:**
• `/users` - Xem danh sách tất cả người dùng bot
• `/removeuser` - Xóa người dùng khỏi bot

"""
                help_message += admin_help
            
            help_message += """
💡 **HƯỚNG DẪN SỬ DỤNG CHI TIẾT:**

**📊 Lệnh /getgraph:**
```
/getgraph server01
/getgraph 192.168.1.100
```
- Bot sẽ hiển thị danh sách items phổ biến (CPU, Memory, Disk, Network)
- Sử dụng inline keyboard để chọn nhanh
- Biểu đồ hiển thị thống kê: hiện tại, trung bình, max, min

**🤖 Lệnh /ask:**
```
/ask server01
/ask 192.168.1.100
```
- Thu thập thông tin hệ thống từ Zabbix
- Phân tích hiệu suất với AI
- Đưa ra khuyến nghị tối ưu hóa

**📈 Lệnh /analyze:**
```
/analyze
```
- Phân tích toàn bộ problems trong 3 ngày
- Tìm patterns và mối quan hệ
- Dự đoán vấn đề tương lai

🔧 **TÍNH NĂNG ĐẶC BIỆT:**
• Tự động chụp ảnh cho mỗi problem
• Dọn dẹp dữ liệu cũ sau 3 tháng
• Ngăn chặn cảnh báo trùng lặp
• Phân tích pattern lỗi và giải pháp
• Hỗ trợ nhiều host groups

📞 **HỖ TRỢ:**
Nếu gặp vấn đề, vui lòng liên hệ admin hoặc kiểm tra log của bot.
"""
            
            await update.message.reply_text(help_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý lệnh help: {str(e)}")
            await update.message.reply_text("Có lỗi xảy ra khi xử lý lệnh. Vui lòng thử lại sau.") 