"""ẢNH / VIDEO MINH HOẠ MIỄN PHÍ TỪ PIXABAY (giấy phép Pixabay Content License: dùng thương mại được,
không bắt buộc ghi nguồn; không bán lại nguyên ảnh; không dùng người trong ảnh để quảng cáo kiểu giả làm khách hàng).
(Pexels đã tạm ngừng cấp mã API mới từ 11/2026 nên dùng Pixabay.)

    dv.py khoa-anh                                   lưu mã API Pixabay (hộp thoại để người dùng tự dán)
    dv.py anh-mien-phi <dự án> --tu "knee pain" [--tu "walking park"…] [--so 3]
        → tải ứng viên (video + ảnh), tất cả thành clip dọc 1080×1920 (ảnh: phóng to chậm; video ngang: nền mờ),
          ghi bảng ứng viên doc/bang-ung-vien-<từ khoá>.jpg + doc/nguon-anh.json để AI chọn
    dv.py them-phu <dự án> <clip>…                  thêm clip đã chọn làm cảnh phụ (xem hình, không nghe lại lời)
"""
import getpass, json, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C

TEP_KHOA = os.path.join(C.NHA, "pixabay.json")
UA = "dung-video (cong cu dung video tieng Viet)"
API = "https://pixabay.com/api/"


def nha_cung_cap(k):
    """Mã Pixabay dạng «12345678-abcdef…»; mã Pexels là một chuỗi chữ-số liền, không gạch nối."""
    return "pixabay" if re.fullmatch(r"\d+-[0-9a-fA-F]{16,}", k) else "pexels"


def _goi_pexels(url, k):
    rq = urllib.request.Request(url, headers={"Authorization": k, "User-Agent": UA})
    with urllib.request.urlopen(rq, timeout=20) as r:
        return json.load(r)


def khoa():
    """Mã Pixabay/Pexels nếu người dùng đã lưu; không có thì None → dùng Wikimedia Commons (không cần mã)."""
    d = C.doc_json(TEP_KHOA)
    return d.get("khoa") if d else None


GIAY_PHEP_DUNG_DUOC = re.compile(r"^(CC0|Public domain|PD|CC BY \d(\.\d)?)$", re.I)   # không lấy CC BY-SA, NC, ND


def _tim_wikimedia(q, slug, so, kho, nguon):
    """Wikimedia Commons: chỉ lấy ảnh CC0 / phạm vi công cộng / CC BY (CC BY phải ghi nguồn — máy tự hiện dòng nguồn)."""
    import html
    tham = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 20,
            "gsrsearch": f"{q} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1600,
            "iiextmetadatafilter": "LicenseShortName|Artist"}
    rq = urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(tham), headers={"User-Agent": UA})
    with urllib.request.urlopen(rq, timeout=20) as r:
        trang = json.load(r).get("query", {}).get("pages", {})
    ung = []
    for p in sorted(trang.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        gp = md.get("LicenseShortName", {}).get("value", "").strip()
        if not GIAY_PHEP_DUNG_DUOC.match(gp) or min(ii.get("width", 0), ii.get("height", 0)) < 700:
            continue
        tac_gia = re.sub(r"<[^>]+>", "", html.unescape(md.get("Artist", {}).get("value", ""))).strip()[:60] or "không rõ"
        anh = os.path.join(kho, f"{slug}-w{p['pageid']}.jpg")
        ra = anh[:-4] + ".mp4"
        if not os.path.exists(ra):
            _tai(ii.get("thumburl") or ii["url"], anh)
            anh_thanh_clip(anh, ra)
        ung.append(ra)
        nguon[os.path.basename(ra)] = {"loai": "anh", "trang": ii.get("descriptionurl"), "tac_gia": tac_gia,
                                       "giay_phep": gp, "nguon": "Wikimedia Commons", "tu_khoa": q,
                                       "can_ghi_nguon": gp.upper().startswith("CC BY")}
        if len(ung) >= so:
            break
    return ung


def _hop_thoai():
    """Hộp thoại của máy (Mac: AppleScript, Windows: PowerShell) — dễ hơn gõ trong cửa sổ dòng lệnh."""
    import subprocess
    huong = "Mã nằm ở trang pixabay.com/api/docs, mục Parameters, dòng key (sau khi đăng nhập)."
    if sys.platform == "darwin":
        r = subprocess.run(["osascript", "-e",
                            f'text returned of (display dialog "Dán mã API Pixabay hoặc Pexels vào ô dưới (Cmd + V) rồi bấm OK.\n\n{huong}" '
                            'default answer "" with title "Lưu mã ảnh miễn phí" buttons {"Huỷ", "OK"} default button "OK")'],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    if os.name == "nt":
        ps = ("Add-Type -AssemblyName Microsoft.VisualBasic;"
              f"[Microsoft.VisualBasic.Interaction]::InputBox('Dán mã API Pixabay (Ctrl + V) rồi bấm OK. {huong}','Lưu mã ảnh miễn phí')")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
        return r.stdout.strip()
    return getpass.getpass("Dán mã API Pixabay rồi nhấn Enter: ")


def luu_khoa():
    dan = _hop_thoai()
    if not dan.strip():
        raise SystemExit("Chưa dán mã (đã bấm Huỷ hoặc để trống).")
    # người dùng hay chép dính chữ xung quanh ("Your API key: …") → tự lọc lấy phần mã
    m = re.search(r"\d{5,}-[0-9a-fA-F]{16,}", dan) or re.search(r"(?<![A-Za-z0-9])[A-Za-z0-9]{40,80}(?![A-Za-z0-9])", dan)
    if not m:
        raise SystemExit("Không thấy mã trong chữ vừa dán. Mã Pixabay có dạng 12345678-0a1b2c… (dãy số, gạch ngang, chữ số).")
    k = m.group(0)
    ncc = nha_cung_cap(k)
    try:
        if ncc == "pixabay":
            _goi({"q": "walking", "per_page": 3}, k)
        else:
            _goi_pexels("https://api.pexels.com/v1/search?query=walking&per_page=1", k)
    except Exception as e:
        raise SystemExit(f"{ncc.capitalize()} không nhận mã này ({e}). Kiểm tra lại mã.")
    C.ghi_json(TEP_KHOA, {"khoa": k, "nha": ncc, "luc": time.strftime("%Y-%m-%d")})
    os.chmod(TEP_KHOA, 0o600)
    print(f"✅ Đã lưu mã {ncc.capitalize()} trên máy này.")


def _goi(tham, k, video=False):
    url = (API + ("videos/" if video else "")) + "?" + urllib.parse.urlencode(dict(tham, key=k, safesearch="true"))
    rq = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(rq, timeout=20) as r:
        return json.load(r)


def _tai(url, ra):
    rq = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(rq, timeout=120) as r, open(ra, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b:
                break
            f.write(b)


def video_thanh_doc(vao, ra, giay=8.0):
    """Video bất kỳ khổ → clip dọc 1080×1920 không tiếng: nền mờ của chính video + video ở giữa."""
    W, H, FPS = C.W, C.H, C.FPS
    C.sh([C.ffmpeg(), "-v", "error", "-y", "-t", f"{giay}", "-i", vao, "-filter_complex",
          f"[0:v]fps={FPS},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,"
          f"eq=brightness=-0.08[nen];[b]scale={W}:-2[giua];[nen][giua]overlay=0:(H-h)/2,format=yuv420p",
          "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", ra])


def anh_thanh_clip(anh, ra, giay=4.0):
    """Ảnh tĩnh → clip dọc 1080×1920: nền mờ của chính ảnh + ảnh ở giữa phóng to chậm."""
    W, H, FPS = C.W, C.H, C.FPS
    n = int(giay * FPS)
    C.sh([C.ffmpeg(), "-v", "error", "-y", "-loop", "1", "-t", f"{giay}", "-i", anh, "-filter_complex",
          f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,eq=brightness=-0.08[nen];"
          f"[b]scale={W * 2}:-2,zoompan=z='min(1.0+0.0015*on,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:"
          f"s={W}x{int(W * 1.25)}:fps={FPS}[giua];[nen][giua]overlay=0:(H-h)/2,format=yuv420p,trim=duration={giay}",
          "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", ra])


def tim(du_an, tu_khoa, so=3):
    k = khoa()
    kho = os.path.join(du_an, "kho-anh")
    os.makedirs(kho, exist_ok=True)
    nguon_p = os.path.join(du_an, "doc", "nguon-anh.json")
    nguon = C.doc_json(nguon_p, {})
    for q in tu_khoa:
        slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")
        C.in_ra(f"Tìm «{q}»…")
        ung = []
        if not k:
            ung = _tim_wikimedia(q, slug, max(so, 4), kho, nguon)
            v = {"hits": []}
        elif nha_cung_cap(k) == "pexels":
            ung = _tim_pexels(q, slug, so, k, kho, nguon)
            v = {"hits": []}
        else:
            v = _goi({"q": q, "video_type": "film", "per_page": max(3, so)}, k, video=True)
        for it in v.get("hits", [])[:so]:
            tep = it.get("videos", {}).get("medium") or it.get("videos", {}).get("small")
            if not tep or not tep.get("url") or it.get("duration", 0) < 3:
                continue
            ra = os.path.join(kho, f"{slug}-v{it['id']}.mp4")
            if not os.path.exists(ra):
                goc = ra[:-4] + "-goc.mp4"
                _tai(tep["url"], goc)
                video_thanh_doc(goc, ra)
                os.remove(goc)
            ung.append(ra)
            nguon[os.path.basename(ra)] = {"loai": "video", "trang": it.get("pageURL"), "tac_gia": it.get("user"),
                                           "giay_phep": "Pixabay Content License", "tu_khoa": q}
        a = {"hits": []} if (not k or nha_cung_cap(k) == "pexels") else \
            _goi({"q": q, "image_type": "photo", "orientation": "vertical", "per_page": max(3, so)}, k)
        for it in a.get("hits", [])[:so]:
            anh = os.path.join(kho, f"{slug}-a{it['id']}.jpg")
            ra = anh[:-4] + ".mp4"
            if not os.path.exists(ra):
                _tai(it["largeImageURL"], anh)
                anh_thanh_clip(anh, ra)
            ung.append(ra)
            nguon[os.path.basename(ra)] = {"loai": "anh", "trang": it.get("pageURL"), "tac_gia": it.get("user"),
                                           "giay_phep": "Pixabay Content License", "tu_khoa": q}
        C.ghi_json(nguon_p, nguon)
        if ung:
            bang_ung_vien(ung, os.path.join(du_an, "doc", f"bang-ung-vien-{slug}.jpg"))
            C.in_ra(f"  {len(ung)} ứng viên → doc/bang-ung-vien-{slug}.jpg")
            for i, u in enumerate(ung):
                C.in_ra(f"    #{i + 1} {u}")
        else:
            C.in_ra("  (không có kết quả — thử từ khoá tiếng Anh khác)")


def _tim_pexels(q, slug, so, k, kho, nguon):
    ung = []
    v = _goi_pexels("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": q, "orientation": "portrait", "size": "medium", "per_page": so}), k)
    for it in v.get("videos", [])[:so]:
        tep = sorted([f for f in it.get("video_files", []) if f.get("height") and 900 <= f["height"] <= 2000],
                     key=lambda f: abs(f["height"] - 1920))
        if not tep or it.get("duration", 0) < 3:
            continue
        ra = os.path.join(kho, f"{slug}-v{it['id']}.mp4")
        if not os.path.exists(ra):
            goc = ra[:-4] + "-goc.mp4"
            _tai(tep[0]["link"], goc)
            video_thanh_doc(goc, ra)
            os.remove(goc)
        ung.append(ra)
        nguon[os.path.basename(ra)] = {"loai": "video", "trang": it.get("url"), "tac_gia": it.get("user", {}).get("name"),
                                       "giay_phep": "Pexels License", "tu_khoa": q}
    a = _goi_pexels("https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": q, "orientation": "portrait", "per_page": so}), k)
    for it in a.get("photos", [])[:so]:
        anh = os.path.join(kho, f"{slug}-a{it['id']}.jpg")
        ra = anh[:-4] + ".mp4"
        if not os.path.exists(ra):
            _tai(it["src"]["large2x"], anh)
            anh_thanh_clip(anh, ra)
        ung.append(ra)
        nguon[os.path.basename(ra)] = {"loai": "anh", "trang": it.get("url"), "tac_gia": it.get("photographer"),
                                       "giay_phep": "Pexels License", "tu_khoa": q}
    return ung


def bang_ung_vien(ung, ra):
    from PIL import Image, ImageDraw, ImageFont
    import tempfile
    font = ImageFont.truetype(os.path.join(C.FONT, "BeVietnamPro-Bold.ttf"), 20)
    o = []
    with tempfile.TemporaryDirectory() as td:
        for i, u in enumerate(ung):
            p = os.path.join(td, f"{i}.jpg")
            C.sh([C.ffmpeg(), "-v", "error", "-y", "-ss", "1", "-i", u, "-frames:v", "1", "-vf", "scale=240:-2", p], bat_buoc=False)
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGB")
            ImageDraw.Draw(im).rectangle([0, 0, 240, 28], fill=(0, 0, 0))
            ImageDraw.Draw(im).text((6, 2), f"#{i + 1} {'video' if '-v' in os.path.basename(u) else 'ảnh'}", font=font, fill=(255, 220, 0))
            o.append(im)
    if not o:
        return
    w = 240
    h = max(i.height for i in o)
    tam = Image.new("RGB", (w * len(o), h))
    for i, im in enumerate(o):
        tam.paste(im, (i * w, 0))
    tam.save(ra, quality=85)


def them_phu(du_an, clips):
    """Thêm clip làm cảnh phụ cho dự án đã đọc: xem hình (mặt, chuyển động) để chữ tránh đúng chỗ."""
    import numpy as np
    import doc as D
    viec = C.doc_json(os.path.join(du_an, "viec.json"))
    mat = C.doc_json(os.path.join(du_an, "doc", "mat.json"))
    dp = os.path.join(du_an, "doc", "dong-phu.npz")
    dong = [np.load(dp)[f"arr_{i}"] for i in range(len(viec.get("phu", [])))] if os.path.exists(dp) else []
    for c in clips:
        c = os.path.abspath(c)
        if any(p["duong"] == c for p in viec.get("phu", [])):
            continue
        ts = dict(C.thong_so(c), duong=c)
        m, d = D.xem_hinh(c, ts)
        viec.setdefault("phu", []).append(ts)
        mat.setdefault("phu", []).append(m)
        dong.append(d)
        C.in_ra(f"phụ[{len(viec['phu']) - 1}] = {os.path.basename(c)} ({ts['dur']:.1f}s)")
    C.ghi_json(os.path.join(du_an, "viec.json"), viec)
    C.ghi_json(os.path.join(du_an, "doc", "mat.json"), mat)
    np.savez_compressed(dp, *dong)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["khoa"]:
        luu_khoa()
    elif a[:1] == ["them-phu"] and len(a) >= 3:
        them_phu(os.path.abspath(a[1]), a[2:])
    elif a[:1] == ["tim"] and len(a) >= 2:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("du_an")
        ap.add_argument("--tu", action="append", required=True)
        ap.add_argument("--so", type=int, default=4)
        x = ap.parse_args(a[1:])
        tim(os.path.abspath(x.du_an), x.tu, x.so)
    else:
        print(__doc__)
