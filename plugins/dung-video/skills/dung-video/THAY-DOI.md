# Các bản đã phát hành

## 1.4.0
- Tìm ảnh/video minh hoạ miễn phí theo lời nói: Pixabay (mã miễn phí, hộp thoại để tự dán), Pexels (nếu đã có mã),
  Wikimedia Commons khi chưa có mã (chỉ ảnh dùng thương mại được). Ảnh tĩnh tự thành cảnh dọc chuyển động chậm.
- `dv.py them-phu`: thêm cảnh phụ vào dự án đã đọc mà không cần nghe lại lời.
- Thẻ minh hoạ động tự tạo từ biểu tượng Material Symbols (Apache 2.0): `dv.py the-minh-hoa`, dấu nên/không nên/cảnh báo;
  phụ đề tự ẩn khi thẻ hiện.
- Bộ tiếng theo ý nghĩa: dung (nên), sai (không nên), canh-bao, don-nen (dồn lên, đặt trước câu bằng `truoc`), tick, chuong, lap-lanh, bung-tay.

## 1.3.3
- Bàn tay múa trước ngực không còn bị nhận nhầm là khuôn mặt thứ hai (bỏ hộp mờ khi khung đã có mặt rõ; mặt chính = rõ nhất × to nhất).

## 1.3.2
- Cận mặt: khối chữ và phụ đề chỉ đặt dưới cằm (thử giữa, trái, phải). Ngoại lệ `vi_tri: "tren-dau"` khi tay đang thao tác ngay dưới cằm.
- Sticker và hiệu ứng âm thanh bám đúng chữ đang nói (`theo_loi`).
- Vòng sáng khoanh vùng trọng tâm (`vong-sang`): làm tối xung quanh, vòng tự vẽ quanh điểm cần nhìn, nằm dưới chữ.
- `am.sfx_tang`: tăng chung mức hiệu ứng âm thanh.
- Sửa lỗi treo khi dựng lại: tự dọn khung sticker cũ.

## 1.3.1
- Bỏ hộp «mặt» xuất hiện lẻ loi (bàn tay bị nhận nhầm là mặt làm mất chỗ đặt chữ).
- Phụ đề chia nhóm tối đa 5 giây để bám đúng vị trí mặt từng đoạn.
- Chữ trên ảnh bìa tự thu nhỏ đến khi không chạm mặt; khối đã yêu cầu «phía trên» được giữ phía trên.

## 1.3.0
- Lồng tiếng bằng giọng đọc AI chạy trên máy (VieNeu-TTS v3 Turbo, Apache 2.0): 23 giọng Bắc/Trung/Nam, giọng riêng
  (nhân bản, chỉ khi có đồng ý), bảng sửa phát âm chữ nước ngoài, tự ghép nền mỗi câu một cảnh; phụ đề lấy đúng chữ kịch bản.
- Luật "không che mặt" thành luật cứng cho cả khối chữ, phụ đề, sticker, chữ chạy: xét mọi vị trí mặt trong lúc chữ hiện,
  giữ dấu mặt khi người cúi/nghiêng; sticker tìm chỗ khắp vùng an toàn; phụ đề tránh khối chữ, hết chỗ thì tạm ẩn.

## 1.2.0
- Chuyển cảnh: lật 3D, zoom xoáy, lia máy, flash, mờ — đặt ở chỗ đổi ý hoặc lúc vào/ra cảnh chèn.
- Sticker động tự vẽ (không bản quyền): mũi tên, khoanh tròn, gạch chân, lấp lánh, tim, dấu tích, dấu X, huy hiệu có chữ.
  Tự dời chỗ để không che mặt, động tác, chữ.
- Chữ cong theo cung tròn, dải chữ chạy ngang, hiệu ứng chữ xuất hiện (pop, nảy, trượt, gõ từng chữ).

## 1.1.0
- Học phong cách từ video mẫu (kèm bản thô nếu có): đo nhịp cắt, chỗ ngừng, nhạc, phóng to, màu nhấn; AI xem 24 khung để học kiểu chữ.
- Dựng theo phong cách đã học (`"phong_cach"` trong kế hoạch).
- Thêm chữ có chân nghiêng (Playfair Display, giấy phép OFL), dòng nhỏ chữ hoa giãn, làm tối nền khi hiện thẻ chữ, thẻ chỉ có viền.

## 1.0.0 — bản bán đầu tiên
- Chạy được nhánh nhận giọng cho Windows và Mac Intel (faster-whisper), tương thích ffmpeg cũ (5–6).
- Sửa lỗi đường dẫn có dấu nháy đơn (vd tên người dùng Windows).
- Đóng gói dạng plugin Claude Code, cập nhật bằng /plugin.

## 0.3.0
- Logo, intro/outro, phóng to vào mặt, tốc độ, giảm ồn, chỉnh màu (khi được phép), xuất thêm khổ ngang 16:9 và 4:5.

## 0.2.0
- Chèn cảnh minh hoạ (B-roll), nhạc nền tự nhỏ khi có lời (3 kiểu nhạc tự tạo, không bản quyền), hiệu ứng âm thanh tự tạo.

## 0.1.0
- Nghe lời tiếng Việt, cắt khoảng ngừng theo kiểu video (tư vấn / bài tập), chữ chốt ý tránh mặt và động tác,
  phụ đề tô chữ đang nói, ảnh bìa phủ 0,8 s, chuẩn âm lượng −16 LUFS, mã bản quyền ký số.
