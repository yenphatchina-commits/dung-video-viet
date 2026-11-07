# Tệp phong cách `~/.dung-video/phong-cach/<tên>.json`

AI viết tệp này sau bước `dv.py hoc`, từ số đo trong `hoc/tom-tat-hoc.md` và những gì nhìn thấy ở `bang-24.jpg`, `khung-1..5.jpg`.
Khi dựng, ghi `"phong_cach": "<tên>"` vào `ke-hoach.json`. Giá trị ghi thẳng trong kế hoạch luôn thắng phong cách.

```jsonc
{
  "ten": "soi-dong",
  "mo_ta": "1 câu dễ hiểu cho người dùng: cắt chặt, phụ đề vàng, chữ chốt ý phía trên, nhạc rõ",
  "hoc_tu": "tên tệp video mẫu",

  // ---- MÁY TỰ ÁP ----
  "cat": {"do_chat": "chat", "dem_truoc": 0.12, "dem_sau": 0.08},
        // do_chat: chat (bỏ mọi ngừng > 0,35 s) | vua (chỉ bỏ ngừng > 0,8 s) | giu-nguyen (như video bài tập)
        // dem_*: giây chừa lại trước/sau chỗ cắt. Học từ "chua_lai_tb" khi có bản thô (chia đôi).
  "phu_de": {"bat": true, "toi_da_chu": 4, "co": 56, "mau_noi": "#FFD400"},   // mau_noi = màu chữ đang nói
  "mau": {"nhan": "#FFD400", "canh_bao": "#E5383B"},
  "font_tieu_de": "khong-chan",            // khong-chan (Be Vietnam Pro) | co-chan-nghieng (Playfair Display nghiêng)
  "am": {"nhac": true, "nhac_db": -16, "nhac_tep": "mau:nhe-nhang", "sfx": true},
        // nhac_db: lấy từ "nhac_so_voi_giong_db" (thường −25…−10). Không có nhạc → "nhac": false
  "toc_do": 1.0,

  // ---- AI ĐỌC ĐỂ VIẾT KẾ HOẠCH (máy không tự áp) ----
  "chu": {
    "mat_do_giay": 6,                      // trung bình mấy giây có 1 khối chữ chốt ý mới
    "kieu_uu_tien": ["tieu-de", "nhan"],   // the-den | tieu-de | nhan
    "vi_tri": "tren",                      // tren | giua | duoi
    "can": "giua",                         // giua | trai
    "viet_hoa": true,
    "mo_dau": "tiêu đề câu hỏi 2 tầng trắng + vàng, giữa khung",
    "ket": "viên vàng kêu gọi bình luận"
  },
  "lam_toi_the": 0.45,                     // video mẫu làm tối nền khi hiện thẻ tiêu đề (0 = không)
  "zoom": {"moi_phut": 2, "muc": 1.2},     // 0 = không phóng to
  "chen_canh": "nhiều | ít | không",       // video mẫu có hay chèn cảnh minh hoạ không
  "khong_lam_duoc": ["chuyển cảnh lật trang 3D", "sticker động"],   // báo người dùng
  "ghi_chu": "điều đặc trưng khác"
}
```

## Cách suy ra từ số đo
| Số đo | Gợi ý |
|---|---|
| `so_voi_ban_tho.chua_lai_tb` ≤ 0,3 | `do_chat: chat`, dem_truoc ≈ dem_sau ≈ chua_lai_tb / 2 |
| `ti_le_chu_giu` ≥ 0,95 và ít chỗ cắt | `do_chat: giu-nguyen` |
| `loi.ngung_giua_chu_trung_vi` < 0,1 và `so_ngung_tren_0_5s` gần 0 | cắt chặt |
| `nhac_so_voi_giong_db` | Tiếng nền lúc không nói so với giọng. Tiếng phòng thường −25…−18 dB nên **không đủ để kết luận có nhạc**. Có bản thô: chỉ coi là có nhạc khi cao hơn `nen_tho_so_voi_giong_db` ≥ 3 dB. Không có bản thô: > −15 dB mới coi là có nhạc; còn lại hỏi người dùng |
| `phong_to_so_lan` (trừ `phong_to_ban_tho` nếu có) / phút | `zoom.moi_phut`. Máy quay di chuyển cũng làm mặt to nhỏ — đối chiếu ảnh |
| `mau_noi_bat[0]` | ứng viên `mau.nhan` — đối chiếu với màu chữ thấy trong ảnh |
| Ảnh thấy chữ chạy theo lời, chữ đang nói đổi màu | `phu_de.bat: true`, `mau_noi` = màu đó |
| Ảnh thấy chữ có chân, nghiêng | `font_tieu_de: co-chan-nghieng` |
| `doi_canh.so_lan` | Máy đếm thiếu khi các cảnh cùng tông màu — đếm thêm bằng mắt trên `bang-24.jpg` |
| Ảnh thấy nền tối hẳn khi hiện thẻ chữ | `lam_toi_the` ≈ 0,4–0,55 |
