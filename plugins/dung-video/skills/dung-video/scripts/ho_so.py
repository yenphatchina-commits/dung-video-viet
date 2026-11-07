"""Hồ sơ kênh: tên thương hiệu, người dẫn, từ riêng, bảng sửa chữ nghe nhầm, màu, thời gian bìa."""
import os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C

MAC_DINH = {
    "ten_kenh": "", "nguoi_dan": "", "tu_rieng": [], "sua_tu": {},
    "mau_nhan": "#FFD400", "mau_canh_bao": "#E5383B", "mau_chu": "#FFFFFF", "mau_nen": "#111111",
    "bia_giay": 0.8, "chu_mo_dau_giay": 0.9,
    "phu_de": {"tu-van": True, "bai-tap": False},
    "am_luong_lufs": -16, "logo": "",
}
THU_MUC = os.path.join(C.NHA, "ho-so")


def lay(ten=""):
    """Hồ sơ theo tên (trong ~/.dung-video/ho-so). Không có thì dùng mặc định."""
    hs = dict(MAC_DINH)
    if ten:
        p = ten if ten.endswith(".json") and os.path.exists(ten) else os.path.join(THU_MUC, ten + ".json")
        d = C.doc_json(p)
        if d is None:
            raise SystemExit(f"Không thấy hồ sơ «{ten}» ({p}). Tạo bằng: dv.py ho-so tao {ten}")
        hs.update(d)
        hs["_ten"] = os.path.abspath(p) if ten.endswith(".json") else ten
    hs["bia_giay"] = min(1.0, max(0.5, float(hs["bia_giay"])))
    return hs


def goi_y_nhan_giong(hs):
    """Câu gợi ý cho Whisper để nghe đúng tên riêng."""
    tu = [hs.get("ten_kenh", ""), hs.get("nguoi_dan", "")] + list(hs.get("tu_rieng", []))
    tu = [t for t in tu if t]
    return ("Video tiếng Việt. Tên riêng: " + ", ".join(tu) + ".") if tu else None


def _chuan(s):
    s = unicodedata.normalize("NFC", s.lower())
    return re.sub(r"[^\w]", "", s)


def sua_tu(tu, bang):
    """Thay cụm chữ nghe nhầm theo bảng {"so bóp": "xoa bóp", "dưỡng phức thống": "Dưỡng Cốt Thống"}.
    Giữ mốc thời gian: cùng số chữ thì thay từng chữ; khác số chữ thì gộp vào chữ đầu."""
    if not bang:
        return tu
    tu = [dict(w) for w in tu]
    for sai, dung in sorted(bang.items(), key=lambda kv: -len(kv[0].split())):
        ks = [_chuan(x) for x in sai.split()]
        rs = dung.split()
        i = 0
        while i + len(ks) <= len(tu):
            if [_chuan(w["w"]) for w in tu[i:i + len(ks)]] == ks:
                duoi = re.search(r"\W*$", tu[i + len(ks) - 1]["w"]).group()  # giữ dấu câu ở cuối
                if len(rs) == len(ks):
                    for j, r in enumerate(rs):
                        tu[i + j]["w"] = r + (duoi if j == len(rs) - 1 else "")
                else:
                    g = dict(tu[i], w=dung + duoi, b=tu[i + len(ks) - 1]["b"])
                    tu[i:i + len(ks)] = [g]
                i += max(1, len(rs) if len(rs) == len(ks) else 1)
            else:
                i += 1
    return tu


def tao(ten):
    p = os.path.join(THU_MUC, ten + ".json")
    if os.path.exists(p):
        return p
    mau = C.doc_json(os.path.join(C.SKILL, "ho-so-mau", "mau.json"), {})
    hs = {k: v for k, v in dict(MAC_DINH, **mau).items() if not k.startswith("_")}
    C.ghi_json(p, hs)
    return p
