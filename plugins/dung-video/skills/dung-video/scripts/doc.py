"""ĐỌC VIDEO: nhận giọng (từng chữ có mốc giây), tìm mặt, dò vùng chuyển động, đề xuất chỗ cắt, viết bản tóm tắt.

    dv.py doc <thư mục dự án> --video a.mov [--video b.mov …] [--ho-so <tên>]
"""
import argparse, os, re, subprocess, sys, tempfile, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C
import ho_so as HS

CAU_BIA = ["đăng ký kênh", "subscribe", "cảm ơn các bạn đã theo dõi", "cảm ơn các bạn đã xem", "like và share",
           "hẹn gặp lại các bạn", "ghiền mì gõ", "để không bỏ lỡ"]
LUOI_C, LUOI_D = 27, 48     # lưới chuyển động: 27 cột × 48 hàng (khung dọc)
MAU_FPS = 4                 # số khung/giây khi xem hình


# ---------- nhận giọng ----------
def _am_thanh(src, wav):
    C.sh([C.ffmpeg(), "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])


def nhan_giong(wav, goi_y):
    """Trả danh sách câu [{a,b,txt,tu:[{w,a,b,p}], nghi}]. Mac M dùng mlx-whisper, máy khác dùng faster-whisper."""
    if C.LA_MAC_M:
        import mlx_whisper
        r = mlx_whisper.transcribe(wav, path_or_hf_repo=f"mlx-community/whisper-{C.MO_HINH_GIONG}", language="vi",
                                   word_timestamps=True, condition_on_previous_text=False, initial_prompt=goi_y,
                                   verbose=None)
        segs = [(s["start"], s["end"], s["text"], s.get("avg_logprob", 0), s.get("no_speech_prob", 0),
                 s.get("compression_ratio", 1), [(w["word"], w["start"], w["end"], w.get("probability", 1))
                                                  for w in s.get("words", [])]) for s in r["segments"]]
    else:
        from faster_whisper import WhisperModel
        try:
            import ctranslate2
            cuda = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda = False
        m = WhisperModel(C.MO_HINH_GIONG, device="cuda" if cuda else "cpu",
                         compute_type="float16" if cuda else "int8")
        import wave
        with wave.open(wav) as f:                 # tự đọc WAV: tránh lỗi tương thích thư viện PyAV
            am = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
        it, _ = m.transcribe(am, language="vi", word_timestamps=True, vad_filter=True,
                             condition_on_previous_text=False, initial_prompt=goi_y)
        segs = [(s.start, s.end, s.text, s.avg_logprob, s.no_speech_prob, s.compression_ratio,
                 [(w.word, w.start, w.end, w.probability) for w in (s.words or [])]) for s in it]
    cau = []
    for a, b, txt, lp, ns, cr, ws in segs:
        txt = C.nfc(txt).strip()
        tu = [{"w": C.nfc(w).strip(), "a": round(wa, 2), "b": round(wb, 2), "p": round(p, 2)}
              for w, wa, wb, p in ws if w.strip()]
        dai = max(0.01, b - a)
        dem_so = sum(bool(re.fullmatch(r"\d+[.,]?", w["w"])) for w in tu) >= max(1, len(tu) * 0.6)  # đang đếm 1, 2, 3…
        nghi = ((ns > 0.6 and lp < -0.8) or cr > 2.4 or any(k in txt.lower() for k in CAU_BIA)
                or (dai > 4 and len(tu) / dai < 0.8 and not dem_so))
        cau.append({"a": round(a, 2), "b": round(b, 2), "txt": txt, "tu": tu, "nghi_bia": bool(nghi)})
    return cau


def tinh_chinh_tu(cau, wav):
    """Whisper hay kéo dài chữ phủ cả khoảng lặng (vd «cúi» 9,6–11,7 s). Dùng năng lượng âm thanh
    để thu đầu/cuối mỗi chữ về đúng chỗ có tiếng — nhờ vậy mới thấy và cắt được khoảng ngừng."""
    import wave
    with wave.open(wav) as f:
        x = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    k = 320                                            # 20 ms ở 16 kHz
    n = len(x) // k
    if n < 10:
        return cau
    db = 20 * np.log10(np.sqrt((x[:n * k].reshape(n, k) ** 2).mean(1)) + 1e-6)
    nen, noi = np.percentile(db, 10), np.percentile(db, 95)
    nguong = nen + 0.35 * (noi - nen)
    co = db > nguong
    for c in cau:
        for w in c["tu"]:
            i0, i1 = int(w["a"] / 0.02), min(n, int(np.ceil(w["b"] / 0.02)))
            vung = np.nonzero(co[i0:i1])[0]
            if len(vung) == 0:
                continue
            a = (i0 + vung[0]) * 0.02 - 0.03
            b = (i0 + vung[-1] + 1) * 0.02 + 0.05
            a, b = max(w["a"], a), min(w["b"], b)
            if b - a >= 0.08:
                w["a"], w["b"] = round(a, 2), round(b, 2)
        if c["tu"]:
            c["a"], c["b"] = c["tu"][0]["a"], c["tu"][-1]["b"]
    return cau


# ---------- xem hình ----------
def xem_hinh(src, ts):
    """Mẫu 4 khung/giây: hộp mặt (toạ độ 0..1) và lưới chuyển động."""
    import cv2
    ow = 360
    oh = int(round(ow * ts["h"] / ts["w"] / 2) * 2)
    p = subprocess.Popen([C.ffmpeg(), "-v", "error", "-i", src, "-vf", f"fps={MAU_FPS},scale={ow}:{oh}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    det = cv2.FaceDetectorYN.create(os.path.join(C.MO_HINH, "yunet.onnx"), "", (ow, oh), 0.6, 0.3, 50)
    luoi = (LUOI_C, LUOI_D) if oh >= ow else (LUOI_D, LUOI_C)
    mat, dong, truoc = [], [], None
    n = ow * oh * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        img = np.frombuffer(buf, np.uint8).reshape(oh, ow, 3)
        _, f = det.detect(img)
        hop = []
        if f is not None:
            for r in f:
                x, y, w, h, diem = float(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[-1])
                hop.append([round(x / ow, 3), round(y / oh, 3), round(w / ow, 3), round(h / oh, 3), round(diem, 2)])
        mat.append(hop)
        xam = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        nho = cv2.resize(xam, luoi, interpolation=cv2.INTER_AREA).astype(np.int16)
        dong.append(np.zeros(nho.shape, np.uint8) if truoc is None else (np.abs(nho - truoc) >= 10).astype(np.uint8))
        truoc = nho
    p.wait()
    return mat, np.array(dong, np.uint8)


def bang_khung(srcs, ra, n=12, nhan=None):
    """Ảnh 12 khung có ghi giây để AI nhìn tổng thể."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(os.path.join(C.FONT, "BeVietnamPro-Bold.ttf"), 22)
    tong = sum(s["dur"] for s in srcs)
    o = []
    with tempfile.TemporaryDirectory() as td:
        for k in range(n):
            t = tong * (k + 0.5) / n
            for i, s in enumerate(srcs):
                if t < s["dur"] or i == len(srcs) - 1:
                    break
                t -= s["dur"]
            f = os.path.join(td, f"{k}.jpg")
            C.sh([C.ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", s["duong"], "-frames:v", "1",
                  "-vf", "scale=270:-2", f])
            im = Image.open(f).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 150, 30], fill=(0, 0, 0))
            d.text((6, 2), f"{nhan if nhan else f'[{i}]'} {t:5.1f}s", font=font, fill=(255, 220, 0))
            o.append(im)
    w, h = o[0].size
    tam = Image.new("RGB", (w * 6, h * ((n + 5) // 6)))
    for k, im in enumerate(o):
        tam.paste(im.resize((w, h)), ((k % 6) * w, (k // 6) * h))
    tam.save(ra, quality=85)


# ---------- đề xuất cắt ----------
def de_xuat_cat(nguon, loi, dong_list):
    """Khoảng ngừng giữa hai chữ > 0,35 s. Ghi mức chuyển động để biết đang làm động tác hay chỉ chờ."""
    khoang, dau_cuoi = [], []
    for i, s in enumerate(nguon):
        nen = float(np.median(dong_list[i].mean(axis=(1, 2)))) if len(dong_list[i]) else 0.0
        tu = [w for c in loi if c["src"] == i and not c["nghi_bia"] for w in c["tu"]]
        if not tu:
            dau_cuoi.append({"src": i, "a": 0.0, "b": s["dur"]})
            continue
        dau_cuoi.append({"src": i, "a": max(0.0, tu[0]["a"] - 0.15), "b": min(s["dur"], tu[-1]["b"] + 0.4)})
        dong = dong_list[i]
        for x, y in zip(tu, tu[1:]):
            g = y["a"] - x["b"]
            if g > 0.35:
                k0, k1 = int(x["b"] * MAU_FPS), max(int(x["b"] * MAU_FPS) + 1, int(y["a"] * MAU_FPS))
                muc = float(dong[k0:k1].mean()) if len(dong) and k0 < len(dong) else 0.0
                khoang.append({"src": i, "a": round(x["b"], 2), "b": round(y["a"], 2), "dai": round(g, 2),
                               "dong": round(muc, 3), "dong_tuong_doi": round(muc / nen, 2) if nen else 0.0, "truoc": x["w"], "sau": y["w"]})
    return dau_cuoi, khoang


def giu_theo_kieu(dau_cuoi, khoang, kieu, dem_truoc=0.15, dem_sau=0.10):
    """Danh sách đoạn GIỮ. tu-van: bỏ mọi khoảng ngừng. bai-tap: chỉ bỏ khoảng chờ dài không có động tác."""
    giu = []
    for dc in dau_cuoi:
        a = dc["a"]
        for k in khoang:
            if k["src"] != dc["src"]:
                continue
            bo = (k["dai"] > 0.35) if kieu == "tu-van" else (k["dai"] > 4.0 and k["dong_tuong_doi"] < 0.3)
            if bo:
                cat_a, cat_b = k["a"] + dem_truoc, k["b"] - dem_sau
                if cat_b - cat_a > 0.12:
                    giu.append({"src": dc["src"], "a": round(a, 2), "b": round(cat_a, 2)})
                    a = cat_b
        giu.append({"src": dc["src"], "a": round(a, 2), "b": round(dc["b"], 2)})
    return [g for g in giu if g["b"] - g["a"] > 0.05]


# ---------- tóm tắt cho AI ----------
def tom_tat(du_an, nguon, loi, mat_list, dong_list, khoang, ho_so):
    L = [f"# Tóm tắt dự án `{os.path.basename(du_an)}`", ""]
    for i, s in enumerate(nguon):
        L.append(f"- Nguồn [{i}] `{os.path.basename(s['duong'])}`: {s['dur']:.1f}s, {s['w']}×{s['h']}, {s['fps']} fps")
    L += ["", f"Hồ sơ: **{ho_so.get('ten_kenh', '')}** · người dẫn: {ho_so.get('nguoi_dan', '')}", "",
          "## Lời nói (giây GỐC của từng nguồn)", ""]
    for c in loi:
        dau = "⚠️ NGHI BỊA " if c["nghi_bia"] else ""
        L.append(f"- [{c['src']}] {c['a']:6.2f}–{c['b']:6.2f} {dau}{c['txt']}")
    L += ["", "## Hình (mỗi 5 giây): mặt to nhất và vùng chuyển động", ""]
    for i, s in enumerate(nguon):
        mat, dong = mat_list[i], dong_list[i]
        for t0 in range(0, int(s["dur"]) + 1, 5):
            k0, k1 = t0 * MAU_FPS, (t0 + 5) * MAU_FPS
            hop = [h for f in mat[k0:k1] for h in f]
            if hop:
                to = max(hop, key=lambda h: h[2] * h[3])
                cm = "CẬN MẶT" if to[3] > 0.13 else ("mặt vừa" if to[3] > 0.06 else "mặt nhỏ")
                m = f"{cm} (cằm ở {to[1] + to[3]:.2f} chiều cao)"
            else:
                m = "không thấy mặt"
            d = dong[k0:k1]
            if len(d):
                hang = d.mean(axis=(0, 2))
                ba = [hang[:16].mean(), hang[16:32].mean(), hang[32:].mean()]
                v = ["trên", "giữa", "dưới"]
                dd = ", ".join(f"{v[j]} {ba[j] * 100:.0f}%" for j in range(3))
            else:
                dd = "-"
            L.append(f"- [{i}] {t0:3d}–{t0 + 5:3d}s: {m}; chuyển động {dd}")
    L += ["", "## Khoảng ngừng > 0,35 s (động = chuyển động so với mức thường của video; ≥ 0,6 là đang làm động tác)", ""]
    for k in khoang:
        L.append(f"- [{k['src']}] {k['a']:.2f}–{k['b']:.2f} ({k['dai']:.2f}s, động {k['dong_tuong_doi']:.2f}) "
                 f"sau «{k['truoc']}» trước «{k['sau']}»")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("du_an")
    ap.add_argument("--video", action="append", required=True)
    ap.add_argument("--phu", action="append", default=[], help="clip cảnh minh hoạ (B-roll)")
    ap.add_argument("--ho-so", default="")
    a = ap.parse_args()
    t_bat_dau = time.time()
    du_an = os.path.abspath(a.du_an)
    os.makedirs(os.path.join(du_an, "doc"), exist_ok=True)
    ho_so = HS.lay(a.ho_so)

    nguon, phu, tong_giay, tong_byte = [], [], 0.0, 0
    for v in a.phu:
        v = os.path.abspath(v)
        if not os.path.exists(v):
            raise SystemExit(f"Không thấy tệp: {v}")
        ts = C.thong_so(v)
        ts["duong"] = v
        phu.append(ts)
        tong_giay += ts["dur"]
        tong_byte += os.path.getsize(v)
    for v in a.video:
        v = os.path.abspath(v)
        if not os.path.exists(v):
            raise SystemExit(f"Không thấy tệp: {v}")
        ts = C.thong_so(v)
        ts["duong"] = v
        nguon.append(ts)
        tong_giay += ts["dur"]
        tong_byte += os.path.getsize(v)
    if tong_giay > C.GIOI_HAN_GIAY or tong_byte > C.GIOI_HAN_BYTE:
        raise SystemExit(f"Vượt giới hạn bản này: {tong_giay / 60:.1f} phút, {tong_byte / 1e9:.2f} GB "
                         f"(tối đa 5 phút và 1 GB mỗi lượt). Hãy chia nhỏ clip rồi làm từng phần.")
    C.ghi_json(os.path.join(du_an, "viec.json"), {"nguon": nguon, "phu": phu, "ho_so": ho_so.get("_ten", ""),
                                                  "phien_ban": C.PHIEN_BAN, "tao_luc": time.strftime("%Y-%m-%d %H:%M")})

    goi_y = HS.goi_y_nhan_giong(ho_so)
    loi, mat_list, dong_list = [], [], []
    for i, s in enumerate(nguon):
        C.in_ra(f"[{i + 1}/{len(nguon)}] Nghe lời: {os.path.basename(s['duong'])}")
        with tempfile.TemporaryDirectory() as td:
            wav = os.path.join(td, "a.wav")
            if s["co_am"]:
                _am_thanh(s["duong"], wav)
                for c in tinh_chinh_tu(nhan_giong(wav, goi_y), wav):
                    c["src"] = i
                    c["tu"] = HS.sua_tu(c["tu"], ho_so.get("sua_tu", {}))
                    c["txt"] = " ".join(w["w"] for w in c["tu"]) or c["txt"]
                    loi.append(c)
        C.in_ra(f"[{i + 1}/{len(nguon)}] Xem hình: tìm mặt, dò chuyển động")
        m, d = xem_hinh(s["duong"], s)
        mat_list.append(m)
        dong_list.append(d)

    mat_phu, dong_phu = [], []
    for j, p in enumerate(phu):
        C.in_ra(f"Cảnh phụ [{j + 1}/{len(phu)}]: {os.path.basename(p['duong'])}")
        m, d = xem_hinh(p["duong"], p)
        mat_phu.append(m)
        dong_phu.append(d)
        bang_khung([p], os.path.join(du_an, "doc", f"bang-phu-{j}.jpg"), nhan=f"phụ[{j}]")
    if dong_phu:
        np.savez_compressed(os.path.join(du_an, "doc", "dong-phu.npz"), *dong_phu)

    dau_cuoi, khoang = de_xuat_cat(nguon, loi, dong_list)
    doc = os.path.join(du_an, "doc")
    C.ghi_json(os.path.join(doc, "loi.json"), {"cau": loi})
    C.ghi_json(os.path.join(doc, "mat.json"), {"fps_mau": MAU_FPS, "nguon": mat_list, "phu": mat_phu})
    np.savez_compressed(os.path.join(doc, "dong.npz"), *dong_list)
    C.ghi_json(os.path.join(doc, "de-xuat-cat.json"), {
        "dau_cuoi": dau_cuoi, "khoang": khoang,
        "giu_tu_van": giu_theo_kieu(dau_cuoi, khoang, "tu-van"),
        "giu_bai_tap": giu_theo_kieu(dau_cuoi, khoang, "bai-tap")})
    with open(os.path.join(doc, "tom-tat.md"), "w", encoding="utf-8") as f:
        f.write(tom_tat(du_an, nguon, loi, mat_list, dong_list, khoang, ho_so))
        if phu:
            f.write("\n## Cảnh phụ (B-roll) — xem ảnh doc/bang-phu-<số>.jpg để biết mỗi clip quay gì\n\n")
            for j, p in enumerate(phu):
                f.write(f"- phụ[{j}] `{os.path.basename(p['duong'])}`: {p['dur']:.1f}s, {p['w']}×{p['h']}\n")
    bang_khung(nguon, os.path.join(doc, "bang-khung.jpg"))
    C.in_ra(f"Đọc xong sau {time.time() - t_bat_dau:.0f} giây.")
    C.in_ra(f"→ Mở {os.path.join(doc, 'tom-tat.md')} và {os.path.join(doc, 'bang-khung.jpg')}, "
            f"rồi viết {os.path.join(du_an, 'ke-hoach.json')}")


if __name__ == "__main__":
    main()
