# Deploy VLearn Tutor+ lên internet

## Cách đơn giản nhất: 1 service duy nhất trên Render

FastAPI tự phục vụ luôn bản build tĩnh của React (`frontend/dist`) — không
cần Vercel, không cần CORS, không cần đồng bộ URL giữa 2 nơi. Đã setup sẵn
trong code ([main.py](backend/main.py) mount `StaticFiles` ở cuối file,
[api.js](frontend/src/api.js) tự dùng path tương đối khi build production).

### Điều kiện cần trước

- Code đã push lên GitHub.
- Cần **tài khoản GitHub có quyền đọc repo này** để liên kết OAuth với
  Render — có thể không phải tài khoản git CLI đang dùng trên máy.
- Anthropic API key thật (**không commit vào repo** — dán trực tiếp vào
  dashboard Render).

### Các bước

1. Vào [render.com](https://render.com) → **New** → **Web Service** → chọn
   repo GitHub này (liên kết tài khoản GitHub nếu chưa).
2. Điền cấu hình:

   | Trường | Giá trị |
   |---|---|
   | **Root Directory** | `codebase/prototype` |
   | **Runtime** | Python 3 |
   | **Build Command** | `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build` |
   | **Start Command** | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | **Health Check Path** | `/healthz` |
   | **Instance Type** | Free (đủ cho demo) |

3. Tab **Environment** → thêm biến:

   | Key | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | key thật của bạn |
   | `LLM_MODE` | `dev` (Haiku, rẻ) hoặc `demo` (Opus, có fallback Sonnet) |
   | `PYTHON_VERSION` | `3.10.6` |
   | `NODE_VERSION` | `20` (hoặc mới hơn — cần cho bước `npm run build`) |

4. Bấm **Create Web Service** — Render build cả backend lẫn frontend rồi
   deploy (~3-5 phút, lâu hơn deploy Python thường vì có thêm bước `npm
   install && npm run build`).
5. Xong sẽ có 1 URL duy nhất, ví dụ `https://<tên-app>.onrender.com` —
   **mở thẳng URL đó là dùng được app**, không cần domain thứ hai.

### Kiểm tra

- `https://<tên-app>.onrender.com/healthz` → `{"status":"ok"}`.
- `https://<tên-app>.onrender.com/` → load được giao diện VLearn Tutor+
  (không phải JSON).
- `https://<tên-app>.onrender.com/pdfs` → danh sách 13 file PDF.
- Mở app → làm onboarding → chọn slide → hỏi chat → tạo quiz → nộp bài, đều
  phải chạy được, không lỗi CORS/network trong Console (vì giờ cùng origin,
  vốn dĩ không thể có lỗi CORS nữa).

### Lưu ý

- **SQLite là ephemeral trên free tier:** mỗi lần Render redeploy hoặc app
  "ngủ" rồi tỉnh lại (free tier tự ngủ sau ~15 phút không traffic), ổ đĩa
  tạm bị xoá → `store.db` mất, PDF phải ingest lại (tự động, chỉ chậm lần
  đầu), session/quiz cũ mất theo. Chấp nhận được cho demo; cần bền vững lâu
  dài thì nâng cấp gói có Persistent Disk hoặc đổi sang Postgres.
- Request đầu tiên sau khi app "ngủ" có thể mất 20-30s để tỉnh dậy — bình
  thường, không phải lỗi.
- Chi phí: Render free tier = **$0**. Chi phí thực tế duy nhất là
  **Anthropic API usage**, theo dõi ở Anthropic Console.

## Phương án khác: 2 service riêng (Render + Vercel)

Chỉ cần nếu muốn scale/deploy độc lập frontend và backend (không cần thiết
cho demo hackathon). Backend deploy y hệt phần trên nhưng **bỏ** bước build
frontend trong Build Command. Frontend deploy riêng lên Vercel:

- Root Directory: `codebase/prototype/frontend`
- Framework Preset: Vite (auto-detect)
- Environment Variable: `VITE_API_BASE=https://<url-backend-render>` (không
  có dấu `/` cuối)

`api.js` đã hỗ trợ sẵn override qua `VITE_API_BASE` nếu chọn hướng này.
