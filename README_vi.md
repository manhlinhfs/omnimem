# OmniMem v1.1.0 - Bộ Não Đa Năng Cho Mọi AI 🧠

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

## Runtime offline-safe
- Các lệnh `omni_add.py`, `omni_search.py`, `omni_import.py` giờ mặc định load model từ `.omnimem_models/`.
- Nếu thiếu thư mục model local, OmniMem sẽ thử khôi phục từ cache local của Hugging Face trước.
- Nếu vẫn thiếu model, OmniMem sẽ báo rõ cần chạy `python3 omni_bootstrap.py` thay vì văng traceback giữa chừng.
- Chỉ đặt `OMNIMEM_ALLOW_MODEL_DOWNLOAD=1` nếu bạn muốn runtime tự tải model khi cần.

## Hướng dẫn kết nối cho các AI Agents (Bước bắt buộc)

Để các con AI có thể "thức tỉnh" và biết cách xài bộ não này, bạn BẮT BUỘC phải dán đoạn mã (System Prompt) sau vào phần cấu hình cốt lõi của chúng (Ví dụ: file `.gemini/GEMINI.md`, phần *Custom Instructions* của Claude Code, hoặc *Rules for AI* của Cursor):

```markdown
## Giao thức OmniMem (Second Brain)
1. **LUÔN TÌM KIẾM TRƯỚC:** Trước khi trả lời các câu hỏi về dự án, BẮT BUỘC phải chạy lệnh: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_search.py "câu truy vấn" --full` để lấy ngữ cảnh. Bắt buộc dùng cờ `--full` để lấy trọn vẹn văn bản. Có thể dùng thêm `--json` nếu cần phân tách dữ liệu tĩnh.
2. **LUÔN NẠP TÀI LIỆU:** Khi người dùng yêu cầu đọc hoặc nhớ một file (PDF, DOCX, Code, Ảnh OCR...), hãy chạy lệnh: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_import.py <đường_dẫn_file>` để trích xuất file thông qua lõi Kreuzberg.
3. **LƯU TRỮ THÀNH QUẢ:** Sau khi fix xong bug lớn hoặc chốt một cột mốc, hãy chạy lệnh: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_add.py "tóm tắt ngắn gọn"` để lưu kết quả cho những phiên chat vào ngày mai.
```
*(Lưu ý: Bạn phải thay chữ `[OMNIMEM_PATH]` thành đường dẫn tuyệt đối tới thư mục omnimem trên máy của bạn, ví dụ: `/root/omnimem` hoặc `C:\omnimem`)*

## Sử dụng thủ công bằng tay (Dành cho con người)
- **Xem version:** `python3 omni_search.py --version`
- **Doctor:** `python3 omni_doctor.py`
- **Bootstrap model:** `python3 omni_bootstrap.py`
- **Thêm note:** `python3 omni_add.py "Mật khẩu là 123"`
- **Đọc file:** `python3 omni_import.py tai_lieu.pdf`
- **Tìm kiếm:** `python3 omni_search.py "mật khẩu" --full`
- **Dọn dẹp DB:** `python3 omni_del.py --wipe-all`
