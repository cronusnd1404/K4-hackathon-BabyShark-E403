# AI SPEC — VLearn Tutor+ (cá nhân hoá + tóm tắt toàn slide có căn cứ) · Nhóm BabyShark · Zone 2
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [x] Tối ưu tính năng có sẵn  [ ] Tính năng mới

> Trạng thái: §1, §2, §4, §5, §7, §8 (thiếu willing users), §9 đã điền. §3, §6 và phần dữ liệu thật của `validation/`
> còn TODO — xem cuối file. **Ưu tiên cao nhất: chưa có golden set nào chạy thật trên backend, xem §7.**
> Prototype = duy nhất `codebase/prototype/backend/` (FastAPI + Claude) + `codebase/prototype/frontend/` (React) —
> bản mock cũ (`index.html` + `codebase/server/`) đã bị xoá khỏi repo sau khi hoàn thành vai trò của nó (chứng minh
> lát cắt bấm được ở CP2/CP3); lịch sử vẫn xem lại được qua `git log`.

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

Prototype: `codebase/prototype/backend/` (FastAPI + Claude) + `codebase/prototype/frontend/` (React).

- **Lát cắt MỘT CÂU:** Một học viên đang xem một tài liệu bài giảng đã tải lên hệ thống · muốn nắm lại toàn bộ nội dung
  mình đã bỏ lỡ mà không phải đọc lại tuyến tính từ đầu · AI quyết định cấu trúc + nội dung của một cây tóm tắt phân cấp
  (tối đa 3 tầng, mỗi nhánh gắn số trang cụ thể) dựng từ đúng nội dung PDF đã trích xuất — rồi khi học viên bấm vào một
  nhánh, AI giải thích nhánh đó theo đúng hồ sơ năng lực đã khai (mức thuật ngữ, ví dụ minh hoạ) · kết quả là một mindmap
  bấm-để-đào-sâu, mỗi lần giải thích đều trích trang và liệt kê trang liên quan khác để tự kiểm.
- **Non-goals** (KHÔNG build trong sự kiện này):
  1. Chưa nối vào đúng data pack VLearn thật (`data/vlearn-pack/slides/`) — hiện `backend/data/raw_pdfs/` đang chứa
     12 PDF môn Data Mining dùng làm dữ liệu demo/test lúc build (**cần thay bằng slide thật của khoá trước khi nộp
     bản cuối/demo chính thức — xem cảnh báo ở TODO**).
  2. Chưa hỗ trợ nhiều tài liệu song song qua sidebar — "Day02"/"Day03" hiện bị khoá cứng (`disabled` trong
     `MainScreen.jsx`), chỉ 1 tài liệu mẫu (`SAMPLE_PDF_FILENAME`) chạy được.
  3. Không có tài khoản/đăng nhập, không lưu lịch sử qua nhiều lần mở app — `session_id` chỉ sống trong 1 lần tải
     trang (state React `App.jsx`); sửa lại câu trả lời onboarding chỉ làm được bằng nút "Quay lại" **trong lúc** đang
     trả lời khảo sát, không sửa được sau khi đã vào màn chính.
- **Mức prototype:** khai báo **Working** (không còn là Mock) — pipeline chạy thật đầu-cuối: ingest PDF thật
  (`pymupdf`, fallback vision model cho trang ảnh) → lưu SQLite (`store.db`) → gọi Claude thật ở nhiều điểm quyết định:
  - 🟢 **AI thật (Claude, `claude-haiku-4-5-20251001`, `codebase/prototype/backend/core/llm_client.py`):**
    1. **Trung tâm theo lát cắt:** `GET /summary/{document_id}` (`tree_summary.py`) — sinh cây tóm tắt phân cấp từ
       toàn bộ nội dung đã ingest, ép model chỉ dùng nội dung đã cho ("Based SOLELY on the content of the following
       pages").
    2. `POST /explain` (`deep_explain.py`, mode `node` hoặc `highlight`) — giải thích 1 nhánh mindmap hoặc 1 đoạn bôi
       đen, cá nhân hoá theo `background` (chuỗi build từ onboarding), luôn trích `[Page X]` + liệt kê trang liên quan.
    3. `POST /exercise` — sinh bài tập thực hành theo yêu cầu tự do, phù hợp trình độ.
    4. `describe_page_with_vision_model` trong lúc ingest — mô tả trang ảnh/biểu đồ khi PDF không có text layer.
  - ⚪ **Mock duy nhất còn lại:** nguồn PDF demo (12 file Data Mining thay vì slide VLearn thật) — không phải mock
    hành vi AI, mà là mock *nguồn dữ liệu đầu vào*.
- **Automation:** **Augment** — mọi giải thích/tóm tắt đều do học viên chủ động bấm (bấm node mindmap, hoặc yêu cầu bài
  tập), AI không tự động đẩy nội dung. Lý do cost-of-error: một cây tóm tắt/giải thích sai lệch có thể khiến học viên
  hiểu sai kiến thức nền — **sai thì không rẻ** — nên giữ augment (chờ người bấm) thay vì tự động tóm tắt toàn bộ khi
  vừa mở tài liệu; nhưng bên trong mỗi lần giải thích, mô hình được ép grounded chặt (gần Conditional ở cấp prompt: chỉ
  "tự tin" trả lời khi có nội dung nguồn, còn lại phải nói rõ không có).
- **§4b. Nguyên tắc HAX/PAIR đã áp dụng (≥4):**

  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|
  | G2 — Làm rõ nó làm tốt đến đâu | Mọi kết quả `/explain` đều có khối "Related Pages" + trích `[Page X]` (`build_explain_prompt` trong `deep_explain.py`) — học viên tự đối chiếu với slide gốc |
  | G10 — Thu hẹp phạm vi khi nghi ngờ *(bắt buộc)* | `TREE_PROMPT`: "Based SOLELY on the content of the following pages" (`tree_summary.py`); `JARGON_INSTRUCTION` ép chú thích mọi thuật ngữ lạ ngay khi dùng, không giả định học viên đã biết (`deep_explain.py`) |
  | G8 — Gạt bỏ dễ dàng | `MindmapPopup`/`ExercisePopup` là popup có nút đóng (`×`) tường minh, không chặn luồng chính, học viên có thể bỏ qua bất cứ lúc nào mà không mất gì |
  | G11 — Giải thích vì sao | Mỗi trang liên quan trong "Related Pages" có `reason` (1 dòng lý do liên quan) đi kèm, không chỉ liệt kê số trang trơ |

  *Gap còn lại (chưa đạt, ghi nhận trung thực thay vì che):* **G1** (chưa có màn giới thiệu rõ hệ thống làm được gì
  trước khi vào onboarding) và **G9 đầy đủ** (sửa hồ sơ chỉ làm được trong lúc đang khảo sát, không sửa được sau khi
  vào MainScreen) — cả hai là việc nên làm trước CP5 nếu còn thời gian.

## §5. Kiểu lỗi — kịch bản rủi ro đầu tiên (≥4, sẽ mở rộng lên ≥8 trước CP4)

| Tình huống cụ thể | Lớp | Hành vi mong muốn | Nguyên tắc áp |
|---|---|---|---|
| Claude bịa nội dung không có trong các trang đã ingest khi trả lời `/summary` hoặc `/explain` (đặc biệt dễ xảy ra nếu 1 trang bị OCR/vision-model mô tả sai) | ① Nguồn sự thật | `TREE_PROMPT`/`build_explain_prompt` ép "Based SOLELY on the content of the following pages" + luôn yêu cầu trích `[Page X]` để học viên tự đối chiếu với `PdfViewer` cạnh bên | G10, G2 |
| Gọi Claude lỗi (401/429/timeout) khi đang ingest 1 trang cần vision-model, hoặc khi gọi `/explain`, `/exercise` — **gap đã xác nhận thật**: `ingest()` không bắt lỗi, cả PDF ingest fail hoàn toàn (đã tự gặp lỗi này khi test với key sai, xem §9); `handleExplainPending`/`handleExplainNode` ở frontend (`MainScreen.jsx`, `MindmapPopup.jsx`) dùng `try/finally` **không có `catch`** → lỗi rơi vào unhandled promise rejection, học viên không thấy thông báo gì, chỉ thấy loading tắt im lặng | ① Nguồn sự thật | *(mong muốn, CHƯA đúng thực tế — cần sửa trước CP4)*: bắt lỗi ở cả 2 phía, hiện banner rõ ràng thay vì im lặng hoặc 500 thô | G10, G2 |
| Học viên bấm vào 1 node mindmap hoặc bôi đen đoạn văn khi `session_id` chưa có / đã hết hạn phiên (đóng tab, mở lại) | ② Mơ hồ/thiếu thông tin | `App.jsx` bắt buộc onboarding trước khi vào `MainScreen` (`if (!sessionId) return <Onboarding/>`) — không có đường nào gọi `/explain` mà thiếu `sessionId`; backend cũng tự trả 404 "Unknown session_id" nếu ai cố gọi thẳng API | G10 |
| Học viên gõ yêu cầu bài tập ngoài phạm vi tài liệu (vd đòi đề thi thật, đòi giải hộ bài tập môn khác) vào ô tự do trong `ExercisePopup` | ③ Ngoài phạm vi/thẩm quyền | `build_exercise_prompt` chỉ đưa đúng `slide_content` của trang hiện tại làm ngữ cảnh — Claude không có gì ngoài phạm vi đó để "giúp" thêm; cần thêm case golden set kiểm tra hành vi từ chối cụ thể (chưa có, xem TODO) | G10 |
| Slide chứa thuật ngữ kỹ thuật — học viên "chưa biết" thấy giải thích thiếu chú giải, học viên "hiểu sâu" thấy bị giải thích lại cái đã biết, gây khó chịu | ④ Đặc thù domain | `JARGON_INSTRUCTION` trong `_system_prompt(background)` (`deep_explain.py`) ép chú giải mọi thuật ngữ lạ ngay khi dùng dựa theo đúng `background` build từ onboarding — áp dụng cho mọi lượt `/explain`/`/exercise`, không phải 1 bản giải thích chung | G2, G11 |

---

## §7. Kiểm thử

> ⚠️ **Chưa có golden set nào chạy được thật trên `codebase/prototype/backend/`.** Bản golden set trước đó
> (`eval/golden-set.js`, đã xoá cùng đợt dọn code — xem §9 Changelog) test một backend khác đã không còn tồn tại.
> `eval/golden-set-v2.js` (60 case, Phạm Tiến Đại/Nguyễn Ngọc Đạt) hiện có trong repo nhưng viết cho payload/tên file
> khác với `main.py` thật (xem TODO) — **cần sửa xong rồi chạy trước khi §7 này có số liệu thật.** Đây là việc ưu
> tiên cao nhất còn lại cho R4 (15đ) + R5 (8đ).

- **Golden set dự kiến:** `eval/golden-set-v2.js`, 60 case theo đúng 4 lớp chỗ khó, nhắm 4 endpoint thật
  (`/session /explain /summary/:id /exercise`) — cần sửa payload cho khớp `main.py` (§4 non-goal, TODO) trước khi
  chạy được.
- **4 chiều chất lượng dự kiến áp dụng** (giữ nguyên định nghĩa đã kiểm chứng độ rõ từ bản trước, chỉ đổi đối tượng
  test):
  1. **D1 — Có căn cứ**: mọi `[Page X]` trích trong `/explain`, `/summary` phải nằm trong tập trang đã ingest — chấm
     tự động được (so `related_pages`/`page_refs` với `db.get_pages()`).
  2. **D2 — Không bịa nội dung ngoài slide** — chấm tay.
  3. **D3 — An toàn/đúng phạm vi** — chấm tay.
  4. **D4 — Đúng tầm persona** (so sánh cặp cùng nội dung khác `background`) — chấm tay.
- **Quality bar** (chốt tại thời điểm commit spec.md, giữ nguyên sau đó):

  > Đạt khi: **≥90% case pass D1 VÀ 100% case pass D3 VÀ ≥80% case pass D2 VÀ ≥50% cặp persona (D4) có khác biệt rõ rệt.**

- **Kết quả các lượt chạy:** chưa có — sẽ cập nhật ngay khi golden-set-v2 chạy được trên backend thật (xem TODO).
  *(Bản trước đã từng đo được thật trên backend cũ: lượt 1 phát hiện AI bịa nội dung khi thiếu input + persona không
  đổi được cách giải thích, lượt 2 sau khi sửa đạt cả 4 tiêu chí — quy trình `chạy → sửa → chạy lại` này áp dụng y hệt
  cho backend hiện tại, xem lịch sử git nếu cần tham khảo cách làm.)*

---

## §8. Phân công & kế hoạch

**Nhóm BabyShark · Zone 2:** Đỗ Quang Huy · Phạm Tiến Đại · Nguyễn Ngọc Đạt

| Người | Phần phụ trách | Đã làm trong repo (để CP5 hỏi ngẫu nhiên vẫn trả lời được) |
|---|---|---|
| **Đỗ Quang Huy** | Spec + Evidence | `spec.md` §1-§2 (evidence mining + khảo sát), §4-§5 (thiết kế + kịch bản rủi ro) |
| **Phạm Tiến Đại** | Prototype (backend + frontend) | `codebase/prototype/backend/` (FastAPI + Claude: ingest PDF, tree summary, explain, exercise), `codebase/prototype/frontend/` (React) — **lát cắt được chấm chính thức, §4** |
| **Nguyễn Ngọc Đạt** | Eval mở rộng + Validation + Demo | `eval/golden-set-v2.js` (60 case — cần adapter để chạy được trên backend thật, xem §7), `validation/README.md` + `validation/feedback-log.md` (chạy phiên test thật với ≥3 người ngoài team), chuẩn bị `demo-slides.pdf` |

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
| Sau khi merge nhánh `Dai_Contribute`, trong ngày 1 | (1) Sửa bug `ingest_document()` trong `core/ingest.py`: giờ kiểm tra path cached còn tồn tại trên đĩa không trước khi tin cache, không thì ingest lại. (2) Đổi lát cắt chính thức của §4 từ bản `index.html`/`codebase/server/` sang bản `codebase/prototype/backend/`+`frontend/` | (1) `store.db` commit sẵn có 1 dòng trỏ path tuyệt đối trên máy Đại (`D:\Project_Vin\vlearn-react\...`) — máy khác load PDF bị 404 "Failed to load PDF file." dù `/ingest` báo thành công. (2) Bản của Đại đầy đủ hơn hẳn (ingest PDF thật, mindmap, explain theo trang, exercise) và là bản team thực sự sẽ demo — spec.md phải mô tả đúng bản đang chạy để không mất điểm R5 "mức prototype khai báo khớp thực tế". |
| Ngay sau đó, cùng ngày 1 | **Xoá hẳn** `codebase/prototype/index.html`, `codebase/server/` và bộ eval cũ tương ứng (`eval/golden-set.js`, `golden-set.md`, `run-golden-set.js`, `results-run-1/2.json/.md`) khỏi repo | Prototype đã chốt là bản của Đại (dòng trên) — giữ song song 2 bản gây rối cho người đọc và có thể bị chấm nhầm "mức prototype khai báo không khớp thực tế" (R5). Lịch sử/phương pháp vẫn xem lại được qua `git log` nếu cần. |

---

## TODO — các bước sau (chưa làm trong lượt này)

- §3. Giải pháp tương tự đã nghiên cứu — chưa làm.
- §5 *(đã viết lại theo backend thật — 5 kịch bản, xem trên)* — mở rộng lên ≥8, ≥2 case/lớp, trước CP4; ưu tiên vá
  gap error-handling đã phát hiện (`/explain` không có `catch` ở frontend, ingest không bắt lỗi LLM).
- §6. Bốn đường đi trải nghiệm — chưa làm.
- **§7 — golden set chưa khớp backend thật, đây là việc ưu tiên nhất cho R4+R5:**
  - Cần adapter chuyển persona `{answers:{...}}` của `golden-set-v2.js` sang đúng 8 field `role/goal/level_*` mà
    `POST /session` thật cần, và đổi tên file PDF test cho khớp `backend/data/raw_pdfs/` thật (hoặc thay bằng slide
    VLearn thật — xem non-goal #1 ở §4).
  - Sau khi adapter xong: viết `eval/run-golden-set-v2.js` (theo mẫu `eval/run-golden-set.js`), chạy thật, ghi
    `eval/results-v2-run-1.md`.
  - Vẫn cần người thứ 2 chấm độc lập D2/D3/D4 cho cả 2 bộ.
- §8 *(đã điền tên + phân công lại theo lát cắt mới — xem trên)* — còn thiếu: **willing users (≥3 tên người ngoài
  team)** — cần trước khi chạy `validation/`.
- **`validation/`** — đã tạo scaffold (`validation/README.md`, `validation/feedback-log.md`) nhưng **chưa có dữ liệu
  thật** — cần ≥3 người ngoài team thử trước Demo, ≥5 mẩu feedback cho CP5 (rubric R6). Đây là việc CHỈ người thật
  trong team làm được, không thể tạo hộ.
- **Trước khi nộp bản cuối:** thay 12 PDF Data Mining trong `backend/data/raw_pdfs/` bằng slide VLearn thật
  (`data/vlearn-pack/slides/`), và cân nhắc bỏ `store.db` khỏi git tracking (nguyên nhân bug vừa sửa — vẫn chưa
  quyết định, xem hội thoại trước).
- `demo-slides.pdf`, `reflection/` — chưa làm.
