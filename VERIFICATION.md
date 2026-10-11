# Kiểm chứng Gemini 2.5 Flash

Ngày chạy: **11/10/2026**. Windows, Python 3.11.9; google-genai 2.29.0,
python-dotenv 1.2.4. Mọi đề xuất của planner trong các case cần model đều đến từ
API `gemini-2.5-flash`; ghi response_id, model_version và token thực tế.

## Kết quả thực tế

- `python -m unittest -v test_live`: **10 test đạt, 0 skipped**, 195.767 giây.
- Suite gửi **13 request**, tổng **3151 token**. C/J dừng trước request theo gate
  đầu vào/phê duyệt. Không cộng lượt CLI riêng vào số liệu của suite.
- A: completed/criteria_met, 2 bước, 1 lần thử tool, 100000 VND.
- B: failed/validation_failed; D: failed/retry_exhausted; H: failed/no_progress.
- E/F/G: budget_exhausted với step_limit/tool_limit/time_limit tương ứng.
- I: completed sau 2 lần thử tool. J: blocked/approval_required.
- G dùng đồng hồ thực và tool chờ 26 giây; deadline 25 giây, thời gian lần chạy
  39.672 giây gồm chờ giãn request. Controller nhận time_limit tại điểm kiểm tra.
- Cài dependencies theo README trong venv ở checkout repo: pip check đạt,
  py_compile cả bảy file đạt. Chạy CLI `--quantity 4 --unit-price 25000` bằng
  interpreter này: exit 0, completed, 2 response Gemini thật, tổng 488 token.
- Bảy file Python, requirements và cấu hình mẫu đồng bộ với bộ mã đi kèm bài.

Bằng chứng: [log test](verification/live_suite_tests.txt),
[kết quả đầy đủ](verification/live_suite_results.json),
[tóm tắt A–J](verification/live_suite_summary.txt),
[case A](verification/live_success.json),
[CLI trong môi trường repo](verification/cli_success.json),
[phiên bản suite](verification/versions.txt),
[phiên bản môi trường repo](verification/repo_versions.txt).

## Phạm vi và giới hạn

B/D/F/G/I chủ động tạo lỗi hoặc độ trễ ở tool để kích hoạt nhánh cần kiểm tra.
H thêm chỉ dẫn chẩn đoán yêu cầu model lặp đề xuất. Các quyết định vẫn được
Gemini sinh qua API. Những case này không chứng minh tần suất lỗi trong vận hành.
Số token, thời gian và khả năng làm theo chỉ dẫn có thể thay đổi giữa các lần chạy.

Controller kiểm schema, tổng tiền, đơn vị và bằng chứng tool khớp nhiệm vụ;
đưa bản sao sâu của lịch sử cho planner; kiểm đúng kiểu bool của cờ phê duyệt.
Lần kiểm thử này gồm các nhánh A–J, không phải kiểm thử mọi tổ hợp đầu vào.

SDK thử HTTP một lần, timeout tối đa 30 giây và giảm theo thời gian tác vụ còn lại.
Khoảng cách request mặc định 15 giây chỉ điều tiết một tiến trình. Deadline mềm
không hủy tool đang chạy. HTTP 429 là failed/model_error; ngân sách cục bộ hết
là budget_exhausted. Token được ghi, chưa là ngân sách dừng.
Chưa có checkpoint bền vững, xác thực phê duyệt, nhóm tool, backoff tool hoặc
idempotency cho thao tác ghi. Chưa chạy trực tiếp trên macOS/Linux.

Task và bằng chứng tool được gửi tới Google. Bộ mã dùng dữ liệu mẫu;
.env thật được bỏ qua bởi Git. Không đưa key, venv, cache hoặc tài liệu LaTeX/PDF
vào repo code. Dùng requirements và hướng dẫn API trong README để chạy lại.
