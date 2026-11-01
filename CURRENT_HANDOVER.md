# Передача проекта: нестабильная диаризация после возврата первой Stage 4.2

Дата фиксации: 2026-11-01. Этот файл актуальнее прежнего STAGE2_HANDOVER.md:
последний был намеренно восстановлен вместе с первой версией 4.2.

## Проект опубликован после явного согласия пользователя

Public repository: https://github.com/Amin71518/armenian-speech-translator .
Основной source/submission commit b7bbc959ccb256a9ff27348f46d95a9a363f2589 уже
отправлен в main, remote hash проверен. Предыдущие4commits сохранены, без force
и squash. Локальная веткаmaster отслеживаетorigin/main. Текущий follow-up фиксирует
итог публикации и обновляет chat snapshots; runtime/models не меняются.

По документу включены source/README/docs/tests и3реальных AI chats; не включены
веса, аудио, API keys, .cache/.venv/data/local/reports. Preceding165history blobs
проверены на credential patterns без совпадений; это не абсолютное доказательство
отсутствия любых секретов. Guardian_review exports исключены. Staged deletion
chats/README.md включена в коммит. Итог: PUBLICATION.md и SUBMISSION_CHECKLIST.md.
223tests прошли; качество/physical<=5s не подтверждены и не переобозначались.
Для дальнейших изменений снова учитывать пользовательское разрешение на коммиты;
последующие разговоры требуют нового экспорта, исходные чаты Codex сохранить.

## Пользователь разрешил финальный коммит и публикацию

Пользователь подтвердил «давай закоммитим», с соблюдением документа: включить
исходники/README/полные реальные AI chats; не коммитить веса, аудио или API keys.
Разрешение относится к текущему reviewed snapshot и отправке в public
Amin71518/armenian-speech-translator. Перед commit обновляются3реальных chatexports
и проверяются файлы/история. Исходная staged deletion chats/README.md включается.
Runtime/model changes не входят в этот заключительный шаг.

## GitHub подготовлен, согласие на коммит ещё требуется

Пользователь указал public, Amin71518, armenian-speech-translator. Через сохранённую
Windows Git-авторизацию подтверждён Amin71518; создан пустой public repository:
https://github.com/Amin71518/armenian-speech-translator . Auto-init=False,
source commit/push ещё не делались. Токен не выводился и не сохранялся в проекте.
План конкретного коммита/набора файлов — PUBLICATION_PLAN.md. Предыдущий запрет
коммитить без согласия всё ещё действует; данные о репозитории не отменяют его.

Перед публикацией исправлена существенная ошибка экспортов:7(позднее9)дочерних
журналов оказались внутренними guardian_review, а не проектными беседами. Их
generatedMD убраны из chats/ в ignored.cache/internal-review-exports, исходники
не менялись. Для публикации3настоящих project conversations. В exporter добавлен
фильтр meta.thread_source/source и regression test. Финальные223tests passed
in23.13s, Ruff passed; runtime frozen. Проверка candidates/history paths и credential
patterns прошла. В полный chat экспорт не включать внутренние review-журналы.

## Текущая цель изменена пользователем на оформление к сдаче

После последнего звонка пользователь сказал «Пусть будет так» и поручил оформлять
проект к завершению. GitHub — под конец. Это разрешает Stage5 documentation/delivery
preparation вопреки прежнему noStage5, но не новые алгоритмы, запись звонка или
коммит. Runtime frozen; выбран explicit --experimental-speaker-matching,
default first4.2 сохраняется. Качество ID и physical<=5s не объявлены подтверждёнными.

Прочитан полный Mathrix_AI_Coding_Challenge.docx. Новый evaluator-facing README,
SUBMISSION_CHECKLIST.md, DEMO_GUIDE.md, CHAT_EXPORTS.md. Прежний README сохранён
побайтно в DEVELOPMENT_HISTORY.md. Исправленная классификация локальных журналов дала3экспорта
реальных чатов в chats/; guardian_review служебные журналы исключены, manifest содержит source/export hashes; исходные
журналы не менялись. Это local-record-derived export, не официальный UI export;
нужно проверить охват и обновить текущую сессию непосредственно перед GitHub.
Служебные инструкции/внутренние записи не экспортируются, сообщения не переписываются.
Staged deletion chats/README.md сохраняется. .gitattributes сохраняет байты chatMD.
Скрипт экспорта имеет4теста. Финальная валидация оформления — VALIDATION_REPORT.md:
222passed in20.05s, Ruff/Poetry/CLIhelp прошли. check_submission проверяет candidates,
ключевые credential patterns, локальные ссылки и export hashes; он не меняет index.

Все исторические протоколы ниже остаются историей, не отменой выбранного snapshot.

## Последний реальный звонок с trial — оценка пользователя ещё не получена

Пользователь сообщил о дефиците времени и хочет оставить вариант, если результат
звонка его устроит. Прислан log с --experimental-speaker-matching; менять алгоритм
автоматически после этого не следует. Numeric report:
reports/user_call_trial_observation.json, transcript повторно не сохранялся.

67.6s wall,12/12jobs,16printed parts (2Me+14System),8/14System parts Unknown,
созданы2ID без3/4/5. Speaker2 зарегистрирован только44.893s из1.552s short views;
перед ним реплики40.445/41.885/43.165s длительностью1.136/1.072/1.328s не могли
создать новый ID. В24.445s full matchSpeaker1=.7279, halves=.4583; только первая
половина matchSpeaker1, втораяUnknown, поэтому anchored exception не сработал.
Есть отдельные Unknown tails528/336/864ms. В48.189s снова Speaker1, но истинную
личность этого участка пользователь ещё не подтвердил; фактическое число людей
данного звонка не установлено из одного log. Me сохранился.

Raw/phrase losses и VAD discontinuities0, workerexit0, resourcesclosed, unfinished0.
MaxVADdecision→output1.886s НЕ speech-end E2E; clocks unvalidated. Этот короткий
звонок не доказывает стабильность/DER и содержит многоUnknown. Удовлетворённость
пользователя и соответствие ID реальным людям ещё нужно узнать. Stage4.3 не
объявлять принятым, коммитов/новой записи звонка нет.

## Актуальное продолжение: отдельный matching trial, baseline по умолчанию

Пользователь поручил «делай всё возможное» и дал реальные источники теста:
YouTube eVz3O9Z6h7g0–15s и -n9QX6VAaUM42–44s, в каждом один голос со слов
пользователя. Скачаны только публичные отрывки (не запись звонка), hash/provenance
в data/local/user_source_sections. yt-dlp отдельно в.cache/ytdlp-runtime;
Poetry/runtime dependency versions не менялись. Полный протокол и отрицательные
результаты: **SPEAKER_MATCHING_TRIAL.md** (читать прежде следующей настройки).

Реальный Silero даёт A6+6+3.248s, B1.648s. На A/B×3 baseline получает1ID и16.944s
Unknown, trial2ID и0Unknown на этом материале. Полная FastConformer/NLLB worker
проверка:12/12jobs в обоих режимах,15parts/6Unknown baseline против12parts/0Unknown
trial; workerexit0, session/WAV cleaned. Это повтор одних файлов, не независимая
проверка звонков или WER/DER/latency. Reports:user_sources_production_verified.json,
user_source_pipeline_trial.json подreports/. Hypotheses не сохранены; временный
technical console capture public ASR/MT удалён после проверки, numeric JSON оставлен.

**Новый флаг `--experimental-speaker-matching` требует `--diarize`, default=False.**
Short1.5–<2s новый ID возможен после согласия first/last1s views в пределах этой
же ячейки; known short matches не обучаются. При несогласии полных2s halves
существующий ID допускается только когда full и каждая половина отдельно match
одному ID по старым threshold/margin, без learning в exception. Нет cross-job
аудиобуфера/накопления контекста, подавления Unknown, новых фильтров или лимита2ID.
Обычная команда остаётся first4.2; exact reference parity150jobs/169cells прошла.

**Известные риски, не скрывать:** short1.5 при synthetic band даёт6ID/3voices,
3duplicates и1.52s wrong-person; anchored halves принял одну2s overlap ячейку.
Baseline тоже неверно маркирует некоторые short mixed windows. Поэтому trial
не стал default и не считается принятым. Source policy/candidate reports описаны
в SPEAKER_MATCHING_TRIAL.md, прежние отвергнутые варианты не возвращались.

Терминальные Speaker decision JSON сокращены, добавлены pre-updatehalf_matches,
probe_kind/experimental; numeric observers получают полное событие. Это не
посекундный спам. Итоговые216tests прошли, Ruff/Poetry прошли. ASR/MT/WAV неизменны,
Me/HY+EN/accounting/shutdown сохранены. Коммитов и записи живого звука нет.

Команда для **отдельной экспериментальной** пользовательской проверки:
`poetry run python -m armenian_speech.combined --microphone-device 14 --device 16 --diarize --speaker-diagnostics --experimental-speaker-matching`.
Для прежнего baseline убрать толькопоследний флаг. Stage4.3не принят, Stage5не начинать.
Финальная release-проверка после двух boundary cases:218 passed in19.98s,
reports/speaker_trial_release_tests.xml. Итоговый adverse report:
reports/speaker_candidates_production_verified.json; оба baseline/trial совпадают
с соответствующими offline candidate labels/durations во всех проверенных сценариях.

## Последний пользовательский тест — Me → первый → второй собеседник

Получен новый diagnostic log; пользователь явно указал порядок. Это **два** remote
в данном контроле, не три из исторического звонка ниже. Источник mic14, loopback16.
Числовой разбор: reports/user_ordered_two_remote_diagnosis.json; подробности в
начале DIARIZATION_DIAGNOSIS.md. Transcript из вложения повторно не сохранялся.

Speaker1 соответствует первому блоку18.952–23.064s; Speaker2 — второму28.648–44.632s
с4s Unknown внутри34.648–38.648s. Обе2s ячейки отклонены только по half disagreement:
full к Speaker2=.7103/.7798, к Speaker1=.0839/.1946, half-to-half=.4121/.3140<.47.
Принимая пользовательский порядок, это отказ внутри блока второго голоса, а не
новый человек или потеря registry. Затем снова Speaker2. Есть отдельный160ms
too_short tail первого блока, давший empty ASR. Новых3/4/5ID в этом запуске нет.
9/9jobs, zero registered raw/phrase/VAD losses, workerexit0. Физическая точность
mic ADC остаётся unvalidated. Изменений live алгоритма после этого лога нет.

Следующий узкий контроль — проверить каждую половину относительно уже известных
голосов (и реальные смены), а не просто отменять half gate. Этих half-to-centroid
чисел в текущих событиях ещё нет; их нельзя вывести из full score/half score.
Решение о конкретном изменении пока не принято; прежние отвергнутые эксперименты
автоматически не возвращать. Нельзя объявлять общую стабильность по этому контролю.

## Последнее изменение устройств — 2026-11-01, подключены OnePlus Buds 3

После ошибки `Selected device does not support the requested input channel count`
выполнен read-only опрос в обычной Windows **вне песочницы**, без захвата звука.
Старые9/10 больше не соответствуют прежней паре устройств:

- sounddevice9 теперь render `Первичный звуковой драйвер`, input channels=0.
  Именно это объясняет отказ проверки микрофона с `--microphone-device 9`.
- Встроенный Microphone Array WASAPI теперь **14**, default48kHz; отдельная
  `check_input_settings` приняла mono PCM16 48000Hz. Реальный захват не запускался.
- Микрофон OnePlus Buds3 WASAPI —15, mono16kHz; его использовать только при
  явном выборе пользователя, с `--microphone-rate 16000`.
- PyAudioWPatch loopback **16** — OnePlus Buds3; **17** — Realtek Speakers.
  Выбирать по фактическому устройству, в котором слышен звонок. Список сам по себе
  не доказывает маршрут конкретного приложения. Нумерации двух библиотек различны.

Для встроенного микрофона: `--microphone-device 14`; если звонок в Buds,
`--device 16`, если в Realtek speakers — `--device 17`. Остальные настройки прежние.
Перечисления устройств внутри/вне песочницы опять различались (число WDM inputs
и reported MME channels), поэтому актуальность проверять в обычной Windows.
Команды9/10 ниже — исторические результаты, не текущие универсальные ID.

## Дополнение текущего чата: первый диагностический шаг

Пользователь уточнил: в последнем звонке **три удалённых человека**, громкость и
качество точно менялись. Полный лог ниже сохранён; покадровой разметки голосов нет.

После чтения документов подтверждены194 baseline tests. Далее добавлено только
opt-in наблюдение `--speaker-diagnostics`, требующее `--diarize`: события до ASR
с причинами/длительностями/RMS/half и registry scores/counts/centroid step, плюс
финальный health summary без посекундных уровней. Обычная команда остаётся прежней.
Исходные SHA63 файлов ниже относятся к состоянию восстановления **до этого шага**;
четыре live/speaker файла теперь имеют диагностические добавления. Правила первой
4.2 и параметры не изменены. Нет накопления контекста/склейки/новых фильтров.

Подробный протокол и план: DIARIZATION_DIAGNOSIS.md. Native offline comparison
точного SHA-проверенного первого speakers.py с текущими quiet/diagnostic arms:
везде совпали labels/PCM/bounds/counts/centroids/extractor inputs. Синтетическая
полоса300–3400Hz после чистого enrollment воспроизвела пять ID для трёх публичных
голосов (два дубликата). Gain×0.1 показал отказы тихих половин даже при хорошем
full-window match. Это механизмы на повторно использованных английских клипах,
не доказательство причин конкретного звонка и не улучшение качества.

После изменения:209 tests passed in23.08s; Ruff/Poetry passed. Отчёты:
reports/speaker_diagnostics_tests.xml, reports/speaker_decisions_verified.json.
Точный reference: .cache/first42-speakers-baseline.py, hash проверяет сам probe.
Исходный snapshot этой сессии: .cache/diarization-diagnostic-start.json.
Живые устройства/звонки в этом чате не запускались, запись не согласовывалась.
ASR/MT/WAV/зависимости не менялись, коммитов нет. Stage4.3 всё ещё не принят.
Дополнительный offline контроль channel vs frozen/online centroid выполнен с
сохранением возможности новых людей: freeze ухудшил5->6ID и дал2s ошибочного
присвоения чужого ID на bandwidth-серии. В live freeze не переносился. При возврате
исходного канала оба варианта узнают исходные1/2/3 (повторены те же клипы, не новая
речь). reports/speaker_decisions_with_frozen_control.json содержит итог150jobs/
169cells с полной baseline/quiet/diagnostic идентичностью. Следующий шаг —
отдельно согласованный независимый материал армянского разговора/числовые события
пользовательского запуска. Не менять live алгоритм только ради меньшего Unknown.
Финальная проверка после offline control:210 passed in23.81s, Ruff/Poetry passed;
reports/speaker_diagnostics_control_tests.xml. Предыдущие209tests выше относятся
к первому шагу до добавления отдельного теста самого offline control.

## Рабочая среда и ограничения

- Проект: `C:\Users\gorma\PycharmProjects\SpeechRecognition`.
- Windows, PowerShell, Python 3.13, Poetry, CPU без CUDA; ориентир железа из прежних
  этапов: i5-13420H, 16 GB RAM.
- ASR: локальный FastConformer RNN-T INT8 (Vana-Labs), greedy.
- Перевод: локальный NLLB-200 distilled 600M, greedy, CPU float32.
- VAD: Silero ONNX. Микрофон: sounddevice 0.5.6. Системный звук:
  PyAudioWPatch 0.2.12.9 WASAPI loopback. Speaker embeddings: CAMPPlus ONNX,
  sherpa-onnx 2.0.1, один CPU-поток.
- Существующий WAV pipeline должен продолжать работать. HY/EN всегда выводятся
  вместе после перевода; промежуточный HY отдельно не показывать.
- Коммиты — только после согласования пользователя. В этой работе коммитов не было.
- Сохранить ВСЕ существующие dirty changes и staged deletion `chats/README.md`.
  Не делать общий `git reset`, `checkout .`, очистку untracked, автоматический stash.
- Не сохранять новые записи звонков без отдельного согласования. Приведённый ниже
  текст пользователь прямо попросил сохранить. Это не экспорт всего AI-чата.
- Проблема английских терминов внутри армянской речи отложена. Сейчас фокус —
  качество определения говорящих. Диаризация не должна считаться принятой.

## Что сейчас реально восстановлено

По прямому запросу пользователя выполнен точный возврат к **первой Stage 4.2** —
той версии, в итоговом сообщении которой было «194 теста» и команда без min-audio-ms.
Это не предыдущая экспериментальная версия с накоплением контекста.

Проверка возврата: `reports/restore_first42.json`:

- Все 63 файла из снимка перед первыми исправлениями звонков совпали по SHA-256.
- Отличий и лишних исходных файлов на момент проверки не было.
- Git index сохранился.
- После возврата: **194 passed in 18.94s**, Ruff, Poetry и whitespace check прошли.
- Снимок контрольных сумм: `.cache/stage43_before.json`.
- Вариант непосредственно перед откатом сохранён в
  `.cache/before-first42-restore/` (только локальная страховка).
- В отчёте был `live_sessions: 1`: это наблюдение наличия каталога в тот момент,
  а не доказательство работающего процесса. Ничего такого не удалять вслепую.

**В текущем коде НЕТ:**

- `--min-audio-ms`, 300/500 ms фильтра аудиочастей;
- пула коротких speaker-кандидатов / накопления контекста между репликами;
- специального `speaker_epoch`, отличающего потери от обычного VAD idle;
- последних специальных текстовых правил против `Հովհ.` и отдельных ա/է;
- добавленного после первого звонка числового ASR guard для аудио <20 ms.

Восстановление последнего пункта тоже было отменено ради точного возврата. Известная
причина RuntimeWarning остаётся: NumPy NeMo preprocessing на 160/319 samples
давал undefined variance и nonfinite features; на320samples предупреждения не было.
Это было воспроизведено синтетически, а не доказано для конкретного звонка.
Не путать: в последнем присланном логе такого предупреждения нет.

Не запускать архивные исправления из `.cache/` и не восстанавливать автоматически
отвергнутый вариант. Старые отчёты stage43 в `reports/` — история экспериментов,
а не результаты действующей версии. Отдельные поздние диагностические скрипты
`check_short_features.py` и `check_speaker_stability.py` убраны из активного scripts/;
их копии могут находиться в локальной страховке.

## Запуск и проверенные устройства

Текущая команда первой 4.2:

```powershell
poetry run python -m armenian_speech.combined --microphone-device 9 --device 10 --diarize
```

Без `--diarize` сохраняется прежний Me/System режим. Перед проверкой новой версии
нужно остановить старый процесс Ctrl+C и запустить заново: загруженный worker
сам не перечитывает изменённый исходный код.

Устройства проверялись повторно в обычной среде Windows:

- sounddevice input9: **Microphone Array (Intel Smart Sound Technology for Digital
  Microphones), WASAPI**, встроенный микрофон, 48 kHz.
- PyAudioWPatch loopback10: **Speakers (Realtek(R) Audio) [Loopback]**, 48 kHz stereo.
- Это две отдельные системы нумерации. Устройство9 не означает микрофон гарнитуры.
- Один раз пользователь получил пустой список loopback. Причина не установлена.
  При повторном опросе вне песочницы loopback10 появился и успешно открылся.
  Список внутри песочницы отличался от обычной среды Windows.

Пользователь подтвердил поступление реального системного звука командой:

```powershell
poetry run python -m armenian_speech.system_audio --device 10 --duration 10
```

Результат:469blocks,480256frames,10.0053s аудио, peak0.0999146,
status_events=0, input_overflows=0, queue_dropped_frames=0, все кадры обработаны,
pending_frames=0, поток закрыт. Это подтверждает захват того воспроизведения,
но не автоматически любой маршрут приложения звонка и не качество диаризации.

При смене устройства/подключении гарнитуры повторно выполнить:

```powershell
poetry run python -m armenian_speech.combined --list-devices
```

## Действующие интерфейсы и возможные причины проблемы

Основные файлы:

- `src/armenian_speech/combined.py`: два источника, отдельные VAD/ресемплеры,
  общая очередь с обслуживанием по источникам и один ASR/MT worker.
- `src/armenian_speech/live_pipeline.py`: Windows spawn, WorkerConfig,
  InferenceJob; System внутри worker проходит SpeakerTracker до ASR.
  `source_label` сохраняет System для счётчиков; `speaker` — отображаемая метка.
  Один исходный job завершается только на last_part; части выводят отдельные HY/EN.
- `src/armenian_speech/speakers.py`: Extractor, Registry, SpeakerTracker.
- `src/armenian_speech/loopback_vad.py`: завершение по idle без выдуманных нулей;
  обычный idle может менять epoch VAD. Это не обязательно потеря аудио.
- `src/armenian_speech/asr_onnx.py`: файловый transcribe(Path).

Восстановленный алгоритм:

1. Делит System VAD PCM на неперекрывающиеся2sячейки.
2. Для полной ячейки дополнительно сравнивает embeddings её1sполовин;
   при провале проверок выставляет Unknown.
3. Extractor не выдаёт embedding для <1s и RMS<0.003.
4. Новые ID создаются только из полной2sячейки (`learn=True`). Короткие ячейки
   могут лишь совпасть с существующим голосом или остаться Unknown.
5. Registry использует нормализованные embeddings, cosine threshold0.47,
   margin0.08, максимум8centroids. Если лучший score ниже threshold, при разрешённом
   обучении создаётся новый ID. Близкие два score дают Unknown. Нет объединения
   дублирующих кластеров, учёта канала или подтверждения нового ID несколькими ходами.
6. Соседние одинаковые метки склеиваются. Разные, в том числе Unknown, дают
   самостоятельные ASR/MT-фрагменты. Это может обрывать слова/контекст.

Это объясняет **механизмы**, способные создавать много Unknown и дополнительные ID,
но не доказывает причину каждой ошибки в звонке без аудио/сопоставления с людьми.
Нельзя объявлять Speaker3/4/5 реальными новыми участниками только по номерам.
Нельзя просто скрыть Unknown, принудительно присвоить предыдущий ID или ограничить
число говорящих двумя: это может замаскировать ошибки и слить разных людей.

## Последний звонок после точного возврата первой 4.2

Пользователь сообщает: «Спикеры со временем увеличиваются почему-то и unknown
очень много». Его оценка до этого: самая первая версия работала лучше поздних
исправлений, поэтому выбран именно этот baseline. Однако текущий звонок показывает,
что даже baseline не решает задачу устойчиво.

Наблюдения по тексту:

Подсчёт именно напечатанных строк (не всех VAD/worker jobs):

| Метка | Строк |
| --- | ---: |
| Me | 23 |
| Unknown | 13 |
| Speaker 1 | 11 |
| Speaker 3 | 2 |
| Speaker 4 | 1 |
| Speaker 5 | 1 |
| Всего | 51 |

Из28строк системного источника13имеют Unknown. Это частота метки в данном выводе,
а не ошибка диаризации/DER: истинные личности и пропущенные фразы не размечены.

- Видны Speaker1, Speaker3, Speaker4, Speaker5. Speaker2 в присланных строках нет.
  Он мог быть создан внутренне без напечатанного текста: ASR/фильтр могут подавить
  результат. Это гипотеза, а не подтверждение конкретного события.
- Первый видимый Speaker3 —1:55, Speaker4 —3:32, Speaker5 —4:04.
- Частые Unknown есть и на содержательных фразах, а не только на одиночных звуках.
- Повторился подозрительный `Me HY: Հովհ. EN: John: I know.` в0:58. Без аудио
  нельзя независимо установить, был ли это шум, кашель, речь или другая причина.
- Ошибки ASR и перевода остаются отдельными от ошибок меток. Английский текст
  не является эталоном распознанной армянской речи.
- Нет записи аудио, правильного текста, разметки личности говорящего для каждой
  строки, диагностических similarity scores и финального capture summary.
- Точное фактическое число удалённых говорящих и время их смены **в этом звонке**
  не указано. В более ранних проверках планировались два удалённых собеседника,
  но это не заменяет ground truth последнего звонка.
- Метрики DER, accuracy идентичностей, WER этого звонка и реальную задержку
  по такому текстовому выводу честно вычислить нельзя.

## Полный лог, присланный пользователем

Сохранён без исправления слов, меток и переводов:

```text
Combined live active. Sources: Me + System. Press Ctrl+C to stop.
[00:00:02] Me  HY: Բարեւ ձեզ։  EN: Hello to you.
[00:00:06] Me  HY: Ինչպե՞ս եք։  EN: How are you?
[00:00:11] Me  HY: Ես լավ եմ, դուք ոնց եք։  EN: I'm fine, you are.
[00:00:58] Me  HY: Հովհ.  EN: John: I know.
[00:00:58] Unknown  HY: Քա։  EN: What is it?
[00:01:03] Me  HY: Ինչպե՞ս ես։  EN: How are you?
[00:01:06] Unknown  HY: Լավ էլ դու ասա, ինչի մեկ։  EN: Well, you say one of these.
[00:01:08] Speaker 1  HY: Կինոյի զուգը շատ ցածր ա։  EN: The movie's pairing is very low.
[00:01:15] Me  HY: Չեմ կարա պատասխանեմ էդ հարցին։  EN: I can't answer that question.
[00:01:23] Me  HY: Դե տենց ասաց։  EN: That's what he said.
[00:01:23] Speaker 1  HY: Ցածր զուկով։  EN: With a low pitch.
[00:01:25] Unknown  HY: Ցածր ձայնով ենք նաեւ։  EN: We're also quiet.
[00:01:27] Speaker 1  HY: Չի լսվում ընդհանրապես։  EN: It's not heard at all.
[00:01:29] Unknown  HY: Կոչ չունի քույրե։  EN: There's no call, sister.
[00:01:38] Unknown  HY: Այ։ Այուս մ։  EN: Yes, yes, yes, yes.
[00:01:40] Speaker 1  HY: Բիտվային ռուկի։  EN: It's like a live rock.
[00:01:42] Me  HY: Պարզ ա, պարզ ա, քեռ ինչո՞վ ա զբաղվում։  EN: It's simple, it's simple, what is it that you do?
[00:01:46] Unknown  HY: Էդյու, մնացել ա։  EN: Ed, you're out of here.
[00:01:51] Me  HY: Ո՞ւր ա գնացել։  EN: Where did he go?
[00:01:53] Speaker 1  HY: Ի՞ւր է գնացել էդ գարի։  EN: Where did you go?
[00:01:55] Speaker 3  HY: Թուն Թգայյան։  EN: I'm not going to lie.
[00:01:57] Unknown  HY: Ոչ։  EN: No, I did not.
[00:02:01] Me  HY: Հյուրը գնացը։  EN: The guest train.
[00:02:04] Speaker 1  HY: Այո։  EN: Yes, you did.
[00:02:07] Me  HY: Ասեցի՝ գնացինք, գնացք գրեց։  EN: I said, "We're going". The train called.
[00:02:14] Unknown  HY: Ուրեմն չի լսում։  EN: So he doesn't listen.
[00:02:18] Me  HY: Կա բարեր, որ ճիշտ ա լսում, բայց կա բարեր, որ շատ սխալ ա լվում։  EN: There are good things about hearing right, but there are good things about washing wrong.
[00:02:28] Me  HY: Կխոսեմ մի քիչ էլ։  EN: Let me tell you a little bit.
[00:02:32] Unknown  HY: Տղա ջան, ես ուզում եմ։  EN: Man, I want to.
[00:02:36] Speaker 1  HY: Որ հասցնենք ֆիլմս նայել, գնամ լողանամ, մազերս։  EN: I'm going to go swimming, my hair.
[00:02:44] Speaker 1  HY: Նաավ աշխատանքի։  EN: So was work.
[00:02:51] Me  HY: Հասկանալի է...  EN: It is understandable.
[00:02:59] Me  HY: Տմբան։  EN: The drum.
[00:02:59] Speaker 1  HY: Տատիկը ինչո՞վ է։  EN: What is Grandma?
[00:03:04] Me  HY: Տատիկա։  EN: I'm not going to be a big fan.
[00:03:08] Me  HY: Ուզում ա կոֆի։  EN: I'll have some coffee.
[00:03:11] Speaker 1  HY: Ժամը վեցին։  EN: It's six o'clock.
[00:03:15] Me  HY: Կամ էլ ճաշ չգիտեմ։  EN: Or I don't know about lunch.
[00:03:23] Speaker 1  HY: Հասկանալի է։  EN: That is understandable.
[00:03:26] Me  HY: Թող ամուսկանի բան մասին։  EN: Let the husband talk about something.
[00:03:29] Unknown  HY: Ամսայի ընդունեցի։  EN: I accepted a month.
[00:03:32] Speaker 4  HY: Առաջյանը այդ սած։  EN: The first one is this one.
[00:03:34] Unknown  HY: Ա, լավ։  EN: Oh, that's good.
[00:03:36] Speaker 3  HY: Իսկ եթեուց վանոն։  EN: What about Van Gogh?
[00:03:38] Unknown  HY: Աղջահար հարցին պատասխան։  EN: The answer to the greeting question.
[00:03:39] Me  HY: Ներվերը ուտելու ա, ուտելու ա։  EN: Forgiveness is to eat, to eat.
[00:03:43] Unknown  HY: Այ է խոսեմ, վ։  EN: I'm going to talk to you, W.
[00:03:49] Me  HY: Աե ասեմ մի բառը էլի զսրրեցիր։  EN: Let me just say one more word.
[00:03:58] Me  HY: Դու ասապրուստը բարեւ ու սո։  EN: You're the one who said goodbye.
[00:04:04] Speaker 5  HY: Դեքս քիչ մսվող է, մազիսամ շ։  EN: It's a little bit of a mess, you hairy guy.
[00:04:11] Me  HY: Արրա ինչքան ս, ինչքան սոլը չէ։  EN: Do as much as you can, not as much as you can.
```

## Что уже пробовали и почему не повторять автоматически

После первого 4.2 были несколько итераций, отвергнутых по реальным звонкам:

- Склейка Unknown/маленьких хвостов с соседними speaker-фрагментами: пользователь
  сообщил ухудшение и пропажу второго говорящего.
- Фильтр аудиочастей300/500ms и дополнительные текстовые исключения: короткие
  фантомы могли исчезать, но устойчивость меток не была достигнута.
- Удаление проверки1sполовин и bounded-пул сходных коротких реплик: unit tests и
  чистые публичные английские клипы показывали улучшение, однако пользователь
  снова сообщил «ужасно работает» и потребовал именно первую4.2.

Те эксперименты проходили207/206/211тестов в разные моменты. Это **не текущий**
набор тестов и не доказательство качества настоящего армянского разговора.
Текущая восстановленная версия —194теста. Не выдавать чистые клипы с известными
границами за подтверждённую диаризацию звонка.

## Следующая работа

1. Прочитать этот файл, README, PLAN, DECISIONS, TESTS, DIARIZATION_COMPARISON,
   действующий код и состояние Git. Старые документы восстановлены к baseline.
2. Сначала отделить потерю аудио/ошибки маршрута, VAD/ASR-обрывки и ошибки
   speaker matching. Не исправлять все симптомы произвольной сменой порогов.
3. Сделать причины Unknown/создания нового ID наблюдаемыми: длительность окна,
   best/second similarity, причина отказа, состояние кластера. Диагностика должна
   быть opt-in и по событиям, без возвращения посекундного спама в обычный режим.
4. Проверить дрейф/дробление centroid, влияние длины и звонкового канала,
   согласованность идентичностей между VAD-фрагментами. Подобрать воспроизводимый
   контроль с несколькими различимыми голосами и заранее известным порядком.
5. Явно различать уменьшение Unknown и ошибочное принудительное присвоение ID.
   Оценивать ложные новые ID, слияние людей, возврат старого голоса, короткие ответы,
   ASR-контекст, очередь и задержку. Не объявлять успех по одним unit tests.
6. Не накапливать новые сложные механизмы без сравнительных результатов. Если
   нужна запись/разметка живой речи, сначала согласовать это с пользователем.
7. Stage4.3 не принят. Stage5 не начинать, физическую задержку<=5s не обещать:
   раньше независимая разметка конца речи была пропущена пользователем, ADC clock
   не подтверждён. Не запрашивать повторно уже отменённую endpoint-проверку.

Краткий стартовый промпт находится в NEXT_CHAT_PROMPT.md.
