Продолжаем оформление Mathrix AI Coding Challenge в этом проекте.

Сначала прочитай CURRENT_HANDOVER.md, README.md, SUBMISSION_CHECKLIST.md,
VALIDATION_REPORT.md и CHAT_EXPORTS.md. При необходимости история —
DEVELOPMENT_HISTORY.md, DECISIONS.md, TESTS.md и SPEAKER_MATCHING_TRIAL.md.

Пользователь выбрал текущий вариант после звонка и разрешил оформление к сдаче.
Runtime/model behavior заморожены. Выбран explicit --experimental-speaker-matching;
обычная команда без флага сохраняет первую Stage4.2. Не продолжать оптимизацию
автоматически и не объявлять физические <=5s/точность диаризации подтверждёнными.

Текущая конфигурация: встроенный mic WASAPI14, Buds loopback16, Realtek loopback17;
IDs меняются, при необходимости проверить вне песочницы.
Команда:
poetry run python -m armenian_speech.combined --microphone-device 14 --device 16 --diarize --experimental-speaker-matching
Для исследования добавить --speaker-diagnostics, для обычного вывода он не нужен.

Финальное оформление подготовлено в Markdown. В chats/ находятся3local-record
экспорта реальных чатов; служебные guardian_review журналы исключены, не пересказы; manifest содержит hashes. Перед GitHub
обновить текущую сессию скриптом export_project_chats, проверить охват/содержимое.
Оригинальные чаты в Codex сохранить. Экспорт не является официальным UI export;
он охватывает найденные локальные session records с cwd проекта, не другиехосты.

GitHub пользователь отложил на самый конец. Не создавать remote/репозиторий,
не публиковать и не коммитить без соответствующего поручения. Сохранить все dirty
changes и staged deletion chats/README.md; этот файл не восстанавливать.
Проверка состава: poetry run python -m scripts.check_submission.
Запись звонков требует отдельного согласования; её не запускать для оформления.
