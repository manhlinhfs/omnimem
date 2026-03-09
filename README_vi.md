# OmniMem v1.8.3 - Bộ Não CLI Tối Ưu Cho Retrieval 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

OmniMem là một hệ thống RAG (Retrieval-Augmented Generation) đa phương thức, hoạt động độc lập trên Terminal và không bị trói buộc với bất kỳ một LLM nào. Nó đóng vai trò như một "Bộ não phụ" (Second Brain) cho các công cụ AI Lập trình (như Claude Code, Gemini CLI, Cursor, Cline, OpenClaw).

Nó cho phép các AI này có khả năng "đọc hiểu", "nhúng" và "ghi nhớ" tri thức từ các tài liệu siêu phức tạp như PDF, Word, Ảnh chứa text (OCR), mã nguồn...

## Công nghệ cốt lõi
- **Kreuzberg (Rust Core):** Trích xuất tự động văn bản chuẩn Markdown và siêu dữ liệu (Metadata) từ hơn 56 định dạng file.
- **ChromaDB:** Cơ sở dữ liệu Vector cục bộ (Local), lưu trữ an toàn ngay trên ổ cứng của bạn (Offline).
- **SentenceTransformers:** Dùng bản local đã được bootstrap của `all-MiniLM-L6-v2` để tạo embeddings trong lúc chạy.

## Cài đặt

### Linux / macOS
```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x setup.sh
./setup.sh
```
`setup.sh` giờ sẽ cài dependencies và tải model embedding vào `.omnimem_models/` để runtime không phụ thuộc mạng.

### Windows (PowerShell)
```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\setup.ps1
```
`setup.ps1` cũng thực hiện bước bootstrap model tương tự trên Windows.

### Chế độ cài package
```bash
python3 -m pip install .
omnimem --version
```
Khi cài theo kiểu package, OmniMem sẽ lưu dữ liệu runtime vào user data directory thay vì `site-packages`, đồng thời cung cấp lệnh `omnimem` trực tiếp trên PATH.

### Cài trực tiếp từ GitHub
```bash
python3 -m pip install "git+https://github.com/manhlinhfs/omnimem.git@main"
omnimem --version
```

### Bootstrap model thủ công
```bash
python3 omni_bootstrap.py
```
Dùng `--offline-only` nếu bạn chỉ muốn khôi phục model từ local Hugging Face cache mà không truy cập mạng.

### Kiểm tra sức khỏe runtime
```bash
python3 omni_doctor.py
python3 omni_doctor.py --deep
python3 omni_doctor.py --json
```

### Cấu hình đường dẫn runtime
```bash
cp omnimem.example.json omnimem.json
./omnimem doctor
```
Sửa `omnimem.json` để đổi vị trí DB, model hoặc các thiết lập vận hành mà không cần sửa code.

### Update clone hiện tại
```bash
python3 omni_update.py --check
python3 omni_update.py
```
`omni_update.py` sẽ cập nhật branch đang track upstream theo chế độ fast-forward only, từ chối ghi đè worktree đang bẩn, cài lại dependencies nếu `requirements.txt` đổi, và refresh trạng thái bootstrap model local.

Với package install, `omnimem update` không được hỗ trợ; hãy update bằng `pip`.

### Backup, export và restore
```bash
./omnimem backup
./omnimem export
./omnimem restore /path/to/omnimem-backup.tar.gz
./omnimem restore /path/to/omnimem-export.json --force
```

### Reindex dữ liệu import cũ với chunker mới
```bash
./omnimem reindex --dry-run
./omnimem reindex
```
Phần này dành cho người dùng đã import tài liệu từ các phiên bản cũ và muốn rebuild DB theo chiến lược chunking mới.

### Search service local giữ nóng model
```bash
./omnimem serve --status
./omnimem search "release notes" --full
./omnimem search "release notes" --direct
```
`search`, `add`, `import` và `reindex` giờ ưu tiên một local service giữ nóng embedding model và Chroma client giữa các lần chạy lệnh. Lần đầu tiên vẫn phải warm model một lần; các lần sau sẽ tránh phần lớn chi phí startup trước đây.

## Runtime offline-safe
- Các lệnh `omni_add.py`, `omni_search.py`, `omni_import.py` giờ mặc định load model từ `.omnimem_models/`.
- Nếu thiếu thư mục model local, OmniMem sẽ thử khôi phục từ cache local của Hugging Face trước.
- Nếu vẫn thiếu model, OmniMem sẽ báo rõ cần chạy `python3 omni_bootstrap.py` thay vì văng traceback giữa chừng.
- Chỉ đặt `OMNIMEM_ALLOW_MODEL_DOWNLOAD=1` nếu bạn muốn runtime tự tải model khi cần.

## Hướng dẫn kết nối cho các AI Agents (Bước bắt buộc)

Để các con AI có thể "thức tỉnh" và biết cách xài bộ não này, bạn BẮT BUỘC phải dán đoạn mã (System Prompt) sau vào phần cấu hình cốt lõi của chúng (Ví dụ: file `.gemini/GEMINI.md`, phần *Custom Instructions* của Claude Code, hoặc *Rules for AI* của Cursor):

```markdown
## Giao thức OmniMem (Second Brain)
1. **LUÔN TÌM KIẾM TRƯỚC:** Trước khi trả lời các câu hỏi về dự án, BẮT BUỘC phải chạy lệnh: `[OMNIMEM_PATH]/omnimem search "câu truy vấn" --full` để lấy ngữ cảnh. Bắt buộc dùng cờ `--full` để lấy trọn vẹn văn bản. Có thể dùng thêm `--json` nếu cần phân tách dữ liệu tĩnh.
2. **LUÔN NẠP TÀI LIỆU:** Khi người dùng yêu cầu đọc hoặc nhớ một file (PDF, DOCX, Code, Ảnh OCR...), hãy chạy lệnh: `[OMNIMEM_PATH]/omnimem import <đường_dẫn_file>` để trích xuất file thông qua lõi Kreuzberg.
3. **LƯU TRỮ THÀNH QUẢ:** Sau khi fix xong bug lớn hoặc chốt một cột mốc, hãy chạy lệnh: `[OMNIMEM_PATH]/omnimem add "tóm tắt ngắn gọn"` để lưu kết quả cho những phiên chat vào ngày mai.
```
*(Lưu ý: Bạn phải thay chữ `[OMNIMEM_PATH]` thành đường dẫn tuyệt đối tới thư mục omnimem trên máy của bạn, ví dụ: `/root/omnimem` hoặc `C:\omnimem`)*
Nếu bạn cài OmniMem như package và `omnimem` đã có trên PATH, có thể dùng thẳng `omnimem` thay cho `[OMNIMEM_PATH]/omnimem`.
Các script `omni_*.py` cũ vẫn còn dùng được khi cần.

## CLI thống nhất (khuyến nghị)
Hãy ưu tiên launcher của repo khi dùng clone mode vì nó tự chọn `venv` local. Trên Windows, dùng `.\omnimem.ps1` hoặc `.\omnimem.bat` từ thư mục repo. Nếu cài theo package mode, dùng lệnh `omnimem` trực tiếp.

- **Xem version:** `python3 omnimem.py --version`
- **Xem version qua launcher:** `./omnimem --version`
- **Xem version qua package đã cài:** `omnimem --version`
- **Doctor:** `./omnimem doctor`
- **Kiểm tra update:** `./omnimem update --check`
- **Update clone này:** `./omnimem update`
- **Bootstrap model:** `./omnimem bootstrap`
- **Backup runtime:** `./omnimem backup`
- **Export memories:** `./omnimem export`
- **Restore runtime:** `./omnimem restore /path/to/file`
- **Reindex tài liệu đã import:** `./omnimem reindex`
- **Kiểm tra search service:** `./omnimem serve --status`
- **Thêm note:** `./omnimem add "Mật khẩu là 123"`
- **Thêm note theo direct path:** `./omnimem add "Mật khẩu là 123" --direct`
- **Đọc file:** `./omnimem import tai_lieu.pdf`
- **Đọc file theo direct path:** `./omnimem import tai_lieu.pdf --direct`
- **Tìm kiếm:** `./omnimem search "mật khẩu" --full`
- **Tìm kiếm có filter:** `./omnimem search "release" --source omnimem --since 2026-03-06`
- **Bypass search service để debug:** `./omnimem search "mật khẩu" --direct`
- **Reindex theo direct path:** `./omnimem reindex --direct`
- **Chỉ tìm PDF đã import:** `./omnimem search "invoice" --mime-type application/pdf`
- **Xóa sạch DB:** `./omnimem delete --wipe-all --force`

## Script cũ vẫn dùng được
- `python3 omni_add.py "Mật khẩu là 123"`
- `python3 omni_add.py "Mật khẩu là 123" --direct`
- `python3 omni_import.py tai_lieu.pdf`
- `python3 omni_import.py tai_lieu.pdf --direct`
- `python3 omni_search.py "mật khẩu" --full`
- `python3 omni_search.py "mật khẩu" --direct`
- `python3 omni_del.py --wipe-all --force`
- `python3 omni_doctor.py`
- `python3 omni_ops.py backup`
- `python3 omni_ops.py export`
- `python3 omni_ops.py restore /path/to/file`
- `python3 omni_reindex.py --dry-run`
- `python3 omni_reindex.py`
- `python3 omni_reindex.py --direct`
- `python3 omni_update.py --check`

## Dành cho phát triển
- **Chạy test:** `python3 -m unittest discover -s tests -v`
- **Build package:** `python3 -m build`
- **Xem release notes:** `CHANGELOG.md`
- **Xem roadmap:** `ROADMAP.md`
- **Xem tài liệu install mode:** `docs/install-modes.md`
- **Xem tài liệu cấu hình:** `docs/configuration.md`
- **Xem tài liệu vận hành:** `docs/operations.md`
- **Xem tài liệu chunking:** `docs/chunking.md`
- **Xem tài liệu reindex:** `docs/reindexing.md`
- **Xem tài liệu search filter:** `docs/search-filters.md`
- **Xem tài liệu search service:** `docs/search-service.md`
- **Theo checklist release:** `docs/release-checklist.md`
