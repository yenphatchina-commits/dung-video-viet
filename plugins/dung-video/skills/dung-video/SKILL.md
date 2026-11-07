---
name: dung-video
description: Dựng video dọc 9:16 tiếng Việt (TikTok, Reels, Shorts) từ clip quay điện thoại cho người không biết edit — tự nghe lời, cắt khoảng ngừng, bỏ câu nói hỏng, thêm chữ chốt ý tránh mặt và tránh động tác, phụ đề tô chữ đang nói, chèn cảnh minh hoạ (B-roll), nhạc nền tự nhỏ khi có lời, hiệu ứng âm thanh, logo, intro/outro, phóng to đoạn quan trọng, tăng tốc, giảm ồn, ảnh bìa phủ giây đầu, chuẩn âm lượng, xuất MP4 dọc và thêm khổ ngang YouTube / 4:5 Facebook. Dùng khi người dùng đưa video và nói "dựng", "edit", "làm video", "cắt video", "thêm chữ", "làm phụ đề", "làm ảnh bìa", hoặc "cài đặt dựng video", "kích hoạt mã", "kiểm tra máy", "nâng cấp skill", "học phong cách video này", "dựng theo phong cách …".
---

# Dựng video

Người dùng là chủ cơ sở, giáo viên, người bán hàng — **không rành máy tính**. Nói tiếng Việt đơn giản, không dùng từ kỹ thuật,
không bắt họ gõ lệnh. Bạn tự chạy lệnh. Máy làm phần đo đạc; **bạn làm đạo diễn**: chọn câu giữ, viết chữ chốt ý, chọn bìa.

Mọi lệnh chạy qua `scripts/dv.py` bằng Python có sẵn: Mac `python3 <skill>/scripts/dv.py …`, Windows `py <skill>\scripts\dv.py …`
(`<skill>` = thư mục chứa tệp này).

## 0. Trước lần đầu
- `dv.py kiem-may`. Có ❌ thì làm theo dòng → bên dưới. «Cài đặt dựng video» = `dv.py cai-dat` (lần đầu tải ~2 GB, báo trước).
- Thiếu uv: đưa người dùng đúng dòng lệnh kiểm-máy in ra, giải thích họ dán vào Terminal/PowerShell.
- «Kích hoạt mã …» = `dv.py kich-hoat <mã>`. Không bao giờ tạo, sửa, đoán mã hay sửa tệp bản quyền.
- Chỉ chạy được trong **Claude Code** (cửa sổ dòng lệnh hoặc tab Code của ứng dụng Claude). Trên claude.ai web thì báo không hỗ trợ.

## 1. Hỏi nhanh (tối đa 1 lượt, bỏ qua được)
Người xem là ai? Xem xong hiểu gì? Cuối video muốn họ làm gì? Kênh nào (hồ sơ)? Người dùng không trả lời → tự đoán từ lời nói và nói rõ đã đoán gì.
Hồ sơ kênh: `dv.py ho-so ds`; chưa có → `dv.py ho-so tao <tên>` rồi hỏi tên cơ sở, tên người dẫn, các tên riêng hay bị nghe nhầm,
và sửa tệp hồ sơ in ra (`ten_kenh`, `nguoi_dan`, `tu_rieng`, `sua_tu`, `mau_nhan`).

## 2. Đọc
```
dv.py du-an "<chủ đề ngắn>"          → in thư mục dự án
dv.py doc <dự án> --video <clip nói> [--video <clip nói 2>…] [--phu <cảnh minh hoạ>…] --ho-so <tên>
```
`--video` = clip có lời chính (máy nghe và cắt). `--phu` = cảnh minh hoạ không cần tiếng (đèn, tay thao tác, sản phẩm…);
máy xem hình, không nghe. Không chắc clip nào là gì thì nhìn khung đầu của từng clip trước khi chia.
Giới hạn bản này: tổng ≤ 5 phút và ≤ 1 GB; vượt thì máy từ chối — bảo người dùng chia nhỏ.
Rồi **đọc hết** `doc/tom-tat.md` và **nhìn** `doc/bang-khung.jpg` (và `doc/bang-phu-<n>.jpg` nếu có cảnh phụ).

## 3. Viết `<dự án>/ke-hoach.json`
Cấu trúc đầy đủ và ví dụ: `tai-lieu/ke-hoach.md` (đọc trước khi viết lần đầu). Quyết định:
- **kieu**: `tu-van` (nói/giảng giải: bỏ mọi khoảng ngừng, phụ đề bật) hay `bai-tap` (hướng dẫn động tác: giữ nguyên lúc đang làm động tác, phụ đề tắt).
- **bo**: đoạn giây gốc cần bỏ thêm — lời đáp của người phụ ("Đúng", "Dạ"), câu nói hỏng; câu nói lặp thì **giữ lần nói đủ ý, rõ giọng nhất**, bỏ các lần trước.
  Không bỏ câu điều kiện/cảnh báo ("khi phù hợp", "chưa chắc là do…", "nên đi khám bác sĩ").
- **sua_tu**: sửa chữ nghe nhầm theo ngữ cảnh (vd "đạm thẳng"→"đạp thẳng"). Câu đánh dấu ⚠️ NGHI BỊA là máy nghe ra chữ không có thật — không dùng.
- **chu**: chữ chốt ý — vài từ khoá theo lời, KHÔNG chép nguyên câu. Mỗi ý chính một khối; danh sách thì hiện dần từng dòng (`t0` từng dòng);
  bước bài tập đánh số "1 · …"; câu cảnh báo quan trọng làm tiêu đề lớn; câu kết kêu gọi (bình luận / nhắn tin / lưu lại).
- **bia**: khung có mặt rõ hoặc đúng thao tác + 2 dòng tiêu đề ngắn (câu hỏi gây tò mò).
- **chen** (cảnh minh hoạ): đặt cảnh phụ **đúng lúc lời nhắc tới** việc đó (nói "chiếu đèn" → cảnh đèn), mỗi cảnh 1,5–5 s,
  lấy đoạn trong clip phụ có thao tác rõ (xem bảng phụ). Dùng thêm để **phủ chỗ nối bị giật** sau khi cắt.
  Không chèn đè câu mở đầu, câu cảnh báo quan trọng và câu kêu gọi cuối (người xem cần thấy mặt người nói).
- **am.nhac**: hỏi người dùng có nhạc riêng không (`dv.py nhac` liệt kê). Có → đường dẫn tệp; không → `mau:nhe-nhang`
  (tư vấn, sức khoẻ), `mau:tuoi-sang` (bán hàng, ưu đãi), `mau:tram` (chủ đề nghiêm túc). Bài tập có đếm nhịp → nhạc nhỏ hơn (`db` −20).
  Nhạc người dùng đưa phải là nhạc họ có quyền dùng — nhắc một lần nếu là bài hát nổi tiếng.
- **zoom**: phóng to 1,15–1,25 vào mặt ở 1–3 câu quan trọng nhất (câu chốt, cảnh báo) của video nói, mỗi lần 2–6 s.
  Không phóng to video bài tập (dễ cắt mất tay chân đang tập) trừ khi người dùng yêu cầu.
- **logo / intro / outro**: lấy từ hồ sơ kênh nếu có; người dùng đưa tệp mới thì ghi vào kế hoạch. Intro tối đa ~2 s (người xem lướt qua nếu dài).
- **toc_do**: 1,0 mặc định; người nói chậm hoặc người dùng muốn "nhanh gọn" → 1,05–1,15. Không vượt 1,2 với lời nói.
- **giam_on**: bật khi `tom-tat.md` báo ồn nền cao hoặc nghe có quạt/xe; nhắc người dùng nghe lại.
- **mau**: CHỈ khi người dùng cho phép chỉnh màu (luật giữ màu gốc). Nhẹ tay: sang ±0,05, tuong_phan 0,95–1,1, bao_hoa 0,9–1,15.
- **xuat**: hỏi đăng ở đâu. TikTok/Reels/Shorts dùng chung bản dọc. Thêm `"ngang"` cho YouTube thường, `"4x5"` cho bảng tin Facebook.
- **am.sfx_tu_dong**: mặc định bật (tiếng nhẹ khi chữ hiện, "vút" khi hết bìa và khi vào cảnh chèn). Người dùng thấy ồn → tắt.

## 4. Luật bắt buộc (máy tự giữ — không ghi đè)
1. Ảnh bìa phủ kín 0–0,8 s (hồ sơ chỉnh 0,5–1 s); chữ mở đầu hiện từ giây 0,9 → khối mở đầu ghi `"theo":"ra","t0":0.9`.
2. Chữ luôn trong vùng an toàn; không che mặt; cảnh cận mặt đặt dưới cằm; không che động tác (máy dò vùng chuyển động).
   Không vừa chỗ thì máy thu nhỏ, vẫn không được thì báo — khi đó **rút gọn chữ**, không ép vị trí.
3. Âm thanh: giọng nói luôn rõ nhất — nhạc tự nhỏ khi có lời, nhỏ dần cuối video; hiệu ứng nhỏ hơn giọng.
4. Không bịa số, giá, công dụng. Lời nói có số mâu thuẫn (vd "mỗi bên 15 lần" nhưng đếm tới 10) → hỏi người dùng, không tự sửa.
5. Thấy giấy tờ, màn hình có thông tin, hoặc mặt/cơ thể khách trong bảng khung → nhắc người dùng kiểm tra khách đã đồng ý chưa.

## 5. Dựng, tự kiểm, giao
```
dv.py dung <dự án>            (bản thật; --nhap = bản xem nhanh 540p)
```
Đọc `ra/bao-cao.md` và nhìn `ra/xem-lai.jpg`. Mục "Cần người xem lại" có gì → sửa kế hoạch, dựng lại (tối đa 2 lượt).
Giao: đường dẫn video, ảnh bìa `ra/bia.jpg`, 3–5 dòng tóm tắt (dài bao nhiêu, đã bỏ gì, chữ gì) + những chỗ người dùng nên tự xem.
Người dùng chê ("chữ to quá", "cắt mất chữ", "chữ đè tay") → sửa đúng chỗ đó trong `ke-hoach.json` rồi dựng lại.

## 6. Học phong cách từ video mẫu
Khi người dùng đưa video họ thích và nói "học phong cách", "làm giống video này":
1. Hỏi tên phong cách (ngắn, không dấu, vd `soi-dong`) và có **bản thô** của video đó không (có thì học chính xác chỗ cắt).
2. `dv.py hoc <thư mục dự án> --mau <video mẫu> [--tho <bản thô>] --ho-so <tên>` (thư mục dự án lấy từ `dv.py du-an "hoc-<tên>"`).
3. Đọc `hoc/tom-tat-hoc.md`, **nhìn** `hoc/bang-24.jpg` và `hoc/khung-1..5.jpg`. Đọc `tai-lieu/phong-cach.md` rồi viết
   `~/.dung-video/phong-cach/<tên>.json`. Chỉ ghi điều thấy được hoặc đo được; chỗ không chắc (vd có nhạc không) thì hỏi.
4. Báo lại người dùng 4–6 dòng dễ hiểu: cắt thế nào, chữ kiểu gì, màu, nhạc, và **những gì skill chưa làm được** (`khong_lam_duoc`).
   Người dùng sửa → sửa tệp.
5. Dựng theo phong cách: thêm `"phong_cach": "<tên>"` vào kế hoạch; viết khối chữ theo `chu` (mật độ, kiểu, vị trí, viết hoa),
   `lam_toi_the`, `zoom`, `chen_canh`. Danh sách: `dv.py phong-cach ds`.
- Chỉ học **cách làm**. Không chép chữ, câu, logo, mặt, giọng, nhạc của video mẫu; không bắt chước để giả làm kênh khác.
- Luật bắt buộc (mục 4) vẫn thắng phong cách: bìa 0,8 s, chữ không che mặt/động tác, không bịa số.

## 7. Khác
- «Nâng cấp skill» → `dv.py nang-cap` và làm theo hướng dẫn in ra.
- Bước đọc in dòng 🔔 "Đã có bản mới" → báo người dùng một câu ở cuối, không chen ngang việc đang dựng.
- Lỗi lạ → `dv.py kiem-may` trước, rồi đọc thông báo lỗi; nói với người dùng bằng lời dễ hiểu.
- Video gửi đi đâu? Không đâu — mọi thứ chạy trên máy người dùng.
