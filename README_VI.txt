PEARL OF HEAVEN - AEGIS GUARD - WINDOWS PACKAGE

Gói này dùng bot.py từ file bot(2).py do bạn cung cấp. Vì không có dashboard.py
và config.json gốc, dashboard.py và config.json ở đây là bản thay thế tối giản,
KHÔNG phải dashboard nguyên gốc. Dashboard mới chỉ xem trạng thái trên máy cục bộ.

CÀI ĐẶT (PC Windows 10/11):
1. Giải nén toàn bộ ZIP vào thư mục cố định, ví dụ C:\PEARL_OF_HEAVEN.
2. Cài Python 3.11 hoặc 3.12, đánh dấu Add Python to PATH.
3. Chạy INSTALL_FIRST.bat (cần Internet để cài thư viện).
4. Mở .env bằng Notepad, thay PASTE_BOT_TOKEN_HERE bằng token BOT của bạn.
   GUILD_ID: ID server Discord; để 0 sẽ đồng bộ lệnh toàn cục, có thể chậm hiện.
5. Trên Discord Developer Portal bật SERVER MEMBERS INTENT và MESSAGE CONTENT INTENT.
   Cấp bot quyền View Audit Log, Manage Roles, Moderate Members, Manage Channels,
   View Channels và Send Messages; vai trò bot phải đứng cao hơn vai trò cần xử lý.
6. Chạy START_BOT.bat. Đợi dòng "Aegis Guard online".
7. Trên CHÍNH máy chạy bot, mở http://127.0.0.1:8080 (không thêm ?utm_source).
8. Trong Discord, dùng /guard setup chọn kênh log và /guard backup để sao lưu.

CHẠY LÂU DÀI:
- START_BOT.bat tự chạy lại khi bot thoát lỗi; giữ cửa sổ mở.
- Tắt chế độ Sleep của Windows và giữ PC bật, kết nối mạng.
- Muốn chạy khi đăng nhập Windows: Win+R > shell:startup > tạo shortcut tới START_BOT.bat.
- Khi Windows bị tắt hoàn toàn, bot không chạy. Sau khi bật lại và đăng nhập,
  shortcut Startup mới hoạt động. Nếu muốn tự chạy trước đăng nhập cần Task Scheduler
  cấu hình riêng trên máy bạn có quyền quản trị.
- Không dùng máy tính công cộng để lưu token bot lâu dài.

BẢO MẬT:
- KHÔNG gửi file .env có token cho người khác; chỉ gửi ZIP mẫu này.
- Người vận hành bot cần giữ token bí mật. Nếu lộ, reset token ngay.
- Dashboard chỉ bind 127.0.0.1, KHÔNG truy cập trực tiếp từ iPhone/Internet.
- Không mở port 8080 ra Internet; muốn truy cập từ xa cần VPN/zero-trust có xác thực.
- Sao lưu thư mục backups và config.json định kỳ.

GIỚI HẠN:
- Bot phát hiện sau khi audit log ghi nhận hành động, không đảm bảo ngăn được
  hành động phá hoại đầu tiên.
- Hình phạt hiện tại chỉ gỡ role có thể quản lý, không ban/kick thủ phạm.
- Chức năng restore chỉ dựng lại role/kênh cơ bản, không khôi phục tin nhắn,
  permission overrides, thứ tự chính xác hoặc toàn bộ metadata.
- Nếu trùng tên role/kênh, restore có thể bỏ qua tài nguyên bị thiếu.
- Cần thử nghiệm trên server test trước khi dùng ở server thật.
