"""CÀI ĐẶT / KIỂM TRA MÁY. Chỉ dùng thư viện chuẩn của Python để chạy được trên máy mới tinh.

    dv.py cai-dat     cài: môi trường Python 3.12 (qua uv), thư viện, ffmpeg (nếu thiếu), mô hình nhận giọng
    dv.py kiem-may    chỉ kiểm tra, in từng mục ✅/❌ kèm cách sửa
"""
import os, platform, shutil, subprocess, sys

NHA = os.path.join(os.path.expanduser("~"), ".dung-video")
VENV = os.path.join(NHA, "venv")
WIN = os.name == "nt"
PY = os.path.join(VENV, "Scripts", "python.exe") if WIN else os.path.join(VENV, "bin", "python")
MAC_M = sys.platform == "darwin" and platform.machine() == "arm64"

CHUNG = ["numpy", "opencv-python-headless", "pillow", "cryptography",
         # giọng đọc AI (VieNeu-TTS, Apache 2.0). ONNX Runtime ≥ 1.23 chặn đọc mô hình nằm trong bộ nhớ đệm Hugging Face
         # (lỗi «External data path escapes model directory») → giữ 1.22.1 đã thử chạy được.
         "vieneu", "onnxruntime==1.22.1"]
NHAN_GIONG = ["mlx-whisper"] if MAC_M else ["faster-whisper"]

CAI_UV = ('Mac: mở Terminal, dán:  curl -LsSf https://astral.sh/uv/install.sh | sh' if not WIN else
          'Windows: mở PowerShell, dán:  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"')


def tim_uv():
    p = shutil.which("uv")
    if p:
        return p
    for q in [os.path.join(os.path.expanduser("~"), ".local", "bin", "uv" + (".exe" if WIN else "")),
              os.path.join(os.path.expanduser("~"), ".cargo", "bin", "uv" + (".exe" if WIN else ""))]:
        if os.path.exists(q):
            return q
    return None


def chay(cmd):
    print("  $", " ".join(cmd[:4]), "…", flush=True)
    return subprocess.call(cmd)


def kiem():
    ok = True

    def dong(tot, ten, sua=""):
        nonlocal ok
        ok &= tot
        print(("✅ " if tot else "❌ ") + ten + ("" if tot or not sua else f"\n     → {sua}"))

    print(f"Máy: {platform.system()} {platform.machine()} · Python hệ thống {platform.python_version()}")
    dong(tim_uv() is not None, "uv (trình cài Python)", CAI_UV)
    dong(os.path.exists(PY), "Môi trường Python 3.12 của skill", "Nói: «cài đặt dựng video»")
    if os.path.exists(PY):
        thieu = subprocess.run([PY, "-c", "import importlib.util as u,sys;"
                                "m=['numpy','cv2','PIL','cryptography','vieneu','" + ("mlx_whisper" if MAC_M else "faster_whisper") + "'];"
                                "print(' '.join(x for x in m if not u.find_spec(x)))"],
                               capture_output=True, text=True).stdout.strip()
        dong(not thieu, "Thư viện" + (f" (thiếu: {thieu})" if thieu else ""), "Nói: «cài đặt dựng video»")
        ff = shutil.which("ffmpeg") or subprocess.run(
            [PY, "-c", "import static_ffmpeg.run as r;print(r.get_or_fetch_platform_executables_else_raise()[0])"],
            capture_output=True, text=True).stdout.strip()
        dong(bool(ff), "ffmpeg (công cụ dựng hình)", "Nói: «cài đặt dựng video»")
    bq = os.path.exists(os.path.join(NHA, "ban-quyen.json"))
    dong(bq, "Bản quyền đã kích hoạt", "Nói: «kích hoạt mã <mã của bạn>»")
    tu_do = shutil.disk_usage(os.path.expanduser("~")).free / 1e9
    dong(tu_do > 5, f"Ổ đĩa còn trống {tu_do:.0f} GB", "Cần trống ít nhất 5 GB (mô hình ~1,6 GB + video tạm)")
    print("\nMáy sẵn sàng." if ok else "\nSửa các mục ❌ ở trên rồi kiểm lại.")
    return ok


def cai():
    os.makedirs(NHA, exist_ok=True)
    uv = tim_uv()
    if not uv:
        sys.exit("Thiếu uv. " + CAI_UV + "\nCài xong mở lại cửa sổ rồi chạy lại cài đặt.")
    print("1/4 Tạo môi trường Python 3.12…")
    if not os.path.exists(PY) and chay([uv, "venv", "--python", "3.12", VENV]) != 0:
        sys.exit("Không tạo được môi trường Python. Kiểm tra mạng rồi thử lại.")
    print("2/4 Cài thư viện (lần đầu vài phút)…")
    goi = CHUNG + NHAN_GIONG + ([] if shutil.which("ffmpeg") else ["static-ffmpeg"])
    if chay([uv, "pip", "install", "--python", PY, "-q", *goi]) != 0:
        sys.exit("Cài thư viện lỗi. Kiểm tra mạng rồi thử lại.")
    print("3/4 Kiểm tra ffmpeg…")
    if not shutil.which("ffmpeg"):
        subprocess.call([PY, "-c", "import static_ffmpeg.run as r;r.get_or_fetch_platform_executables_else_raise()"])
    print("4/4 Tải mô hình nhận giọng tiếng Việt (~1,6 GB, chỉ lần đầu)…")
    if MAC_M:
        code = "from huggingface_hub import snapshot_download as s;s('mlx-community/whisper-large-v3-turbo')"
    else:
        code = "from faster_whisper import WhisperModel as M;M('large-v3-turbo',device='cpu',compute_type='int8')"
    subprocess.call([PY, "-c", code])
    print()
    kiem()


if __name__ == "__main__":
    kiem() if "--kiem" in sys.argv else cai()
