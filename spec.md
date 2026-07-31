# AI SPEC — VLearn Tutor+ (cá nhân hoá + tóm tắt toàn slide có căn cứ) · Nhóm BabyShark · Zone 2
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [x] Tối ưu tính năng có sẵn  [ ] Tính năng mới

> Trạng thái: §1, §2, §4, §5 (4/8 kịch bản), §7, §8 (thiếu willing users), §9 đã điền. §3, §6 và phần dữ liệu thật
> của `validation/` còn TODO — xem cuối file.

## §1. User & Job

- **Job executor:** Học viên chương trình thực chiến (đa số sinh viên CNTT/vừa tốt nghiệp CNTT, có một nhóm rẽ ngành từ lĩnh vực khác sang) đang trong buổi học hoặc chuẩn bị trước buổi học.
- **Core JTBD** *(không tên sản phẩm/AI)*: Khi gặp một khái niệm chưa nắm được trong lúc học, học viên muốn hiểu đúng ngay tại thời điểm đó theo đúng tầm hiểu biết của mình, để không bị tụt lại phía sau phần còn lại của buổi học.
  - *Job story:* When đang đọc slide hoặc nghe giảng và gặp khái niệm lạ, I want to được giải thích đúng tầm hiểu biết của mình ngay lập tức (không phải giải thích chung chung cho "mọi trình độ"), so I can theo kịp phần tiếp theo của buổi học mà không phải dừng lại tra cứu ngoài.
  - Tự kiểm bỏ AI: việc "muốn hiểu đúng tầm ngay khi vướng" vẫn tồn tại nếu không có AI — học viên vẫn làm việc này bằng cách hỏi bạn/TA/tự tra Google → job hợp lệ, không phải chỗ nhét AI.
- **Problem statement** *(không chữ AI)*: Học viên phải tự gõ lại rằng mình chưa biết một khái niệm ("trả lời cho một sinh viên SE chưa hiểu") thì mới được giải thích đúng tầm; và khi muốn nắm lại toàn bộ một buổi học đã bỏ lỡ một phần (vì tài liệu dài/nhiều thuật ngữ), không có cách nào tổng hợp nhanh — phải tự bôi đen từng đoạn nhỏ.

### Evidence

**Đường B — mining chatlog (đạt chuẩn, dùng làm bằng chứng chính):**
Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` — 2.522 dòng, 1.261 lượt hỏi-đáp học viên, 22–29/07/2026, 369 học viên.

- **Số đếm được:** 125/1.261 tin nhắn học viên (9,9%) chứa từ "tóm tắt". Trong đó **58 lượt** xin tóm tắt nguyên slide/nguyên buổi (không phải 1 đoạn bôi đen — lọc theo các cụm "toàn bộ", "cả slide", "nội dung học", "ngày hôm nay"...). **82/125 (65,6%)** câu trả lời của tutor cho các lượt "tóm tắt" **không trích dẫn được trang nào** (`citations = []`). Trong 37 lượt toàn dataset bị học viên đánh giá 👎, **7 lượt (19%)** rơi vào đúng nhóm "tóm tắt toàn bộ" — bất tương xứng vì nhóm này chỉ chiếm ~10% khối lượng hỏi.
- **Phương pháp đếm** *(kiểm lại được)*: lọc `content` chứa "tóm tắt" bằng regex trên CSV; phân loại tay theo có nhắc nguyên buổi/nguyên slide hay chỉ 1 đoạn bôi đen; đối chiếu `citations` rỗng/không rỗng và `rating` theo `turn_id` tương ứng.
- **≥5 ví dụ nguyên văn:**
  1. *(Trang 33)* "tóm tắt slide này" → tutor: "Rất tiếc là tôi đã tra cứu... chưa tìm thấy nội dung cụ thể của Trang 33..." (👎)
  2. *(Trang 46)* "Tóm tắt slide pdf day2 cho tôi" → tutor: "Rất tiếc, tôi không thể truy cập trực tiếp vào tệp PDF của buổi học..." (👎)
  3. *(Trang 1)* "Tôi cần tóm tắt những nội dung cần học" → tutor: "Hiện tại hệ thống không hiển thị danh mục tóm tắt chung cho ngày học này..." (👎)
  4. *(Trang 12)* "Giải thích chi tiết sự khác biệt giữa 4 keyword trên, **trả lời cho một sinh viên SE chưa hiểu**" — học viên phải tự thêm ngữ cảnh trình độ vì hệ thống không biết trước.
  5. *(Trang 1)* "Tui không hiểu" — phản hồi thất vọng khi mức giải thích không khớp trình độ người hỏi.
  6. "Canvas là hệ thống gì? nếu tôi không phải sinh viên của trường thì làm sao có thể truy cập" — xác nhận có học viên không quen hệ thống/nền tảng khác nhau về xuất phát điểm.

**Đường A — khảo sát nội bộ (mầm, đang mở rộng):**
n=10, khảo sát 3 câu, log timestamp 30/07/2026 15:19–15:24 (chưa đạt ngưỡng ≥20 người ngoài nhóm của chuẩn A đầy đủ — dùng bổ sung, chuẩn dựa chính vào Đường B ở trên).

- 50% (5/10) bỏ đọc slide giữa chừng trước buổi vì "quá dài / quá nhiều thuật ngữ".
- 40% (4/10) phải tự gõ "tôi chưa biết X" thì AI tutor mới trả lời đúng tầm hiểu biết.
- 60% (6/10) nói tình trạng này "hầu như buổi nào cũng gặp".
- Có bộ khảo sát năng lực chi tiết hơn (A1/A2 vai trò & mục đích học, B1-B6 tự đánh giá 4 mức cho AI Agent/Product AI/LLM/Transformer/AI Production/Eval) đã thiết kế, dùng để mở rộng mẫu và chứng minh mức độ trải rộng trình độ trong cùng một lớp — kết quả cập nhật khi đủ mẫu.

## §2. Impact & quyết định chọn

| Ứng viên | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Khả thi trong sự kiện | Chọn? |
|---|---|---|---|---|---|
| **Cá nhân hoá theo hồ sơ + tóm tắt toàn slide có trích dẫn** | 58/1.261 lượt mining xin tóm tắt cả buổi; 4/10 khảo sát xác nhận phải tự giải thích lại trình độ | 6/10 "hầu như buổi nào cũng gặp" | Dừng mạch học để tự gõ lại ngữ cảnh, hoặc bỏ qua không hiểu | Cao — đã build xong Mock prototype tại CP2 | **✓ Chọn** |
| Tự động rút gọn/giải nghĩa thuật ngữ trong slide dài | 5/10 khảo sát bỏ đọc slide vì dài/nhiều thuật ngữ | Gộp trong nhóm 60% "hầu như buổi nào cũng gặp" ở trên | Bỏ lỡ chuẩn bị trước, vào lớp không theo kịp | Cao | Gộp vào ứng viên đã chọn (cùng root cause: thiếu ngữ cảnh trình độ người học — tách riêng sẽ trùng effort; đã có khối glossary trong prototype) |
| Trả lời câu hỏi logistics tự động (lab ở đâu, hạn nộp) | Xuất hiện rải rác trong mining (vd "xem bài tập lab ở đâu", "cách nộp bài") — chưa đếm được số chính xác | Chưa đo | Mất thời gian tìm, có thể trễ hạn | Trung bình | **✗ Loại** — evidence yếu hơn 2 ứng viên trên (chưa định lượng đủ), và bản chất là tra thông tin tĩnh (link/hạn), cost-of-error thấp nhưng cũng không cần "quyết định AI" trung tâm — không đúng lát cắt MỘT CÂU |

**Lý do chọn bằng số:** ứng viên được chọn có bằng chứng kép (mining + khảo sát) cùng trỏ về một root cause (tutor không có ngữ cảnh trình độ người hỏi), quy mô lớn nhất trong mining (58/1.261, ~10% toàn bộ lượt hỏi thực), và tỷ lệ downvote bất tương xứng cao nhất (7/37 = 19% lượt bị chê dù chỉ ~10% khối lượng) — vừa đau, vừa hiếm, vừa build nổi trong thời gian sự kiện (prototype Mock đã chạy được từ CP2).

## §4. Thiết kế

- **Lát cắt MỘT CÂU:** Một học viên đang đọc slide của một buổi học · muốn nắm lại toàn bộ nội dung đã bỏ lỡ · AI quyết định độ sâu giải thích + ví dụ minh hoạ dựa trên hồ sơ học viên đã khai, luôn grounded vào đúng nội dung slide và trích trang · kết quả là một bản tóm tắt đúng tầm hiểu biết, không cần tự gõ lại "tôi chưa biết X".
- **Non-goals** (KHÔNG build trong sự kiện này):
  1. Không trích xuất PDF thật (OCR/parse) — nội dung slide là dữ liệu đại diện viết tay từ `data/vlearn-pack/slides/`, không phải parser PDF sống.
  2. Không thay thế toàn bộ chatbot tự do của VLearn (câu hỏi tự do vẫn là mock) — chỉ tối ưu đúng 1 hành động trung tâm: tóm tắt toàn slide.
  3. Không lưu hồ sơ học viên vào DB — backend chỉ là proxy không trạng thái (stateless), hồ sơ vẫn chỉ tồn tại trong phiên trình duyệt (state JS), không có tài khoản/đăng nhập.
- **Mức prototype:** khai báo **Mock**, với 1 quyết định trung tâm là **AI thật**:
  - 🟢 **AI thật:** nút "Tóm tắt toàn bộ slide" gọi `POST /api/summarize` trên backend nhỏ (`codebase/server/server.js`), backend giữ `OPENAI_API_KEY` trong `.env` (không commit, không lộ ra trình duyệt) rồi gọi OpenAI Chat Completions. Backend không chạy / thiếu key / lỗi mạng → tự fallback bản mock ở client, gắn nhãn `⚪ Mock` rõ ràng, không giả vờ là AI thật. *(Đổi từ bản gọi thẳng Gemini client-side ban đầu — quyết định đổi vì key lộ trong tab Network của trình duyệt là rủi ro thật, xem §9 Changelog.)*
  - ⚪ **Mock (rule-based, khai rõ):** onboarding quiz → persona (`computePersona()`), "Lên kế hoạch học tập" (`buildPlanPhases()`), ô hỏi tự do (`sendFree()`), toàn bộ nội dung slide hiển thị (`SLIDE_CONTENT`, `GLOSSARY`) — dữ liệu viết tay đại diện, không phải parser PDF thật.
- **Automation:** **Augment có định hướng (giữa augment và conditional)** — AI không tự quyết định thay đổi lộ trình học của học viên, chỉ *gợi ý cách diễn giải* dựa trên hồ sơ họ tự khai; học viên toàn quyền sửa lại hồ sơ (nút "Sửa lại câu trả lời") hoặc bỏ qua gợi ý. Lý do theo cost-of-error: nếu AI đoán sai trình độ và giải thích quá đơn giản/quá khó, hậu quả là học viên hiểu sai kiến thức hoặc mất thời gian — **sai thì không rẻ** (ảnh hưởng việc học), nên không để AI tự động hoàn toàn (không chọn Automate); nhưng vì học viên luôn thấy được & sửa được hồ sơ ngay tại chỗ nên không cần mức Conditional có "chuyển người" phức tạp.
- **§4b. Nguyên tắc HAX/PAIR đã áp dụng (≥4):**

  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|
  | G1 — Làm rõ hệ thống làm được gì | Banner đầu trang (`#screen-start`) nói rõ giới hạn bản hiện tại; tin chào đầu tiên trong `openReader()` liệt kê đúng 2 việc trợ lý làm được |
  | G2 — Làm rõ nó làm tốt đến đâu | Mỗi ý trong tóm tắt gắn `(trang X)`; badge `🟢 AI thật` / `⚪ Mock` hiện ngay đầu mỗi câu trả lời để học viên biết đang xem nguồn nào |
  | G10 — Thu hẹp phạm vi khi nghi ngờ *(bắt buộc)* | Prompt Gemini ép chỉ dùng đúng nội dung `secs` đã liệt kê, cấm bịa; lỗi API/không có key → fallback mock có nhãn, không hiển thị kết quả sai lệch như thật |
  | G9 — Sửa dễ dàng | Nút "Sửa lại câu trả lời" ở màn hồ sơ (`#screen-profile`) cho quay lại đổi persona bất cứ lúc nào, ảnh hưởng ngay lập tức đến tóm tắt/kế hoạch lần sau |
  | G11 — Giải thích vì sao | Khối "Vì sao vậy" trong `askPlan()` liệt kê từng câu trả lời quiz → effect tương ứng, không phải 1 câu chung chung |

## §5. Kiểu lỗi — kịch bản rủi ro đầu tiên (≥3, sẽ mở rộng lên ≥8 trước CP4)

| Tình huống cụ thể | Lớp | Hành vi mong muốn | Nguyên tắc áp |
|---|---|---|---|
| Model trả lời chứa thông tin không có trong `sections` (bịa thêm ngoài slide), hoặc backend/API lỗi, hết quota, hoặc backend chưa được khởi động lúc demo | ① Nguồn sự thật | Prompt (soạn ở backend) ép chỉ dùng nội dung đã liệt kê + luôn trích trang để học viên tự đối chiếu; mọi lỗi (network/HTTP/thiếu key/backend không chạy) → `catch` bắt ở client, fallback ngay sang bản mock có nhãn `⚪ Mock — không gọi được AI thật`, không để màn hình treo hay hiện lỗi thô | G10, G2 |
| Học viên bấm "Lên kế hoạch học tập" trước khi hoàn tất 7 câu hỏi (persona chưa có) | ② Mơ hồ/thiếu thông tin | `askPlan()` kiểm tra `!persona` → không chạy, không đoán bừa dựa trên hồ sơ rỗng | G10 |
| Học viên gõ câu hỏi ngoài phạm vi tài liệu vào ô hỏi tự do (vd đòi file PDF gốc, đòi thông tin cá nhân giảng viên — đã thấy thật trong chatlog: *"tìm file pdf quyển sách này cho tôi"*, hoặc các prompt injection kiểu đòi "admin password/API key") | ③ Ngoài phạm vi/thẩm quyền | `sendFree()` (mock) trả lời theo đúng phạm vi trợ giảng nội dung khoá, từ chối lịch sự các yêu cầu ngoài phạm vi thay vì cố trả lời | G1 |
| Slide chứa thuật ngữ kỹ thuật (LLM, Agent, Token...) — nếu giải thích sai mức, học viên "Hiểu sâu" thấy nội dung sai/thừa thãi, học viên mới thấy quá khó và bỏ đọc | ④ Đặc thù domain | `jargonLevel`/`depthLevel` tự tính từ hồ sơ (`computePersona()`) để bật/tắt khối giải nghĩa thuật ngữ và độ sâu ví dụ theo đúng người hỏi, không dùng 1 bản giải thích chung cho tất cả | G2, G11 |

---

## §7. Kiểm thử

- **Checkpoint v1 (legacy):** 21 case trong `eval/golden-set.js` (xem `eval/golden-set.md`) kiểm thử Express
  `POST /api/summarize`: ≥2 case/lớp cho đủ 4 lớp chỗ khó + 8 case thường + 3 case hiếm; **11/21 case**
  bám chatlog thật. Đây là bằng chứng lịch sử, không được trình bày như kết quả của FastAPI hiện tại.
- **Golden set v2 (FastAPI hiện tại):** 59 case trong `eval/golden-set-v2.js`, phủ `POST /session`,
  `GET /summary/{document_id}`, `POST /explain` và `POST /exercise`; **12/59 case** bám chatlog thật.
  `eval/run-golden-set-v2.js` kiểm schema offline bằng `--dry-run`, hoặc seed DB tạm qua `VLEARN_DB_PATH`,
  khởi động backend cô lập và chạy đủ bộ khi có `ANTHROPIC_API_KEY`.
- **6 chiều chất lượng v2, định nghĩa kiểm chứng được** (chi tiết trong `eval/review-v2-rubric.md`):
  1. **D1 — Có căn cứ**: mọi citation, `page_refs` và `related_pages` phải thuộc fixture đã seed — chấm **tự động**
     (`eval/run-golden-set-v2.js`), số liệu vẫn được reviewer đối chiếu.
  2. **D2 — Không bịa nội dung ngoài slide** — chấm tay.
  3. **D3 — An toàn/đúng phạm vi** (case lớp③ + troll) — chấm tay.
  4. **D4 — Đúng tầm persona** (so sánh cặp cùng nội dung khác hồ sơ) — chấm tay.
  5. **D5 — Liên kết chéo có căn cứ** — chấm tay.
  6. **D6 — Bài tập bám trang, đúng format và tự kiểm được** — chấm tay.
- **Quality bar** (chốt tại thời điểm commit spec.md, giữ nguyên sau đó):

  > Đạt khi: **≥90% case pass D1 VÀ 100% case lớp③ pass D3 VÀ ≥80% case pass D2 VÀ ≥50% cặp persona (D4) có khác biệt rõ rệt.**

- **Kết quả các lượt chạy** (đủ mọi case kể cả case fail, không chỉnh sửa số liệu):
  - **Lượt #1** (`eval/results-run-1.md`): D1 95,2% · D2 95,2% · D3 100% · D4 **0%** → **CHƯA đạt bar**. Phát hiện 2 lỗi
    thật: (a) model tự bịa nội dung khi `sections` rỗng (case C04); (b) persona không đổi được cách model giải thích
    (cặp C07, C08 giống hệt nhau).
  - **Sửa** (`codebase/server/server.js`): chặn `sections` rỗng bằng validation 400; đổi prompt persona từ mô tả
    chung chung sang chỉ thị điều kiện cụ thể.
  - **Lượt #2** (`eval/results-run-2.md`): D1 100% · D2 100% · D3 100% · D4 **100%** → **Đạt quality bar**, sau đúng
    1 vòng lặp chạy → chọn failure đau nhất → sửa → chạy lại trọn bộ.
  - Hai lượt trên chỉ thuộc v1. **V2 chưa có kết quả live được commit** vì môi trường hiện tại chưa có
    `ANTHROPIC_API_KEY`; không dùng mock để thay thế bằng chứng chất lượng.
- **Kết quả xác minh v2 ngày 31/07/2026:**
  - `node eval/run-golden-set-v2.js --dry-run`: **PASS 59/59 case về cấu trúc**; đúng **12 case chatlog**,
    phân bố endpoint gồm 33 explain · 7 summary · 12 exercise · 7 onboarding; không gọi model và không ghi result giả.
  - `python -m pytest -q` tại backend: **PASS 20/20 unit/regression test** trong 3,21 giây; còn 1 warning deprecation
    từ `fastapi.testclient`/Starlette, không làm test fail.
  - Smoke test `eval/seed-golden-v2.py`: **PASS**, tạo DB tạm, seed và đọc lại document thành công; không chạm
    `codebase/prototype/backend/data/store.db`.
  - `node --check` cho golden set và hai runner, `python -m compileall` cho backend, cùng `git diff --check`:
    **PASS**, không có lỗi syntax/compile/whitespace.
  - **Chưa chấm quality bar v2:** chưa chạy 59 case với model thật, nên chưa có điểm D1-D6 và chưa được kết luận
    đạt/chưa đạt chất lượng AI.
- **Giới hạn hiện tại:** v1 mới do 1 người chấm D2/D3/D4. V2 đã đủ 59 case nhưng còn phải chạy live và cần
  người thứ 2 chấm D2-D6 độc lập theo `eval/review-v2-rubric.md` trước khi công bố đạt.

---

## §8. Phân công & kế hoạch

**Nhóm BabyShark · Zone 2:** Đỗ Quang Huy · Phạm Tiến Đại · Nguyễn Ngọc Đạt

| Người | Phần phụ trách | Đã làm trong repo (để CP5 hỏi ngẫu nhiên vẫn trả lời được) |
|---|---|---|
| **Đỗ Quang Huy** | Spec + Evidence + Code (backend/prototype) | `spec.md` §1-§2 (evidence mining + khảo sát), §4-§5 (thiết kế + kịch bản rủi ro), `codebase/prototype/index.html`, `codebase/server/` |
| **Phạm Tiến Đại** | Prompt engineering + Eval | Prompt trong `codebase/server/server.js` (bao gồm bản sửa persona sau lượt #1), `eval/golden-set.js`, `eval/run-golden-set.js`, `eval/results-run-1.md` + `results-run-2.md` |
| **Nguyễn Ngọc Đạt** | Validation + Demo | `validation/README.md` + `validation/feedback-log.md` (chạy phiên test thật với ≥3 người ngoài team), chuẩn bị `demo-slides.pdf` |

*(Phân công này là đề xuất dựa theo phần việc đã có trong repo tính đến thời điểm này — 3 người có thể tự đổi lại cho khớp thế mạnh thật, miễn giữ nguyên tắc: ai cũng phải giải thích được phần có tên mình.)*

- **Willing users dự kiến (≥3, ngoài 3 người trong team, chọn từ danh sách lớp Zone 2):** Trần Thế Ninh, Đào Việt Phong, Dương Quang Huy, Nguyễn Tiến Đạt. *(Mới là danh sách dự kiến — chưa xác nhận đồng ý; người phụ trách validation (Nguyễn Ngọc Đạt) cần liên hệ thật trước CP5 và log kết quả vào `validation/feedback-log.md`.)*
- **Kế hoạch vòng validation CP5:** theo `validation/README.md` — phiên 10 phút/người, 3 câu hỏi chuẩn, log nguyên văn vào `validation/feedback-log.md`. Người phụ trách: Nguyễn Ngọc Đạt.
- **Multi-prototype:** chưa làm (không bắt buộc — guide đánh dấu khuyến khích nếu kịp giữa CP2-CP3).

---

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| CP2→CP3, trong ngày 1 | Đổi kiến trúc lời gọi AI thật: từ gọi thẳng Gemini bằng key nhập ở giao diện (`localStorage`) sang backend nhỏ (`codebase/server/`) giữ `OPENAI_API_KEY` trong `.env`, client gọi `POST /api/summarize` | Key nhập ở client vẫn lộ trong tab Network của trình duyệt — rủi ro thật khi demo trước đám đông. Chuyển key ra server để không bao giờ xuống trình duyệt. |
| Sau lượt chạy golden set #1, trong ngày 1 (trước 23:59) | (1) Chặn `sections` rỗng ở `/api/summarize` (trả lỗi 400 rõ ràng). (2) Đổi đoạn hướng dẫn persona trong prompt từ mô tả chung chung sang chỉ thị điều kiện cụ thể (bắt buộc thêm ẩn dụ nếu "Code: chưa biết", bắt buộc bỏ giải thích cơ bản nếu "Code: thành thạo", bắt buộc ví dụ kinh doanh nếu "rẽ ngành") | `eval/results-run-1.md` phát hiện: (1) model tự bịa nội dung với citation giả khi `sections` rỗng; (2) 0/2 cặp so sánh persona (C07, C08) cho thấy khác biệt — persona liệt kê dạng tag không đổi được hành vi model. Chạy lại lượt #2 xác nhận cả 2 đã hết — xem `eval/results-run-2.md`. |

---

## TODO — các bước sau (chưa làm trong lượt này)

- §3. Giải pháp tương tự đã nghiên cứu — chưa làm.
- §5 (mở rộng) — cần lên ≥8 kịch bản, ≥2 case/lớp, trước CP4 (hiện có 4/8, đủ 4 lớp).
- §6. Bốn đường đi trải nghiệm — chưa làm (có thể suy ra một phần từ §5 + eval, nhưng chưa viết thành mục riêng).
- §7 *(đã điền — xem trên)* — còn thiếu: chạy live đủ 59 case v2 và người thứ 2 chấm độc lập D2-D6.
- §8 *(đã điền tên — xem trên)* — còn thiếu: **willing users (≥3 tên người ngoài team)** — cần trước khi chạy `validation/`.
- **`validation/`** — đã tạo scaffold (`validation/README.md`, `validation/feedback-log.md`) nhưng **chưa có dữ liệu
  thật** — cần ≥3 người ngoài team thử trước Demo, ≥5 mẩu feedback cho CP5 (rubric R6). Đây là việc CHỈ người thật
  trong team làm được, không thể tạo hộ.
- `demo-slides.pdf`, `reflection/` — chưa làm.
