# Kiểm chứng trước khi xuất bản

Ngày: 09/10/2026. Môi trường: Windows, Python 3.11.9, thư viện chuẩn.

- Tạo venv mới tại root bộ mã xuất bản, chạy đúng lệnh README: 35 phương thức test đạt.
- Chạy 10 demo A–J; status, reason, steps, tool_calls và output khớp phiên bản trong bài.
- Chạy riêng `--case A --json`: completed/criteria_met, 2 bước, 1 lần thử tool,
  output 100000 VND và một bằng chứng tool.
- Biên dịch cú pháp cả năm file bằng `py_compile` thành công.
- Năm file Python xuất bản khớp từng byte với nguồn chuẩn trong gói bài viết.
- Log ở [verification/tests.txt](verification/tests.txt), [verification/demo.txt](verification/demo.txt)
  và [verification/case-a.json](verification/case-a.json).
- [verification/reproduction.txt](verification/reproduction.txt) lưu lần tái dựng ba file
  tools/contracts/controller từ snippet LaTeX, ghép demo/test đi kèm rồi chạy trong venv mới:
  35 test đạt. Đây là kiểm tra trước bước chuẩn bị repo.

Hai lỗi logic đã sửa và có test hồi quy: planner sửa lịch sử chung để giả mạo bằng chứng;
cờ phê duyệt dạng chuỗi hoặc số được coi là truthy. Controller gửi bản sao sâu của lịch sử,
kiểm kiểu bool của hai cờ trước planner khi đầu vào đầy đủ.

Demo dùng planner theo kịch bản, đồng hồ giả cho G và lỗi giả cho D/F/I;
tool tính tiền dùng số nguyên chạy thật. Chưa gọi LLM/API thật, chưa xác minh macOS/Linux
trực tiếp; lệnh cho các hệ đó dùng cùng code và Python trong venv.
Soft deadline không hủy hàm đang chạy. Chưa triển khai phê duyệt thực,
checkpoint/resume, nhóm tool, timeout/backoff mạng hoặc ngân sách token/chi phí.
