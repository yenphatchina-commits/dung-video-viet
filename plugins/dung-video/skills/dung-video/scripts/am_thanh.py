"""ÂM THANH TỰ TẠO BẰNG CODE — không dùng tệp của ai nên không dính bản quyền.

Hiệu ứng: pop (chữ hiện), whoosh (chuyển ý / hết bìa), ting (nhấn điểm quan trọng), click (nhãn nhỏ), bum (mở đầu mạnh).
Nhạc nền mẫu: các kiểu "nhe-nhang", "tuoi-sang", "tram" — vòng hợp âm êm, dùng khi người dùng chưa có nhạc riêng.
"""
import os, sys, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C

SR = 48000
THU_MUC = os.path.join(C.NHA, "am-thanh-tao")
LOAI_SFX = ("pop", "whoosh", "ting", "click", "bum")
KIEU_NHAC = ("nhe-nhang", "tuoi-sang", "tram")


def _ghi(p, x):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x], 1) if x.ndim == 1 else x
    with wave.open(p, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((st * 32767).astype(np.int16).tobytes())


def _env(n, tan_cong, giam):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(1e-4, tan_cong)) * np.exp(-t / giam)


def sfx(loai):
    rng = np.random.default_rng(7)
    if loai == "pop":
        n = int(0.14 * SR)
        t = np.arange(n) / SR
        f = 900 * np.exp(-t * 28) + 260
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.035)
    elif loai == "click":
        n = int(0.05 * SR)
        x = (rng.standard_normal(n) * 0.5 + np.sin(2 * np.pi * 2200 * np.arange(n) / SR)) * _env(n, 0.0005, 0.008)
    elif loai == "ting":
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        x = sum(a * np.sin(2 * np.pi * 1318.5 * k * t) for k, a in ((1, 1), (2.01, 0.35), (3.02, 0.12))) * _env(n, 0.003, 0.22)
    elif loai == "whoosh":
        n = int(0.55 * SR)
        no = rng.standard_normal(n)
        # lọc thông dải quét lên rồi xuống: làm mượt dần bằng trung bình trượt có độ dài thay đổi
        t = np.linspace(0, 1, n)
        k = (40 - 34 * np.sin(np.pi * t)).astype(int)
        cs = np.cumsum(np.insert(no, 0, 0))
        idx = np.arange(n)
        lo = np.maximum(0, idx - k)
        x = (cs[idx + 1] - cs[lo]) / (idx + 1 - lo)
        x = x * np.sin(np.pi * t) ** 2
        x /= np.abs(x).max() + 1e-9
    elif loai == "bum":
        n = int(0.8 * SR)
        t = np.arange(n) / SR
        f = 120 * np.exp(-t * 6) + 45
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.003, 0.25)
    else:
        raise ValueError(loai)
    return x / (np.abs(x).max() + 1e-9) * 0.9


HOP_AM = {   # (bpm, hợp âm theo nốt MIDI)
    "nhe-nhang": (78, [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]]),   # Am7 Fmaj7 Cmaj7 G7
    "tuoi-sang": (96, [[48, 52, 55, 60], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]),   # C G Am F
    "tram":      (70, [[50, 53, 57, 60], [46, 50, 53, 57], [48, 52, 55, 58], [45, 48, 52, 55]]),   # Dm7 Bb C7 Am
}


def nhac_nen(kieu, giay):
    """Nền hợp âm êm + nốt rải nhẹ, lặp đủ `giay` giây. Không có giai điệu nổi để không át giọng nói."""
    bpm, ha = HOP_AM[kieu]
    nhip = 60 / bpm
    o_nhip = 4 * nhip
    n = int((giay + 1) * SR)
    x = np.zeros(n)
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    t_o = np.arange(int(o_nhip * SR)) / SR
    pad_env = np.minimum(1, t_o / 0.6) * np.minimum(1, (o_nhip - t_o) / 0.6)
    k = 0
    while k * o_nhip < giay + 1:
        hop = ha[k % len(ha)]
        i0 = int(k * o_nhip * SR)
        seg = sum(np.sin(2 * np.pi * hz(m) * t_o) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.003 * t_o) for m in hop)
        seg = seg * pad_env * 0.10
        tron = seg[: max(0, min(len(seg), n - i0))]
        x[i0:i0 + len(tron)] += tron
        for j in range(8):                     # nốt rải nửa nhịp
            m = hop[(j * 3) % len(hop)] + 12
            a = i0 + int(j * nhip / 2 * SR)
            ln = int(0.7 * SR)
            if a + ln >= n:
                break
            tt = np.arange(ln) / SR
            x[a:a + ln] += np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt / 0.25) * 0.06
        k += 1
    # trầm
    x = x + 0.5 * np.convolve(x, np.ones(240) / 240, mode="same")
    x = x[: int(giay * SR)]
    return x / (np.abs(x).max() + 1e-9) * 0.7


def tep_sfx(loai):
    os.makedirs(THU_MUC, exist_ok=True)
    p = os.path.join(THU_MUC, f"sfx-{loai}.wav")
    if not os.path.exists(p):
        _ghi(p, sfx(loai))
    return p


def tep_nhac_mau(kieu, giay):
    os.makedirs(THU_MUC, exist_ok=True)
    giay = int(np.ceil(giay / 30) * 30)
    p = os.path.join(THU_MUC, f"nhac-{kieu}-{giay}s.wav")
    if not os.path.exists(p):
        _ghi(p, nhac_nen(kieu, giay))
    return p


if __name__ == "__main__":
    for l in LOAI_SFX:
        print(tep_sfx(l))
    for k in KIEU_NHAC:
        print(tep_nhac_mau(k, 30))
