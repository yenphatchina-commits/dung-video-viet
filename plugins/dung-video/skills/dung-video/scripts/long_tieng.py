"""LỒNG TIẾNG BẰNG GIỌNG ĐỌC AI (VieNeu-TTS, chạy trên máy, giấy phép Apache 2.0 — dùng thương mại được).

    dv.py long-tieng <dự án> --kich-ban <tệp .txt> [--giong "Ngọc Huyền"] [--canh <clip>…] [--ho-so <tên>] [--toc 1.0]
    dv.py giong ds                                  liệt kê giọng có sẵn + giọng riêng
    dv.py giong them <tên> <tệp ghi âm 5–10 s> --dong-y   thêm giọng riêng (nhân bản) — CHỈ khi có sự đồng ý

Việc làm: đọc kịch bản thành giọng → ghép cảnh minh hoạ thành nền dọc 9:16 khớp độ dài giọng → chạy bước ĐỌC như
video thường (nghe lại giọng AI để có mốc từng chữ, xem hình). Sau đó AI viết ke-hoach.json và dựng như bình thường.
Kịch bản: mỗi đoạn một dòng; dòng trống = nghỉ dài hơn. Dòng bắt đầu bằng "[Tên giọng]" đổi giọng cho dòng đó.
"""
import argparse, json, os, re, subprocess, sys, tempfile, time, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C
import ho_so as HS

GIONG_RIENG = os.path.join(C.NHA, "giong")
GIONG_CO_SAN = {   # tên: (miền, giới, chất giọng) — theo thẻ mô hình VieNeu-TTS v3 Turbo
    "Minh Quân": ("Bắc", "nam", "tự nhiên"), "Ngọc Huyền": ("Bắc", "nữ", "tự nhiên"), "Trúc Ly": ("Bắc", "nữ", "tự nhiên"),
    "Đoan Trang": ("Bắc", "nữ", "tự nhiên"), "Mai Anh": ("Bắc", "nữ", "bản tin"), "Minh Đức": ("Bắc", "nam", "bản tin"),
    "Mạnh Dũng": ("Bắc", "nam", "tự nhiên"), "Phạm Tuyên": ("Bắc", "nam", "tự nhiên"), "Xuân Vĩnh": ("Bắc", "nam", "tự nhiên"),
    "Anh Khôi": ("Bắc", "nam", "kể chuyện"), "Ngọc Linh": ("Bắc", "nữ", "kể chuyện"), "Quỳnh Anh": ("Bắc", "nữ", "kể chuyện"),
    "Thanh Bình": ("Bắc", "nam", "kể chuyện"), "Ngọc Trân": ("Trung", "nữ", "tự nhiên"), "Quang Sơn": ("Trung", "nam", "tự nhiên"),
    "Adam": ("Nam", "nam", "tự nhiên"), "Minh Triết": ("Nam", "nam", "bản tin"), "Thùy Dung": ("Nam", "nữ", "bản tin"),
    "Kim Thanh": ("Nam", "nữ", "kể chuyện"), "Mỹ Duyên": ("Nam", "nữ", "kể chuyện"), "Thái Sơn": ("Nam", "nam", "kể chuyện"),
    "Thục Đoan": ("Nam", "nữ", "kể chuyện"), "Đức Trí": ("Nam", "nam", "kể chuyện"),
}
PHAT_AM_MAC_DINH = {"Zalo": "Da lô", "TikTok": "Tích tốc", "Facebook": "Phây búc", "YouTube": "Diu túp", "Shopee": "Sô pi",
                    "online": "on lai", "spa": "xờ pa", "OK": "ô kê", "inbox": "in bóc"}


def mo_hinh():
    """Nạp VieNeu (lần đầu tự tải ~0,6 GB mô hình)."""
    try:
        from vieneu import Vieneu
    except ImportError:
        raise SystemExit("Chưa cài giọng đọc AI. Nói: «cài đặt dựng video» để cài bổ sung.")
    import logging
    logging.getLogger("vieneu").setLevel(logging.ERROR)
    return Vieneu()


def doi_phat_am(cau, bang):
    for sai, dung in sorted(bang.items(), key=lambda kv: -len(kv[0])):
        cau = re.sub(rf"(?<!\w){re.escape(sai)}(?!\w)", dung, cau, flags=re.IGNORECASE)
    return cau


def tach_cau(doan):
    """Tách đoạn thành câu ngắn để đọc tự nhiên và có điểm nghỉ."""
    cau = [c.strip() for c in re.split(r"(?<=[.!?…])\s+", doan) if c.strip()]
    ra = []
    for c in cau:                       # câu quá dài (> 220 ký tự) cắt tiếp ở dấu phẩy
        while len(c) > 220 and "," in c[:220]:
            k = c[:220].rfind(",")
            ra.append(c[:k + 1].strip())
            c = c[k + 1:].strip()
        ra.append(c)
    return ra


def doc_wav(p):
    with wave.open(p) as f:
        sr, ch = f.getframerate(), f.getnchannels()
        x = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    return (x.reshape(-1, ch).mean(1) if ch > 1 else x), sr


def doc_kich_ban(kich_ban, giong_mac_dinh, bang, ra_wav, toc=1.0):
    v = mo_hinh()
    rieng = {os.path.splitext(f)[0]: os.path.join(GIONG_RIENG, f) for f in os.listdir(GIONG_RIENG)} if os.path.isdir(GIONG_RIENG) else {}
    doan = [d.strip() for d in re.split(r"\n\s*\n", kich_ban.strip()) if d.strip()]
    am, sr, moc = [], None, []
    t = 0.0
    with tempfile.TemporaryDirectory() as td:
        for i, d in enumerate(doan):
            for dong in [x.strip() for x in d.split("\n") if x.strip()]:
                giong = giong_mac_dinh
                m = re.match(r"^\[([^\]]+)\]\s*(.*)$", dong)
                if m:
                    giong, dong = m.group(1).strip(), m.group(2)
                for c in tach_cau(dong):
                    p = os.path.join(td, f"{len(moc)}.wav")
                    noi = doi_phat_am(C.nfc(c), bang)
                    if giong in rieng:
                        a = v.infer(noi, ref_audio=rieng[giong])
                    elif giong in GIONG_CO_SAN:
                        a = v.infer(noi, voice=giong)
                    else:
                        raise SystemExit(f"Không có giọng «{giong}». Xem: dv.py giong ds")
                    v.save(a, p)
                    x, sr = doc_wav(p)
                    moc.append({"a": round(t, 2), "b": round(t + len(x) / sr, 2), "giong": giong, "cau": C.nfc(c)})
                    am.append(x)
                    t += len(x) / sr
                    nghi = 0.28
                    am.append(np.zeros(int(sr * nghi), np.float32))
                    t += nghi
                    C.in_ra(f"  đọc {len(moc)}: {c[:60]}")
            if i < len(doan) - 1:            # nghỉ giữa đoạn
                am.append(np.zeros(int(sr * 0.45), np.float32))
                t += 0.45
    y = np.concatenate(am)
    y = y / max(1e-6, np.abs(y).max()) * 0.9
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tam = f.name
    with wave.open(tam, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((y * 32767).astype(np.int16).tobytes())
    loc = f"atempo={toc:.3f}," if abs(toc - 1) > 0.01 else ""
    C.sh([C.ffmpeg(), "-v", "error", "-y", "-i", tam, "-af", f"{loc}aresample=48000", "-ac", "2", ra_wav])
    os.remove(tam)
    for m_ in moc:
        m_["a"], m_["b"] = round(m_["a"] / toc, 2), round(m_["b"] / toc, 2)
    return moc, t / toc


def dung_nen(canh, moc, dai, ra_mp4, wav, mau_nen="#141418"):
    """Nền hình 9:16: mỗi câu một cảnh (xoay vòng các clip, lấy phần giữa clip); không có clip → nền màu."""
    W, H, FPS = C.W, C.H, C.FPS
    if not canh:
        C.sh([C.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={mau_nen.replace('#', '0x')}:s={W}x{H}:r={FPS}:d={dai:.2f}",
              "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", ra_mp4])
        return
    ts = [C.thong_so(c) for c in canh]
    vao, loc, k = [], [], 0
    for c in canh:
        vao += ["-stream_loop", "-1", "-i", c]
    ranh = [m["a"] for m in moc[1:]] + [dai]
    t0 = 0.0
    for i, t1 in enumerate(ranh):
        j = i % len(canh)
        d = t1 - t0
        a = max(0.0, (ts[j]["dur"] - d) / 2) if ts[j]["dur"] > d else 0.0
        loc.append(f"[{j}:v]trim=start={a:.3f}:duration={d:.3f},setpts=PTS-STARTPTS,"
                   f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[s{i}]")
        t0 = t1
        k += 1
    loc.append("".join(f"[s{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[v]")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(";\n".join(loc))
        tep = f.name
    C.sh([C.ffmpeg(), "-v", "error", "-y", *vao, "-i", wav, *C.doc_bo_loc(tep), "-map", "[v]", "-map", f"{len(canh)}:a",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", ra_mp4])
    os.remove(tep)


def sua_theo_kich_ban(du_an, kich_ban):
    """Phụ đề lấy đúng chữ trong kịch bản (máy nghe lại hay viết nhầm chữ đồng âm: suất/xuất, Zalo/gia lô),
    giữ mốc thời gian của từng chữ do máy nghe."""
    import difflib
    p = os.path.join(du_an, "doc", "loi.json")
    loi = C.doc_json(p)
    kb = [w for w in re.sub(r"^\s*\[[^\]]+\]\s*", "", C.nfc(kich_ban), flags=re.M).split() if w.strip()]
    chuan = lambda s: re.sub(r"\W", "", s.lower())
    tu = [(ci, wi) for ci, c in enumerate(loi["cau"]) for wi, _ in enumerate(c["tu"])]
    nghe = [chuan(loi["cau"][ci]["tu"][wi]["w"]) for ci, wi in tu]
    sm = difflib.SequenceMatcher(a=nghe, b=[chuan(w) for w in kb], autojunk=False)
    doi = 0
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "replace" and a1 - a0 == b1 - b0:
            for k in range(a1 - a0):
                ci, wi = tu[a0 + k]
                loi["cau"][ci]["tu"][wi]["w"] = kb[b0 + k]
                doi += 1
        elif op == "replace" and a1 > a0:        # khác số chữ (vd «299 .000 đồng» ↔ «299.000đ»): gộp vào chữ đầu
            ci, wi = tu[a0]
            loi["cau"][ci]["tu"][wi]["w"] = " ".join(kb[b0:b1])
            for k in range(a0 + 1, a1):
                cj, wj = tu[k]
                loi["cau"][cj]["tu"][wj]["w"] = ""
            doi += 1
        elif op == "equal":
            for k in range(a1 - a0):
                ci, wi = tu[a0 + k]
                loi["cau"][ci]["tu"][wi]["w"] = kb[b0 + k]      # giữ đúng hoa/thường, dấu câu của kịch bản
    for c in loi["cau"]:
        c["tu"] = [w for w in c["tu"] if w["w"]]
        c["txt"] = " ".join(w["w"] for w in c["tu"])
        c["nghi_bia"] = False
    C.ghi_json(p, loi)
    return doi


def ds_giong():
    C.in_ra("Giọng có sẵn (dùng thương mại được):")
    for mien in ("Bắc", "Trung", "Nam"):
        C.in_ra(f"  Miền {mien}: " + " · ".join(f"{t} ({g[1]}, {g[2]})" for t, g in GIONG_CO_SAN.items() if g[0] == mien))
    rieng = sorted(os.path.splitext(f)[0] for f in os.listdir(GIONG_RIENG)) if os.path.isdir(GIONG_RIENG) else []
    C.in_ra("Giọng riêng: " + (", ".join(rieng) if rieng else "(chưa có)"))


def them_giong(ten, tep, dong_y):
    if not dong_y:
        raise SystemExit("Chỉ được nhân bản giọng khi CHÍNH người có giọng đồng ý. Thêm --dong-y để xác nhận điều đó.")
    os.makedirs(GIONG_RIENG, exist_ok=True)
    ts = C.thong_so(tep)
    if ts["dur"] < 3:
        raise SystemExit("Mẫu giọng quá ngắn — cần 5–10 giây nói rõ, không nhạc nền.")
    ra = os.path.join(GIONG_RIENG, ten + ".wav")
    C.sh([C.ffmpeg(), "-v", "error", "-y", "-i", tep, "-t", "10", "-vn", "-ac", "1", "-ar", "24000", ra])
    C.ghi_json(os.path.join(GIONG_RIENG, ten + ".json"), {"ten": ten, "nguon": os.path.basename(tep),
                                                         "dong_y": True, "luc": time.strftime("%Y-%m-%d %H:%M")})
    C.in_ra(f"✅ Đã thêm giọng riêng «{ten}». Dùng: --giong \"{ten}\"")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "giong":
        a = sys.argv[2:]
        if a[:1] == ["them"] and len(a) >= 3:
            return them_giong(a[1], a[2], "--dong-y" in a)
        return ds_giong()
    ap = argparse.ArgumentParser()
    ap.add_argument("du_an")
    ap.add_argument("--kich-ban", required=True)
    ap.add_argument("--giong", default="Ngọc Huyền")
    ap.add_argument("--canh", action="append", default=[])
    ap.add_argument("--ho-so", default="")
    ap.add_argument("--toc", type=float, default=1.0)
    a = ap.parse_args()
    t_bd = time.time()
    du_an = os.path.abspath(a.du_an)
    lt = os.path.join(du_an, "long-tieng")
    os.makedirs(lt, exist_ok=True)
    hs = HS.lay(a.ho_so)
    bang = dict(PHAT_AM_MAC_DINH, **hs.get("phat_am", {}))
    kb = open(a.kich_ban, encoding="utf-8").read()
    C.in_ra(f"1/3 Đọc kịch bản bằng giọng «{a.giong}»…")
    wav = os.path.join(lt, "giong.wav")
    moc, dai = doc_kich_ban(kb, a.giong, bang, wav, min(1.3, max(0.8, a.toc)))
    C.ghi_json(os.path.join(lt, "cau.json"), {"giong": a.giong, "dai": round(dai, 2), "cau": moc})
    C.in_ra(f"2/3 Ghép nền hình {len(a.canh)} cảnh, dài {dai:.1f}s…")
    nen = os.path.join(lt, "nen.mp4")
    dung_nen([os.path.abspath(c) for c in a.canh], moc, dai, nen, wav, hs.get("mau_nen", "#141418"))
    C.in_ra("3/3 Chạy bước đọc trên video lồng tiếng…")
    lenh = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc.py"), du_an, "--video", nen]
    for c in a.canh:
        lenh += ["--phu", os.path.abspath(c)]
    if a.ho_so:
        lenh += ["--ho-so", a.ho_so]
    r = subprocess.call(lenh)
    if r:
        raise SystemExit(r)
    n = sua_theo_kich_ban(du_an, kb)
    C.in_ra(f"Phụ đề đã lấy theo đúng chữ kịch bản ({n} chỗ máy nghe nhầm được sửa).")
    v = C.doc_json(os.path.join(du_an, "viec.json"))
    v["long_tieng"] = {"giong": a.giong, "kich_ban": os.path.abspath(a.kich_ban)}
    C.ghi_json(os.path.join(du_an, "viec.json"), v)
    C.in_ra(f"Lồng tiếng xong sau {time.time() - t_bd:.0f} giây. Nền: mỗi câu một cảnh — AI có thể đổi cảnh bằng «chen».")


if __name__ == "__main__":
    main()
