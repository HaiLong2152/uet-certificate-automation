"""Job worker cho process xac_nhan_sv_demo.

Chạy:  python src/worker.py      (Ctrl+C để dừng)
"""
import time
import uuid
import os
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

import camunda_api as api
from sample_db import tra_cuu
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

WORKER = "nhom16-worker"
ROOT = Path(__file__).resolve().parent.parent


def _register_pdf_font() -> str:
    """Register a Unicode font so Vietnamese text renders in the certificate."""
    font_setting = os.getenv("CAMUNDA_PDF_FONT")
    candidates = ([Path(font_setting)] if font_setting else []) + [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for font_path in candidates:
        if font_path.is_file():
            pdfmetrics.registerFont(TTFont("CertificateUnicode", str(font_path)))
            return "CertificateUnicode"
    raise FileNotFoundError(
        "Không tìm thấy font Unicode để xuất tiếng Việt. Cài Arial/DejaVu Sans hoặc "
        "đặt CAMUNDA_PDF_FONT trỏ tới file .ttf."
    )


def _draw_paragraph(pdf: canvas.Canvas, text: str, x: float, y: float, width: float,
                    style: ParagraphStyle) -> float:
    paragraph = Paragraph(escape(text), style)
    _, height = paragraph.wrap(width, A4[1])
    paragraph.drawOn(pdf, x, y - height)
    return y - height


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
    now = datetime.now()
    so = f"XN-{now:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}"
    ma = uuid.uuid4().hex[:12].upper()
    verify_base = os.getenv("CERTIFICATE_VERIFY_BASE_URL", "").strip().rstrip("/")
    qr_payload = f"{verify_base}/{quote(ma)}" if verify_base else f"Ma xac thuc giay: {ma}"
    output_dir = Path(os.getenv("PDF_OUTPUT_DIR", str(ROOT / "generated" / "pdf"))).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = (output_dir / f"{so}.pdf").resolve()

    font_name = _register_pdf_font()
    title_style = ParagraphStyle("CertificateTitle", fontName=font_name, fontSize=19,
                                 leading=25, alignment=TA_CENTER, textColor=colors.HexColor("#17365D"))
    body_style = ParagraphStyle("CertificateBody", fontName=font_name, fontSize=11,
                                leading=18, alignment=TA_LEFT, textColor=colors.HexColor("#202124"))
    small_style = ParagraphStyle("CertificateSmall", fontName=font_name, fontSize=9,
                                 leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#555555"))

    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_width, page_height = A4
    pdf.setTitle(f"Giấy xác nhận sinh viên {so}")
    pdf.setAuthor("Hệ thống cấp giấy xác nhận sinh viên UET (bản demo)")
    pdf.setStrokeColor(colors.HexColor("#17365D"))
    pdf.setLineWidth(1.2)
    pdf.roundRect(38, 38, page_width - 76, page_height - 76, 12, stroke=1, fill=0)

    y = page_height - 105
    y = _draw_paragraph(pdf, "GIẤY XÁC NHẬN SINH VIÊN", 65, y, page_width - 130, title_style) - 12
    y = _draw_paragraph(pdf, "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ – ĐHQGHN", 65, y,
                        page_width - 130, small_style) - 34
    pdf.setFont(font_name, 11)
    pdf.drawString(75, y, "Xác nhận thông tin sinh viên:")
    y -= 30
    details = [
        ("Họ và tên", str(variables.get("hoTen", ""))),
        ("Mã số sinh viên", str(variables.get("mssv", ""))),
        ("Tình trạng học tập", str(variables.get("trangThaiHocTap", "Đang học"))),
        ("Mục đích", str(variables.get("mucDich", ""))),
    ]
    for label, value in details:
        y = _draw_paragraph(pdf, f"<b>{escape(label)}:</b> {escape(value or '—')}",
                            75, y, page_width - 150, body_style) - 8
    y -= 8
    _draw_paragraph(pdf, "Giấy xác nhận được cấp dưới dạng điện tử; mã QR và mã xác thực "
                    "dùng để đối chiếu thông tin.", 75, y, page_width - 150, body_style)

    qr = QrCodeWidget(qr_payload)
    x1, y1, x2, y2 = qr.getBounds()
    qr_size = 112
    drawing = Drawing(qr_size, qr_size, transform=[qr_size / (x2 - x1), 0, 0,
                                                   qr_size / (y2 - y1), 0, 0])
    drawing.add(qr)
    qr_x = (page_width - qr_size) / 2
    qr_y = 102
    renderPDF.draw(drawing, pdf, qr_x, qr_y)
    _draw_paragraph(pdf, f"Số giấy: {escape(so)}", 65, qr_y - 10,
                    page_width - 130, small_style)
    _draw_paragraph(pdf, f"Mã xác thực: {escape(ma)}", 65, qr_y - 30,
                    page_width - 130, small_style)
    issued = now.strftime("%d/%m/%Y %H:%M:%S")
    _draw_paragraph(pdf, f"Ngày cấp: {issued}", 65, 70, page_width - 130, small_style)
    pdf.save()

    print(f"  sinh-giay-pdf: đã tạo {pdf_path} (số {so}, mã {ma})")
    return {"soGiay": so, "maXacThuc": ma, "ngayCap": now.isoformat(timespec="seconds"),
            "qrUrl": f"{verify_base}/{quote(ma)}" if verify_base else "",
            "pdfPath": str(pdf_path)}


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
