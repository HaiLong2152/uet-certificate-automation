"""Create 40 repeatable Task #10 scenarios and submit each intake form.

Run after deploying the test BPMN and starting the worker:
    python scripts/run_kpi_batch.py

The script creates 32 automatic cases and leaves 8 officer-review cases open.
It does not complete or reject officer tasks.
"""
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

import camunda_api as api
from sample_db import SINH_VIEN

PROCESS_ID = "xac_nhan_sv_tobe"
INTAKE_TASK_ID = "Task_NopDon"
OUTPUT = ROOT / "kpi_scenario_instances.csv"
COMMON_PURPOSES = [
    "Hồ sơ học bổng",
    "Vay vốn ngân hàng",
    "Thực tập",
    "Miễn giảm nghĩa vụ quân sự",
]
MANUAL_PURPOSE = "Khác (cần cán bộ xem xét)"
POLL_INTERVAL = 0.05
TASK_TIMEOUT = 10


def make_cases() -> list[dict]:
    enrolled = [
        (mssv, record)
        for mssv, record in SINH_VIEN.items()
        if record["trangThai"] == "Đang học"
    ]
    if not enrolled:
        raise RuntimeError("sample_db.py không có sinh viên đang học để chạy kịch bản.")

    cases = []
    groups = [
        ("stp", 32, False),
        ("tra_lai", 3, True),
        ("duyet", 2, True),
        ("qua_han", 3, True),
    ]
    for scenario, count, needs_officer in groups:
        for index in range(count):
            mssv, student = enrolled[len(cases) % len(enrolled)]
            purpose = MANUAL_PURPOSE if needs_officer else COMMON_PURPOSES[index % len(COMMON_PURPOSES)]
            cases.append({
                "scenario": scenario,
                "variables": {
                    "mssv": mssv,
                    "hoTen": student["hoTen"],
                    "mucDich": purpose,
                    "hinhThuc": "ban-mem",
                },
            })
    return cases


def wait_for_intake_task(process_instance_key: str) -> dict:
    deadline = time.monotonic() + TASK_TIMEOUT
    while time.monotonic() < deadline:
        tasks = api.search_user_tasks(process_instance_key)
        intake = [task for task in tasks if task.get("elementId") == INTAKE_TASK_ID]
        if intake:
            return intake[0]
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(
        f"Không tìm thấy user task {INTAKE_TASK_ID} cho instance {process_instance_key}."
    )


def save_manifest(records: list[dict]) -> None:
    fields = ["scenario", "processInstanceKey", "intakeUserTaskKey", "mssv", "mucDich", "createdAt"]
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    if not os.getenv("SMTP_HOST"):
        raise SystemExit("Thiếu SMTP_HOST trong .env; dừng trước khi tạo batch để tránh job gửi mail lỗi.")
    if not os.getenv("STAFF_NOTIFICATION_EMAIL"):
        raise SystemExit("Thiếu STAFF_NOTIFICATION_EMAIL trong .env cho 3 ca quá hạn.")
    if not os.getenv("EMAIL_OVERRIDE_TO"):
        raise SystemExit(
            "Thiếu EMAIL_OVERRIDE_TO. Hãy đặt hộp thư kiểm thử vì email sample_db.py là địa chỉ giả."
        )

    api.topology()
    cases = make_cases()
    print("Sẽ tạo 40 process instance; worker sẽ gửi email theo .env. Đang chạy...")
    records = []
    save_manifest(records)
    for index, case in enumerate(cases, start=1):
        variables = case["variables"]
        instance = api.start_instance(PROCESS_ID, variables)
        instance_key = str(instance["processInstanceKey"])
        task = wait_for_intake_task(instance_key)
        # Use actual form keys from nop-don-to-be.form: mssv, hoTen, mucDich, hinhThuc.
        api.complete_user_task(str(task["userTaskKey"]), variables)
        records.append({
            "scenario": case["scenario"],
            "processInstanceKey": instance_key,
            "intakeUserTaskKey": str(task["userTaskKey"]),
            "mssv": variables["mssv"],
            "mucDich": variables["mucDich"],
            "createdAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        })
        save_manifest(records)
        print(f"[{index:02d}/40] {case['scenario']}: instance {instance_key}, đã nộp đơn")

    print(f"Hoàn tất 40 lượt tạo/nộp đơn. Danh sách: {OUTPUT}")
    print("Dự kiến: 32 ca tự duyệt; 3 trả lại, 2 duyệt và 3 quá hạn chờ cán bộ trên Tasklist.")
    print("Các ca tự động và email tiếp tục chạy bất đồng bộ qua worker.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Đã dừng tạo batch; các instance đã tạo vẫn còn trên Camunda.")
