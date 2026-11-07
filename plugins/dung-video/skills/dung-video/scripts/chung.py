"""Phần dùng chung: đường dẫn, chạy lệnh, đọc thông số video, chọn bộ mã hoá, giới hạn."""
import json, os, platform, re, shutil, subprocess, sys, unicodedata

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHIEN_BAN = open(os.path.join(SKILL, "VERSION"), encoding="utf-8").read().strip()
NHA = os.path.join(os.path.expanduser("~"), ".dung-video")          # dữ liệu riêng của người dùng, không mất khi nâng cấp
FONT = os.path.join(SKILL, "font")
MO_HINH = os.path.join(SKILL, "mo-hinh")

GIOI_HAN_GIAY = 5 * 60          # bản đầu: tối đa 5 phút clip thô mỗi lượt
GIOI_HAN_BYTE = 1024 ** 3       # và 1 GB
W, H, FPS = 1080, 1920, 30

LA_WIN = os.name == "nt"
# DV_NHAN_GIONG=faster ép dùng faster-whisper (để thử nhánh Windows trên Mac); DV_MO_HINH đổi cỡ mô hình khi thử
LA_MAC_M = sys.platform == "darwin" and platform.machine() == "arm64" and os.environ.get("DV_NHAN_GIONG") != "faster"
MO_HINH_GIONG = os.environ.get("DV_MO_HINH", "large-v3-turbo")


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def doc_json(p, mac_dinh=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return mac_dinh


def ghi_json(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    tam = p + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def tim_lenh(ten):
    """Tìm ffmpeg/ffprobe: trong PATH, rồi trong ~/.dung-video/bin."""
    p = shutil.which(ten)
    if p:
        return p
    for duoi in ("", ".exe"):
        q = os.path.join(NHA, "bin", ten + duoi)
        if os.path.exists(q):
            return q
    try:  # dự phòng: gói static-ffmpeg cài trong môi trường Python
        import static_ffmpeg.run as sr
        ff, fp = sr.get_or_fetch_platform_executables_else_raise()
        return ff if ten == "ffmpeg" else fp
    except Exception:
        return None


def sh(cmd, bat_buoc=True):
    """Chạy lệnh, trả (mã, stdout, stderr) dạng chữ UTF-8; không mở cửa sổ trên Windows."""
    kw = {}
    if LA_WIN:
        kw["creationflags"] = 0x08000000
    r = subprocess.run(cmd, capture_output=True, **kw)
    out, err = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    if bat_buoc and r.returncode != 0:
        raise RuntimeError(f"Lệnh lỗi ({r.returncode}): {' '.join(map(str, cmd[:6]))}…\n{err[-1500:]}")
    return r.returncode, out, err


def ffmpeg():
    p = tim_lenh("ffmpeg")
    if not p:
        raise SystemExit("Chưa có ffmpeg. Chạy: kiểm tra máy (dv.py kiem-may) để được hướng dẫn cài.")
    return p


def ban_ffmpeg():
    """Số phiên bản chính của ffmpeg (0 nếu không đọc được — bản dựng git)."""
    _, out, _ = sh([ffmpeg(), "-version"], bat_buoc=False)
    m = re.search(r"ffmpeg version n?(\d+)\.", out)
    return int(m.group(1)) if m else 0


def doc_bo_loc(tep):
    """Tham số đọc bộ lọc từ tệp: ffmpeg ≥ 7 dùng -/filter_complex, bản cũ dùng -filter_complex_script."""
    b = ban_ffmpeg()
    if b and b < 7:
        return ["-filter_complex_script", tep]
    return ["-/filter_complex", tep]


def ffconcat_duong(p):
    """Đường dẫn an toàn trong tệp ffconcat (Windows dùng / ; thoát dấu nháy đơn)."""
    return p.replace("\\", "/").replace("'", "'\\''")


def thong_so(duong):
    """Đọc độ dài, khung, fps, xoay, có tiếng hay không."""
    fp = tim_lenh("ffprobe")
    _, out, _ = sh([fp, "-v", "error", "-show_entries",
                    "format=duration,size:stream=codec_type,width,height,r_frame_rate:stream_side_data=rotation",
                    "-of", "json", duong])
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    if not v:
        raise SystemExit(f"Không đọc được hình trong tệp: {duong}")
    xoay = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            xoay = int(sd["rotation"])
    w, h = v["width"], v["height"]
    if abs(xoay) in (90, 270):
        w, h = h, w
    a, b = (v.get("r_frame_rate") or "30/1").split("/")
    return {"dur": float(d["format"]["duration"]), "byte": int(d["format"].get("size", 0)),
            "w": w, "h": h, "fps": round(float(a) / float(b or 1), 2),
            "co_am": any(s["codec_type"] == "audio" for s in d["streams"])}


def chon_ma_hoa():
    """Bộ mã hoá H.264 nhanh nhất chạy được trên máy này."""
    ff = ffmpeg()
    thu = []
    if sys.platform == "darwin":
        thu.append(["-c:v", "h264_videotoolbox", "-b:v", "12M", "-allow_sw", "1"])
    else:
        thu += [["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21", "-b:v", "0"],
                ["-c:v", "h264_qsv", "-global_quality", "22"],
                ["-c:v", "h264_amf", "-quality", "balanced", "-rc", "cqp", "-qp_i", "21", "-qp_p", "23"]]
    for t in thu:
        ma, _, _ = sh([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", *t, "-f", "null", "-"],
                      bat_buoc=False)
        if ma == 0:
            return t
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]


def in_ra(*a):
    print(*a, flush=True)
