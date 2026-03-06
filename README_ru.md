# OmniMem v1.6.0 - Устанавливаемый CLI-Мозг 🧠

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

### Режим package install
```bash
python3 -m pip install .
omnimem --version
```
В режиме package install OmniMem хранит runtime-данные в user data directory, а не внутри `site-packages`, и предоставляет команду `omnimem` прямо в PATH.

### Установка напрямую с GitHub
```bash
python3 -m pip install "git+https://github.com/manhlinhfs/omnimem.git@main"
omnimem --version
```

### Ручной bootstrap модели
```bash
python3 omni_bootstrap.py
```
Используйте `--offline-only`, если нужно восстановить модель только из локального Hugging Face cache без доступа к сети.

### Проверка состояния runtime
```bash
python3 omni_doctor.py
python3 omni_doctor.py --deep
python3 omni_doctor.py --json
```

### Обновление текущего клона
```bash
python3 omni_update.py --check
python3 omni_update.py
```
`omni_update.py` обновляет текущую ветку с fast-forward only семантикой, отказывается перезаписывать грязный worktree, переустанавливает зависимости при изменении `requirements.txt` и обновляет локальное состояние bootstrap модели.

Для package install `omnimem update` не поддерживается; обновляйте через `pip`.

## Offline-safe runtime
- Команды `omni_add.py`, `omni_search.py`, `omni_import.py` теперь по умолчанию загружают модель из `.omnimem_models/`.
- Если локальная директория модели отсутствует, OmniMem сначала пытается восстановить ее из локального Hugging Face cache.
- Если модели все еще нет, OmniMem выводит явную инструкцию запустить `python3 omni_bootstrap.py` вместо непонятного traceback.
- Устанавливайте `OMNIMEM_ALLOW_MODEL_DOWNLOAD=1` только если вы явно хотите разрешить runtime скачивать модель по требованию.

## Как интегрировать с ИИ (Обязательный шаг)

Чтобы ваш ИИ-агент (например, Claude или Cursor) научился использовать эту память, вы ОБЯЗАТЕЛЬНО должны вставить следующие правила в его **Custom Instructions** (пользовательские инструкции) или файл System Prompt:

```markdown
## Протокол OmniMem (Second Brain)
1. **ВСЕГДА ИСКАТЬ СНАЧАЛА:** Прежде чем писать код или решать сложную задачу, ВЫ ОБЯЗАНЫ выполнить: `[OMNIMEM_PATH]/omnimem search "ваш запрос" --full`, чтобы найти контекст. Обязательно используйте флаг `--full` для чтения всего текста. Вы также можете использовать `--json` для вывода в формате JSON.
2. **ВСЕГДА ИМПОРТИРОВАТЬ ДОКУМЕНТЫ:** Когда пользователь просит вас прочитать или запомнить сложный файл (PDF, DOCX, код, изображение), выполните: `[OMNIMEM_PATH]/omnimem import <путь_к_файлу>` для извлечения данных через Kreuzberg.
3. **СОХРАНЯТЬ ЭТАПЫ:** После устранения критической ошибки или завершения этапа выполните: `[OMNIMEM_PATH]/omnimem add "краткое резюме"`, чтобы сохранить контекст для будущих сессий.
```
*(Примечание: Замените `[OMNIMEM_PATH]` на абсолютный путь к вашей директории omnimem, например `/root/omnimem` или `C:\omnimem`)*
Если OmniMem установлен как package и `omnimem` уже доступен в PATH, можно использовать просто `omnimem` вместо `[OMNIMEM_PATH]/omnimem`.
Старые скрипты `omni_*.py` по-прежнему доступны при необходимости.

## Единый CLI (рекомендуется)
Для clone mode используйте launcher-скрипты из репозитория: они автоматически предпочитают локальный `venv`. На Windows используйте `.\omnimem.ps1` или `.\omnimem.bat` из корня репозитория. В package mode используйте установленную команду `omnimem`.

- **Показать версию:** `python3 omnimem.py --version`
- **Показать версию через launcher:** `./omnimem --version`
- **Показать версию через установленный package:** `omnimem --version`
- **Doctor:** `./omnimem doctor`
- **Проверить обновления:** `./omnimem update --check`
- **Обновить этот клон:** `./omnimem update`
- **Bootstrap model:** `./omnimem bootstrap`
- **Добавить текст:** `./omnimem add "Пароль сервера 123"`
- **Импортировать файл:** `./omnimem import my_design.pdf`
- **Поиск:** `./omnimem search "пароль" --full`
- **Поиск с фильтрами:** `./omnimem search "release" --source omnimem --since 2026-03-06`
- **Искать только импортированные PDF:** `./omnimem search "invoice" --mime-type application/pdf`
- **Удалить всё:** `./omnimem delete --wipe-all`

## Старые standalone-скрипты все еще работают
- `python3 omni_add.py "Пароль сервера 123"`
- `python3 omni_import.py my_design.pdf`
- `python3 omni_search.py "пароль" --full`
- `python3 omni_del.py --wipe-all`
- `python3 omni_doctor.py`
- `python3 omni_update.py --check`

## Для разработки
- **Запустить тесты:** `python3 -m unittest discover -s tests -v`
- **Собрать package:** `python3 -m build`
- **Посмотреть release notes:** `CHANGELOG.md`
- **Посмотреть roadmap:** `ROADMAP.md`
- **Прочитать docs по install modes:** `docs/install-modes.md`
- **Прочитать docs по search filters:** `docs/search-filters.md`
- **Следовать release checklist:** `docs/release-checklist.md`
