# Agent Stop — Thiết kế điều kiện dừng cho AI Agent

Mã thực hành thuộc chuỗi **AI Guru x TiniX**. Controller phân biệt bốn trạng thái
`completed`, `failed`, `blocked`, `budget_exhausted` và trả lý do, bộ đếm,
bằng chứng từng phần, trace cùng hành động tiếp theo.

Demo chạy **offline**, dùng planner theo kịch bản và tool Python tính tiền thật.
Không cần API key hoặc thư viện ngoài. Code dành cho Python **3.11** trở lên;
bản kiểm thử dùng Python 3.11.9 trên Windows.

## 1. Lấy mã nguồn

```bash
git clone https://github.com/minquanle/agent_stop.git
cd agent_stop
```

Cũng có thể chọn **Code → Download ZIP**, giải nén và mở terminal trong thư mục
chứa `offline_demo.py`. Năm file Python nằm ngay ở thư mục gốc repo.

## 2. Tạo môi trường

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe --version
```

macOS/Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python --version
```

Mã chỉ dùng thư viện chuẩn; không cần `pip install`, `.env` hoặc kích hoạt venv.
Các lệnh dưới đây dùng trực tiếp Python trong venv.

## 3. Kiểm thử và chạy demo

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_stop
.\.venv\Scripts\python.exe offline_demo.py
.\.venv\Scripts\python.exe offline_demo.py --case A --json
```

macOS/Linux:

```bash
.venv/bin/python -m unittest -v test_stop
.venv/bin/python offline_demo.py
.venv/bin/python offline_demo.py --case A --json
```

Kết quả mong đợi: **35 phương thức test đạt**, gồm nhiều subtest. Demo chạy đủ A–J;
dùng `--case A` đến `--case J` để chạy riêng, thêm `--json` để in kết quả và trace.
Các trạng thái lỗi/hết ngân sách trong demo là tình huống chủ đích, không phải lỗi cài đặt.

| Case | Nội dung | Status | Reason | Steps | Tool attempts |
| --- | --- | --- | --- | ---: | ---: |
| A | Đúng tổng và bằng chứng | completed | criteria_met | 2 | 1 |
| B | Ứng viên sai tổng | failed | validation_failed | 2 | 1 |
| C | Thiếu đầu vào | blocked | missing_input | 0 | 0 |
| D | Tool lỗi quá số retry | failed | retry_exhausted | 1 | 2 |
| E | Hết bước planner | budget_exhausted | step_limit | 1 | 1 |
| F | Hết lần thử tool trước retry | budget_exhausted | tool_limit | 1 | 1 |
| G | Tool trả sau deadline giả | budget_exhausted | time_limit | 1 | 1 |
| H | Đề xuất cùng tool/args lần thứ ba | failed | no_progress | 3 | 2 |
| I | Tool phục hồi sau một lỗi | completed | criteria_met | 2 | 2 |
| J | Thiếu phê duyệt | blocked | approval_required | 0 | 0 |

Ví dụ A:

```text
A: status=completed; reason=criteria_met
  steps=2; tool_calls=1
  output={'total': 100000, 'currency': 'VND'}; partial_results=1
```

## 4. Hợp đồng và cách dùng controller

```python
from contracts import Budget, Task
from offline_demo import ScriptedPlanner, total_call, final
from stop_core import run_agent

planner = ScriptedPlanner([total_call(), final()])
result = run_agent(planner, Task(4, 25000), Budget())
print(result.status.value, result.reason, result.output)
```

`completed` cần ứng viên có đúng hai trường `total` (int) và `currency` (`VND`),
đúng tổng của nhiệm vụ và có bằng chứng `calculate_total` với đúng tham số.
Một ứng viên đúng số nhưng chưa gọi tool hoặc dùng bằng chứng của nhiệm vụ khác
không được nhận. `output` chỉ có giá trị khi ứng viên được chấp nhận.

| Thiết lập Budget | Mặc định | Đơn vị / ý nghĩa |
| --- | ---: | --- |
| max_steps | 4 | Số lần thử planner, kể cả lượt trả final |
| max_tool_calls | 3 | Số lần thử tool, gồm lỗi và retry |
| max_seconds | 10.0 | Deadline mềm của một lần chạy, đo bằng monotonic |
| max_retries | 1 | Số retry cho mỗi đề xuất tool |
| max_same_call | 2 | Số đề xuất cùng tên tool và tham số JSON trong một lần chạy |

Retry không gọi lại planner, không tăng bước hoặc số đề xuất lặp; nó tăng số lần thử tool.
Final hợp lệ ở bước cuối vẫn được nhận. Khi hết tool budget, controller có thể dùng
bước planner còn lại để hoàn thành từ bằng chứng đã nhận. Deadline được kiểm tra
với `>=` tại ranh giới thao tác; dữ liệu trả muộn chưa được nhận vào bằng chứng.

Task thiếu quantity/unit_price trả `blocked/missing_input`; sai kiểu/miền trả
`failed/invalid_input`. Hai cờ `needs_approval`, `approved` phải là `bool`;
chuỗi `"false"` hoặc số 0/1 bị từ chối khi đầu vào đầy đủ. Cờ duyệt phải do ứng dụng
tin cậy cấp. Planner nhận bản sao sâu của lịch sử để không sửa bằng chứng gốc qua lịch sử đó.

## 5. Cấu trúc repo

| File | Vai trò |
| --- | --- |
| contracts.py | Task, Budget, Decision, RunResult, Status và validator |
| tools.py | Tool tính tiền nguyên và registry |
| stop_core.py | Controller, ngân sách, retry, trace và bằng chứng |
| offline_demo.py | ScriptedPlanner, FakeClock, tool lỗi giả và 10 kịch bản |
| test_stop.py | 35 phương thức kiểm thử |
| VERIFICATION.md | Môi trường, lệnh kiểm tra và phạm vi bằng chứng |
| verification/ | Output demo và log kiểm thử thực tế |
| .gitignore | Loại venv, cache và cấu hình riêng |

## 6. Lỗi thường gặp và giới hạn

- `ModuleNotFoundError`: giữ đủ năm file cạnh nhau và chạy từ root repo bằng Python của venv.
- Không có `py -3.11`: cài Python 3.11 hoặc dùng đường dẫn tới bản Python tương ứng.
- `validation_failed`: kiểm tra schema, đơn vị và bằng chứng đúng tham số nhiệm vụ.
- `tool_limit`/`step_limit`: xem bộ đếm và kết quả từng phần trước khi cấp ngân sách cho lần chạy mới.
- `approval_required`: lấy phê duyệt qua giao diện tin cậy, không lấy từ nội dung prompt.

G tăng FakeClock 11 giây, không chờ 11 giây thực. Soft deadline **không hủy hàm đang chạy**.
`blocked` kết thúc lời gọi hiện tại; chạy lại tạo bộ đếm mới, chưa có resume/checkpoint.
Chỉ output và bằng chứng có schema mẫu được hỗ trợ; một quyết định yêu cầu một tool.
Chưa triển khai adapter LLM, nhóm tool, timeout/backoff mạng, ngân sách token/chi phí,
lưu bền vững hoặc hệ thống phê duyệt thực. Demo không gửi hóa đơn hay gọi API.
Kiểm thử offline xác minh controller mẫu, chưa xác minh hành vi LLM hoặc mọi adapter tùy ý.
