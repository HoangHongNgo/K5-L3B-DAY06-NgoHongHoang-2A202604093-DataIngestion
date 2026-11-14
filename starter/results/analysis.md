# Kết quả benchmark v2 — Taiwan Tourism Guide Book 2020

Chạy ngày 2026-11-14. Kết quả đo **truy xuất bằng chứng**, không đo câu trả lời LLM. Sách năm 2020 không phản ánh thông tin du lịch hiện hành.

## Dữ liệu và pipeline

PDF có 48 trang vật lý; chọn 35 trang nội dung (2–5, 7–37), tổng 71.620 ký tự chuẩn hóa. Trang trong gold/trace là trang vật lý. Manifest lưu số ký tự từng trang và SHA-256 PDF. Bản do người dùng cung cấp cục bộ; [trang tải](https://taiwan.net.vn/download) có sách, nhưng [thông báo bản quyền](https://eng.taiwan.net.tw/m1.aspx?sNo=0042571) không cấp quyền tái phân phối PDF. PDF và trace nguyên văn được Git bỏ qua; README hướng dẫn tái tạo.

`pypdf` trích xuất và chuẩn hóa Unicode/whitespace; không OCR ảnh. Mỗi chunk giữ `document_id`, `source`, trang, khoảng ký tự, `category`, năm và ngôn ngữ. `category` dựa trên các khoảng trang của bảy phần trong manifest. Embedding local `sentence-transformers/all-MiniLM-L6-v2`, 384 chiều, L2 normalization, cùng model cho document/query; `sentence-transformers` 5.7.0. PostgreSQL 16.15 + pgvector 0.8.6, exact cosine search. Chi phí API bằng 0; không có văn bản bị cắt theo bộ đếm model. Một lượt chạy mất 36,466 giây, gồm ingest/embedding/lưu 31,298 giây trên máy này. Lượt chạy lại upsert và xóa chunk cũ, không nhân đôi.

## Benchmark và tính độc lập

V1 có 20 câu và 5 test đã được xem khi khảo sát. Sau khi đổi B/C từ fixed sang gom câu, đã lưu V1 tại `questions_v1.json`, chuyển toàn bộ câu cũ sang dev, sửa gold thay thế của q17 và tạo năm test mới q21–q25 **trước lần chạy V2**. V2 có 27 câu (22 dev, 5 test), 8 câu filter (4 test), gồm direct, paraphrase, conditional và exception. `validate_benchmark.py` kiểm tra quote trên đúng trang, loại câu và chia tập. SHA-256 V2: `30d0cfd3c2f0e79cc442d685382aa082034c626c1e2d926a3dadf1ac9e0e6619`. Xem `data/benchmark_protocol.md`. Q05/dev và q23/test cùng trang 10 nhưng hỏi lễ hội khác nhau, nên còn nguy cơ rò rỉ theo trang. Tiêu chí chọn chiến lược không được khóa trước khi xem test; kết luận là **hồi cứu**.

Hit@1 và Evidence Hit@3 yêu cầu một chunk trên đúng nguồn/trang gold chứa đủ quote. Không âm thầm sửa gold theo kết quả.

## Cấu hình và độ chính xác

| Cấu hình | Chunking | Filter | Chunk | Trung bình (min–max) ký tự | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| A | Fixed 450, overlap 45 | Không | 187 | 419,4 (93–450) | 19/22 | 19/22 | 3/5 | 5/5 |
| B | Gom câu, tối đa 650, overlap 0 | Không | 142 | 503,6 (105–647) | 19/22 | 20/22 | 4/5 | 5/5 |
| C | Giống B | `category` khi câu hỏi cung cấp | 142 | 503,6 (105–647) | 19/22 | 20/22 | 4/5 | 5/5 |

A–B đổi phương pháp chunking. B–C **chỉ đổi filter**; dùng cùng chunk, vector, query, store và metric. C chạy không lọc khi câu hỏi không có filter. A lưu nhiều hơn B/C 45 chunk (31,7%). Tổng ký tự nhúng A=78.425, B/C=71.513; C tái dùng vector B trong lượt chạy.

## Năm tiêu chí BENCHMARK.md

1. **Retrieval:** điểm dev/test ở bảng trên; trace top-3 có ID, text, score, metadata và nhãn hit.
2. **Coherence:** cùng 10 vị trí giữa trang của 10 trang nội dung đầu tiên (2, 3, 4, 5, 7–12), đã chọn từ V1 trước lượt V2. Chunk bao phủ có tâm gần nhất được chấm 0–2. A=10/20, trung bình **1,0/2** (số nhãn 0/1/2: 1/8/1); B=C=15/20, **1,5/2** (0/5/5). Từng vị trí, chunk ID, nhãn và lý do ở `manual_audit.json`.
3. **Metadata:** đối chiếu tự động `source`, trang, `document_id`, `category`, năm, ngôn ngữ và text span với PDF/manifest: **45/45** hit top-3 test và **243/243** tổng thể đúng/đủ. C tuân thủ filter **8/8**, riêng test **4/4**. Đây là kiểm tra bằng code, chưa phải kiểm tra nguồn thủ công độc lập. `category` giúp hạn chế phạm vi nhưng phân loại theo trang còn thô.
4. **Grounding:** đọc top-3 của năm câu test cho từng chiến lược. A, B, C đều có **0 mức 0, 0 mức 1, 5 mức 2**, trung bình **2,0/2**. Lý do từng nhãn trong `manual_audit.json`. Nhãn do AI hỗ trợ đọc sau khi xem kết quả, chưa được học viên xác nhận độc lập.
5. **Tác động:** B/C hơn A một câu Evidence Hit@3 trên dev, một câu Hit@1 trên test và 0,5 điểm coherence trung bình, đồng thời ít chunk hơn. B–C không đổi accuracy trên mẫu này; lợi ích đo được của C là tuân thủ phạm vi filter. Test chỉ có 5 câu trong một sách nên không suy rộng.

## Trường hợp sai và quyết định

- `q03` (dev, đèn lồng, trang 8): cả ba không đưa chunk chứa “Taichung will host the festival in 2020” vào top-3 dù trang/category xuất hiện. Lỗi ranh giới chunk/ranking.
- `q16` (dev, Eryanping, trang 26): cả ba trả về các đoạn về đường mòn khác; thiếu gold trong top-3.
- `q27` (dev, ngoại lệ): A bỏ lỡ gold trong top-3, B/C tìm được. Gom câu giữ ngữ cảnh điều kiện tốt hơn ở ví dụ này.
- `q24` (test, quà lưu niệm): cả ba có evidence trong top-3, nhưng không ở top-1. C đổi thứ tự hit khi lọc mà không đổi điểm tổng.

Nếu câu hỏi ràng buộc phần tài liệu, C bảo đảm filter; khi không có phạm vi, B cho cùng kết quả. Đây là lựa chọn hồi cứu, không phải chứng minh chiến lược tối ưu. Muốn xác nhận cần test mới và chấm thủ công độc lập.

## Tệp và lệnh tái lập

`results/traces.json` cục bộ có đầy đủ nguyên văn top-3. `results/traces_public.json` giữ ID, score, metadata, độ dài/SHA-256 text nhưng bỏ nguyên văn do quyền xuất bản. `summary.json`, `metadata_audit.json`, `manual_audit.json` lưu số đo/nhãn. Tải PDF đúng tên vào `starter/data/`, kiểm SHA-256 trong manifest rồi từ project root chạy:

```powershell
.\starter\scripts\local_db.ps1
.\.venv\Scripts\python.exe starter\scripts\check_setup.py
.\.venv\Scripts\python.exe starter\scripts\validate_benchmark.py
Set-Location starter
$env:HF_HUB_OFFLINE='1' # bỏ dòng này khi cần tải model lần đầu
..\.venv\Scripts\python.exe -m src.run
```

Xem `starter/README.md` để dùng Docker hoặc PostgreSQL có sẵn. Không commit `.env` hay PDF.
