# Task #10: batch KPI trên Camunda

Batch được chuẩn bị để tạo 40 process instance và tự complete form “Nộp đơn”:

- 32 ca STP dùng mục đích phổ biến.
- 3 ca ngoại lệ để cán bộ trả lại và nhập lý do.
- 2 ca ngoại lệ để cán bộ duyệt ngay.
- 3 ca ngoại lệ để chờ timer nhắc quá hạn, rồi cán bộ duyệt.

## Chạy batch

Timer trong `bpmn/to-be/xac_nhan_sv_tobe.bpmn` hiện đặt `PT1M` phục vụ lần đo này. Deploy lại BPMN và forms sau khi chỉnh timer. Khởi động Camunda và worker (`python src/worker.py`), rồi xác nhận `.env` có `SMTP_HOST`, `STAFF_NOTIFICATION_EMAIL` và `EMAIL_OVERRIDE_TO`. `EMAIL_OVERRIDE_TO` nên là hộp thư kiểm thử bạn kiểm soát; worker sẽ gửi email thật qua SMTP.

Chạy:

```powershell
python scripts/run_kpi_batch.py
```

Script để lại 8 task duyệt trên Tasklist. Trả lại 3 ca với lý do, duyệt 2 ca ngay, và để 3 ca còn lại qua timer 1 phút trước khi duyệt. Worker tiếp tục chạy nền để xử lý PDF và email.

Manifest `kpi_scenario_instances.csv` ánh xạ loại kịch bản sang `processInstanceKey`. Sau khi xử lý các task, chạy `python src/kpi.py` để xuất timestamps element từ Operate/History vào `kpi_element_instances.csv`. File export chứa mọi instance của process to-be trong lịch sử; dùng manifest để lọc đúng batch 40 ca.

Sau khi thu thập số liệu, đổi timer về `PT4H` và deploy lại nếu muốn khôi phục thời hạn vận hành thông thường.
