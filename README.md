# Zabbix Telegram Bot

A Telegram bot for Zabbix monitoring system that provides alerts, screenshots, and AI-powered analysis.

Bot Telegram để giám sát và quản lý Zabbix, tích hợp với AI để phân tích và dự đoán.

## Features / Tính năng

### For All Users / Cho mọi người dùng
- `/dashboard` - Take screenshot of Zabbix dashboard / Chụp ảnh dashboard Zabbix
- `/help` - Show usage guide / Hiển thị hướng dẫn sử dụng

### Admin Only Features / Chỉ dành cho admin
- `/alerts` - View latest alerts with automatic screenshots for URLs / Xem cảnh báo mới nhất kèm ảnh chụp tự động
- `/hosts` - List all monitored hosts and their status / Liệt kê các host đang giám sát
- `/problems` - View active problems from dashboard ID 10 (Warning and above) / Xem các problem đang tồn tại từ dashboard ID 10 (từ Warning trở lên)
- `/graph` - Get performance graphs for specific items / Xem biểu đồ hiệu suất
- `/askai` - Ask questions about Zabbix using AI / Hỏi đáp về Zabbix với AI
- `/analyze` - Get trend analysis and predictions / Phân tích và dự đoán xu hướng
- `/users` - List all bot users / Xem danh sách người dùng
- `/removeuser` - Remove a user from the bot / Xóa người dùng khỏi bot

### Data Management / Quản lý dữ liệu
- Automatic data retention (3 months) / Tự động xóa dữ liệu cũ (3 tháng)
- Daily cleanup of old data / Dọn dẹp dữ liệu hàng ngày
- Duplicate alert prevention / Ngăn chặn cảnh báo trùng lặp
- Error pattern tracking and analysis / Theo dõi và phân tích pattern lỗi

## Installation / Cài đặt

1. Clone the repository:
```bash
git clone https://github.com/yourusername/zabbix-telegram-bot.git
cd zabbix-telegram-bot
```

2. Install required packages:
```bash
pip install python-telegram-bot python-dotenv zabbix-api selenium webdriver-manager matplotlib schedule requests
```

3. Install Chrome browser:
```bash
# Ubuntu/Debian
sudo apt-get install google-chrome-stable

# CentOS/RHEL
sudo yum install google-chrome-stable
```

4. Create a `.env` file with the following variables:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_IDS=id1,id2,id3

# Zabbix
ZABBIX_URL=https://your-zabbix-server
ZABBIX_USER=your-username
ZABBIX_PASSWORD=your-password

# Screenshot
SCREENSHOT_WIDTH=1920
SCREENSHOT_HEIGHT=1080

# AI Integration
OPENWEBUI_API_URL=your_openwebui_api_url
OPENWEBUI_API_KEY=your_openwebui_api_key
```

5. Run the bot:
```bash
python bot.py
```

## Database Structure / Cấu trúc Database

The bot uses SQLite database (`zabbix_alerts.db`) with the following tables:

### Alerts Table / Bảng cảnh báo
- Stores alert information / Lưu thông tin cảnh báo
- Automatically cleaned up after 3 months / Tự động xóa sau 3 tháng
- Prevents duplicate alerts / Ngăn chặn cảnh báo trùng lặp

### Error Patterns Table / Bảng pattern lỗi
- Tracks error patterns and solutions / Theo dõi pattern lỗi và giải pháp
- Includes frequency and last update time / Bao gồm tần suất và thời gian cập nhật
- Helps in trend analysis / Hỗ trợ phân tích xu hướng

### Users Table / Bảng người dùng
- Stores user information / Lưu thông tin người dùng
- Tracks user status (active/removed) / Theo dõi trạng thái người dùng
- Records join date / Ghi lại ngày tham gia

## Data Retention Policy / Chính sách lưu trữ dữ liệu

- Alerts are automatically deleted after 3 months / Cảnh báo tự động xóa sau 3 tháng
- Error patterns are removed if not updated for 3 months / Pattern lỗi bị xóa nếu không cập nhật trong 3 tháng
- Daily cleanup process to maintain database size / Quá trình dọn dẹp hàng ngày để duy trì kích thước database
- Automatic duplicate detection for alerts / Tự động phát hiện cảnh báo trùng lặp

## Usage Notes / Lưu ý sử dụng

1. Ensure server has enough RAM for Chrome headless / Đảm bảo server có đủ RAM để chạy Chrome headless
2. Configure firewall to allow Zabbix server connection / Cấu hình firewall cho phép kết nối đến Zabbix server
3. Check Zabbix user permissions / Kiểm tra quyền truy cập của user Zabbix
4. Regular database backup / Backup database thường xuyên
5. Configure Open WebUI API for AI features / Cấu hình API Open WebUI để sử dụng tính năng AI

### Problem Monitoring / Giám sát Problem
- Shows last 20 active problems / Hiển thị 20 problem đang tồn tại
- Filters by severity (Warning and above) / Lọc theo mức độ (từ Warning trở lên)
- Only from dashboard ID 10 / Chỉ từ dashboard ID 10
- Admin access only / Chỉ dành cho admin

## Troubleshooting / Xử lý sự cố

If you encounter issues, please check: / Nếu gặp vấn đề, vui lòng kiểm tra:
1. Check logs / Kiểm tra logs
2. Verify .env configuration / Xác nhận cấu hình trong file .env
3. Test Zabbix server connection / Kiểm tra kết nối đến Zabbix server
4. Verify user permissions / Kiểm tra quyền truy cập của user
5. Ensure Chrome browser is properly installed / Đảm bảo Chrome browser đã được cài đặt đúng cách

## Contributing / Đóng góp

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License / Giấy phép

This project is licensed under the MIT License - see the LICENSE file for details. 