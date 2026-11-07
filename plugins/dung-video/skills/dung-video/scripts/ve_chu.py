"""VẼ CHỮ: các kiểu khối chữ (thẻ đen, tiêu đề, nhãn xếp chồng, phụ đề tô chữ đang nói) bằng Pillow.

Mỗi khối được dàn trang MỘT lần (kích thước cố định), rồi vẽ theo thời điểm: dòng nào chưa tới giờ thì chưa hiện,
nên khối không nhảy chỗ khi hiện dần.
"""
import os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import chung as C

DEN = (14, 14, 14)
TRANG = (255, 255, 255)


@lru_cache(maxsize=64)
def font(dam, co):
    if dam.startswith("nghieng"):                 # chữ có chân nghiêng (Playfair Display Italic, biến thể độ đậm)
        f = ImageFont.truetype(os.path.join(C.FONT, "PlayfairDisplay-Italic.ttf"), int(co))
        f.set_variation_by_axes([800 if dam == "nghieng-dam" else 600])
        return f
    ten = {"vua": "Medium", "nua": "SemiBold", "dam": "Bold", "rat": "ExtraBold", "den": "Black"}[dam]
    return ImageFont.truetype(os.path.join(C.FONT, f"BeVietnamPro-{ten}.ttf"), int(co))


def mau(hex_, a=255):
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def ngat_dong(text, f, rong, gian=0):
    """Ngắt dòng theo chữ cho vừa bề rộng; giữ xuống dòng có sẵn (\\n)."""
    ra = []
    for doan in text.split("\n"):
        dong = ""
        for w in doan.split():
            thu = (dong + " " + w).strip()
            if dong and do_dai(thu, f, gian) > rong:
                ra.append(dong)
                dong = w
            else:
                dong = thu
        ra.append(dong)
        # tránh dòng cuối chỉ có 1 chữ lẻ ("LẦN?"): kéo bớt chữ từ dòng trên xuống
        while len(ra) >= 2 and len(ra[-1].split()) == 1 and len(ra[-2].split()) >= 3:
            tren = ra[-2].split()
            moi = tren[-1] + " " + ra[-1]
            if do_dai(moi, f, gian) > rong:
                break
            ra[-2], ra[-1] = " ".join(tren[:-1]), moi
    return ra


def do_dai(s, f, gian=0):
    return f.getlength(s) + gian * max(0, len(s) - 1)


def _chu(d, xy, s, f, fill, gian=0, vien=0, mau_vien=(0, 0, 0, 255)):
    if not gian:
        d.text(xy, s, font=f, fill=fill, stroke_width=vien, stroke_fill=mau_vien)
        return
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill, stroke_width=vien, stroke_fill=mau_vien)
        x += f.getlength(ch) + gian


def _cao(f):
    a, b = f.getmetrics()
    return a + b


# ---------------- KIỂU DÒNG ----------------
# mỗi vai: (độ đậm, cỡ chữ, viết hoa, nền, màu chữ, đệm ngang, đệm dọc, bo góc, khoảng chữ, bóng, viền)
def vai(ten, hs):
    nhan, canh = hs["mau_nhan"], hs["mau_canh_bao"]
    V = {
        # thẻ đen
        "nho":      ("nua", 30, True, None, (255, 255, 255, 210), 0, 0, 0, 3, False, 0),
        "to":       ("rat", 78, False, None, TRANG + (255,), 0, 0, 0, 0, False, 0),
        "vang":     ("rat", 44, True, mau(nhan), DEN + (255,), 24, 8, 12, 0, False, 0),
        # tiêu đề lớn
        "tieu-trang": ("rat", 88, True, None, TRANG + (255,), 0, 0, 0, 0, True, 4),
        "tieu-vang":  ("den", 112, True, None, mau(nhan), 0, 0, 0, 0, True, 4),
        # nhãn xếp chồng
        "nhan-vang":  ("rat", 40, False, mau(nhan), DEN + (255,), 22, 9, 14, 0, False, 0),
        "nhan-den":   ("dam", 38, False, (12, 12, 12, 225), TRANG + (255,), 22, 9, 14, 0, False, 0),
        "nhan-do":    ("rat", 42, True, mau(canh), TRANG + (255,), 24, 10, 14, 0, False, 0),
        "dau-muc":    ("den", 50, True, None, mau(nhan), 0, 0, 0, 0, True, 3),
        "chu":        ("dam", 42, False, None, TRANG + (255,), 0, 0, 0, 0, True, 3),
        # chữ có chân nghiêng — dùng được ở mọi kiểu khối
        "tieu-nghieng":      ("nghieng-dam", 92, False, None, TRANG + (255,), 0, 0, 0, 0, True, 0),
        "tieu-nghieng-vang": ("nghieng-dam", 92, False, None, mau(nhan), 0, 0, 0, 0, True, 0),
        "nho-gian":          ("nua", 26, True, None, (255, 255, 255, 220), 0, 0, 0, 5, True, 0),
        "nho-vang":          ("nua", 28, True, None, mau(nhan), 0, 0, 0, 4, True, 0),
    }
    if hs.get("font_tieu_de") == "co-chan-nghieng":   # phong cách đã học: tiêu đề & dòng chính dùng chữ có chân
        doi = {"tieu-trang": "tieu-nghieng", "tieu-vang": "tieu-nghieng-vang"}
        if ten in doi:
            return V[doi[ten]]
        if ten == "to":
            return ("nghieng-dam", 74, False, None, TRANG + (255,), 0, 0, 0, 0, False, 0)
    return V[ten]


VAI_THEO_KIEU = {"the-den": "to", "tieu-de": "tieu-trang", "nhan": "nhan-den"}


# ---------------- DÀN TRANG ----------------
def dan_khoi(el, hs, rong_max):
    """el = {"kieu": "the-den"|"tieu-de"|"nhan", "can": "giua"|"trai", "dong": [{"text","vai","t0"?}]}
    Trả bố cục {w,h,dong:[{x,y,w,h,vai,text,t0,dong_chu:[...]}], khung}."""
    kieu = el.get("kieu", "nhan")
    can = el.get("can", "giua")
    co = float(el.get("co", 1.0))
    dem = (40, 30) if kieu == "the-den" else (0, 0)
    gian_dong = 16 if kieu != "tieu-de" else 2
    trong = rong_max - 2 * dem[0]
    ds = []
    for d in el["dong"]:
        v = d.get("vai") or VAI_THEO_KIEU.get(kieu, "nhan-den")
        dam, c, hoa, nen, mau_chu, dx, dy, bo, gian, bong, vien = vai(v, hs)
        f = font(dam, c * co)
        s = C.nfc(d["text"])
        s = s.upper() if hoa else s
        cac = ngat_dong(s, f, trong - 2 * dx, gian)
        h1 = _cao(f)
        rong = max(do_dai(x, f, gian) for x in cac) + 2 * dx
        cao = h1 * len(cac) + (len(cac) - 1) * 4 + 2 * dy
        ds.append({"vai": v, "text": s, "dong_chu": cac, "w": int(rong), "h": int(cao), "f": f, "h1": h1,
                   "nen": nen, "mau": mau_chu, "dx": dx, "dy": dy, "bo": bo, "gian": gian, "bong": bong,
                   "vien": vien, "t0": d.get("t0")})
    W_ = max(x["w"] for x in ds) + 2 * dem[0]
    y = dem[1]
    for x in ds:
        x["x"] = (W_ - x["w"]) // 2 if can == "giua" else dem[0]
        x["y"] = y
        y += x["h"] + gian_dong
    H_ = y - gian_dong + dem[1]
    le = 24                                  # lề cho bóng chữ
    for x in ds:
        x["x"] += le
        x["y"] += le
    return {"w": W_ + 2 * le, "h": H_ + 2 * le, "le": le, "dong": ds, "kieu": kieu, "can": can,
            "nen_trong": el.get("nen") == "trong"}


def ve_khoi(bc, hs, hien=None):
    """Vẽ khối; hien = tập chỉ số dòng đang hiện (None = tất cả)."""
    im = Image.new("RGBA", (bc["w"], bc["h"]), (0, 0, 0, 0))
    le = bc["le"]
    if bc["kieu"] == "the-den":
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([le, le, bc["w"] - le - 1, bc["h"] - le - 1], radius=26,
                            fill=None if bc.get("nen_trong") else (12, 12, 12, 228),
                            outline=mau(hs["mau_nhan"]), width=4 if bc.get("nen_trong") else 5)
    bong = Image.new("RGBA", im.size, (0, 0, 0, 0))
    db = ImageDraw.Draw(bong)
    d = ImageDraw.Draw(im)
    co_bong = False
    for i, x in enumerate(bc["dong"]):
        if hien is not None and i not in hien:
            continue
        if x["nen"]:
            d.rounded_rectangle([x["x"], x["y"], x["x"] + x["w"], x["y"] + x["h"]], radius=x["bo"], fill=x["nen"])
        yy = x["y"] + x["dy"]
        for s in x["dong_chu"]:
            rr = do_dai(s, x["f"], x["gian"])
            xx = x["x"] + (x["w"] - rr) / 2 if bc["can"] == "giua" or x["nen"] else x["x"] + x["dx"]
            if x["bong"]:
                co_bong = True
                _chu(db, (xx, yy + 6), s, x["f"], (0, 0, 0, 200), x["gian"], x["vien"] + 4, (0, 0, 0, 200))
            _chu(d, (xx, yy - 2), s, x["f"], x["mau"], x["gian"], x["vien"], (0, 0, 0, 255))
            yy += x["h1"] + 4
    if co_bong:
        bong = bong.filter(ImageFilter.GaussianBlur(9))
        bong.alpha_composite(im)
        im = bong
    return im


# ---------------- PHỤ ĐỀ ----------------
def dan_phu_de(tu, rong_max, co=56):
    """tu = [{"w","a","b"}] một cụm 3–6 chữ. Trả bố cục với vị trí từng chữ (tối đa 2 dòng)."""
    f = font("rat", co)
    gian = f.getlength(" ")
    dong, x, y, h1 = [], 0, 0, _cao(f)
    vt = []
    for w in tu:
        rr = f.getlength(w["w"])
        if x and x + rr > rong_max:
            dong.append(x - gian)
            x, y = 0, y + h1 + 2
        vt.append([x, y, w])
        x += rr + gian
    dong.append(x - gian)
    W_ = int(max(dong)) + 2 * 30
    H_ = y + h1 + 2 * 26
    # canh giữa từng dòng
    so_dong = len(dong)
    for p in vt:
        k = int(p[1] // (h1 + 2))
        p[0] += 30 + (max(dong) - dong[k]) / 2
        p[1] += 26
    return {"w": W_, "h": H_, "f": f, "vt": vt, "so_dong": so_dong}


def ve_phu_de(bc, hs, dang_noi):
    im = Image.new("RGBA", (bc["w"], bc["h"]), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    vang = mau(hs.get("phu_de_mau_noi") or hs["mau_nhan"])
    for i, (x, y, w) in enumerate(bc["vt"]):
        d.text((x, y), w["w"], font=bc["f"], fill=vang if i == dang_noi else (255, 255, 255, 255),
               stroke_width=7, stroke_fill=(0, 0, 0, 255))
    return im


# ---------------- BÌA ----------------
def ve_bia(anh_khung, dong, hs, mat=None):
    """Ảnh bìa: khung hình làm tối nhẹ + tiêu đề lớn; tránh mặt (mat = hộp mặt 0..1 nếu có)."""
    im = anh_khung.convert("RGBA").resize((C.W, C.H))
    toi = Image.new("RGBA", im.size, (0, 0, 0, 95))
    im.alpha_composite(toi)
    el = {"kieu": "tieu-de", "dong": [{"text": d["text"], "vai": d.get("vai", "tieu-trang")} for d in dong], "co": 1.15}
    bc = dan_khoi(el, hs, int(C.W * 0.9))
    k = ve_khoi(bc, hs)
    if mat is None:
        y = int(C.H * 0.40 - bc["h"] / 2)
    else:
        tren, duoi = mat[1] * C.H, (mat[1] + mat[3] * 1.15) * C.H
        y_duoi = int(duoi + 20)                              # ưu tiên dưới cằm
        if y_duoi + bc["h"] <= C.H * (1 - 0.22):
            y = y_duoi
        else:                                                # không đủ chỗ: đặt trên đầu
            y = max(int(C.H * 0.07), int(tren - 30 - bc["h"]))
    im.alpha_composite(k, ((C.W - bc["w"]) // 2, y))
    return im
