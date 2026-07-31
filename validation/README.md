# Validation với người dùng thật

> **Chưa có dữ liệu thật trong thư mục này.** Đây là scaffold (kịch bản phiên test + bảng log rỗng)
> chuẩn bị sẵn để team chạy với người thật — tôi (AI) không tự tạo ra phản hồi giả ở đây, vì rubric R6 và
> luật chung của sự kiện yêu cầu ghi nhận trung thực, số liệu bịa/chỉnh sửa sẽ không được tính điểm.

## Cần làm (theo `02-guide.md` §4.2 + rubric R6)

- **≥3 người thật ngoài team đồng ý thử trước Demo** (tiêu chí nghiệm thu #5 trong `01-de-bai.md`) — danh sách dự
  kiến đã có ở `spec.md` §8, **cần liên hệ thật và xác nhận trước khi dùng**.
- **≥5 mẩu feedback** có tên/vai + quote nguyên văn cho CP5 (rubric R6 — 8 điểm).
- Cách nhanh nhất theo guide: đổi chéo với nhóm khác trong zone, hoặc thành viên zone khác — ai cũng là user thật của khoá.

## Cách chạy 1 phiên (10 phút/người, theo guide §4.2)

1. **Chuẩn bị:** chạy `uvicorn main:app --port 8020` trong `codebase/prototype/backend/` (cần `.env` có
   `ANTHROPIC_API_KEY` thật), và `npm run dev` trong `codebase/prototype/frontend/` — đưa `http://localhost:5173`
   cho người thử.
2. **Giao task thật:** "Hãy dùng cái này để tóm tắt lại 1 buổi học bạn từng bỏ lỡ hoặc thấy khó hiểu."
3. **Im lặng quan sát** — không thuyết minh, không gợi ý. Ghi lại: họ bấm gì, kẹt ở đâu.
4. **Hỏi đúng 3 câu sau khi họ dùng xong:**
   - "Điều gì khó hiểu hoặc khó chịu nhất?"
   - "Kết quả này bạn có tin không — vì sao?"
   - "Bạn có dùng thật không — vì sao / vì sao chưa?"
5. **Log nguyên văn** vào `validation/feedback-log.md` (mẫu bảng có sẵn) — không diễn giải lại, chép đúng câu họ nói.

## File trong thư mục này

- `feedback-log.md` — bảng log rỗng, điền sau mỗi phiên thật.
- Sau khi có ≥1 thay đổi rút ra từ feedback (hoặc quyết định giữ nguyên có lý do), cập nhật `spec.md` §9 Changelog.
