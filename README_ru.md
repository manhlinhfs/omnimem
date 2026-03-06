# OmniMem - Универсальный CLI-Мозг 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

OmniMem — это мультимодальная система RAG (Retrieval-Augmented Generation), независимая от конкретных LLM, работающая полностью в терминале. Она действует как «Второй Мозг» (Second Brain) для любого AI-агента или помощника программиста (Claude Code, Gemini CLI, Cursor, Cline, OpenClaw).

Она позволяет вашему ИИ читать, извлекать и запоминать контекст из сложных форматов, таких как PDF, документы Word, исходный код и даже изображения (OCR).

## Базовые Технологии
- **Kreuzberg (Rust Core):** Быстрое извлечение Markdown и метаданных из более чем 56 форматов.
- **ChromaDB:** Локальная векторная база данных, работающая полностью автономно (offline).
- **SentenceTransformers:** Использует локальную bootstrapped-копию `all-MiniLM-L6-v2` для генерации эмбеддингов во время работы.

## Установка

### Linux / macOS
```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x setup.sh
./setup.sh
```
`setup.sh` теперь ставит зависимости и загружает модель эмбеддингов в `.omnimem_models/`, чтобы runtime не зависел от сети.

### Windows (PowerShell)
```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\setup.ps1
```
`setup.ps1` выполняет тот же шаг bootstrap для Windows.

### Ручной bootstrap модели
```bash
python3 omni_bootstrap.py
```
Используйте `--offline-only`, если нужно восстановить модель только из локального Hugging Face cache без доступа к сети.

## Offline-safe runtime
- Команды `omni_add.py`, `omni_search.py`, `omni_import.py` теперь по умолчанию загружают модель из `.omnimem_models/`.
- Если локальная директория модели отсутствует, OmniMem сначала пытается восстановить ее из локального Hugging Face cache.
- Если модели все еще нет, OmniMem выводит явную инструкцию запустить `python3 omni_bootstrap.py` вместо непонятного traceback.
- Устанавливайте `OMNIMEM_ALLOW_MODEL_DOWNLOAD=1` только если вы явно хотите разрешить runtime скачивать модель по требованию.

## Как интегрировать с ИИ (Обязательный шаг)

Чтобы ваш ИИ-агент (например, Claude или Cursor) научился использовать эту память, вы ОБЯЗАТЕЛЬНО должны вставить следующие правила в его **Custom Instructions** (пользовательские инструкции) или файл System Prompt:

```markdown
## Протокол OmniMem (Second Brain)
1. **ВСЕГДА ИСКАТЬ СНАЧАЛА:** Прежде чем писать код или решать сложную задачу, ВЫ ОБЯЗАНЫ выполнить: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_search.py "ваш запрос" --full`, чтобы найти контекст. Обязательно используйте флаг `--full` для чтения всего текста. Вы также можете использовать `--json` для вывода в формате JSON.
2. **ВСЕГДА ИМПОРТИРОВАТЬ ДОКУМЕНТЫ:** Когда пользователь просит вас прочитать или запомнить сложный файл (PDF, DOCX, код, изображение), выполните: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_import.py <путь_к_файлу>` для извлечения данных через Kreuzberg.
3. **СОХРАНЯТЬ ЭТАПЫ:** После устранения критической ошибки или завершения этапа выполните: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_add.py "краткое резюме"`, чтобы сохранить контекст для будущих сессий.
```
*(Примечание: Замените `[OMNIMEM_PATH]` на абсолютный путь к вашей директории omnimem, например `/root/omnimem` или `C:\omnimem`)*

## Использование вручную
- **Bootstrap model:** `python3 omni_bootstrap.py`
- **Добавить текст:** `python3 omni_add.py "Пароль сервера 123"`
- **Импортировать файл:** `python3 omni_import.py my_design.pdf`
- **Поиск:** `python3 omni_search.py "пароль" --full`
- **Удалить всё:** `python3 omni_del.py --wipe-all`
