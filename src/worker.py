"""Job worker cho process xac_nhan_sv_demo.

Chạy:  python src/worker.py      (Ctrl+C để dừng)
"""
import time
import uuid
from datetime import datetime

import camunda_api as api
from sample_db import tra_cuu

WORKER = "nhom16-worker"


def handle_tra_cuu(variables: dict) -> dict:
    mssv = str(variables.get("mssv", "")).strip()
    kq = tra_cuu(mssv, str(variables.get("mucDich", "")))
    print(f"  tra-cuu-mssv: {mssv} -> {kq}")
    return kq


def handle_gui_ket_qua(variables: dict) -> dict:
    # Bản demo: chỉ ghi log. Task #9 sẽ sinh PDF và gửi email thật.
    so = f"XN-{datetime.now():%Y%m%d%H%M%S}"
    print(f"  gui-ket-qua: cấp giấy {so} cho {variables.get('hoTen')} ({variables.get('mssv')})")
    return {"soGiay": so, "ngayCap": datetime.now().isoformat(timespec="seconds")}


def handle_sinh_pdf(variables: dict) -> dict:
    # Bản to-be: sinh số giấy + mã xác thực. Task #9 sẽ dựng file PDF/QR thật.
    now = datetime.now()
    so = f"XN-{now:%Y%m%d%H%M%S}"
    ma = uuid.uuid4().hex[:10].upper()
    print(f"  sinh-giay-pdf: {so}, mã xác thực {ma}")
    return {"soGiay": so, "maXacThuc": ma, "ngayCap": now.isoformat(timespec="seconds"),
            "qrUrl": f"https://xacthuc.example.edu.vn/{ma}"}


def handle_gui_thong_bao(variables: dict, headers: dict) -> dict:
    mau = headers.get("mau", "chung")
    print(f"  gui-thong-bao [{mau}]: tới {variables.get('email', variables.get('mssv'))}"
          f" ({variables.get('hoTen')}) - {variables.get('soGiay', variables.get('ghiChu', ''))}")
    return {"trangThaiYeuCau": mau}


HANDLERS = {"tra-cuu-mssv": handle_tra_cuu, "gui-ket-qua": handle_gui_ket_qua,
            "sinh-giay-pdf": handle_sinh_pdf, "gui-thong-bao": handle_gui_thong_bao}


def main() -> None:
    print(f"Worker '{WORKER}' đang chờ job tại {api.BASE_URL} ...")
    while True:
        for job_type, handler in HANDLERS.items():
            try:
                jobs = api.activate_jobs(job_type, WORKER, request_timeout_ms=5_000)
            except Exception as exc:  # engine chưa chạy, mất kết nối...
                print(f"Lỗi kết nối: {exc}. Thử lại sau 5 giây.")
                time.sleep(5)
                continue
            for job in jobs:
                key = job["jobKey"]
                print(f"[{job_type}] job {key} (instance {job['processInstanceKey']})")
                try:
                    vars_ = job.get("variables", {})
                    if job_type == "gui-thong-bao":
                        out = handler(vars_, job.get("customHeaders", {}))
                    else:
                        out = handler(vars_)
                    api.complete_job(key, out)
                except Exception as exc:
                    api.fail_job(key, max(job.get("retries", 1) - 1, 0), str(exc))
                    print(f"  thất bại: {exc}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Đã dừng worker.")
