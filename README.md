# Zabbix Telegram Bot

A Telegram bot for Zabbix monitoring system that provides alerts, screenshots, and AI-powered analysis.

Bot Telegram để giám sát và quản lý Zabbix, tích hợp với AI để phân tích và dự đoán.

## Features / Tính năng

### For All Users / Cho mọi người dùng
- `/dashboard` - Take screenshot of Zabbix dashboard / Chụp ảnh dashboard Zabbix
- `/help` - Show usage guide / Hiển thị hướng dẫn sử dụng

### Admin Only Features / Chỉ dành cho admin
- `/getproblems` - View latest problems filtered by host groups / Xem problems mới nhất được lọc theo host groups
- `/hosts` - List all monitored hosts and their status / Liệt kê các host đang giám sát
- `/problems` - View active problems from dashboard ID 10 (Warning and above) / Xem các problem đang tồn tại từ dashboard ID 10 (từ Warning trở lên)
- `/graph <host/IP>` - Lấy biểu đồ hiệu suất với gợi ý items / Get performance graphs with item suggestions
- `/ask <host/IP>` - Phân tích thông tin hệ thống với AI / Analyze system information with AI
- `/analyze` - Phân tích problems và dự đoán vấn đề hệ thống / Analyze problems and predict system issues
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

# Host Groups for filtering problems (optional)
HOST_GROUPS=Production Servers,Web Servers,Database Servers

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
- Shows last 10 latest problems / Hiển thị 10 problems mới nhất
- Filters by host groups (configurable) / Lọc theo host groups (có thể cấu hình)
- Includes severity and acknowledgment status / Bao gồm mức độ nghiêm trọng và trạng thái xác nhận
- Admin access only / Chỉ dành cho admin
- Automatic screenshot for each problem / Tự động chụp ảnh cho mỗi problem

### AI System Analysis / Phân tích hệ thống với AI
- Tìm kiếm host theo tên hoặc IP / Search host by name or IP
- Thu thập thông tin CPU, RAM, disk, network / Collect CPU, RAM, disk, network information
- Phân tích hiệu suất hệ thống với AI / Analyze system performance with AI
- Đưa ra khuyến nghị tối ưu hóa / Provide optimization recommendations
- Dự đoán xu hướng sử dụng tài nguyên / Predict resource usage trends

### Problem Analysis & Prediction / Phân tích và dự đoán Problems
- Phân tích problems trong 3 ngày qua / Analyze problems from last 3 days
- Xác định hosts có vấn đề nghiêm trọng / Identify hosts with critical issues
- Phân tích mối quan hệ phụ thuộc giữa hosts / Analyze dependencies between hosts
- Tìm clusters problems xảy ra cùng lúc / Find problem clusters occurring simultaneously
- Dự đoán vấn đề có thể xảy ra tiếp theo / Predict potential future issues

### Performance Graphs / Biểu đồ hiệu suất
- Tìm kiếm host theo tên hoặc IP / Search host by name or IP
- Gợi ý items phổ biến (CPU, Memory, Disk, Network) / Suggest common items
- Tạo biểu đồ với thông tin chi tiết / Create graphs with detailed information
- Inline keyboard để chọn nhanh / Inline keyboard for quick selection
- Hiển thị thống kê (hiện tại, trung bình, max, min) / Display statistics

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

## Integration Guide / Hướng dẫn tích hợp

### 1. Tích hợp với Telegram
- Tạo bot mới trên Telegram bằng cách nhắn cho @BotFather và lấy token.
- Thêm token vào file `.env` với biến TELEGRAM_BOT_TOKEN.
- Thêm user ID của admin vào biến ADMIN_IDS (cách nhau bởi dấu phẩy).

### 2. Tích hợp với Zabbix
- Đảm bảo Zabbix server đã bật API (Zabbix >= 3.0).
- Tạo user trên Zabbix có quyền đọc dữ liệu (Read-only hoặc Admin).
- Lấy URL, username, password của Zabbix và điền vào file `.env`:
  - ZABBIX_URL
  - ZABBIX_USER
  - ZABBIX_PASSWORD
- Cấu hình host groups để lọc problems (tùy chọn):
  - HOST_GROUPS: Danh sách tên host groups cách nhau bởi dấu phẩy
  - Ví dụ: `HOST_GROUPS=Production Servers,Web Servers,Database Servers`
  - Nếu không cấu hình, sẽ lấy tất cả problems
- Đảm bảo server chạy bot có thể truy cập được Zabbix server qua mạng nội bộ hoặc internet.

### 3. Tích hợp AI (Open WebUI hoặc GPT API)
- Đăng ký tài khoản Open WebUI hoặc dịch vụ AI tương thích OpenAI API.
- Lấy API URL và API KEY, điền vào file `.env`:
  - OPENWEBUI_API_URL
  - OPENWEBUI_API_KEY
- Đảm bảo server chạy bot có thể truy cập được API AI này.

### 4. Tích hợp Screenshot (Selenium + Chrome)
- Cài đặt Google Chrome trên server.
- Đảm bảo các biến môi trường SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT đã được cấu hình trong `.env` (mặc định 1920x1080).
- Nếu chạy trên server Linux, nên cài đặt thêm các gói hỗ trợ headless Chrome (`libnss3`, `libgconf-2-4`, `fonts-liberation`, ...).

### 5. Tích hợp với hệ thống cảnh báo Zabbix (tùy chọn)
- Có thể cấu hình Zabbix gửi cảnh báo qua HTTP hoặc script để gọi API của bot Telegram này.
- Hoặc sử dụng bot để chủ động lấy cảnh báo từ Zabbix qua lệnh `/getproblems`.

### 6. Sử dụng tính năng AI phân tích hệ thống
- Tìm kiếm host: `/ask server01` hoặc `/ask 192.168.1.100`
- Bot sẽ tự động thu thập thông tin CPU, RAM, disk, network
- AI sẽ phân tích và đưa ra:
  - Đánh giá tổng quan hiệu suất hệ thống
  - Các vấn đề tiềm ẩn cần chú ý
  - Khuyến nghị tối ưu hóa
  - Dự đoán xu hướng sử dụng tài nguyên

### 7. Sử dụng tính năng phân tích và dự đoán problems
- Chạy phân tích: `/analyze`
- Bot sẽ phân tích problems trong 3 ngày qua và đưa ra:
  - **Tổng quan**: Số lượng problems, hosts bị ảnh hưởng, hosts critical
  - **Phân bố severity**: Thống kê theo mức độ nghiêm trọng
  - **Hosts có vấn đề**: Danh sách hosts có nhiều problems nhất
  - **Patterns phổ biến**: Các loại vấn đề thường xảy ra
  - **Mối quan hệ phụ thuộc**: Host nào phụ thuộc vào host nào
  - **Problem clusters**: Các vấn đề xảy ra cùng lúc
  - **Dự đoán**: Vấn đề nào có thể xảy ra tiếp theo
  - **Khuyến nghị**: Cách khắc phục và phòng ngừa

### 8. Sử dụng tính năng biểu đồ hiệu suất
- Tìm kiếm host: `/graph server01` hoặc `/graph 192.168.1.100`
- Bot sẽ hiển thị danh sách items phổ biến được nhóm theo category:
  - **CPU**: CPU utilization, load average
  - **Memory**: Memory usage, available memory
  - **Disk**: Disk usage, inode usage
  - **Network**: Network traffic, errors, dropped packets
  - **System**: Uptime, swap usage
  - **Processes**: Process count, status
  - **Services**: TCP port status
- Sử dụng inline keyboard để chọn nhanh CPU, Memory, Disk, Network
- Biểu đồ sẽ hiển thị:
  - Đường biểu đồ với màu sắc đẹp
  - Thông tin host và item
  - Thống kê (hiện tại, trung bình, max, min)
  - Khoảng thời gian và số điểm dữ liệu

### 9. Kiểm thử & Tích hợp CI/CD
- Chạy toàn bộ test bằng lệnh:
  ```bash
  python -m pytest test_bot.py -v
  ```
- Đảm bảo tất cả test đều pass trước khi deploy.
- Có thể tích hợp vào pipeline CI/CD (GitHub Actions, GitLab CI, Jenkins, ...).

### 10. Lưu ý khi tích hợp thực tế
- Luôn backup file database `zabbix_alerts.db` định kỳ.
- Đảm bảo file `.env` không bị public lên git.
- Kiểm tra log file `bot.log` để debug khi có lỗi.
- Có thể mở rộng thêm các API hoặc webhook tùy nhu cầu doanh nghiệp.

---
Nếu cần hướng dẫn chi tiết hơn cho từng môi trường (Linux, Windows, Docker, Cloud), hãy liên hệ hoặc để lại yêu cầu! 