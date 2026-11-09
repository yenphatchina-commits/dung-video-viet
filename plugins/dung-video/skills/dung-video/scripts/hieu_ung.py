"""HIỆU ỨNG ĐỘNG tự vẽ bằng code (không dùng tệp của ai → không dính bản quyền):

- Sticker động: mui-ten, khoanh-tron, gach-chan, sao, tim, tich, x, nhan (huy hiệu xoay có chữ). Xuất thành chuỗi PNG.
- Chữ cong: chữ xếp theo cung tròn.
- Dải chữ chạy ngang (chữ chạy kiểu bảng tin).
- Biểu thức ffmpeg cho chuyển cảnh: lat-3d (lật thẻ 3D), zoom-xoay, lia (lia máy), flash, mo (mờ chuyển).
"""
import math, os, shutil
from PIL import Image, ImageDraw, ImageFilter

import chung as C
import ve_chu as V

FPS = C.FPS
LOAI_STICKER = ("mui-ten", "khoanh-tron", "gach-chan", "sao", "tim", "tich", "x", "nhan", "vong-sang")
LOAI_CHUYEN = ("lat-3d", "zoom-xoay", "lia", "flash", "mo")


# ---------------- sticker ----------------
def _ease(u):
    return 1 - (1 - min(1, max(0, u))) ** 3


def _vien_net(d, pts, mau, rong):
    d.line(pts, fill=mau, width=rong, joint="curve")
    r = rong // 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=mau)


def khung_sticker(loai, w, h, n, mau_hex, chu="", huong="phai"):
    """Trả danh sách n ảnh RGBA w×h (vẽ ở 2× rồi thu nhỏ cho mịn)."""
    S = 2
    W2, H2 = w * S, h * S
    mau = V.mau(mau_hex)
    trang = (255, 255, 255, 255)
    vien = max(6, int(min(W2, H2) * 0.07)) if loai != "gach-chan" else max(8, int(W2 * 0.035))
    ra = []
    for k in range(n):
        u = k / max(1, n - 1)                  # 0..1 suốt đoạn
        t = k / FPS
        im = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if loai == "mui-ten":                  # mũi tên nhún về phía hướng chỉ
            off = math.sin(t * 2 * math.pi * 1.6) * min(W2, H2) * 0.08
            L = min(W2, H2) * 0.42
            cx, cy = W2 / 2, H2 / 2
            ang = {"phai": 0, "trai": math.pi, "xuong": math.pi / 2, "len": -math.pi / 2}.get(huong, 0)
            ux, uy = math.cos(ang), math.sin(ang)
            dau = (cx + ux * (L + off), cy + uy * (L + off))
            duoi = (cx - ux * (L - off), cy - uy * (L - off))
            for mau_, rong in ((trang, vien + 10), (mau, vien)):
                _vien_net(d, [duoi, dau], mau_, rong)
                for s in (1, -1):
                    nhanh = (dau[0] - ux * L * 0.45 - s * uy * L * 0.38, dau[1] - uy * L * 0.45 + s * ux * L * 0.38)
                    _vien_net(d, [nhanh, dau], mau_, rong)
        elif loai in ("khoanh-tron", "gach-chan", "tich", "x"):   # nét vẽ dần trong 0,5 s rồi giữ
            p = _ease(t / 0.5)
            if loai == "khoanh-tron":
                m = vien
                d.arc([m, m, W2 - m, H2 - m], start=-100, end=-100 + 370 * p, fill=mau, width=vien)
            elif loai == "gach-chan":
                y = H2 * 0.6
                pts = [(W2 * 0.04 + i / 20 * W2 * 0.92 * p, y + math.sin(i / 3) * H2 * 0.06) for i in range(21)]
                _vien_net(d, pts, mau, vien)
            elif loai == "tich":
                a, b, c = (W2 * 0.18, H2 * 0.52), (W2 * 0.42, H2 * 0.76), (W2 * 0.84, H2 * 0.24)
                d.ellipse([0, 0, W2 - 1, H2 - 1], fill=(30, 170, 80, 235))
                pts = [a, b] if p < 0.4 else [a, b, (b[0] + (c[0] - b[0]) * (p - 0.4) / 0.6, b[1] + (c[1] - b[1]) * (p - 0.4) / 0.6)]
                if p < 0.4:
                    pts = [a, (a[0] + (b[0] - a[0]) * p / 0.4, a[1] + (b[1] - a[1]) * p / 0.4)]
                _vien_net(d, pts, trang, vien)
            else:
                d.ellipse([0, 0, W2 - 1, H2 - 1], fill=(220, 50, 55, 235))
                m = W2 * 0.27
                q1, q2 = min(1, p * 2), max(0, p * 2 - 1)
                _vien_net(d, [(m, m), (m + (W2 - 2 * m) * q1, m + (H2 - 2 * m) * q1)], trang, vien)
                if q2:
                    _vien_net(d, [(W2 - m, m), (W2 - m - (W2 - 2 * m) * q2, m + (H2 - 2 * m) * q2)], trang, vien)
        elif loai == "sao":                    # 3 ngôi sao lấp lánh lệch nhịp
            for j, (fx, fy, fs) in enumerate(((0.3, 0.35, 0.34), (0.72, 0.28, 0.22), (0.6, 0.72, 0.27))):
                sc = 0.55 + 0.45 * abs(math.sin(t * 3.2 + j * 1.9))
                R = min(W2, H2) * fs * sc / 2
                cx, cy = W2 * fx, H2 * fy
                pts = []
                for i in range(8):
                    rr = R if i % 2 == 0 else R * 0.28
                    a = i * math.pi / 4 + t * 0.6
                    pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
                d.polygon(pts, fill=mau if j != 1 else trang)
        elif loai == "tim":                    # tim bật lên rồi đập nhẹ
            sc = (_ease(t / 0.25) * 1.15 if t < 0.25 else 1 + 0.08 * math.sin((t - 0.25) * 2 * math.pi * 1.4))
            R = min(W2, H2) * 0.3 * sc
            cx, cy = W2 / 2, H2 / 2
            pts = [(cx + R * 1.2 * 16 * math.sin(a) ** 3 / 16,
                    cy - R * 1.2 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16)
                   for a in [i / 60 * 2 * math.pi for i in range(60)]]
            d.polygon(pts, fill=(235, 60, 90, 255), outline=trang)
        elif loai == "nhan":                   # huy hiệu răng cưa xoay chậm, chữ ở giữa
            R = min(W2, H2) * 0.46
            cx, cy = W2 / 2, H2 / 2
            sc = _ease(t / 0.3)
            pts = [(cx + (R if i % 2 == 0 else R * 0.86) * sc * math.cos(i * math.pi / 12 + t * 0.8),
                    cy + (R if i % 2 == 0 else R * 0.86) * sc * math.sin(i * math.pi / 12 + t * 0.8)) for i in range(24)]
            d.polygon(pts, fill=mau)
            if chu and sc > 0.5:
                f = V.font("den", int(R * 0.55 * sc))
                d.text((cx, cy), C.nfc(chu).upper(), font=f, fill=(15, 15, 15, 255), anchor="mm")
        ra.append(im.resize((w, h), Image.LANCZOS))
    return ra


def xuat_sticker(thu_muc, loai, w, h, giay, mau_hex, chu="", huong="phai"):
    """Ghi chuỗi PNG; trả mẫu đường dẫn cho ffmpeg (-framerate 30 -i …%04d.png)."""
    shutil.rmtree(thu_muc, ignore_errors=True)          # xoá khung cũ của lần dựng trước
    os.makedirs(thu_muc, exist_ok=True)
    n = max(2, int(round(giay * FPS)))
    for k, im in enumerate(khung_sticker(loai, w, h, n, mau_hex, chu, huong)):
        im.save(os.path.join(thu_muc, f"{k:04d}.png"), compress_level=1)
    return os.path.join(thu_muc, "%04d.png")


def xuat_vong_sang(thu_muc, W, H, cx, cy, r, giay, mau_hex, toi=0.42):
    """Khoanh vùng trọng tâm: làm tối cả khung trừ vòng tròn quanh (cx, cy), vòng sáng tự vẽ dần, nhịp nhẹ. Trả mẫu PNG cho ffmpeg."""
    shutil.rmtree(thu_muc, ignore_errors=True)
    os.makedirs(thu_muc, exist_ok=True)
    n = max(2, int(round(giay * FPS)))
    px, py = int(cx * W), int(cy * H)
    lo = Image.new("L", (W, H), 255)
    ImageDraw.Draw(lo).ellipse([px - r, py - r, px + r, py + r], fill=0)
    lo = lo.filter(ImageFilter.GaussianBlur(10))
    mau = V.mau(mau_hex)
    for k in range(n):
        t = k / FPS
        con = (n - 1 - k) / FPS
        muc = min(1.0, t / 0.15, (con + 0.02) / 0.15)      # hiện/tắt mượt
        anh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        den = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        den.putalpha(lo.point(lambda v, m_=toi * muc: int(v * m_)))
        anh.alpha_composite(den)
        d = ImageDraw.Draw(anh)
        rr = r + int(5 * math.sin(t * 2 * math.pi * 1.2)) if t > 0.45 else r
        ve = min(1.0, t / 0.45)
        d.arc([px - rr, py - rr, px + rr, py + rr], start=-90, end=-90 + 360 * ve, fill=mau[:3] + (int(255 * muc),), width=10)
        anh.save(os.path.join(thu_muc, f"{k:04d}.png"), compress_level=1)
    return os.path.join(thu_muc, "%04d.png")


# ---------------- chữ cong ----------------
def chu_cong(text, hs, co=78, do_cong=60, vai="tieu-vang"):
    """Chữ xếp theo cung tròn; do_cong > 0 cong lên (mặt cười úp), < 0 cong xuống."""
    dam, c, hoa, _, mau_chu, *_ = V.vai(vai, hs)
    f = V.font(dam, co)
    s = C.nfc(text)
    s = s.upper() if hoa else s
    rong = f.getlength(s)
    goc = math.radians(max(15, min(180, abs(do_cong))))
    R = rong / goc
    pad = co * 1.6
    W_ = int(2 * R * math.sin(min(goc, math.pi) / 2) + pad * 2) if goc < math.pi else int(2 * R + pad * 2)
    H_ = int(R * (1 - math.cos(min(goc, math.pi) / 2)) + pad * 2.4)
    im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    bong = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    len_tren = do_cong > 0
    cx = W_ / 2
    cy = (pad + R) if len_tren else (H_ - pad - R)
    x = -rong / 2
    for ch in s:
        cw = f.getlength(ch)
        a = (x + cw / 2) / R                  # góc của ký tự
        px = cx + R * math.sin(a)
        py = cy - R * math.cos(a) if len_tren else cy + R * math.cos(a)
        o = Image.new("RGBA", (int(cw + co), int(co * 1.6)), (0, 0, 0, 0))
        do_ = ImageDraw.Draw(o)
        do_.text((o.width / 2, o.height / 2), ch, font=f, fill=mau_chu, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 255))
        o = o.rotate(-math.degrees(a) if len_tren else math.degrees(a), resample=Image.BICUBIC, expand=True)
        sh = Image.new("RGBA", o.size, (0, 0, 0, 0))
        sh.putalpha(o.getchannel("A").point(lambda v: int(v * 0.7)))
        bong.alpha_composite(sh, (int(px - o.width / 2), int(py - o.height / 2 + 6)))
        im.alpha_composite(o, (int(px - o.width / 2), int(py - o.height / 2)))
        x += cw
    bong = bong.filter(ImageFilter.GaussianBlur(7))
    bong.alpha_composite(im)
    return bong.crop(bong.getbbox() or (0, 0, 1, 1))


# ---------------- dải chữ chạy ngang ----------------
def dai_chu_chay(text, hs, co=46, vai="nhan-vang"):
    el = {"kieu": "nhan", "dong": [{"text": "   ·   ".join([C.nfc(text)] * 2), "vai": vai}], "co": co / 40}
    bc = V.dan_khoi(el, hs, 100000)
    return V.ve_khoi(bc, hs)


# ---------------- chuyển cảnh: biểu thức ffmpeg ----------------
def bo_loc_chuyen(ds, W, H):
    """ds = [{t, kieu, dai}] theo giây thành phẩm. Trả chuỗi bộ lọc (có thể rỗng) áp lên luồng hình."""
    if not ds:
        return ""
    def ghep(ds_con, fn, mac, tv="t"):
        """if(between(t,…),giá trị,…) chỉ cho các chuyển cảnh cùng loại."""
        e = mac
        for c in reversed(ds_con):
            e = f"if(between({tv},{c['t'] - c['dai'] / 2:.3f},{c['t'] + c['dai'] / 2:.3f}),{fn(c)},{e})"
        return e
    def u(c, tv="t"):        # 0→1 trong đoạn chuyển
        return f"(({tv}-{c['t'] - c['dai'] / 2:.3f})/{c['dai']:.3f})"
    theo = lambda k: [c for c in ds if c["kieu"] == k]
    loc = []
    # lật thẻ 3D: ép bề ngang về 0 ở giữa đoạn và nghiêng phối cảnh. Bộ lọc perspective không có biến
    # thời gian, chỉ có số khung «on» → thời gian = on / FPS (luồng hình đã đều 30 khung/giây từ 0).
    if theo("lat-3d"):
        tv = f"(on/{FPS})"
        fx = ghep(theo("lat-3d"), lambda c: f"abs(cos(PI*{u(c, tv)}))", "1", tv)
        ng = ghep(theo("lat-3d"), lambda c: f"(1-abs(cos(PI*{u(c, tv)})))*0.12*H*(1-2*lt({u(c, tv)},0.5))", "0", tv)
        # viền đen 2 px quanh khung: phần ngoài thẻ khi lật sẽ lấy màu viền (đen) thay vì kéo vệt ảnh
        loc.append(f"pad=iw+4:ih+4:2:2:black")
        loc.append(f"perspective=x0='W/2*(1-({fx}))':y0='{ng}':x1='W/2*(1+({fx}))':y1='-({ng})':"
                   f"x2='W/2*(1-({fx}))':y2='H-({ng})':x3='W/2*(1+({fx}))':y3='H+({ng})':"
                   f"sense=destination:eval=frame,crop={W}:{H}:2:2")
    # zoom xoáy: phóng to + xoay nhẹ quanh điểm cắt
    if theo("zoom-xoay"):
        z = ghep(theo("zoom-xoay"), lambda c: f"(1+0.4*sin(PI*{u(c)}))", "1")
        goc = ghep(theo("zoom-xoay"), lambda c: f"(0.07*sin(PI*{u(c)})*(1-2*lt({u(c)},0.5)))", "0")
        # phóng to → xoay trên khung lớn → mới cắt về khung chuẩn, để góc không lộ nền đen
        loc.append(f"scale=w='{W}*({z})':h='{H}*({z})':eval=frame,rotate=a='{goc}':ow=iw:oh=ih:fillcolor=black,crop={W}:{H}")
    # lia máy: phóng nhẹ, trượt ngang nhanh + nhoè (chỉ trong đoạn chuyển)
    if theo("lia"):
        z = ghep(theo("lia"), lambda c: "1.25", "1")
        x = ghep(theo("lia"), lambda c: f"(0.1*iw*sin(PI*{u(c)})*(1-2*lt({u(c)},0.5)))", "0")
        loc.append(f"scale=w='{W}*({z})':h='{H}*({z})':eval=frame,crop={W}:{H}:x='(iw-{W})/2+{x}':y='(ih-{H})/2'")
        for c in theo("lia"):
            loc.append(f"boxblur=luma_radius=18:luma_power=2:enable='between(t,{c['t'] - c['dai'] / 3:.3f},{c['t'] + c['dai'] / 3:.3f})'")
    # flash trắng và mờ chuyển
    if theo("flash"):
        b = ghep(theo("flash"), lambda c: f"(0.8*(1-abs(2*{u(c)}-1)))", "0")
        loc.append(f"eq=brightness='{b}':eval=frame")
    for c in theo("mo"):
        loc.append(f"boxblur=luma_radius=24:luma_power=2:enable='between(t,{c['t'] - c['dai'] / 2:.3f},{c['t'] + c['dai'] / 2:.3f})'")
    return ",".join(loc)
