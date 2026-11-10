"""Thẻ minh hoạ động: biểu tượng Material Symbols (Apache 2.0) + chữ ngắn → clip dọc 1080×1920, tự thêm làm cảnh phụ.

    dv.py the-minh-hoa <dự án> --ten di-bo --bieu-tuong directions_walk --chu "Đi bộ vừa sức" --chu-phu "vẫn rất tốt" --dau nen
Tên biểu tượng tra ở fonts.google.com/icons (vd directions_walk, elderly, stairs, footprint, timer, chair, medical_services,
stethoscope, personal_injury, healing, self_improvement, spa, water_drop, bedtime, restaurant, local_hospital, favorite).
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chung as C
import ho_so as HS
import hieu_ung as HU
import anh_mien_phi as AMP

ap = argparse.ArgumentParser()
ap.add_argument("du_an")
ap.add_argument("--ten", required=True)
ap.add_argument("--bieu-tuong", required=True)
ap.add_argument("--chu", required=True)
ap.add_argument("--chu-phu", default="")
ap.add_argument("--dau", default="", choices=["", "nen", "khong-nen", "canh-bao"])
ap.add_argument("--giay", type=float, default=2.4)
a = ap.parse_args()
du_an = os.path.abspath(a.du_an)
viec = C.doc_json(os.path.join(du_an, "viec.json"))
hs = HS.lay(viec.get("ho_so") or "")
os.makedirs(os.path.join(du_an, "kho-anh"), exist_ok=True)
ra = os.path.join(du_an, "kho-anh", f"the-{a.ten}.mp4")
HU.xuat_the_minh_hoa(ra, a.bieu_tuong, a.chu, hs, a.giay, a.dau, a.chu_phu)
AMP.them_phu(du_an, [ra])
