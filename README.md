# Agent Stop — Điều kiện dừng với Gemini 2.5 Flash

Mã thực hành thuộc chuỗi **AI Guru x TiniX**. Gemini 2.5 Flash sinh quyết định
qua API thật; Python chạy tool tính tiền và kiểm tra bốn trạng thái
`completed`, `failed`, `blocked`, `budget_exhausted`.

Cần Python 3.11, Git, kết nối mạng và API key có quyền gọi **gemini-2.5-flash**.
Tác vụ và lịch sử kết quả tool được gửi tới Google. Dùng dữ liệu mẫu khi thực hành.

## 1. Clone và cài môi trường

```bash
git clone https://github.com/minquanle/agent_stop.git
cd agent_stop
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

macOS/Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

Các lệnh dùng Python trực tiếp trong venv, không cần activate.
Thư viện trực tiếp được ghim: google-genai 2.29.0, python-dotenv 1.2.4.

## 2. Cấu hình API

Nếu chưa có `.env`, tạo từ mẫu. Windows:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

macOS/Linux:

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
```

Mở `.env` và điền key của bạn:

```dotenv
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MIN_INTERVAL=15
```

`.env` được nạp theo vị trí `gemini_planner.py`. Biến môi trường đã tồn tại được ưu tiên.
Repo chỉ chứa cấu hình mẫu; không commit key thật. Mẫu chỉ chấp nhận model
`gemini-2.5-flash`. Quyền model và quota phụ thuộc project; kiểm tra trong AI Studio.
Google hiện giới hạn quyền sử dụng 2.5 cho một số project đã dùng model trước đây:
[tài liệu model](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash).

`GEMINI_MIN_INTERVAL` là khoảng cách giữa thời điểm bắt đầu các request trong một tiến trình,
đơn vị giây, nhận 0–120. Mặc định 15 giúp giãn tải, không cấp thêm quota. Quota áp dụng
[theo project](https://ai.google.dev/gemini-api/docs/rate-limits), không theo từng key.
Nhiều tiến trình cần bộ giới hạn dùng chung; giới hạn này không phối hợp giữa các tiến trình.

## 3. Chạy Agent bằng API thật

Windows:

```powershell
.\.venv\Scripts\python.exe agent_stop.py --quantity 4 --unit-price 25000
```

macOS/Linux:

```bash
.venv/bin/python agent_stop.py --quantity 4 --unit-price 25000
```

Chương trình in JSON gồm `result`, `api_calls`, `planner_events` và `elapsed_seconds`.
Luồng mong đợi: Gemini đề xuất tool → Python tính tiền → Gemini đưa ứng viên cuối
→ validator nhận 100000 VND với bằng chứng đúng tham số.
Mỗi response được ghi ID, model version, token, quyết định và thời gian.
Thông báo ngoại lệ thô không được đưa vào log; đọc `error_type`/`http_status` khi API lỗi.

Thiếu số lượng:

```powershell
.\.venv\Scripts\python.exe agent_stop.py --unit-price 25000
```

Chờ phê duyệt:

```powershell
.\.venv\Scripts\python.exe agent_stop.py --quantity 4 --unit-price 25000 --needs-approval
```

Hai trường hợp này bị chặn trước request. Khi người vận hành có quyền đã duyệt,
chạy mới với cả `--needs-approval --approved`. Cờ CLI là quyết định của ứng dụng/người vận hành,
không phải cơ chế xác thực người duyệt. Mã không gửi hóa đơn.
CLI trả exit code 0 khi completed, 1 khi dừng ở trạng thái khác, 2 khi cấu hình/khởi chạy sai.

## 4. Demo và kiểm thử tích hợp

```powershell
.\.venv\Scripts\python.exe live_demo.py --case A --json
.\.venv\Scripts\python.exe live_demo.py --save live_results.json
.\.venv\Scripts\python.exe -m unittest -v test_live
```

macOS/Linux dùng `.venv/bin/python` thay đường dẫn trên. Có 10 test tích hợp;
các nhánh cần planner gọi Gemini thật, dùng quota và có thể chạy vài phút.
Khi gặp 429, runner dừng các case cần API còn lại; test đánh dấu case bị ảnh hưởng là
fail, các case cần API phía sau là skipped. C/J vẫn kiểm tra gate mà không gửi request.
Không coi skipped là đạt. Bộ test ghi kết quả vào `live_results.json`, tóm tắt
`live_output.txt`; lệnh chạy test tiếp tục ghi log mới nếu bạn chuyển hướng output.

| Case | Điều kiện chẩn đoán | Status / reason mong đợi khi API hoạt động |
| --- | --- | --- |
| A | Tổng và bằng chứng đúng | completed / criteria_met |
| B | Tool trả tổng lệch 1 | failed / validation_failed |
| C | Thiếu số lượng | blocked / missing_input |
| D | Tool lỗi quá retry | failed / retry_exhausted |
| E | Chỉ cấp 1 bước | budget_exhausted / step_limit |
| F | Tool lỗi, chỉ cấp 1 lần thử | budget_exhausted / tool_limit |
| G | Deadline 25 giây; tool chờ thật 26 giây | budget_exhausted / time_limit |
| H | Prompt chẩn đoán yêu cầu đề xuất lặp | failed / no_progress |
| I | Tool lỗi 1 lần rồi phục hồi | completed / criteria_met |
| J | Chưa được duyệt | blocked / approval_required |

B/D/F/G/I chủ động tạo lỗi hoặc độ trễ ở tool để kiểm tra chính sách. Gemini vẫn
sinh quyết định qua API; không thay response bằng quyết định viết sẵn. G dùng đồng hồ
và sleep thật. H phụ thuộc mô hình làm theo chỉ dẫn chẩn đoán; kết quả có thể lệch kỳ vọng
và cần đọc log. API 429 hoặc timeout có thể khiến một case dừng trước nhánh mong đợi.

**Kiểm chứng ngày 11/10/2026:** cả 10 test tích hợp đạt, 0 skipped.
Bộ test gửi 13 request thật tới gemini-2.5-flash, ghi nhận tổng 3151 token.
C/J dừng trước API; G dùng thời gian thực. A completed với hai response,
output 100000 VND và token từng response là 197, 291. Các con số có thể đổi khi chạy lại.
Xem [hồ sơ kiểm chứng](verification/live_suite_results.json) và
[log test](verification/live_suite_tests.txt).

## 5. Hợp đồng, ngân sách và file

| Cấu hình Budget | Mặc định | Ý nghĩa |
| --- | ---: | --- |
| max_steps | 4 | Số lần thử planner, kể cả lỗi và lượt final |
| max_tool_calls | 3 | Số lần thử tool, gồm lỗi và retry |
| max_seconds | 90.0 | Deadline mềm, gồm chờ request, API, tool và retry |
| max_retries | 1 | Retry tool cho mỗi đề xuất |
| max_same_call | 2 | Đề xuất cùng tên tool và tham số JSON trong lần chạy |

CLI hỗ trợ `--max-steps`, `--max-tool-calls`, `--max-seconds`, `--max-retries`,
`--max-same-call`. Ngân sách sai kiểu/miền bị từ chối. Retry tool không tăng bước planner
hoặc bộ đếm đề xuất lặp, nhưng tăng tool_calls. Token được ghi, chưa dùng làm điều kiện dừng.

Adapter dùng JSON Schema cho quyết định `tool`/`final`, sau đó parser kiểm kiểu và
controller kiểm nghiệp vụ. Đây là giao thức JSON của ứng dụng, không dùng native
Function Calling hoặc để SDK tự chạy tool. `temperature=0.0`, thinking_budget=0,
max_output_tokens=512 phù hợp tác vụ nhỏ; không bảo đảm tham số hoặc đáp án đúng.
SDK chỉ thử HTTP một lần; timeout tối đa 30 giây và giảm theo thời gian còn lại của tác vụ.

`completed` cần schema `{total: int, currency: VND}`, đúng tổng nhiệm vụ và bằng chứng
calculate_total đúng quantity/unit_price. Final đúng số nhưng thiếu/sai bằng chứng bị từ chối.
Cờ needs_approval/approved phải là bool. Planner nhận bản sao sâu của lịch sử;
`output` chỉ được nhận khi completed. Dữ liệu tool đã nhận được giữ trong partial_results.

| File | Vai trò |
| --- | --- |
| contracts.py | Task, Budget, Decision, RunResult, Status và validator |
| tools.py | Tool tính tiền nguyên và registry |
| stop_core.py | Controller, ngân sách, retry và trace |
| gemini_planner.py | Client Gemini, schema, pacing, parser và metadata API |
| agent_stop.py | CLI dùng API và đóng client sau khi chạy |
| live_demo.py | 10 kịch bản chẩn đoán với Gemini thật |
| test_live.py | Test tích hợp, dừng khi quota không đủ |
| requirements.txt | Phiên bản hai thư viện trực tiếp |
| .env.example | Cấu hình mẫu, không chứa key thật |
| VERIFICATION.md / verification/ | Phạm vi và bằng chứng kiểm chứng |

## 6. Lỗi và giới hạn

- `startup_error`: kiểm tra .env, Python venv, dependencies và giá trị CLI.
- 400/403/404: kiểm key, quyền model và cấu hình schema; không tự đổi model để né quyền.
- 429: xem RPM/TPM/RPD trong AI Studio; chờ quota reset hoặc bổ sung quota/billing hợp lệ.
- `validation_failed`: kiểm schema, tổng, VND và bằng chứng đúng nhiệm vụ.
- `time_limit`: xem pacing, API và tool; controller chưa hủy tool đang chạy.

`api_calls` chỉ giữ request đã bắt đầu gửi. `planner_events` còn ghi lượt hết deadline
trước khi gửi; số bước vì vậy có thể lớn hơn số request. HTTP 429 là lỗi provider,
trả failed/model_error; khác budget_exhausted của ngân sách cục bộ.
Blocked kết thúc lần gọi; chạy lại tạo bộ đếm mới, chưa có checkpoint/resume bền vững.
Chưa triển khai nhóm tool, backoff tool, kiểm token/chi phí, xác thực phê duyệt hoặc
idempotency cho tác vụ ghi dữ liệu. Không dùng ví dụ này để gửi tiền/hóa đơn trước khi bổ sung các lớp đó.
