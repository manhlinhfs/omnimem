# OmniMem v1.3.2 - Bộ Não CLI Thứ Hai 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

> **Cài đặt 60 giây.** [`QUICKSTART.md`](QUICKSTART.md) hướng dẫn đường nhanh nhất cho user dùng Claude Code / Codex CLI / Gemini CLI / Cursor.
>
> ```bash
> git clone https://github.com/manhlinhfs/omnimem.git && cd omnimem
> ./scripts/setup.sh
> ./omnimem quickstart        # tương tác: phát hiện agent, cài đặt, seed welcome note
> ```

OmniMem là "bộ não thứ hai" multimodal, LLM-agnostic, chạy hoàn toàn trong terminal. Nó cho mọi AI coding agent (Claude Code, Codex CLI, Gemini CLI, Cursor, Cline, OpenClaw) **6 thứ trong 1 CLI**:

1. **Document RAG** — ingest PDF, Word, source code và ảnh OCR qua Kreuzberg + ChromaDB.
2. **Note có cấu trúc** — note kiểu Zettelkasten trong vault Markdown portable, có wikilink hai chiều.
3. **Codemap** — `omnimem codemap build` quét repo, viết structural map cho từng source file. Hỗ trợ Python (stdlib `ast`), JavaScript, TypeScript, Go và Rust qua parser registry, có per-symbol record trong ChromaDB.
4. **Tích hợp một lệnh** — `omnimem init --agent claude|codex|gemini|cursor|all` ghi rule vào instructions file của từng agent + đăng ký MCP server; `omnimem hook --agent claude|codex|all` thêm lifecycle hook cho Claude Code và Codex CLI.
5. **Federated search + truy vấn theo thời gian** — `omnimem search --all` xếp hạng kết quả từ documents, structured notes, và codemap symbols cùng nhau. `--at-date YYYY-MM-DD` tái dựng trạng thái vault tại một ngày cụ thể.
6. **Canvas export + redact secret** — `omnimem note canvas` xuất note graph dạng Obsidian Canvas JSON. `omnimem redact` quét text tìm AWS / GitHub / OpenAI / Anthropic token, PEM key, JWT, và các chuỗi credential phổ biến.

## Kiến trúc cốt lõi

- **Kreuzberg (Rust Core):** Trích xuất Markdown sạch + metadata từ hơn 56 định dạng.
- **ChromaDB:** Vector DB cục bộ, persistent, chạy hoàn toàn offline trên ổ cứng (collection `omnimem_core` cho documents, `omnimem_notes` cho notes, `omnimem_codemap` cho source map).
- **SentenceTransformers:** Bản local của `all-MiniLM-L6-v2` (đã bootstrap) để sinh embedding lúc runtime.
- **MCP server:** Stdio Model Context Protocol server với 6 tool có introspection.
- **Markdown vault:** Cây `vault/` portable dưới `OMNIMEM_HOME` mà người đọc / Obsidian dùng được.

## Cài đặt

### Linux / macOS

```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x scripts/setup.sh
./scripts/setup.sh
./omnimem quickstart
```

`scripts/setup.sh` cài dependencies và tải model embedding vào `.omnimem_models/`. `omnimem quickstart` là wizard tương tác để wire OmniMem vào agent CLI bạn đã cài.

### Windows (PowerShell)

```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\scripts\setup.ps1
.\omnimem quickstart
```

### Cài như package

```bash
python3 -m pip install "git+https://github.com/manhlinhfs/omnimem.git@main"
omnimem --version
omnimem quickstart
```

### One-line installer (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/manhlinhfs/omnimem/main/install.sh | bash
~/.omnimem-cli/omnimem quickstart
```

## Tích hợp với từng agent CLI

Mỗi agent một dòng. Wizard `omnimem quickstart` lo hết, hoặc làm tay:

| Agent | Lệnh |
|---|---|
| Claude Code | `./omnimem init --agent claude && ./omnimem hook --agent claude` |
| Codex CLI | `./omnimem init --agent codex && ./omnimem hook --agent codex` |
| Gemini CLI | `./omnimem init --agent gemini` |
| Cursor | `./omnimem init --agent cursor` |
| Cài hết một lượt | `./omnimem init --agent all && ./omnimem hook --agent all` |

Installer **idempotent và reversible**:

```bash
./omnimem init --status                          # xem cài đặt nào đang active
./omnimem init --uninstall --agent claude        # gỡ sạch khối có marker
```

Chi tiết từng CLI ở [`docs/integrations/`](docs/integrations/).

## Lệnh thường dùng

```bash
# Notes
./omnimem note new "Vì sao chọn FastAPI" --type decision --tags auth,backend
./omnimem note search "fastapi"
./omnimem note canvas vault.canvas               # xuất note graph cho Obsidian Canvas

# Documents
./omnimem import path/to/spec.pdf
./omnimem search "rate limit" --all              # tìm xuyên 3 collection

# Codemap
./omnimem codemap build .
./omnimem codemap query "TokenManager"

# An toàn
echo "AKIA... ghp_..." | ./omnimem redact -      # phát hiện + che secret

# Vận hành
./omnimem doctor                                  # health check toàn bộ runtime
./omnimem backup                                  # snapshot vault + DB + model
./omnimem hook --status                           # xem hook nào đã cài
```

## Vault sống ở đâu

```
$OMNIMEM_HOME/
├── chroma/                 # vector DB (offline)
├── .omnimem_models/        # embedding model đã bootstrap
└── vault/
    ├── notes/              # Zettelkasten markdown — Obsidian-friendly
    ├── conversations/      # transcript đã import
    ├── attachments/        # file phụ trợ
    └── codemap/<repo>/     # structural map của source code
```

Mặc định `OMNIMEM_HOME` = `~/.omnimem` trên mọi OS (Linux, macOS, Windows). Đè bằng env var `OMNIMEM_HOME` hoặc trong `omnimem.json`.

## Tài liệu

- [`QUICKSTART.md`](QUICKSTART.md) — đường nhanh nhất cho user mới
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — lỗi thường gặp + cách fix
- [`docs/notes.md`](docs/notes.md) — tham chiếu CLI cho note module
- [`docs/codemap.md`](docs/codemap.md) — codemap usage và parser registry
- [`docs/hooks.md`](docs/hooks.md) — lifecycle hook cho Claude Code + Codex CLI
- [`docs/redact.md`](docs/redact.md) — bảng pattern + cách dùng redaction
- [`docs/benchmarks.md`](docs/benchmarks.md) — kết quả retrieval / latency / parser accuracy
- [`docs/faq.md`](docs/faq.md) — offline?, vs Mem0?, note hay document?, etc.
- [`docs/integrations/`](docs/integrations/) — setup chi tiết từng agent CLI
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — đóng góp cho dự án

## License

MIT.
