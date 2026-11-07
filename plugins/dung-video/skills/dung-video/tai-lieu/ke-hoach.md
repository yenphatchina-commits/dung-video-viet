# Cấu trúc `ke-hoach.json`

Mọi giây mặc định là **giây gốc** của nguồn (như trong `tom-tat.md`); máy tự đổi sang giây thành phẩm sau khi cắt.
Ghi `"theo": "ra"` nếu muốn tính theo giây thành phẩm (dùng cho khối mở đầu). Nhiều nguồn: thêm `"src": <số>`.

```jsonc
{
  "ten": "ten-tep-xuat",                 // không dấu, gạch nối
  "kieu": "tu-van",                      // tu-van | bai-tap
  "phu_de": {"bat": true, "toi_da_chu": 4},
  "giu": null,                           // bỏ trống = dùng đề xuất của máy theo kieu; hoặc tự liệt kê [{"src":0,"a":..,"b":..}]
  "bo": [{"a": 2.9, "b": 3.85, "ly_do": "khách đáp 'Đúng'"}],
  "sua_tu": {"đạm thẳng": "đạp thẳng"},
  "bia": {"t": 6.0, "dai": 0.8,          // t = giây gốc lấy khung hình
          "dong": [{"text": "Hay đau ngang", "vai": "tieu-trang"}, {"text": "thắt lưng?", "vai": "tieu-vang"}]},
  "chen": [{"phu": 0, "a": 120.0, "t0": 17.5, "t1": 21.3}],   // cảnh phụ [0] từ giây 120 của nó, phủ 17,5–21,3 s (giây gốc nguồn chính)
  "am": {
    "nhac": {"tep": "mau:nhe-nhang", "db": -16, "ne_giong": true, "bat_dau": 0},  // tep: đường dẫn hoặc mau:nhe-nhang|tuoi-sang|tram
    "sfx_tu_dong": true,                                    // pop khi chữ hiện, click khi dòng hiện dần, whoosh hết bìa / vào cảnh chèn
    "sfx": [{"t": 12.0, "loai": "ting", "db": -18}]         // thêm tay: pop | whoosh | ting | click | bum
  },
  "zoom": [{"t0": 21.4, "t1": 28.5, "muc": 1.2, "tam": "mat"}],   // tam: "mat" (tự theo mặt) hoặc [x, y] 0..1
  "logo": {"tep": "/đường/logo.png", "goc": "tren-phai", "rong": 0.14, "mo": 0.9},   // goc: tren-phai | tren-trai
  "intro": "/đường/intro.mp4 hoặc .png", "intro_giay": 1.5,          // ảnh tĩnh cần _giay; clip tối đa 8 s
  "outro": "/đường/outro.png", "outro_giay": 2.0,
  "toc_do": 1.0,                                                     // 0,75–1,5 cho cả video
  "giam_on": false,
  "mau": {"sang": 0.02, "tuong_phan": 1.05, "bao_hoa": 1.08, "am": 0.3},  // chỉ khi người dùng cho phép; am > 0 ấm hơn
  "xuat": ["ngang", "4x5"],                                          // thêm bản: ngang (YouTube) | 4x5 (Facebook) | vuong
  "chu": [ /* các khối, xem dưới */ ]
}
```
- Có intro thì `"theo":"ra"` tính từ sau intro (chữ mở đầu vẫn vào ở giây 0,9 của nội dung). Logo được giữ chỗ — chữ tự tránh logo.
- `am.nhac.db`: nhạc nhỏ hơn giọng bao nhiêu (−14 rõ nhạc · −16 vừa · −20 rất nhẹ). Nhạc tự lặp nếu ngắn hơn video.
- Cảnh chèn không đè lên 0,8 s ảnh bìa; hai cảnh chèn chồng nhau thì máy cắt cảnh trước.

## Khối chữ
`{"id", "kieu", "t0", "t1", "dong": [...], "can": "giua"|"trai", "vi_tri": "tren"|"giua"|"duoi", "theo": "ra"?}`

| kieu | Dùng khi | vai của dòng |
|---|---|---|
| `the-den` | Thẻ đen viền màu nhấn: câu hỏi mở đầu, ý chốt, câu kết | `nho` (dòng nhỏ chữ hoa) · `to` (dòng chính) · `vang` (viên màu nhấn) |
| `tieu-de` | Tiêu đề lớn giữa khung: câu mở, cảnh báo quan trọng, câu kết | `tieu-trang` · `tieu-vang` |
| `nhan` | Nhãn/danh sách xếp chồng, hiện dần | `nhan-vang` · `nhan-den` · `nhan-do` (cảnh báo) · `dau-muc` (đầu mục chữ màu) · `chu` |

- Mỗi dòng có thể có `"t0"` riêng → hiện dần (khối giữ nguyên chỗ, không nhảy).
- `t1` bỏ trống = 3 giây. Khối nên kéo tới khi lời chuyển sang ý khác.
- `vi_tri` chỉ là ưu tiên; máy vẫn tránh mặt, động tác, vùng an toàn và các khối khác.
- Đủ thời gian đọc: ≥ 0,25 s mỗi chữ + 0,6 s.

## Ví dụ — video hướng dẫn bài tập
```json
{"id":"mo","kieu":"the-den","theo":"ra","t0":0.9,"t1":8.5,
 "dong":[{"text":"Giơ tay lên đầu, phơi đồ khó?","vai":"nho"},{"text":"Tập theo Yến","vai":"to"},{"text":"Động tác này nha","vai":"vang"}]},
{"id":"b1","kieu":"nhan","t0":10.9,"t1":17.6,
 "dong":[{"text":"1 · TÌM BỨC TƯỜNG PHẲNG","vai":"nhan-vang"},{"text":"Đứng cách tường một gang tay","vai":"nhan-den","t0":14.6}]}
```

## Ví dụ — video tư vấn
```json
{"id":"mo","kieu":"tieu-de","theo":"ra","t0":0.9,"t1":4.0,
 "dong":[{"text":"Hay đau ngang","vai":"tieu-trang"},{"text":"thắt lưng?","vai":"tieu-vang"}]},
{"id":"hoi","kieu":"nhan","can":"trai","t0":68.7,"t1":78.9,
 "dong":[{"text":"Được hỏi rõ:","vai":"dau-muc"},{"text":"Đau ở đâu?","vai":"nhan-den","t0":70.5},
         {"text":"Đau như thế nào?","vai":"nhan-den","t0":73.1}]},
{"id":"canh-bao","kieu":"tieu-de","t0":54.9,"t1":63.5,
 "dong":[{"text":"Đau thắt lưng","vai":"tieu-trang"},{"text":"chưa chắc do căng cơ","vai":"tieu-vang"}]}
```
