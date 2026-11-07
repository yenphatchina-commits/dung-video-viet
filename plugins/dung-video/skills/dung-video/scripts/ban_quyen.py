"""BẢN QUYỀN: mã ký số có in tên người mua. Kiểm tra ngay trên máy — không cần mạng, không gửi gì đi đâu.

    dv.py kich-hoat <MÃ>     # dán mã nhận khi mua
    dv.py ban-quyen          # xem mã đang dùng cấp cho ai
"""
import base64, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C

TEP = os.path.join(C.NHA, "ban-quyen.json")
KHOA_CONG_KHAI = os.path.join(C.SKILL, "scripts", "khoa_cong_khai.txt")
BI_KHOA = os.path.join(C.SKILL, "scripts", "ma-bi-khoa.txt")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def giai_ma(ma):
    """Trả nội dung mã {id, ten, lh, ngay} nếu chữ ký đúng; sai thì báo lỗi."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    ma = "".join(ma.split())
    try:
        dau, noi_dung, ky = ma.split(".")
        assert dau == "DV1"
        pub = Ed25519PublicKey.from_public_bytes(_b64d(open(KHOA_CONG_KHAI).read().strip()))
        pub.verify(_b64d(ky), noi_dung.encode())
        d = json.loads(_b64d(noi_dung))
    except Exception:
        raise SystemExit("Mã bản quyền không hợp lệ. Hãy dán lại đúng nguyên mã trong tin nhắn giao hàng.")
    if os.path.exists(BI_KHOA) and d.get("id") in open(BI_KHOA, encoding="utf-8").read().split():
        raise SystemExit("Mã này đã bị khoá. Vui lòng liên hệ người bán.")
    return d


def kich_hoat(ma):
    d = giai_ma(ma)
    C.ghi_json(TEP, {"ma": "".join(ma.split())})
    C.in_ra(f"✅ Đã kích hoạt. Bản quyền cấp cho: {d['ten']}")
    C.in_ra("Việc dùng skill nghĩa là bạn đồng ý Điều khoản sử dụng (tệp DIEU-KHOAN.md): mã chỉ dành cho bạn, "
            "không chia sẻ, không sao chép hay bán lại skill.")


def kiem_tra():
    """Gọi trước khi đọc/dựng. Trả chuỗi 'tên người mua' để ghi vào báo cáo và tệp video."""
    d = C.doc_json(TEP)
    if not d:
        raise SystemExit("Chưa kích hoạt bản quyền. Hãy nói: «kích hoạt mã <mã của bạn>».")
    return giai_ma(d["ma"])["ten"]


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "kich-hoat":
        kich_hoat(" ".join(sys.argv[2:]))
    else:
        C.in_ra("Bản quyền cấp cho:", kiem_tra())
