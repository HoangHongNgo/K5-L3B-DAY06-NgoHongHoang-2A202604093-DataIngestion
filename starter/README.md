# Starter · PostgreSQL + pgvector

Bộ khởi động dùng PostgreSQL + pgvector, embedding local `sentence-transformers/all-MiniLM-L6-v2` (384 chiều), fixed chunking và gom câu. Docker Compose là một cách dựng database; có thể dùng PostgreSQL + pgvector cài sẵn và chỉnh `DATABASE_URL`.

Workspace này có [manifest](data/manifest.json) cho *2020 Taiwan Tourism Guide Book* (35 trang nội dung) và [27 câu hỏi đã gắn evidence](data/questions.json). PDF được cung cấp để xử lý cục bộ; quyền tái phân phối chưa xác minh nên PDF và trace chứa đoạn văn được loại khỏi Git. Tải bản PDF từ [trang nguồn](https://taiwan.net.vn/download) và đặt tại `starter/data/2020_Taiwan_Tourism_Guide_Book_(E).pdf`; kiểm SHA-256 theo manifest. [Kết quả V2](results/analysis.md) ghi điểm số, lỗi và giới hạn; [lịch sử benchmark](data/benchmark_protocol.md) ghi rõ V1 đã được xem và bộ test V2 mới.

## Cấu trúc

```text
starter/
├── docker-compose.yml     # PostgreSQL 16 + pgvector, chỉ mở cổng local
├── init.sql               # bật extension khi tạo database mới
├── requirements.txt       # psycopg, pypdf và python-dotenv
├── .env.example           # cấu hình mẫu; copy thành .env
├── scripts/check_setup.py # kiểm tra kết nối và extension (đã chạy được)
├── src/
│   ├── models.py          # cấu trúc dữ liệu mẫu
│   ├── ingestion.py       # đọc PDF / chuẩn hóa văn bản
│   ├── chunking.py        # fixed-size và gom câu, giữ số trang
│   ├── embeddings.py      # sentence-transformers local
│   ├── store.py           # pgvector, cosine, metadata filter
│   ├── evaluation.py      # Hit@1, Evidence Hit@3, metadata audit
│   └── run.py             # điều phối pipeline A/B/C
├── data/                  # manifest, PDF và questions.json của bạn
└── results/               # trace và thống kê sinh khi chạy
```

## 1. Cài và kiểm tra database

Cần PostgreSQL có pgvector, Python **3.11–3.14**, và mạng để tải model/dependencies lần đầu. Nếu dùng Docker Compose, cần Docker Desktop hoặc Docker Engine + Compose. Các lệnh sau chạy từ thư mục `starter/`:

```bash
cd starter
python3 -m venv .venv
```

Kích hoạt `.venv`: macOS/Linux dùng `source .venv/bin/activate`; Windows PowerShell dùng `.venv\Scripts\Activate.ps1`. Sau đó:

```bash
python -m pip install -r requirements.txt
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
# Chỉ khi dùng Docker:
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kỳ vọng: hiện tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây **chỉ là kiểm tra hạ tầng**, không phải kết quả benchmark. Nếu dùng PostgreSQL cài trực tiếp, tạo database, bật `CREATE EXTENSION vector`, rồi đặt URL kết nối đúng trong `.env`. Docker dùng cổng `127.0.0.1:55433` và mật khẩu cố định **chỉ dùng local cho lab**; nếu cổng bận, sửa đồng thời port trong `docker-compose.yml` và `DATABASE_URL` trong `.env`.

Trên máy Windows có sẵn `.local/postgres` (như workspace này), có thể bỏ qua Docker và chạy từ project root:

```powershell
.\starter\scripts\local_db.ps1
.\.venv\Scripts\python.exe starter\scripts\check_setup.py
```

Script tạo `starter/.env` với mật khẩu ngẫu nhiên, khởi tạo database rỗng và bật pgvector. Chạy lại để khởi động database; dừng bằng `.\starter\scripts\local_db.ps1 -Stop`. Không commit `.env`.

Dừng container nhưng giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```

## 2. Embedding model

Mặc định dùng `sentence-transformers/all-MiniLM-L6-v2`, 384 chiều, chạy local và không cần API key. Model được tải lần đầu vào `.local/models/huggingface` tại project root. Cùng model và cách chuẩn hóa vector được dùng cho document và query. Ghi version model/thư viện trong báo cáo. Model này được huấn luyện chủ yếu cho tiếng Anh; nếu corpus tiếng Việt, cần đánh giá chất lượng truy xuất thực tế.

## 3. Hoàn thiện pipeline

1. Đặt PDF đúng tên vào `starter/data/`; manifest và benchmark đã nằm ở đó. Xem [mẫu định dạng](data/README.md) khi đổi corpus. Chạy `python scripts/validate_benchmark.py` để kiểm 35 trang và 27 câu (22 dev / 5 test).
2. Chạy `python -m src.run` từ thư mục `starter/`. Có thể dùng `python -m src.run --ingest-only` khi chưa có bộ câu hỏi.
3. A: fixed 450 ký tự, overlap 45. B: gom câu tối đa 650 ký tự, không overlap. C: cùng chunk/vector như B, thêm filter `category` khi câu hỏi cung cấp. Cả ba dùng cùng corpus, model và exact cosine search.
4. Xem `results/traces.json` và `results/summary.json`. Trace đầy đủ chỉ ở máy cục bộ. `traces_public.json` bỏ nguyên văn chunk nhưng giữ ID, score, metadata và hash để kiểm chứng; chạy lại để tái tạo trace đầy đủ. Lệnh chạy lại đồng bộ dữ liệu, không nhân đôi chunk và xóa chunk cũ khi tài liệu hoặc manifest thay đổi.
5. Xem [phân tích](results/analysis.md) và `manual_audit.json`. Nhãn coherence/grounding do AI hỗ trợ đọc, cần học viên xác nhận độc lập nếu muốn gọi là audit thủ công. `metadata_audit.json` là đối chiếu bằng chương trình, không thay thế kiểm nguồn thủ công.

Lưu code, cấu hình, kết quả và lệnh chạy để người chấm tái lập; không commit key, dữ liệu mật hoặc dữ liệu không có quyền chia sẻ.
