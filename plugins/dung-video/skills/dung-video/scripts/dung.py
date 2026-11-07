"""DỰNG: đọc ke-hoach.json → cắt, xếp chữ (tránh mặt, tránh động tác, trong vùng an toàn), phụ đề, bìa,
chuẩn âm lượng, xuất MP4 + ảnh bìa + ảnh xem lại + báo cáo.

    dv.py dung <thư mục dự án> [--ten <tên tệp ra>] [--nhap]   (--nhap: bản xem nhanh 540p)
"""
import argparse, hashlib, os, re, sys, tempfile, time
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C
import ho_so as HS
import ve_chu as V
import ban_quyen as BQ
import am_thanh as AT

W, H = C.W, C.H
ANH_DUOI = (".png", ".jpg", ".jpeg", ".webp")
AN_TOAN = {"tren": 0.07, "duoi": 0.22, "trai": 0.05, "phai": 0.12}   # vùng an toàn TikTok/Reels/Shorts (tỉ lệ khung)
LC, LD = 27, 48


# ---------------- thời gian ----------------
class BanDo:
    """Đổi giây gốc (src, t) ⇄ giây thành phẩm theo danh sách đoạn giữ."""

    def __init__(self, giu):
        self.giu, t = [], 0.0
        for g in giu:
            self.giu.append(dict(g, ra=t))
            t += g["b"] - g["a"]
        self.tong = t

    def ra(self, src, t):
        sau = None
        for g in self.giu:
            if g["src"] != src:
                continue
            if g["a"] <= t <= g["b"]:
                return g["ra"] + t - g["a"]
            if t < g["a"] and sau is None:
                sau = g["ra"]
        return sau if sau is not None else self.tong

    def goc(self, t):
        for g in self.giu:
            if t < g["ra"] + (g["b"] - g["a"]):
                return g["src"], g["a"] + max(0.0, t - g["ra"])
        g = self.giu[-1]
        return g["src"], g["b"]


# ---------------- vùng bận (mặt + chuyển động) ----------------
class VungBan:
    def __init__(self, du_an, nguon):
        self.mat = C.doc_json(os.path.join(du_an, "doc", "mat.json"))["nguon"]
        z = np.load(os.path.join(du_an, "doc", "dong.npz"))
        self.dong = [z[f"arr_{i}"] for i in range(len(nguon))]
        self.nguon = nguon
        # mức nền chuyển động (máy rung tay, nhiễu) của từng nguồn để trừ đi
        self.nen = [float(np.median(d.mean(axis=(1, 2)))) if len(d) else 0.0 for d in self.dong]
        self.nen_tb = float(np.mean(self.nen)) if self.nen else 0.0
        # cảnh chèn: hình lúc đó là của clip phụ
        self.chen = []
        mp = C.doc_json(os.path.join(du_an, "doc", "mat.json")).get("phu", [])
        dp = os.path.join(du_an, "doc", "dong-phu.npz")
        zp = np.load(dp) if os.path.exists(dp) else None
        self.mat_phu = mp
        self.zoom = []
        self.dong_phu = [zp[f"arr_{i}"] for i in range(len(mp))] if zp is not None else []

    def luoi(self, bd, t0, t1):
        """Lưới 48×27 (hàng × cột) điểm bận trong khoảng thành phẩm [t0,t1]; cùng lúc trả mặt lớn nhất."""
        g = np.zeros((LD, LC), np.float32)
        mat_to, n = None, 0
        for t in np.arange(t0, max(t0 + 0.01, t1), 0.25):
            c = next((c for c in self.chen if c["t0"] <= t < c["t1"]), None)
            if c is not None:
                k = int((c["a"] + t - c["t0"]) * 4)
                d, mats = self.dong_phu[c["phu"]], self.mat_phu[c["phu"]]
            else:
                src, tg = bd.goc(float(t))
                k = int(tg * 4)
                if src >= len(self.dong):                 # intro/outro
                    n += 1
                    continue
                d, mats = self.dong[src], self.mat[src]
            z = None if c is not None else next((z for z in self.zoom if z["t0"] <= t < z["t1"]), None)
            if len(d):
                m = d[min(k, len(d) - 1)].astype(np.float32)
                if m.shape != (LD, LC):          # nguồn ngang: lấy phần giữa theo khung cắt
                    m = np.array(Image.fromarray(m * 255).resize((LC, LD))) / 255.0
                if z:                            # đang phóng to: lấy phần khung được giữ rồi phóng lên
                    x0, y0 = z["cx"] - 0.5 / z["z"], z["cy"] - 0.5 / z["z"]
                    hop_c = (int(x0 * LC), int(y0 * LD), int(np.ceil((x0 + 1 / z["z"]) * LC)), int(np.ceil((y0 + 1 / z["z"]) * LD)))
                    m = np.array(Image.fromarray((m * 255).astype(np.uint8)).crop(hop_c).resize((LC, LD))) / 255.0
                g += m
            ds_mat = mats[min(k, len(mats) - 1)] if mats else []
            if z:
                x0, y0 = z["cx"] - 0.5 / z["z"], z["cy"] - 0.5 / z["z"]
                ds_mat = [((x - x0) * z["z"], (y - y0) * z["z"], w * z["z"], h * z["z"], s_) for (x, y, w, h, s_) in ds_mat]
            for (x, y, w, h, s) in ds_mat:
                x0, x1 = max(0, x - w * 0.15), min(1, x + w * 1.15)
                y0, y1 = max(0, y - h * 0.25), min(1, y + h * 1.12)   # tới cằm
                g[int(y0 * LD):int(np.ceil(y1 * LD)), int(x0 * LC):int(np.ceil(x1 * LC))] += 6.0
                if mat_to is None or w * h > mat_to[2] * mat_to[3]:
                    mat_to = (x, y, w, h)
            n += 1
        return np.clip(g / max(1, n) - self.nen_tb, 0, None), mat_to

    def tam_mat(self, bd, t0, t1):
        """Tâm khuôn mặt trung vị trong [t0,t1] (toạ độ 0..1), để phóng to vào mặt."""
        tam = []
        for t in np.arange(t0, max(t0 + 0.01, t1), 0.25):
            src, tg = bd.goc(float(t))
            if src >= len(self.mat) or not self.mat[src]:
                continue
            f = self.mat[src][min(int(tg * 4), len(self.mat[src]) - 1)]
            if f:
                x, y, w, h, _ = max(f, key=lambda r: r[2] * r[3])
                tam.append((x + w / 2, y + h / 2))
        if not tam:
            return 0.5, 0.42
        return float(np.median([p[0] for p in tam])), float(np.median([p[1] for p in tam]))


# ---------------- xếp chỗ ----------------
def xep(bc, ban, mat_to, uu_tien, da_dat, can):
    """Chọn (x, y) cho khối kích thước bc['w']×bc['h']: điểm phạt = đè mặt/động tác + đè khối khác + lệch ưu tiên."""
    bw, bh = bc["w"], bc["h"]
    le = bc.get("le", 0)
    x = (W - bw) // 2 if can == "giua" else int(W * AN_TOAN["trai"]) - le
    y_min = int(H * AN_TOAN["tren"]) - le
    y_max = int(H * (1 - AN_TOAN["duoi"])) - bh + le
    if y_max < y_min:
        return None
    can_cam = mat_to is not None and mat_to[3] > 0.13
    cam = (mat_to[1] + mat_to[3] * 1.12) if mat_to else None
    tot = None
    for y in range(y_min, y_max + 1, 12):
        c0, c1 = max(0, (x + le) * LC // W), min(LC, (x + bw - le) * LC // W + 1)
        r0, r1 = max(0, (y + le) * LD // H), min(LD, (y + bh - le) * LD // H + 1)
        phat = float(ban[r0:r1, c0:c1].sum()) * 4
        for (ox, oy, ow, oh) in da_dat:
            dx = max(0, min(x + bw, ox + ow) - max(x, ox))
            dy = max(0, min(y + bh, oy + oh) - max(y, oy))
            phat += dx * dy / 400.0
        tam = (y + bh / 2) / H
        if can_cam and uu_tien != "tren":                      # cận mặt: ưu tiên ngay dưới cằm
            phat += abs((y + le) / H - (cam + 0.015)) * 60
        else:
            muc = {"tren": 0.13, "giua": 0.40, "duoi": 0.68}.get(uu_tien, 0.4)
            phat += abs(tam - muc) * 40
        if tot is None or phat < tot[0]:
            tot = (phat, x, y, float(ban[r0:r1, c0:c1].max()) if r1 > r0 and c1 > c0 else 0.0)
    return tot


# ---------------- phụ đề ----------------
def cum_phu_de(loi, bd, giu, sua, toi_da=4):
    """Chia lời thành cụm ≤ toi_da chữ, ngắt ở dấu câu / chỗ ngừng; đổi sang giây thành phẩm."""
    def trong_giu(src, a, b):
        return any(g["src"] == src and g["a"] - 0.05 <= a and b <= g["b"] + 0.05 for g in giu)

    cum, hien = [], []
    for c in loi:
        if c.get("nghi_bia"):
            continue
        tu = HS.sua_tu(c["tu"], sua)
        for w in tu:
            if not trong_giu(c["src"], w["a"], w["b"]):
                continue
            ww = {"w": w["w"], "a": bd.ra(c["src"], w["a"]), "b": bd.ra(c["src"], w["b"])}
            if hien and (len(hien) >= toi_da or ww["a"] - hien[-1]["b"] > 0.3 or re.search(r"[.,!?;:]$", hien[-1]["w"])):
                cum.append(hien)
                hien = []
            hien.append(ww)
        if hien:
            cum.append(hien)
            hien = []
    ra = []
    for i, k in enumerate(cum):
        a = k[0]["a"]
        b = k[-1]["b"] + 0.25
        if i + 1 < len(cum):
            b = min(b, cum[i + 1][0]["a"])
        for w in k:
            w["w"] = w["w"].rstrip(",.;:")
        ra.append({"a": a, "b": max(b, a + 0.3), "tu": k})
    return ra


# ---------------- chính ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("du_an")
    ap.add_argument("--ten", default="")
    ap.add_argument("--nhap", action="store_true", help="bản xem nhanh 540p")
    a = ap.parse_args()
    bat_dau = time.time()
    du_an = os.path.abspath(a.du_an)
    giay_phep = BQ.kiem_tra()
    viec = C.doc_json(os.path.join(du_an, "viec.json"))
    ke = C.doc_json(os.path.join(du_an, "ke-hoach.json"))
    if not viec or ke is None:
        raise SystemExit("Thiếu viec.json (chạy bước đọc) hoặc ke-hoach.json (AI chưa viết kế hoạch).")
    nguon = viec["nguon"]
    hs = HS.lay(viec.get("ho_so") or "")
    hs_tep = os.path.join(du_an, "ho-so.json")
    if os.path.exists(hs_tep):
        hs.update(C.doc_json(hs_tep, {}))
    loi = C.doc_json(os.path.join(du_an, "doc", "loi.json"))["cau"]
    dx = C.doc_json(os.path.join(du_an, "doc", "de-xuat-cat.json"))
    kieu = ke.get("kieu", "tu-van")
    giu = ke.get("giu") or dx["giu_tu_van" if kieu == "tu-van" else "giu_bai_tap"]
    giu = [dict(g, src=g.get("src", 0)) for g in giu]
    for b in ke.get("bo", []):            # AI bỏ thêm: lời đáp của người phụ, câu nói hỏng…
        sb, ba, bb = b.get("src", 0), float(b["a"]), float(b["b"])
        moi = []
        for g in giu:
            if g["src"] != sb or bb <= g["a"] or ba >= g["b"]:
                moi.append(g)
                continue
            if ba - g["a"] > 0.05:
                moi.append(dict(g, b=ba))
            if g["b"] - bb > 0.05:
                moi.append(dict(g, a=bb))
        giu = moi
    # ---- intro / outro: thêm như nguồn phụ ở đầu/cuối (ảnh tĩnh hoặc clip) ----
    nguon_all = list(nguon)
    goc_ra = 0.0                                   # nội dung chính bắt đầu sau intro
    for vai_io in ("intro", "outro"):
        tep = ke.get(vai_io, hs.get(vai_io)) or ""
        if not tep:
            continue
        if not os.path.exists(tep):
            raise SystemExit(f"Không thấy tệp {vai_io}: {tep}")
        if tep.lower().endswith(ANH_DUOI):
            dur = float(ke.get(vai_io + "_giay", hs.get(vai_io + "_giay", 2.0)))
            ts = {"duong": tep, "dur": dur, "w": W, "h": H, "co_am": False, "anh": True}
        else:
            ts = dict(C.thong_so(tep), duong=tep)
            dur = min(ts["dur"], 8.0)
        idx = len(nguon_all)
        nguon_all.append(ts)
        if vai_io == "intro":
            giu.insert(0, {"src": idx, "a": 0.0, "b": dur})
            goc_ra = dur
        else:
            giu.append({"src": idx, "a": 0.0, "b": dur})
    bd = BanDo(giu)
    vb = VungBan(du_an, nguon)
    may_sua, canh_bao = [], []
    sua = dict(hs.get("sua_tu", {}), **ke.get("sua_tu", {}))

    bia_giay = min(1.0, max(0.5, float(ke.get("bia", {}).get("dai", hs["bia_giay"]))))
    mo_dau = float(hs.get("chu_mo_dau_giay", 0.9))

    def doi(el_t, el):
        if el_t is None:
            return None
        if el.get("theo") == "ra":
            return float(el_t) + goc_ra
        return bd.ra(int(el.get("src", 0)), float(el_t))

    # ---- cảnh chèn (B-roll) ----
    phu = viec.get("phu", [])
    chen = []
    for c in ke.get("chen", []):
        i = int(c.get("phu", 0))
        if i >= len(phu):
            canh_bao.append(f"Cảnh chèn trỏ tới clip phụ [{i}] không có — bỏ qua.")
            continue
        t0, t1 = doi(c["t0"], c), doi(c["t1"], c)
        t0 = max(t0, bia_giay)                          # không chèn đè ảnh bìa
        a0 = float(c.get("a", 0))
        if a0 + (t1 - t0) > phu[i]["dur"]:
            t1 = t0 + max(0.0, phu[i]["dur"] - a0)
            may_sua.append(f"Cảnh chèn từ clip phụ [{i}] ngắn hơn yêu cầu — rút còn {t1 - t0:.1f}s")
        if t1 - t0 < 0.5:
            continue
        chen.append({"phu": i, "a": a0, "t0": round(t0, 3), "t1": round(t1, 3)})
    chen.sort(key=lambda c: c["t0"])
    for x, y in zip(chen, chen[1:]):
        if y["t0"] < x["t1"]:
            x["t1"] = y["t0"]
    vb.chen = chen

    # ---- phóng to (zoom) ----
    zoom = []
    for z in ke.get("zoom", []):
        t0, t1 = doi(z["t0"], z), doi(z["t1"], z)
        t0 = max(t0, bia_giay)
        if t1 - t0 < 0.6:
            continue
        muc = min(1.5, max(1.05, float(z.get("muc", 1.2))))
        tam = z.get("tam", "mat")
        if isinstance(tam, (list, tuple)):
            cx, cy = float(tam[0]), float(tam[1])
        else:
            cx, cy = vb.tam_mat(bd, t0, t1)
            cy += 0.06                                 # chừa khoảng trên đầu, mặt nằm 1/3 trên
        nua = 0.5 / muc
        cx, cy = min(1 - nua, max(nua, cx)), min(1 - nua, max(nua, cy))
        zoom.append({"t0": round(t0, 3), "t1": round(t1, 3), "z": muc, "cx": cx, "cy": cy})
    zoom.sort(key=lambda z: z["t0"])
    vb.zoom = zoom

    # ---- âm thanh: nhạc nền + hiệu ứng ----
    am = ke.get("am", {})
    sfx_ds = []
    for s in am.get("sfx", []):
        if s.get("loai") in AT.LOAI_SFX:
            sfx_ds.append({"t": doi(s["t"], s), "loai": s["loai"], "db": float(s.get("db", -18))})
    if am.get("sfx_tu_dong", hs.get("sfx_tu_dong", True)):
        sfx_ds.append({"t": max(0.0, bia_giay - 0.2), "loai": "whoosh", "db": -20})
        for c in chen:
            sfx_ds.append({"t": max(0.0, c["t0"] - 0.15), "loai": "whoosh", "db": -24})

    # ---- phụ đề ----
    phu_de_bat = ke.get("phu_de", {}).get("bat", hs["phu_de"].get(kieu, kieu == "tu-van"))
    cums = cum_phu_de(loi, bd, giu, sua, int(ke.get("phu_de", {}).get("toi_da_chu", 4))) if phu_de_bat else []
    lop = []          # mỗi lớp: {loai, a, b, bc, x, y, ...}
    da_dat_theo_t = []
    logo = dict(hs.get("logo") if isinstance(hs.get("logo"), dict) else {"tep": hs.get("logo", "")}, **(ke.get("logo") or {}))
    anh_logo = None
    if logo.get("tep") and logo.get("bat", True):
        if not os.path.exists(logo["tep"]):
            canh_bao.append(f"Không thấy tệp logo: {logo['tep']} — bỏ logo.")
        else:
            anh_logo = Image.open(logo["tep"]).convert("RGBA")
            rong = int(W * min(0.3, max(0.08, float(logo.get("rong", 0.16)))))
            anh_logo = anh_logo.resize((rong, max(1, int(anh_logo.height * rong / anh_logo.width))), Image.LANCZOS)
            if float(logo.get("mo", 0.9)) < 1:
                a_ = anh_logo.getchannel("A").point(lambda v: int(v * float(logo.get("mo", 0.9))))
                anh_logo.putalpha(a_)
            trai = logo.get("goc", "tren-phai") == "tren-trai"
            lx = int(W * AN_TOAN["trai"]) if trai else W - anh_logo.width - int(W * 0.05)
            ly = int(H * AN_TOAN["tren"])
            vi_tri_logo = (lx, ly)
            da_dat_theo_t.append((0, 1e9, (lx - 10, ly - 10, anh_logo.width + 20, anh_logo.height + 20)))
    # nhóm cụm theo câu để giữ 1 vị trí ổn định
    nhom, cur = [], []
    for c in cums:
        if cur and c["a"] - cur[-1]["b"] > 0.6:
            nhom.append(cur)
            cur = []
        cur.append(c)
    if cur:
        nhom.append(cur)
    for ng in nhom:
        bcs = [V.dan_phu_de(c["tu"], int(W * 0.84)) for c in ng]
        to = max(bcs, key=lambda b: b["w"] * b["h"])
        ban, mat_to = vb.luoi(bd, ng[0]["a"], ng[-1]["b"])
        r = xep(dict(to, le=0), ban, mat_to, "duoi", [], "giua")
        if r is None:
            continue
        _, _, y, dinh = r
        for c, bc in zip(ng, bcs):
            lop.append({"loai": "phu", "a": c["a"], "b": c["b"], "bc": bc, "x": (W - bc["w"]) // 2,
                        "y": y + (to["h"] - bc["h"]) // 2, "tu": c["tu"]})
            da_dat_theo_t.append((c["a"], c["b"], ((W - to["w"]) // 2, y, to["w"], to["h"])))

    # ---- khối chữ ----
    chu = sorted(ke.get("chu", []), key=lambda e: doi(e.get("t0", 0), e) or 0)
    for i, el in enumerate(chu):
        t0 = doi(el.get("t0", 0), el)
        t1 = doi(el.get("t1"), el)
        if t1 is None:
            t1 = min(bd.tong, t0 + 3.0)
        if t0 < goc_ra + mo_dau:
            may_sua.append(f"«{el.get('id', i)}»: dời giờ hiện từ {t0:.2f}s sang {goc_ra + mo_dau:.2f}s (luật chữ mở đầu)")
            t0 = goc_ra + mo_dau
        if t1 - t0 < 0.4:
            continue
        for d in el.get("dong", []):
            if d.get("t0") is not None:
                d["t0"] = max(t0, doi(d["t0"], el))
        for co in (1.0, 0.85, 0.72):
            el["co"] = co
            bc = V.dan_khoi(el, hs, int(W * (0.88 if el.get("can", "giua") == "giua" else 0.80)))
            ban, mat_to = vb.luoi(bd, t0, t1)
            dang = [o for (a0, b0, o) in da_dat_theo_t if a0 < t1 and t0 < b0]
            r = xep(bc, ban, mat_to, el.get("vi_tri", {"the-den": "tren", "nhan": "tren", "tieu-de": "giua"}
                                     .get(el.get("kieu"), "giua")), dang, el.get("can", "giua"))
            if r and r[3] < 3.0:        # không đè mặt
                break
        if r is None:
            canh_bao.append(f"«{el.get('id', i)}» không còn chỗ trong vùng an toàn — bỏ qua.")
            continue
        if co < 1.0:
            may_sua.append(f"«{el.get('id', i)}»: thu nhỏ còn {int(co * 100)}% để không che mặt/động tác")
        if r[3] >= 3.0:
            canh_bao.append(f"«{el.get('id', i)}» ({t0:.1f}–{t1:.1f}s) vẫn chạm vùng mặt — nên rút gọn chữ.")
        _, x, y, _ = r
        so_chu = sum(len(d["text"].split()) for d in el["dong"])
        if t1 - t0 < 0.25 * so_chu + 0.6:
            canh_bao.append(f"«{el.get('id', i)}» hiện {t1 - t0:.1f}s cho {so_chu} chữ — có thể đọc không kịp.")
        lop.append({"loai": "khoi", "a": t0, "b": t1, "bc": bc, "x": x, "y": y, "el": el})
        if am.get("sfx_tu_dong", hs.get("sfx_tu_dong", True)):     # tiếng nhẹ khi chữ hiện
            sfx_ds.append({"t": t0, "loai": "pop" if el.get("kieu") != "tieu-de" else "bum",
                           "db": -21 if el.get("kieu") != "tieu-de" else -19})
            for d in el["dong"]:
                if d.get("t0") is not None and d["t0"] > t0 + 0.2:
                    sfx_ds.append({"t": d["t0"], "loai": "click", "db": -24})
        da_dat_theo_t.append((t0, t1, (x, y, bc["w"], bc["h"])))

    # ---- bìa ----
    bia = ke.get("bia") or {}
    with tempfile.TemporaryDirectory() as td:
        src_b = int(bia.get("src", 0))
        t_b = float(bia.get("t", min(2.0, nguon[src_b]["dur"] / 3)))
        anh = os.path.join(td, "khung.png")
        C.sh([C.ffmpeg(), "-v", "error", "-y", "-ss", f"{t_b:.2f}", "-i", nguon[src_b]["duong"], "-frames:v", "1",
              "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", anh])
        dong_bia = bia.get("dong") or [{"text": d["text"], "vai": "tieu-trang"} for d in (chu[0]["dong"] if chu else [])]
        import cv2
        img = cv2.imread(anh)
        det = cv2.FaceDetectorYN.create(os.path.join(C.MO_HINH, "yunet.onnx"), "", (img.shape[1], img.shape[0]), 0.6)
        _, f = det.detect(img)
        mat_bia = None
        if f is not None and len(f):
            r = max(f, key=lambda r: r[2] * r[3])
            mat_bia = (r[0] / W, r[1] / H, r[2] / W, r[3] / H)
        anh_bia = V.ve_bia(Image.open(anh), dong_bia, hs, mat_bia)
    ra_dir = os.path.join(du_an, "ra")
    os.makedirs(ra_dir, exist_ok=True)
    anh_bia.convert("RGB").save(os.path.join(ra_dir, "bia.jpg"), quality=92)

    # ---- trạng thái lớp phủ theo thời gian ----
    moc = {0.0, bia_giay, bd.tong}
    for l in lop:
        moc |= {l["a"], l["b"]}
        if l["loai"] == "phu":
            moc |= {w["a"] for w in l["tu"]}
        else:
            moc |= {d["t0"] for d in l["el"]["dong"] if d.get("t0") is not None}
    moc = sorted(m for m in moc if 0 <= m <= bd.tong)
    tam = os.path.join(du_an, "tam", "lop")
    os.makedirs(tam, exist_ok=True)
    trong = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, da_ve = [], {}
    for s, e in zip(moc, moc[1:]):
        if e - s < 1 / 60:
            continue
        if s < bia_giay:
            khoa = ("bia",)
        else:
            khoa = []
            for j, l in enumerate(lop):
                if l["a"] <= s < l["b"]:
                    if l["loai"] == "phu":
                        k = max([i for i, w in enumerate(l["tu"]) if w["a"] <= s + 1e-3] or [-1])
                        khoa.append((j, k))
                    else:
                        hien = tuple(i for i, d in enumerate(l["el"]["dong"]) if d.get("t0") is None or d["t0"] <= s + 1e-3)
                        khoa.append((j, hien))
            khoa = tuple(khoa)
        if khoa not in da_ve:
            p = os.path.join(tam, hashlib.md5(repr(khoa).encode()).hexdigest()[:12] + ".png")
            if khoa == ("bia",):
                anh_bia.save(p, compress_level=1)
            else:
                im = trong.copy()
                if anh_logo is not None:
                    im.alpha_composite(anh_logo, vi_tri_logo)
                for j, v in khoa:
                    l = lop[j]
                    k = V.ve_phu_de(l["bc"], hs, v) if l["loai"] == "phu" else V.ve_khoi(l["bc"], hs, set(v))
                    im.alpha_composite(k, (int(l["x"]), int(l["y"])))
                im.save(p, compress_level=1)
            da_ve[khoa] = p
        ds.append((da_ve[khoa], e - s))
    fc = os.path.join(du_an, "tam", "lop.ffconcat")
    with open(fc, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for p, d in ds:
            f.write(f"file '{C.ffconcat_duong(p)}'\nduration {d:.4f}\n")
        f.write(f"file '{C.ffconcat_duong(ds[-1][0])}'\n")

    # ---- ghép bằng ffmpeg ----
    vao, loc = [], []
    for s in nguon_all:
        vao += (["-loop", "1", "-t", f"{s['dur']:.2f}", "-i", s["duong"]] if s.get("anh") else ["-i", s["duong"]])
    mau = ke.get("mau") or {}
    loc_mau = ""
    if mau:                                            # chỉ khi người dùng cho phép chỉnh màu
        loc_mau = (f",eq=brightness={float(mau.get('sang', 0)):.3f}:contrast={float(mau.get('tuong_phan', 1)):.3f}"
                   f":saturation={float(mau.get('bao_hoa', 1)):.3f}")
        if mau.get("am"):
            m_ = float(mau["am"])
            loc_mau += f",colorbalance=rm={m_ * 0.06:.3f}:bm={-m_ * 0.06:.3f}"
    for i, g in enumerate(giu):
        s = nguon_all[g["src"]]
        if s.get("anh"):
            khung = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
        elif s["w"] / s["h"] > W / H + 0.01 and g["src"] < len(nguon):   # nguồn ngang: cắt dọc theo vị trí mặt
            hop = [h for f in vb.mat[g["src"]] for h in f]
            cx = float(np.median([h[0] + h[2] / 2 for h in hop])) if hop else 0.5
            khung = f"scale=-2:{H},crop={W}:{H}:'min(max(iw*{cx:.3f}-{W // 2},0),iw-{W})':0"
        else:
            khung = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        if g["src"] < len(nguon):
            khung += loc_mau
        loc.append(f"[{g['src']}:v]trim=start={g['a']:.3f}:end={g['b']:.3f},setpts=PTS-STARTPTS,{khung},setsar=1,fps={C.FPS},format=yuv420p[v{i}]")
        dai = g["b"] - g["a"]
        if s["co_am"]:
            loc.append(f"[{g['src']}:a]atrim=start={g['a']:.3f}:end={g['b']:.3f},asetpts=PTS-STARTPTS,"
                       f"aformat=sample_rates=48000:channel_layouts=stereo,"
                       f"afade=t=in:d=0.012,afade=t=out:st={max(0, dai - 0.012):.3f}:d=0.012[a{i}]")
        else:
            loc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={dai:.3f}[a{i}]")
    n = len(giu)
    loc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    # ---- chèn cảnh minh hoạ (B-roll): hình phủ kín khung, tiếng gốc tắt, giọng chính chạy liên tục ----
    so_vao = len(nguon_all)
    vtruoc = "vc"
    if zoom:                                           # phóng to (cắt khung) theo đoạn, trước cảnh chèn
        def ghep(gia_tri, mac_dinh):
            e = mac_dinh
            for z in reversed(zoom):
                e = f"if(between(t,{z['t0']:.3f},{z['t1']:.3f}),{gia_tri(z)},{e})"
            return e
        ez = ghep(lambda z: f"{z['z']:.3f}", "1")
        ex = ghep(lambda z: f"{z['cx'] - 0.5 / z['z']:.4f}*iw", "0")
        ey = ghep(lambda z: f"{z['cy'] - 0.5 / z['z']:.4f}*ih", "0")
        loc.append(f"[vc]scale=w='{W}*({ez})':h='{H}*({ez})':eval=frame,crop={W}:{H}:x='{ex}':y='{ey}',setsar=1[vz]")
        vtruoc = "vz"
    for j, c in enumerate(chen):
        p = phu[c["phu"]]
        vao += ["-i", p["duong"]]
        khung = (f"scale=-2:{H},crop={W}:{H}" if p["w"] / p["h"] > W / H + 0.01
                 else f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
        loc.append(f"[{so_vao}:v]trim=start={c['a']:.3f}:end={c['a'] + c['t1'] - c['t0']:.3f},"
                   f"setpts=PTS-STARTPTS+{c['t0']:.3f}/TB,{khung},setsar=1,fps={C.FPS}[b{j}]")
        loc.append(f"[{vtruoc}][b{j}]overlay=0:0:eof_action=pass:enable='between(t,{c['t0']:.3f},{c['t1']:.3f})'[vb{j}]")
        vtruoc = f"vb{j}"
        so_vao += 1
    chi_so_lop = so_vao
    so_vao += 1                                         # lớp chữ (ffconcat) là đầu vào kế tiếp
    loc.append(f"[{chi_so_lop}:v]fps={C.FPS},format=rgba[ov]")
    cuoi = f"scale=540:960," if a.nhap else ""
    toc = min(1.5, max(0.75, float(ke.get("toc_do", 1.0))))
    loc.append(f"[{vtruoc}][ov]overlay=0:0:eof_action=pass:format=auto,{cuoi}format=yuv420p"
               + (f",setpts=PTS/{toc:.3f}[v]" if toc != 1 else "[v]"))

    # ---- âm thanh: giọng chuẩn hoá → nhạc nền né giọng → hiệu ứng ----
    muc_giong = float(hs.get("am_luong_lufs", -16))
    vao_sau = []
    tron = ["[giong]"]
    nhac = am.get("nhac")
    giam_on = "afftdn=nf=-30:nr=12," if ke.get("giam_on") else ""
    loc.append(f"[ac]{giam_on}loudnorm=I={muc_giong}:TP=-1.5:LRA=11,aresample=48000" + (",asplit=2[giong][kich]" if nhac else "[giong]"))
    if nhac:
        tep = nhac.get("tep", "mau:nhe-nhang")
        if tep.startswith("mau:"):
            tep = AT.tep_nhac_mau(tep[4:] if tep[4:] in AT.KIEU_NHAC else "nhe-nhang", bd.tong + 3)
        elif not os.path.exists(tep):
            raise SystemExit(f"Không thấy tệp nhạc: {tep}")
        vao_sau += ["-stream_loop", "-1", "-i", tep]
        rel = float(nhac.get("db", -16))                # nhạc nhỏ hơn giọng bao nhiêu dB (LUFS)
        loc.append(f"[{so_vao}:a]atrim=start={float(nhac.get('bat_dau', 0)):.2f}:duration={bd.tong + 0.5:.2f},asetpts=PTS-STARTPTS,"
                   f"aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I={muc_giong + rel:.1f}:LRA=20:TP=-3,"
                   f"aresample=48000,afade=t=in:d=0.8,afade=t=out:st={max(0, bd.tong - 2.5):.2f}:d=2.5[nhac0]")
        if nhac.get("ne_giong", True):
            loc.append("[nhac0][kich]sidechaincompress=threshold=0.015:ratio=8:attack=40:release=600:makeup=1[nhac]")
        else:
            loc.append("[kich]anullsink;[nhac0]anull[nhac]")
        tron.append("[nhac]")
        so_vao += 1
    for k, s in enumerate(sfx_ds):
        vao_sau += ["-i", AT.tep_sfx(s["loai"])]
        ms = int(max(0, s["t"]) * 1000)
        loc.append(f"[{so_vao}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s['db']:.1f}dB,adelay={ms}|{ms}[sx{k}]")
        tron.append(f"[sx{k}]")
        so_vao += 1
    if len(tron) > 1:
        loc.append("".join(tron) + f"amix=inputs={len(tron)}:normalize=0:duration=first,alimiter=limit=0.89:level=false"
                   + (f",atempo={toc:.3f}[a]" if toc != 1 else "[a]"))
    else:
        loc.append("[giong]" + (f"atempo={toc:.3f}[a]" if toc != 1 else "anull[a]"))
    loc_tep = os.path.join(du_an, "tam", "loc.txt")
    with open(loc_tep, "w", encoding="utf-8") as f:
        f.write(";\n".join(loc))
    ten = a.ten or ke.get("ten") or os.path.basename(du_an)
    ten = re.sub(r'[\\/:*?"<>|]', "-", ten) + ("-nhap" if a.nhap else "")
    ra = os.path.join(ra_dir, ten + ".mp4")
    ma_hoa = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"] if a.nhap else C.chon_ma_hoa()
    C.in_ra(f"Dựng {n} đoạn, {len(da_ve)} lớp chữ, dài {bd.tong:.1f}s…")
    C.sh([C.ffmpeg(), "-v", "error", "-y", *vao, "-f", "concat", "-safe", "0", "-i", fc, *vao_sau,
          *C.doc_bo_loc(loc_tep), "-map", "[v]", "-map", "[a]", *ma_hoa, "-c:a", "aac", "-b:a", "192k",
          "-movflags", "+faststart", "-metadata", f"comment=Dung video {C.PHIEN_BAN} - ban quyen cap cho: {giay_phep}",
          ra])

    # ---- kiểm sau dựng ----
    _, _, err = C.sh([C.ffmpeg(), "-nostats", "-i", ra, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"], bat_buoc=False)
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    muc = float(hs.get("am_luong_lufs", -16))
    if lufs and abs(float(lufs[-1]) - muc) > 0.8:      # loudnorm 1 lượt hụt với tiếng lên xuống nhiều → bù thêm
        bu = muc - float(lufs[-1])
        tam_ra = ra + ".tam.mp4"
        C.sh([C.ffmpeg(), "-v", "error", "-y", "-i", ra, "-c:v", "copy", "-af",
              f"volume={bu:.2f}dB,alimiter=limit=0.84:level=false", "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", "-map_metadata", "0", tam_ra])
        os.replace(tam_ra, ra)
        _, _, err = C.sh([C.ffmpeg(), "-nostats", "-i", ra, "-af", "ebur128", "-vn", "-f", "null", "-"], bat_buoc=False)
        lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    tong_ra = bd.tong / toc
    # ---- xuất thêm khổ khác cho nền tảng khác (nền mờ hai bên, video dọc giữa) ----
    tep_them = []
    for k in ke.get("xuat", []):
        kh = {"ngang": (1920, 1080, "youtube-ngang"), "4x5": (1080, 1350, "facebook-4x5"), "vuong": (1080, 1080, "vuong-1x1")}.get(k)
        if not kh or a.nhap:
            continue
        w2, h2, duoi = kh
        p2 = os.path.join(ra_dir, f"{ten}-{duoi}.mp4")
        C.sh([C.ffmpeg(), "-v", "error", "-y", "-i", ra, "-filter_complex",
              f"[0:v]split[a][b];[a]scale={w2}:{h2}:force_original_aspect_ratio=increase,crop={w2}:{h2},"
              f"boxblur=40:4,eq=brightness=-0.10[nen];[b]scale=-2:{h2}[giua];[nen][giua]overlay=(W-w)/2:0,format=yuv420p[v]",
              "-map", "[v]", "-map", "0:a", *C.chon_ma_hoa(), "-c:a", "copy", "-movflags", "+faststart",
              "-map_metadata", "0", p2])
        tep_them.append(p2)
    if tong_ra > 180:
        canh_bao.append(f"Video dài {tong_ra:.0f}s — YouTube Shorts và Reels giới hạn 3 phút; TikTok vẫn đăng được.")
    xem = os.path.join(ra_dir, "xem-lai.jpg")
    C.sh([C.ffmpeg(), "-v", "error", "-y", "-i", ra, "-vf", f"fps=12/{tong_ra:.2f},scale=270:-2,tile=6x2",
          "-frames:v", "1", xem], bat_buoc=False)
    tong_goc = sum(s["dur"] for s in nguon)
    bc = [f"# Báo cáo dựng: {ten}", "",
          f"- Bản quyền cấp cho: **{giay_phep}** · Dựng video {C.PHIEN_BAN}",
          f"- Kiểu video: **{kieu}** · Gốc {tong_goc:.1f}s → thành phẩm **{tong_ra:.1f}s** (giữ {n} đoạn"
          f"{', tốc độ ×' + format(toc, '.2f') if toc != 1 else ''})",
          f"- Thêm: {', '.join(x for x in [f'{len(chen)} cảnh chèn' if chen else '', f'{len(zoom)} đoạn phóng to' if zoom else '', 'logo' if anh_logo is not None else '', 'intro' if goc_ra else '', 'outro' if len(nguon_all) - len(nguon) > (1 if goc_ra else 0) else '', 'nhạc nền' if am.get('nhac') else '', f'{len(sfx_ds)} hiệu ứng âm thanh' if sfx_ds else '', 'giảm ồn' if ke.get('giam_on') else '', 'chỉnh màu' if mau else ''] if x) or 'không'}",
          f"- Ảnh bìa phủ 0–{bia_giay:.1f}s · chữ mở đầu từ {mo_dau:.1f}s · phụ đề: {'bật' if phu_de_bat else 'tắt'}",
          f"- Âm lượng thành phẩm: {lufs[-1] if lufs else '?'} LUFS (chuẩn {hs.get('am_luong_lufs', -16)})",
          f"- Thời gian dựng: {time.time() - bat_dau:.0f} giây", "", "## Máy đã tự sửa", ""]
    bc += [f"- {m}" for m in may_sua] or ["- (không có)"]
    bc += ["", "## Cần người xem lại", ""] + ([f"- {m}" for m in canh_bao] or ["- (không có)"])
    bc += ["", "## Tệp", "", f"- Video dọc (TikTok · Reels · Shorts): `{ra}`"] + [f"- Bản khác khổ: `{p}`" for p in tep_them] + [ f"- Ảnh bìa: `{os.path.join(ra_dir, 'bia.jpg')}`", f"- Xem lại: `{xem}`"]
    with open(os.path.join(ra_dir, "bao-cao.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(bc) + "\n")
    C.in_ra("\n".join(bc))


if __name__ == "__main__":
    main()
