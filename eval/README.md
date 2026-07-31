# Eval

## Bộ hiện tại: FastAPI v2

Kiểm tra cấu trúc 59 case mà không gọi model:

```powershell
node eval/run-golden-set-v2.js --dry-run
```

Chạy live trên backend và SQLite tạm, không chạm `backend/data/store.db`:

```powershell
$env:ANTHROPIC_API_KEY="..."
node eval/run-golden-set-v2.js --run-id 2026-07-31
```

Runner tạo `results-v2-<run-id>.json` và `.md`, từ chối ghi đè nếu không có
`--overwrite`. Chấm D2-D6 theo `review-v2-rubric.md`; hai reviewer làm độc lập.

Có thể dùng backend đã seed sẵn:

```powershell
node eval/run-golden-set-v2.js --server-url http://localhost:8020 --run-id local
```

## Checkpoint v1

`golden-set.js`, `run-golden-set.js` và `results-run-{1,2}.*` là bằng chứng lịch sử
cho Express `POST /api/summarize`. Chúng không đại diện cho FastAPI hiện tại.
