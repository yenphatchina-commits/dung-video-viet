"""HỌC PHONG CÁCH từ một video mẫu (có thể kèm video thô của nó để học chính xác chỗ cắt).

    dv.py hoc <thư mục học> --mau <video mẫu đã edit> [--tho <video thô của nó>] [--ho-so <tên>]

Máy đo: nhịp cắt cảnh, khoảng ngừng giữa câu, tốc độ nói, âm lượng nhạc so với giọng, số lần phóng to,
màu nhấn nổi bật. Rồi chụp 24 khung để AI xem kiểu chữ, vị trí chữ, cách mở/kết.
AI đọc `hoc/tom-tat-hoc.md`, xem ảnh, rồi viết tệp phong cách (đường dẫn in ở cuối).
Chỉ học CÁCH LÀM — không lấy chữ, logo, mặt, giọng, nhạc của video mẫu.
"""
import argparse, colorsys, json, os, re, subprocess, sys, tempfile, time, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C
import doc as D
import ho_so as HS

THU_MUC_PC = os.path.join(C.NHA, "phong-cach")


def nghe(duong, goi_y):
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        D._am_thanh(duong, wav)
        cau = D.tinh_chinh_tu(D.nhan_giong(wav, goi_y), wav)
        with wave.open(wav) as f:
            x = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    return [c for c in cau if not c["nghi_bia"]], x


def nhac_so_voi_giong(cau, x):
    """Mức tiếng nền (nhạc) trong khoảng không nói so với lúc đang nói, tính dB."""
    k = 320
    n = len(x) // k
    db = 20 * np.log10(np.sqrt((x[:n * k].reshape(n, k) ** 2).mean(1)) + 1e-6)
    noi = np.zeros(n, bool)
    for c in cau:
        for w in c["tu"]:
            noi[int(w["a"] / 0.02):int(w["b"] / 0.02) + 1] = True
    if noi.sum() < 10 or (~noi).sum() < 10:
        return None
    return round(float(np.median(db[~noi]) - np.median(db[noi])), 1)


def cat_canh(duong):
    """Các mốc đổi cảnh (giây)."""
    _, _, err = C.sh([C.ffmpeg(), "-nostats", "-i", duong, "-vf", "scale=320:-2,select='gt(scene,0.13)',showinfo",
                      "-an", "-f", "null", "-"], bat_buoc=False)
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", err)]


def phong_to(mat, cat):
    """Đếm lần mặt to/nhỏ đột ngột (≥ 15%) mà không đổi cảnh = có phóng to/thu nhỏ."""
    dem, truoc = 0, None
    for k, f in enumerate(mat):
        h = max((r[3] for r in f), default=None)
        if h and truoc and abs(h / truoc - 1) > 0.15 and not any(abs(k / D.MAU_FPS - c) < 0.5 for c in cat):
            dem += 1
        truoc = h or truoc
    return dem // 2   # vào rồi ra tính 1 lần


def mau_noi_bat(duong, dur):
    """Màu bão hoà, sáng xuất hiện nhiều nhất (thường là màu chữ nhấn / nền nhãn)."""
    p = subprocess.run([C.ffmpeg(), "-v", "error", "-i", duong, "-vf", f"fps=8/{max(1, dur):.2f},scale=96:-2",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    px = np.frombuffer(p.stdout, np.uint8).reshape(-1, 3).astype(np.float32) / 255
    if not len(px):
        return []
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in px[::3]])
    m = (hsv[:, 1] > 0.6) & (hsv[:, 2] > 0.75)
    if m.sum() < 20:
        return []
    hue = (hsv[m, 0] * 24).astype(int) % 24
    ra = []
    for h, so in sorted(((h, int((hue == h).sum())) for h in set(hue)), key=lambda t: -t[1])[:3]:
        r, g, b = colorsys.hsv_to_rgb((h + 0.5) / 24, 0.9, 1.0)
        ra.append({"mau": "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255)), "ti_le": round(so / len(hsv), 3)})
    return ra


def so_khop(tho, mau):
    """Ghép từng chữ của bản thô với bản edit → biết đoạn nào bị cắt và còn chừa bao nhiêu."""
    import difflib
    def tu(cau):
        return [(re.sub(r"\W", "", w["w"].lower()), w["a"], w["b"]) for c in cau for w in c["tu"] if re.sub(r"\W", "", w["w"])]
    R, E = tu(tho), tu(mau)
    sm = difflib.SequenceMatcher(a=[w[0] for w in R], b=[w[0] for w in E], autojunk=False)
    cap = [(R[b.a + k], E[b.b + k]) for b in sm.get_matching_blocks() for k in range(b.size)]
    giu_ti_le = len(cap) / max(1, len(R))
    bo, con = [], []
    for (r1, e1), (r2, e2) in zip(cap, cap[1:]):
        gap_tho, gap_ed = r2[1] - r1[2], e2[1] - e1[2]
        if gap_tho - gap_ed > 0.3:
            bo.append(round(gap_tho - gap_ed, 2))
            con.append(round(max(0, gap_ed), 2))
    return {"ti_le_chu_giu": round(giu_ti_le, 2), "so_cho_cat": len(bo),
            "bo_tb": round(float(np.mean(bo)), 2) if bo else 0, "chua_lai_tb": round(float(np.median(con)), 2) if con else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc")
    ap.add_argument("--mau", required=True)
    ap.add_argument("--tho", default="")
    ap.add_argument("--ho-so", default="")
    a = ap.parse_args()
    t_bd = time.time()
    hoc = os.path.join(os.path.abspath(a.thu_muc), "hoc")
    os.makedirs(hoc, exist_ok=True)
    hs = HS.lay(a.ho_so)
    goi_y = HS.goi_y_nhan_giong(hs)
    ts = dict(C.thong_so(os.path.abspath(a.mau)), duong=os.path.abspath(a.mau))
    if ts["dur"] > C.GIOI_HAN_GIAY:
        raise SystemExit("Video mẫu dài quá 5 phút — hãy cắt lấy một đoạn tiêu biểu.")
    C.in_ra("1/4 Nghe lời video mẫu…")
    cau, x = nghe(ts["duong"], goi_y)
    tu = [w for c in cau for w in c["tu"]]
    gap = [y["a"] - w["b"] for w, y in zip(tu, tu[1:])]
    C.in_ra("2/4 Xem hình: đổi cảnh, mặt, phóng to, màu nhấn…")
    cat = cat_canh(ts["duong"])
    mat, _ = D.xem_hinh(ts["duong"], ts)
    do = {
        "video_mau": os.path.basename(ts["duong"]), "dai_giay": round(ts["dur"], 1), "khung": f"{ts['w']}x{ts['h']}",
        "doi_canh": {"so_lan": len(cat), "moi_lan_giay": round(ts["dur"] / max(1, len(cat) + 1), 1)},
        "loi": {"so_chu": len(tu), "chu_moi_giay": round(len(tu) / max(1, ts["dur"]), 2),
                "ngung_giua_chu_trung_vi": round(float(np.median(gap)), 2) if gap else None,
                "ngung_dai_nhat": round(float(max(gap)), 2) if gap else None,
                "so_ngung_tren_0_5s": int(sum(g > 0.5 for g in gap))},
        "nhac_so_voi_giong_db": nhac_so_voi_giong(cau, x),
        "phong_to_so_lan": phong_to(mat, cat),
        "ti_le_khung_co_mat": round(sum(bool(f) for f in mat) / max(1, len(mat)), 2),
        "mau_noi_bat": mau_noi_bat(ts["duong"], ts["dur"]),
    }
    if a.tho:
        C.in_ra("3/4 Nghe bản thô và so từng chữ…")
        ts_tho = dict(C.thong_so(os.path.abspath(a.tho)), duong=os.path.abspath(a.tho))
        cau_tho, x_tho = nghe(ts_tho["duong"], goi_y)
        do["so_voi_ban_tho"] = so_khop(cau_tho, cau)
        do["so_voi_ban_tho"]["tho_dai_giay"] = round(ts_tho["dur"], 1)
        # cùng phép đo trên bản thô: chênh lệch mới là phần người dựng thêm vào
        do["so_voi_ban_tho"]["nen_tho_so_voi_giong_db"] = nhac_so_voi_giong(cau_tho, x_tho)
        mat_tho, _ = D.xem_hinh(ts_tho["duong"], ts_tho)
        do["so_voi_ban_tho"]["phong_to_ban_tho"] = phong_to(mat_tho, cat_canh(ts_tho["duong"]))
    C.in_ra("4/4 Chụp khung cho AI xem…")
    D.bang_khung([ts], os.path.join(hoc, "bang-24.jpg"), n=24, nhan="mẫu")
    for k, t in enumerate([0.3, 1.5, ts["dur"] * 0.35, ts["dur"] * 0.65, ts["dur"] - 1.5]):
        C.sh([C.ffmpeg(), "-v", "error", "-y", "-ss", f"{max(0, t):.2f}", "-i", ts["duong"], "-frames:v", "1",
              "-vf", "scale=540:-2", os.path.join(hoc, f"khung-{k + 1}.jpg")], bat_buoc=False)
    C.ghi_json(os.path.join(hoc, "do-dac.json"), do)
    L = ["# Học phong cách — số đo", "", "```json", json.dumps(do, ensure_ascii=False, indent=1), "```", "",
         "## Lời video mẫu (để hiểu chữ chốt ý bám lời thế nào — KHÔNG chép nội dung)", ""]
    L += [f"- {c['a']:6.2f}–{c['b']:6.2f} {c['txt']}" for c in cau]
    with open(os.path.join(hoc, "tom-tat-hoc.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    os.makedirs(THU_MUC_PC, exist_ok=True)
    C.in_ra(f"Đo xong sau {time.time() - t_bd:.0f} giây.")
    C.in_ra(f"→ Đọc {os.path.join(hoc, 'tom-tat-hoc.md')}, xem bang-24.jpg và khung-1..5.jpg,")
    C.in_ra(f"  rồi viết phong cách vào {THU_MUC_PC}/<tên>.json (mẫu: tai-lieu/phong-cach.md)")


if __name__ == "__main__":
    main()
