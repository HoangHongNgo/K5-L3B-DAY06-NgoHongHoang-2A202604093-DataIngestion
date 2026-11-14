# Day 06 · Data Ingestion Engineering

## Bài làm — Ngô Hồng Hoàng · 2A202604093 · L3B

Pipeline đã chạy với 35 trang nội dung của *2020 Taiwan Tourism Guide Book*, embedding local `sentence-transformers/all-MiniLM-L6-v2`, PostgreSQL + pgvector và ba cấu hình fixed/gom câu/filter. Benchmark V2 có 27 câu (22 dev, 5 test). Xem [báo cáo cá nhân](report/individual/2A202604093_NgoHongHoang.md), [kết quả chi tiết](starter/results/analysis.md), [manifest](starter/data/manifest.json), [câu hỏi và gold](starter/data/questions.json), [nhật ký thí nghiệm](artifacts/experiment_log.csv).

**Tái lập:** tải PDF từ [trang nguồn](https://taiwan.net.vn/download), đặt đúng tên `starter/data/2020_Taiwan_Tourism_Guide_Book_(E).pdf` và kiểm SHA-256 theo manifest. PDF và trace chứa nguyên văn chunk không được đưa lên repo do chưa xác minh quyền tái phân phối; [trace công khai](starter/results/traces_public.json) giữ ID, score, metadata, hash và độ dài text. Chạy lại tạo trace đầy đủ cục bộ. Xem [hướng dẫn setup/chạy](starter/README.md); Docker không bắt buộc nếu có PostgreSQL + pgvector. `STUDENT.md` có thông tin nộp bài.

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và chạy pipeline đã hiện thực. Bài làm dùng PostgreSQL cục bộ; Docker Compose là lựa chọn khác.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Bộ V2 có **22 câu dev / 5 câu test**, mỗi câu có bằng chứng và trang nguồn. [Lịch sử benchmark](starter/data/benchmark_protocol.md) ghi rõ V1 đã được xem và hạn chế của kết quả V2; đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Pipeline và benchmark của bài làm nằm trong `starter/`; bài tập không yêu cầu chatbot.
