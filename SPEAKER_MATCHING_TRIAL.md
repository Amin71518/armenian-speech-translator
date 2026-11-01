# Speaker matching trial — 2026-11-01

Пользователь поручил продолжить исправления и предоставил два публичных источника:

- A: https://www.youtube.com/shorts/eVz3O9Z6h7g —0–15s, один голос со слов пользователя.
- B: https://www.youtube.com/watch?v=-n9QX6VAaUM —42–44s, один другой голос.

Получены только указанные отрывки, не запись звонка. Они находятся в игнорируемом
`data/local/user_source_sections/`, ссылки/границы/SHA-256 — в PROVENANCE.json.
Первоначальный web fetch не сработал. Для подготовки использован yt-dlp2026.10.26
в изолированном `.cache/ytdlp-runtime` и уже установленный ffmpeg. Poetry и версии
runtime зависимостей проекта не менялись. YouTube предупреждал о неполном JS
challenge solving; оба отрывка скачались. Декодирование проверяет длительность
с допуском0.1s и checksum перед каждым replay. Все следующие inference checks offline.

## Что удалось воспроизвести

Реальный Silero, прежняя конфигурация, mono16k PCM, известная1s тишина вокруг каждого
отрывка; resampling через PyAV. A даёт сегменты6.0,6.0,3.248s, B —**1.648s**.
Тишина/pre-roll входят в PCM длительность, не объявляются размеченной речью.
Повтор A/B трижды, registry не сбрасывается. Это12 jobs и50.688s VAD PCM, не50s
независимых наблюдений. Прямые файлы не моделируют Bluetooth/WASAPI/громкость Windows.

Baseline создаёт только Speaker1: B не может создать ID при1.648s. Ещё6 ячеек A
остаются Unknown из-за half gate. Совпадения отдельных половин с centroid теперь
видны в opt-in событии `half_matches`, вычисленном **до** создания/обновления ID.

## Проверенные варианты, включая отрицательные результаты

`scripts/check_speaker_candidates.py` проводит ablation на прежних12 evaluation
utterances LibriSpeech, трёх corpus speaker ID; длительности1/1.264/1.52/1.968/2/4s,
gain, synthetic band300–3400Hz, pre-roll, AB/BA, overlap и короткие смеси25/50/75%.
Без подбора cosine threshold по ошибкам;0.47/margin0.08/capacity8 сохранены. Длины
для исследования включают наблюдавшиеся в пользовательском логе; это исследование
сбоев, не независимая оценка accuracy. Кэш native embeddings используется только
в offline probe; время вычислений из него не является benchmark.

- Регистрация от1.25s убирает Unknown на чистой серии1.264s, но создаёт4ID для3голосов.
- Регистрация от1.5s на clean1.52s даёт3ID и0Unknown, но после band-смены —6ID
  для3голосов,3дубликата и1.52s присвоения другому человеку. После synthetic pre-roll
  на коротких репликах тоже появляется дубликат. Это известные регрессии.
- Сопоставление обеих половин одному существующему ID снижает Unknown clean4s
  с10s до4s, но присваивает один ID одной2s overlap-ячейке, где baseline abstained.
  Это риск смешения, а не улучшение overlap detection.
- Baseline сам присваивает некоторые короткие смешанные окна одному человеку:
  на short_mixed1.52s —13.68s, плюс4.56s Unknown. Однооконный embedding не разделяет
  людей внутри окна. В коротком trial дополнительно создан ID смешанного окна.

Метрики отчёта разделены: `wrong_person_s`, `mixed_single_label_s`, `mixed_new_ids`,
`duplicate_ids`, `duplicate_s`, `unknown_s`. Смешанная ownership включает внутреннюю
тишину исходных файлов; эти числа — control outcomes, **не DER**. В начальных
отчётах поле `wrong_person_or_mixed_s` объединяло две категории; окончательные
`speaker_candidates_scored.json`/`speaker_candidates_verified.json` их разделяют.
Начальный short-вариант также проверял уже известные short matches повторными
views; в последующем варианте они сохраняют исходное поведение без обучения.
Не выдавать эти версии и выборки за одно неизменное сравнение.

## Доступный live trial

Поэтому baseline оставлен по умолчанию. Trial включается только явно:

```powershell
poetry run python -m armenian_speech.combined --microphone-device 14 --device 16 --diarize --speaker-diagnostics --experimental-speaker-matching
```

ID14 — встроенный микрофон,16 — Buds loopback по последней проверке; при смене
устройств снова проверить IDs. Старый процесс остановить Ctrl+C перед запуском.
Без нового флага работают прежние правила первой4.2. Ни один ID не ограничен
двумя людьми; capacity8 остаётся прежней, IDs не переименовываются/не скрываются.

Два изменения trial:

1. Для ещё не совпавшей ячейки1.5–<2s вычисляются первый/последний1s views из
   **этой же ячейки**. При согласии views >=0.47 разрешено обычное создание/обучение
   registry. Эти views перекрываются и не являются независимыми свидетельствами.
   Материал между репликами не накапливается. Известные короткие matches по-прежнему
   не обучают centroid, окна<1.5s новый ID не создают. Unknown PCM не фильтруется.
2. При несогласии половин полной2s ячейки допускается существующий ID, если full
   и каждая половина **отдельно** совпадают с одним и тем же ID по прежним cosine
   threshold/margin. Ни обучение, ни создание нового ID в этом исключении не идут.
   Половина без embedding/с другим ID/ambiguous не даёт исключение. Это не удаление
   half gate, но оно всё ещё может принять смесь двух людей — adverse test выше.

ASR/MT/WAV контракты, Me, paired HY/EN, queue credits, shutdown deadline и модели
не менялись. Иная speaker-разбивка меняет ASR/MT контекст; одинакового текста
и качества перевода не обещаем. Нет новых аудио/текстовых фильтров, контекстного пула
и принудительной склейки Unknown. Соседние реально совпавшие labels объединяются
по прежнему правилу.

Диагностический терминальный JSON сокращён: без повторения всех source anchors;
сохраняет время/длину/ID/причину/best/second/halves/counts/probe_kind/experimental.
Полное numeric event по-прежнему получает optional observer. `half_matches` —
pre-update, чтобы не сравнивать половины с только что созданным из них ID.
Обычный вывод без diagnostics не получает новых событий.

## Результат на предоставленных источниках

`scripts/check_user_sources.py` проверяет baseline и trial непосредственно через
production SpeakerTracker и сравнивает labels с offline candidate. Оба совпали.
Отчёт `reports/user_sources_production_verified.json`:

| A/B три повтора | Первая4.2 | Trial |
| --- | ---: | ---: |
| Создано ID |1|2|
| Unknown PCM, s |16.944|0|
| Присвоение чужому ID, s на этих файлах |0|0|
| Дубликаты ID |0|0|

Полная проверка с настоящими spawn/FastConformer INT8/NLLB greedy:
`scripts/check_user_source_pipeline.py`, `reports/user_source_pipeline_trial.json`.

| Показатель | Первая4.2 | Trial |
| --- | ---: | ---: |
| Accepted/completed jobs |12/12|12/12|
| ASR/MT parts, все напечатаны |15|12|
| Unknown parts |6|0|
| Empty/filtered |0/0|0/0|
| Найдено ID |1|2|
| Worker exit |0|0|
| Session/WAV cleanup |да|да|

Это paced file replay без устройств, не реальный throughput или speech-end E2E.
Текстовых эталонов нет, WER/качество перевода не измерены. Консольный вывод public
ASR/MT временно попал в технический capture и был удалён после проверки; сохранён
только numeric_result JSON без hypotheses. Не перенаправлять helper stdout в файл
с расшифровками. Повторное исполнение helper откажется перезаписывать этот отчёт.

## Проверки и состояние

Финальная release-проверка: **218 passed in19.98s**, включая границу23999/24000
samples без потери PCM; JUnit:reports/speaker_trial_release_tests.xml. Предыдущие216
ниже — до добавления этих двух граничных случаев. Итоговый adverse report
`reports/speaker_candidates_production_verified.json` отдельно проверяет совпадение
labels/durations кандидата и production tracker (baseline и trial) на всех сценариях.

`216 passed in19.54s`, Ruff/Poetry passed. Проверены short enrollment, необходимость
двух совпадающих halves для exception, отсутствие training при exception, новые
CLI flags, opt-in output и pre-update half_matches. Старые native Windows spawn/
paired-output/Me/accounting/shutdown tests сохранены. После добавления trial exact
SHA-reference первой4.2 снова сравнен с default на150jobs/169cells: совпали PCM,
labels/counts/centroids/model inputs. Report: `reports/first42_parity_after_trial.json`.
WAV/ASR/MT source bytes не менялись, полный WAV benchmark не повторялся.

Ни один результат не означает принятия Stage4.3. Trial известным образом ошибается
на mixed/channel controls и требует пользовательского сравнения на реальном
маршруте плюс независимом материале. Следующая проверка — тот же A/B порядок,
прежний запуск и trial, затем новые фразы/третий голос/короткие ответы без настройки
порогов по этому набору. Живой звонок не записывался; запись по-прежнему требует
отдельного согласования. Stage5 не начинался, коммитов нет.
