"""CSDL sinh viên giả lập (thay cho hệ thống quản lý đào tạo thật)."""
SINH_VIEN = {
    "24020001": {"hoTen": "Nguyễn Văn An", "trangThai": "Đang học", "email": "an.nv@example.com"},
    "24020002": {"hoTen": "Trần Thị Bình", "trangThai": "Đang học", "email": "binh.tt@example.com"},
    "23020003": {"hoTen": "Lê Minh Châu", "trangThai": "Bảo lưu", "email": "chau.lm@example.com"},
    "22020004": {"hoTen": "Phạm Quốc Dũng", "trangThai": "Thôi học", "email": "dung.pq@example.com"},
}
HOP_LE = {"Đang học"}
# Mục đích thường gặp: hệ thống tự duyệt. Mục đích khác => chuyển cán bộ CTSV duyệt tay.
MUC_DICH_THUONG = {"Hồ sơ học bổng", "Vay vốn ngân hàng", "Thực tập", "Miễn giảm nghĩa vụ quân sự"}


def tra_cuu(mssv: str, muc_dich: str = "") -> dict:
    sv = SINH_VIEN.get(mssv)
    if sv is None:
        return {"hopLe": False, "trangThaiHocTap": "Không tìm thấy MSSV", "canDuyetTay": False}
    hop_le = sv["trangThai"] in HOP_LE
    can_tay = hop_le and muc_dich not in MUC_DICH_THUONG
    return {"hopLe": hop_le, "trangThaiHocTap": sv["trangThai"], "email": sv["email"],
            "canDuyetTay": can_tay,
            "lyDoDuyetTay": f"Mục đích ngoài danh mục thường gặp: {muc_dich}" if can_tay else ""}
