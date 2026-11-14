# Báo cáo cá nhân — Ngô Hồng Hoàng (2A202604093, L3B)

## Dữ liệu và pipeline

- **Chủ đề/nguồn:** *2020 Taiwan Tourism Guide Book*, bản PDF do tôi cung cấp cục bộ, có tại [trang tải](https://taiwan.net.vn/download). [Thông báo bản quyền](https://eng.taiwan.net.tw/m1.aspx?sNo=0042571) không cấp quyền tái phân phối PDF; vì vậy repo chỉ có manifest và hướng dẫn tải, không đăng PDF hoặc trace nguyên văn.
- **Trang:** 48 trang vật lý, chọn 35 trang nội dung 2–5 và 7–37, 71.620 ký tự chuẩn hóa. Trang bìa, trang ít nội dung và phần quảng cáo không tính. Số trang trong gold là trang vật lý; manifest ghi số ký tự, SHA-256 và category từng khoảng trang.
- **Chuẩn hóa:** `pypdf`, Unicode/whitespace; không OCR ảnh. Một số ngắt từ trong PDF còn lỗi.
- **Embedding/store:** local `sentence-transformers/all-MiniLM-L6-v2`, 384 chiều, L2 normalization, `sentence-transformers` 5.7.0. PostgreSQL 16.15 + pgvector 0.8.6, exact cosine. Document/query cùng model. Chi phí API bằng 0; không có text bị model cắt. Chạy `python -m src.run` từ `starter/` sau khi dựng DB; chi tiết trong `starter/README.md`.
- **Metadata:** `document_id`, `source`, trang, khoảng ký tự, `category`, năm, ngôn ngữ; `category` lấy từ các khoảng trang trong manifest, có bảy giá trị để lọc phần sách. Phân loại theo trang có thể gộp nhiều ý.

## Cấu hình và benchmark

- A: fixed 450 ký tự, overlap 45, không filter. B: gom câu tối đa 650, không overlap, không filter. C: cùng chunk/vector như B, chỉ thêm `category` filter khi câu hỏi cho sẵn phạm vi. Cả ba dùng cùng corpus, query, model, store và cosine.
- Benchmark V2: 27 câu, 22 dev/5 test; 8 câu filter (4 test), gồm direct, paraphrase, conditional, exception. Evidence quote được đối chiếu trên đúng trang PDF trước lượt V2 bằng `starter/scripts/validate_benchmark.py`. SHA-256 câu hỏi: `30d0cfd3c2f0e79cc442d685382aa082034c626c1e2d926a3dadf1ac9e0e6619`.
- V1 đã có năm câu test được xem; sau khi đổi chunking, V1 được giữ lại, các câu đó chuyển sang dev và viết năm test mới trước lượt V2. Q05/dev và q23/test dùng cùng trang 10 nhưng hỏi lễ hội khác nhau; còn rủi ro rò rỉ theo trang. **Không có tiêu chí chọn cấu hình được chốt trước khi xem test**; lựa chọn dưới đây là hồi cứu.

## Kết quả

| Strategy | Split | Hit@1 | Evidence Hit@3 | Chunk count | Thời gian lượt chạy | Chi phí API |
|---|---|---:|---:|---:|---:|---:|
| A | dev | 19/22 | 19/22 | 187 | 36,466 giây | 0 |
| A | test | 3/5 | 5/5 | 187 | cùng lượt | 0 |
| B | dev | 19/22 | 20/22 | 142 | cùng lượt | 0 |
| B | test | 4/5 | 5/5 | 142 | cùng lượt | 0 |
| C | dev | 19/22 | 20/22 | 142 | cùng lượt | 0 |
| C | test | 4/5 | 5/5 | 142 | cùng lượt | 0 |

Thời gian 36,466 giây là cả lượt ba cấu hình, trong đó ingest/embedding/lưu 31,298 giây; không phải thời gian riêng mỗi cấu hình. Chạy trên máy cục bộ ngày 2026-11-14.

| Strategy | Coherence trung bình /2 (n) | Metadata đúng/đủ test top-3 | Filter tuân thủ | Grounding 0/1/2 và trung bình /2 |
|---|---:|---:|---:|---|
| A | 1,0 (10) | 15/15 | N/A | 0/0/5; 2,0 |
| B | 1,5 (10) | 15/15 | N/A | 0/0/5; 2,0 |
| C | 1,5 (10) | 15/15 | 4/4 test; 8/8 tổng | 0/0/5; 2,0 |

Metadata được đối chiếu **bằng code** với PDF/manifest: 45/45 hit test và 243/243 hit toàn bộ. Đây chưa phải kiểm tra nguồn thủ công. Coherence chọn cùng 10 vị trí giữa trang ở 10 trang nội dung đầu tiên, cố định trước lượt V2; nhãn 0–2 và lý do tại `starter/results/manual_audit.json`. Grounding đọc cùng 5 câu test/top-3 cho mỗi cấu hình; nhãn do AI hỗ trợ, chưa được tôi kiểm tra độc lập. Trace nguyên văn là `starter/results/traces.json` cục bộ (Git bỏ qua); `traces_public.json` lưu ID, score, metadata và hash/độ dài text để đối chiếu sau khi tái tạo PDF.

## Phân tích và kết luận

- A–B: B tăng Evidence Hit@3 dev một câu (19→20/22), Hit@1 test một câu (3→4/5), coherence 1,0→1,5; giảm 45 chunk (31,7%). `q27` dev là ví dụ B giữ đủ điều kiện/ngoại lệ trong chunk còn A không tìm được gold top-3.
- B–C: C chỉ thêm filter, tuân thủ 8/8 câu có filter nhưng không tăng Hit@1/3 trong mẫu này. Filter giúp giới hạn phạm vi theo phần sách; chưa chứng minh tăng độ chính xác.
- `q03` dev: cả ba tìm thấy trang lễ hội nhưng không đưa đoạn chứa Taichung vào top-3. `q16` dev: cả ba nhầm các đường mòn khác với Eryanping trang 26. `q24` test: cả ba có bằng chứng trong top-3 nhưng không ở top-1.
- Với câu hỏi chỉ rõ phần sách, tôi chọn C để bảo đảm phạm vi; nếu không có phạm vi, B cho cùng kết quả. Kết luận hồi cứu trên một sách và năm câu test, không phải tối ưu tổng quát.
- Giới hạn: V1 đã được xem, test V2 nhỏ và cùng tài liệu với dev; gold dùng quote đầy đủ nên nhạy với ranh giới chunk; nhãn AI hỗ trợ cần học viên tự xác nhận; PDF trích xuất còn lỗi; thời gian chỉ đo một máy. Nếu mở rộng, tạo test độc lập theo trang/chủ đề, kiểm audit thủ công, cân nhắc OCR và đánh giá thêm các kích thước trên dev mới.

Xem `starter/results/analysis.md` để biết lịch sử benchmark, tệp kết quả và lệnh tái lập.

## AI và cách kiểm chứng

Tôi dùng Codex (GPT-6) hỗ trợ viết pipeline, câu hỏi, phân tích trace và nhãn coherence/grounding. Các số liệu truy xuất đến từ lần chạy PostgreSQL + pgvector thực; quote và filter được chương trình đối chiếu với trang PDF bằng `validate_benchmark.py`, trace và bảng tổng hợp được kiểm tra nhất quán. Nhãn đọc bằng AI chưa được tôi xác nhận độc lập; vì vậy không trình bày chúng như kiểm tra thủ công của học viên. Tôi cần đọc lại các chunk và giải thích lựa chọn chiến lược khi bảo vệ bài.
