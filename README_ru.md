# OmniMem v1.3.0 - CLI «Второй Мозг» 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

> **Установка за 60 секунд.** [`QUICKSTART.md`](QUICKSTART.md) показывает самый быстрый путь для пользователей Claude Code / Codex CLI / Gemini CLI / Cursor.
>
> ```bash
> git clone https://github.com/manhlinhfs/omnimem.git && cd omnimem
> ./scripts/setup.sh
> ./omnimem quickstart        # интерактивно: обнаружить агенты, установить, создать welcome-заметку
> ```

OmniMem — это мультимодальный «второй мозг», LLM-агностик, работающий полностью в терминале. Даёт любому AI-помощнику программиста (Claude Code, Codex CLI, Gemini CLI, Cursor, Cline, OpenClaw) **6 возможностей в одном CLI**:

1. **Document RAG** — ингестит PDF, Word, исходный код и OCR-картинки через Kreuzberg + ChromaDB.
2. **Структурированные заметки** — заметки в стиле Zettelkasten в переносимом Markdown-хранилище с двунаправленными wiki-ссылками.
3. **Codemap** — `omnimem codemap build` обходит репозиторий и пишет структурную карту для каждого исходного файла. Поддерживает Python (stdlib `ast`), JavaScript, TypeScript, Go и Rust через реестр парсеров, с записями отдельных символов в ChromaDB.
4. **Интеграция одной командой** — `omnimem init --agent claude|codex|gemini|cursor|all` прописывает правило в файл инструкций агента + регистрирует MCP-сервер; `omnimem hook --agent claude|codex|all` добавляет lifecycle-хуки для Claude Code и Codex CLI.
5. **Объединённый поиск + временные запросы** — `omnimem search --all` ранжирует результаты из документов, заметок и codemap-символов вместе. `--at-date YYYY-MM-DD` восстанавливает состояние хранилища на конкретный день.
6. **Canvas-экспорт + редакция секретов** — `omnimem note canvas` экспортирует граф заметок в формате Obsidian Canvas JSON. `omnimem redact` сканирует текст на токены AWS / GitHub / OpenAI / Anthropic, PEM-блоки, JWT и типичные шаблоны учётных данных.

## Базовая архитектура

- **Kreuzberg (Rust Core):** извлекает чистый Markdown и метаданные из 56+ форматов.
- **ChromaDB:** локальная персистентная векторная БД, работающая полностью офлайн (коллекции `omnimem_core` для документов, `omnimem_notes` для заметок, `omnimem_codemap` для карт исходного кода).
- **SentenceTransformers:** локальная копия `all-MiniLM-L6-v2`, забутстрапленная на диск, для embedding-ов в рантайме.
- **MCP-сервер:** stdio Model Context Protocol сервер с шестью инспектируемыми инструментами.
- **Markdown-хранилище:** переносимое дерево `vault/` под `OMNIMEM_HOME`, читаемое человеком и Obsidian-ом.

## Установка

### Linux / macOS

```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x scripts/setup.sh
./scripts/setup.sh
./omnimem quickstart
```

`scripts/setup.sh` устанавливает зависимости и скачивает embedding-модель в `.omnimem_models/`. `omnimem quickstart` — интерактивный мастер для подключения OmniMem к установленным CLI агентов.

### Windows (PowerShell)

```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\scripts\setup.ps1
.\omnimem quickstart
```

### Установка как пакет

```bash
python3 -m pip install "git+https://github.com/manhlinhfs/omnimem.git@main"
omnimem --version
omnimem quickstart
```

### Однострочный установщик (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/manhlinhfs/omnimem/main/install.sh | bash
~/.omnimem-cli/omnimem quickstart
```

## Интеграция с CLI агентов

Для каждого агента — одна строка. Мастер `omnimem quickstart` делает всё сам, или вручную:

| Агент | Команда |
|---|---|
| Claude Code | `./omnimem init --agent claude && ./omnimem hook --agent claude` |
| Codex CLI | `./omnimem init --agent codex && ./omnimem hook --agent codex` |
| Gemini CLI | `./omnimem init --agent gemini` |
| Cursor | `./omnimem init --agent cursor` |
| Все сразу | `./omnimem init --agent all && ./omnimem hook --agent all` |

Установщик **идемпотентен и обратим**:

```bash
./omnimem init --status                          # посмотреть, что уже установлено
./omnimem init --uninstall --agent claude        # удалить только размеченный блок
```

Подробности по каждому CLI — в [`docs/integrations/`](docs/integrations/).

## Часто используемые команды

```bash
# Заметки
./omnimem note new "Почему выбрали FastAPI" --type decision --tags auth,backend
./omnimem note search "fastapi"
./omnimem note canvas vault.canvas               # экспорт графа заметок в Obsidian Canvas

# Документы
./omnimem import path/to/spec.pdf
./omnimem search "rate limit" --all              # поиск через 3 коллекции сразу

# Codemap
./omnimem codemap build .
./omnimem codemap query "TokenManager"

# Безопасность
echo "AKIA... ghp_..." | ./omnimem redact -      # обнаружить + замазать секреты

# Эксплуатация
./omnimem doctor                                  # health-check всего рантайма
./omnimem backup                                  # снимок vault + DB + модели
./omnimem hook --status                           # какие хуки сейчас установлены
```

## Где живут файлы

```
$OMNIMEM_HOME/
├── chroma/                 # векторная БД (офлайн)
├── .omnimem_models/        # embedding-модель (забутстрапленная)
└── vault/
    ├── notes/              # Zettelkasten-markdown — совместимо с Obsidian
    ├── conversations/      # импортированные транскрипты
    ├── attachments/        # вспомогательные файлы
    └── codemap/<repo>/     # структурные карты исходного кода
```

Значение `OMNIMEM_HOME` по умолчанию: `~/.omnimem` на всех ОС (Linux, macOS, Windows). Переопределить через переменную окружения `OMNIMEM_HOME` или в `omnimem.json`.

## Документация

- [`QUICKSTART.md`](QUICKSTART.md) — самый быстрый путь для нового пользователя
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — типичные ошибки и решения
- [`docs/notes.md`](docs/notes.md) — справочник CLI для модуля заметок
- [`docs/codemap.md`](docs/codemap.md) — использование codemap и реестр парсеров
- [`docs/hooks.md`](docs/hooks.md) — lifecycle-хуки для Claude Code + Codex CLI
- [`docs/redact.md`](docs/redact.md) — таблица паттернов и применение redaction
- [`docs/benchmarks.md`](docs/benchmarks.md) — числа по retrieval / latency / parser accuracy
- [`docs/faq.md`](docs/faq.md) — офлайн?, vs Mem0?, заметка или документ?, и др.
- [`docs/integrations/`](docs/integrations/) — детальная настройка для каждого CLI агента
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — как контрибьютить в проект

## Лицензия

MIT.
