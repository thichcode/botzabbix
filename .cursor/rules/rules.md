# Quy tắc code cho dự án bottelegram

## 1. Chất lượng code
- Code phải chạy được ngay, không được bịa API, hàm, class, biến hoặc import không tồn tại.
- Nếu không chắc chắn về một API/hàm, phải kiểm tra lại trong codebase trước khi sử dụng.
- Ưu tiên sử dụng các hàm, class, module đã có sẵn trong dự án.
- Nếu cần tạo mới, phải mô tả rõ ràng và tạo đầy đủ file/module/class/hàm đó.

## 2. Phong cách code
- Tuân thủ PEP8 cho Python.
- Tên biến, hàm, class phải rõ nghĩa, tiếng Anh, snake_case cho biến/hàm, PascalCase cho class.
- Thêm docstring cho class, function quan trọng.
- Thêm comment giải thích các đoạn code phức tạp.

## 3. Xử lý lỗi
- Luôn kiểm tra đầu vào (input validation) cho các hàm nhận dữ liệu từ ngoài (user, API).
- Sử dụng try/except hợp lý, log lỗi chi tiết, trả về thông báo rõ ràng cho user.

## 4. Đảm bảo không bịa đặt
- Không tự ý tạo ra các hàm, class, module, API, biến mà chưa có trong codebase hoặc chưa được yêu cầu tạo mới.
- Nếu cần tạo mới, phải hỏi lại hoặc mô tả rõ ràng lý do và cách sử dụng.

## 5. Đảm bảo code có thể chạy được
- Luôn kiểm tra import, dependency, và các file liên quan.
- Nếu thêm thư viện mới, phải cập nhật requirements.txt.
- Nếu sửa đổi cấu trúc project, phải cập nhật README.md nếu cần.

## 6. Test và kiểm thử
- Nếu có test, phải đảm bảo code mới không làm hỏng test cũ.
- Nếu thêm tính năng mới, nên bổ sung test nếu có thể.

## 7. Ngôn ngữ trả lời
- Luôn trả lời bằng tiếng Việt, trừ khi user yêu cầu ngược lại. 