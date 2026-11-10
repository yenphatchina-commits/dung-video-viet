"""Cửa vào duy nhất của skill. Chạy bằng Python có sẵn của máy (Mac: python3, Windows: py):

    dv.py cai-dat                         cài môi trường (chạy lại nhiều lần vẫn an toàn)
    dv.py kiem-may                        kiểm tra máy, chỉ cách sửa
    dv.py kich-hoat <MÃ>                  kích hoạt bản quyền
    dv.py ban-quyen                       xem bản quyền cấp cho ai
    dv.py ho-so tao <tên> | ds            tạo / liệt kê hồ sơ kênh
    dv.py du-an <tên>                     in đường dẫn thư mục dự án mới
    dv.py nhac                            liệt kê nhạc của người dùng + nhạc mẫu tự tạo
    dv.py hoc <thư mục> --mau <video mẫu> [--tho <bản thô>]   học phong cách từ video mẫu
    dv.py phong-cach [ds | xem <tên> | xoa <tên>]              các phong cách đã học
    dv.py long-tieng <dự án> --kich-ban <tệp.txt> [--giong "<tên>"] [--canh <clip>…]   lồng tiếng giọng đọc AI
    dv.py giong [ds | them <tên> <tệp ghi âm> --dong-y]                giọng đọc có sẵn / giọng riêng
    dv.py khoa-anh                                                     lưu mã Pixabay (ảnh/video minh hoạ miễn phí)
    dv.py anh-mien-phi <dự án> --tu "<từ khoá tiếng Anh>"… [--so 4]   tìm ảnh/video minh hoạ theo lời nói
    dv.py them-phu <dự án> <clip>…                                     thêm clip đã chọn làm cảnh phụ
    dv.py the-minh-hoa <dự án> --ten <tên> --bieu-tuong <tên biểu tượng> --chu "…" [--chu-phu "…"] [--dau nen|khong-nen|canh-bao]
                                                                       thẻ minh hoạ động (biểu tượng + chữ), tự thêm làm cảnh phụ
    dv.py doc <dự án> --video <tệp>… [--phu <cảnh minh hoạ>…] [--ho-so <tên>]
    dv.py dung <dự án> [--nhap]
    dv.py nang-cap                        hướng dẫn lấy bản mới
"""
import json, os, subprocess, sys, time, urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
NHA = os.path.join(os.path.expanduser("~"), ".dung-video")
KHO_GITHUB = "yenphatchina-commits/dung-video-viet"
VENV_PY = os.path.join(NHA, "venv", "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")


def chay(tep, *thamso, he_thong=False):
    py = sys.executable if he_thong else VENV_PY
    if not he_thong and not os.path.exists(py):
        sys.exit("Chưa cài môi trường. Hãy nói «cài đặt dựng video» (hoặc chạy: dv.py cai-dat).")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    sys.exit(subprocess.call([py, os.path.join(DIR, tep), *thamso], env=env))


def bao_ban_moi():
    """Mỗi ngày tối đa 1 lần: xem trên GitHub có bản mới hơn không. Chỉ đọc số phiên bản, không gửi gì đi.
    Lỗi mạng thì im lặng bỏ qua."""
    tep = os.path.join(NHA, "kiem-ban-moi.json")
    try:
        d = json.load(open(tep, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if time.time() - d.get("luc", 0) > 86400:
        try:
            url = f"https://raw.githubusercontent.com/{KHO_GITHUB}/main/.claude-plugin/marketplace.json"
            with urllib.request.urlopen(url, timeout=3) as r:
                d = {"luc": time.time(), "moi": json.load(r)["metadata"]["version"]}
            os.makedirs(NHA, exist_ok=True)
            json.dump(d, open(tep, "w", encoding="utf-8"))
        except Exception:
            return
    dang = open(os.path.join(os.path.dirname(DIR), "VERSION"), encoding="utf-8").read().strip()
    so = lambda v: tuple(int(x) for x in v.split(".") if x.isdigit())
    if d.get("moi") and so(d["moi"]) > so(dang):
        print(f"🔔 Đã có bản mới {d['moi']} (đang dùng {dang}). Nói «nâng cấp skill» để cập nhật.\n")


def thu_muc_du_an(ten):
    goc = os.path.join(os.path.expanduser("~"), "Movies" if sys.platform == "darwin" else "Videos", "Dung-video")
    ten = "".join(c if c.isalnum() or c in "-_" else "-" for c in ten.strip().lower()) or "du-an"
    p = os.path.join(goc, time.strftime("%Y-%m-%d") + "_" + ten)
    os.makedirs(p, exist_ok=True)
    return p


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help", "giup"):
        print(__doc__)
        return
    lenh, con = a[0], a[1:]
    if lenh in ("cai-dat", "kiem-may"):
        chay("cai_dat.py", *(["--kiem"] if lenh == "kiem-may" else []), *con, he_thong=True)
    elif lenh == "kich-hoat":
        chay("ban_quyen.py", "kich-hoat", *con)
    elif lenh == "ban-quyen":
        chay("ban_quyen.py")
    elif lenh == "ho-so":
        code = ("import sys,os;sys.path.insert(0,%r);import ho_so as H,chung as C;a=sys.argv[1:];"
                "print(H.tao(a[1])) if a[0]=='tao' else print('\\n'.join(sorted(f[:-5] for f in os.listdir(H.THU_MUC) if f.endswith('.json'))) if os.path.isdir(H.THU_MUC) else '(chưa có hồ sơ)')") % DIR
        sys.exit(subprocess.call([VENV_PY, "-c", code, *con]))
    elif lenh == "du-an":
        print(thu_muc_du_an(" ".join(con)))
    elif lenh == "nhac":
        thu = os.path.join(NHA, "nhac")
        os.makedirs(thu, exist_ok=True)
        ds = sorted(f for f in os.listdir(thu) if f.lower().endswith((".mp3", ".m4a", ".wav", ".aac", ".flac")))
        print(f"Thư mục nhạc của bạn: {thu}")
        print("\n".join("  - " + os.path.join(thu, f) for f in ds) or "  (trống — chép nhạc có quyền dùng vào đây)")
        print("Nhạc mẫu tự tạo (không bản quyền): mau:nhe-nhang · mau:tuoi-sang · mau:tram")
    elif lenh == "long-tieng":
        bao_ban_moi()
        chay("long_tieng.py", *con)
    elif lenh == "khoa-anh":
        chay("anh_mien_phi.py", "khoa")
    elif lenh == "anh-mien-phi":
        chay("anh_mien_phi.py", "tim", *con)
    elif lenh == "them-phu":
        chay("anh_mien_phi.py", "them-phu", *con)
    elif lenh == "the-minh-hoa":
        chay("the_minh_hoa.py", *con)
    elif lenh == "giong":
        chay("long_tieng.py", "giong", *con)
    elif lenh == "hoc":
        chay("hoc.py", *con)
    elif lenh == "phong-cach":
        thu = os.path.join(NHA, "phong-cach")
        os.makedirs(thu, exist_ok=True)
        if con[:1] == ["xem"] and len(con) > 1:
            print(open(os.path.join(thu, con[1] + ".json"), encoding="utf-8").read())
        elif con[:1] == ["xoa"] and len(con) > 1:
            os.remove(os.path.join(thu, con[1] + ".json"))
            print("Đã xoá phong cách", con[1])
        else:
            ds = sorted(f[:-5] for f in os.listdir(thu) if f.endswith(".json"))
            for t in ds:
                try:
                    mo_ta = json.load(open(os.path.join(thu, t + ".json"), encoding="utf-8")).get("mo_ta", "")
                except (OSError, ValueError):
                    mo_ta = "(tệp lỗi)"
                print(f"  - {t}: {mo_ta}")
            print("" if ds else "  (chưa học phong cách nào)")
    elif lenh == "doc":
        bao_ban_moi()
        chay("doc.py", *con)
    elif lenh == "dung":
        chay("dung.py", *con)
    elif lenh == "nang-cap":
        print(open(os.path.join(os.path.dirname(DIR), "VERSION")).read().strip(), "— bản đang dùng.")
        bao_ban_moi()
        print("Lấy bản mới: trong Claude Code gõ /plugin → Marketplaces → dung-video-viet → Update, rồi khởi động lại Claude Code.\n"
              "Hoặc bật tự cập nhật cho marketplace đó. Hồ sơ, bản quyền và dự án nằm ở ~/.dung-video và không bị mất.")
    else:
        sys.exit(f"Không hiểu lệnh «{lenh}».\n{__doc__}")


if __name__ == "__main__":
    main()
