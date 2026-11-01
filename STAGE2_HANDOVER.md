# Stage 2 handover

## Stage 4.2 — 2026-11-01

Implemented opt-in --diarize for combined and system_audio --live. Command:
poetry run python -m armenian_speech.combined --microphone-device9 --device10 --diarize
(separate option values with spaces). CAMPPlus CPU1thread loads inside the existing
worker before ready. sherpa-onnx2.0.1 moved dev->runtime; no version change.
speakers.py uses2s cells beforeASR, half-window consistency guard, merging same labels,
short cells no learning, Unknown preserved, bounded8centroid registry across idle.
Split PCM is contiguous/exact, metadata preserved. Coarse boundaries/word cuts and
missed mixes/overlap are known limitations. No Armenian-call/DER acceptance yet.
Per-part display speaker differs from source_label System. Original job completion
increments only on last_part; result_parts separate, empty/filter counts perpart.
Me unchanged. One worker/fair source queue/shutdown deadline retained. --diarize off
preserves previous behavior. User should next test4.3 with independent Armenian voices.
Real public-model replay labels1,2,1,2,Unknown,Me;4/4 jobs,6 parts; Unknown empty ASR,
Me synthetic noise filtered. Actual Ctrl+C both inputsexit130,1.292s,zero cleanupkills.
No private recordings or commits. Full limitations/commands inREADME andTESTS.

## Stage 4.1 — 2026-11-01

User authorized the isolated first experiment, not live integration yet. Added only
scripts for model/data preparation, experimental embeddings/registry, CPU comparison
and existing-VAD boundary probe, plus tests/docs. Production src/ is unchanged.
Two new pinned dev packages: sherpa-onnx/core2.0.1; no existing package updates.
CAMPPlus provisionally selected over TitaNet Small: lower fresh-process memory,
both 0/14 clip-label errors at2/4s but7/14 at1s on tiny English reading subset.
Three public LibriSpeech speaker IDs, separate calibration/evaluation files;
not Armenian-call validation or DER. Existing VAD mixes adjacent voices without
pauses; embedding model does not detect overlap. See DIARIZATION_COMPARISON.md for
commands, hashes, full metrics and next4.2 requirements. Live remains Me/System.
Do not integrate by simply assigning one speaker to the current six-second chunk.
Keep short useful text with Unknown, session-stable IDs, bounded state and existing
queue/shutdown semantics. Physical<=5s still unconfirmed. No commits made.

## Stage 3.3 — 2026-11-01

Пользователь разрешил3.3, английские термины отложены. combined.py запускает оба
входа: --microphone-device9 (sounddevice) --device10 (PyAudioWPatch loopback).
Один ASR/MT worker, отдельные VAD/resampler/raw queues. Метки в InferenceJob.speaker,
не в переключаемом глобальном состоянии. Старые Me/System команды сохранены.
FairQueue: pending2 отдельно на источник, round-robin, credits<=worker.capacity
включая активный job. Политикаdropincoming; pending/worker очереди и потери считаются
отдельно. Микрофон и System читаются по одному блоку на круг. Микрофон watchdog2s,
System idle logic прежняя. Общие session timestamps приблизительны, не physical ADC.
Оба потока закрываются до finaldrain; общий15sdeadline, pendingcancel и workerabort
на ошибке/дедлайне. --diagnostics для счётчиков, обычный вывод тихий.
Реальные устройства30s: 3Me+2System jobs,5/5completed,0raw/phrase drops; Me content
не размечен. Replay2WAVодновременно:1Me+3System,4/4completed,одни модели.
Ctrl+C обоих входовexit130, shutdown0.911s,безkill. ВерификацияполностьювTESTS.md.
При сменеустройстваперечислитьIDиперезапустить; нетauto-switch/echo cancellation.
Не объявлять<=5sдоказанным. SpeakerDiarizationостаётсяStage4. Коммитовнет.

## Stage 3.2 — 2026-11-01

Пользователь разрешил 3.2. Команда system_audio --device10 --live добавляет System
HY/EN через отдельный VAD/PyAV и один существующий spawn ASR/MT worker. Без --live
остаётся capture-only. --diagnostics включает подробности, обычный live тихий.
LoopbackVAD завершает при 650ms без блоков (очередь пуста), не добавляет PCM тишины,
сбрасывает состояние на новый burst, не склеивает проигрывания. Гапы пропускаются.
SpeechSegment.timeline_origin_s optional сохраняет паузы в System timestamps;
origin оценён по receipt-block_duration, метки не physical gold. Raw anchors сохранены.
InferenceWorker speaker по умолчанию Me, для этого источника System. HY/EN вместе.
Реальное проигрывание двух обрезанных001.wav: 2/2 задач, 2idle flush, парыдо
следующего воспроизведения, timestamps1s/10s, zero drops, workerexit0. Это smoke,
не оценка качества/latency. Ctrl+C с реальными моделями exit130, без kill.
Никаких новых зависимостей/моделей/коммитов. Следующий3.3 — оба источника и очередь;
диаризация4. Условия и окончательные тесты в TESTS.md.
Итог:173теста/Ruff/Poetry прошли. WAV15/15 сохранилWER/CER6.67%/2.03%.
Временныхsessionsпослепроверокнет; Gitindex и посторонниеdirtyfilesсохранены.

## Stage 3.1 — 2026-11-01

Пользователь разрешил Stage3. Реализован только первый capture-only подэтап:
system_audio.py, PyAudioWPatch0.2.12.9 Windows wheel cp313, native PCM16 stereo48k,
loopback ID10 на этом компьютере. CLI --list-devices / --device10 / --duration;
обычно до Ctrl+C. При тишине может не быть callback, это нормальное ожидание.
Никаких моделей/файлов/диаризации. 162 теста прошли; реальный звук захвачен,
реальный Ctrl+C exit130, освобождение устройства проверено. Детали и ограничение
границ (6.66s проиграно,6.6347s доставлено) в TESTS.md, не объявлять lossless capture.
Далее3.2: отдельный VAD и подключение к существующему worker. Пользователь ещё не
проверял этот новый CLI вручную. Коммитов нет; исходные dirty changes сохранены.

## Stage 2.4 — аудит 2026-10-31–2026-11-01, приёмка с ограничениями

Пользователь разрешил 2.4, после него просил объяснить план 3; Stage 3 не реализуем.
В InferenceWorker добавлен optional on_result, вызывается после совместного print/flush.
latency.py сохраняет только числовые времена и считает endpoint E2E со всеми стадиями,
интервалами неопределённости, пропусками/фильтром/очередью. Пустые/filtered результаты
не имеют output timestamp. Обычный CLI/вывод, модели и настройки не изменены.
scripts.check_live_latency: nominal-rate WAV replay + optional настоящий микрофон
для проверки устойчивости под нагрузкой; микрофон не источник речи для моделей.
scripts.check_live_shutdown: реальный CTRL_C_EVENT в отдельную скрытую Windows-консоль.
data/latency_endpoints.json: 15 предварительных интервалов, просмотр RMS последних 4 s
независимо от Silero, human_verified=false. Нужна проверка прослушиванием, страница
reports/stage24_endpoint_review.html. Пользователь явно попросил пропустить проверку
разметки прослушиванием: human_verified остаётся false, больше её не запрашивать.
Пользователь разрешил проигрывание WAV через динамики, громкость Windows не менять,
новое аудио не сохранять. Добавлен scripts.check_acoustic_latency: физический
динамик -> микрофон -> VAD/ASR/MT, перенос provisional границ по корреляции волновых
форм независимо от VAD. Эталон/запись держатся только в RAM до конца теста.
На WASAPI 9 реальный 10 s probe дал 999/999 ADC timestamps ~10 ms в будущем
относительно callback. Смещение stream clock -> perf_counter стабильно (span ~0.04 ms),
но это не подтверждает физическую точность ADC; поправка наугад не вводилась.
Нельзя объявлять физический критерий <=5 s выполненным по replay/provisional labels.
Финальные команды, метрики, ошибки и статус приёмки записываются в TESTS.md.
Аудит завершён 2026-11-01 в согласованном объёме; физический <=5 s не подтверждён.
Replay 338.92 s + настоящий mic health: 54/54 задач, 52 пары HY/EN, 2 empty ASR,
без raw/phrase drops и driver errors. 30 предварительных концов: 14 измерены,
mean/p95/max 4.164/5.025/5.038 s; 2 интервала пересекают 5 s, ещё 16 не покрыты
одним PCM-сегментом. Не выдавать эти 14 за успешные 30 и не править границы под VAD.
Оба acoustic теста дали 0 VAD сегментов/надёжных совпадений. Повтор трёх WAV с peak0.3
не менял громкость Windows, raw drops=0, mic peak0.000671/RMS0.0000244; причина
слабого сигнала не установлена, настройки ОС не менялись. Первый неудачный отчёт
с 9 raw drops сохранён отдельно; порядок открытия streams в helper исправлен.
Ctrl+C: реальный CTRL_C_EVENT, exit130, закрытие за1.639s, worker exit0, без kill.
Raw overload: 215 намеренно отброшенных blocks/103200frames, всё учтено, 49 gaps.
В Stage 3 следующий шаг только 3.1 захват System Audio без моделей, backend выбрать
после проверки Windows/Python3.13. Дальше отдельные VAD состояния, общий worker,
Me/System и тесты двух источников; Speaker Diarization остаётся Stage 4.
Финально: 156 pytest прошли, Ruff/Poetry прошли. WAV регрессия 15/15 сохранила
WER/CER6.67%/2.03%, mean/max1.838/2.784s (не live latency). TESTS.md содержит
все отчёты/провалы/ограничения. Git index и посторонние изменения сохранены,
временных WAV/sessions нет, зависимостей/коммитов/реализации Stage3 не добавлено.

## Пропуск одиночных ASR-обрывков — 2026-10-31

Пользователь снова прислал HY «Հ։»/«Հ.» с выдуманным EN и попросил фильтровать
мелкие срабатывания. В live_pipeline добавлен asr_fragment_reason: после ASR,
до tokenizer/MT, пропускать одиночную букву или результат без букв/чисел.
Короткие слова, числа, армянские ա/է и և сохранены. Внутри длинного имени инициалы
не удаляются. Это не акустический классификатор кашля и не confidence threshold;
более длинная бессмыслица может пройти. Точная причина пользовательского аудио
по тексту не установлена. Для произнесения отдельных букв есть --allow-asr-fragments.
WorkerConfig.filter_asr_fragments=True; run_live передаёт выключатель в spawn worker.
Пропуск возвращает пустые HY/EN + skip_reason, не вызывает MT, увеличивает
filtered_asr_fragments и completed. Empty ASR/queue drops считаются отдельно.
Только --diagnostics показывает причину пропуска/счётчик; обычный вывод тихий.
HY/EN для принятых текстов печатаются вместе. WAV CLI/VAD/размеры сегментов/модели
и зависимости не изменены. Результаты проверок ниже в TESTS.md; коммита нет.
Итог: 138 тестов/Ruff/Poetry прошли. На 15 WAV с реальными Silero/FastConformer
ни один из 27 результатов не отфильтрован, WER/CER до/после 11.67%/3.72%.
Пропущенные/пустые результаты не входят в max_decision_to_output_s: у них нет
HY/EN вывода; diagnostic endpoint называется completion. Шум пользователя не
записан/не размечен, поэтому false-positive rate в его комнате не измерялся.

## Более частый вывод длинной речи — 2026-10-31

Пользователь одобрил короткие фрагменты, явно сохранив совместный вывод HY/EN.
VADConfig: target_segment_s=3.5, split_silence_ms=256, max_segment_s=6.
Остальные пороги и короткие реплики с тишиной 600 ms сохранены. Target считается
от начала PCM фрагмента до последнего положительного окна, включая pre-roll и
внутренние паузы. Завершение по короткой паузе имеет reason=short_pause.
Max-duration остаётся непрерывным без overlap/потерь сэмплов; это не гарантия
сохранности слов на принудительном стыке. Новая pre-roll не заходит в прошлый PCM.
CLI: --segment-target-s, --segment-pause-ms, --segment-max-s. Target < max;
live max <= 12 s. Прежняя политика: --segment-max-s 12 --segment-pause-ms 600.
В worker/formatter нет промежуточных результатов; HY ждёт EN, печатаются одной строкой.
scripts.check_live_pipeline --realtime доставляет WAV в номинальном темпе, не ждёт
освобождения phrase queue. Это проверка worker/очереди, не физической live latency.
Результаты проверок и границы качества — в TESTS.md. Исторические записи ниже
сохраняют старые настройки/измерения. Зависимости, WAV pipeline и модели не менялись.
На 15 WAV VAD+ASR: 16 -> 27 фрагментов, WER 6.67% -> 11.67%, CER 2.25% -> 3.72%.
Это регрессия качества live-разбиения; её нельзя выдавать за качество WAV pipeline.
Nominal-rate проверка на батарее выявила full queue и shutdown timeout, поэтому
задержка/throughput Stage 2.4 не закрыты. В helper отчёт теперь сохраняется и при
ошибке, с ненулевым exit status. Реальные результаты не подменять mock-тестами.
Итог: 113 тестов/Ruff/Poetry прошли; повтор пяти WAV в реальном темпе на AC — 10/10,
без drops/forced termination, max decision->output 2.483 s (не physical speech-end).
Исходный WAV pipeline повторно прошёл 15/15, WER/CER 6.67%/2.03% без изменения.
Первый неудачный запуск не отменён повтором; все отчёты/условия описаны в TESTS.md.

## Текущие настройки после замечаний о шуме/ТВ — 2026-10-31

По запросу пользователя --live теперь работает без посекундных строк. Для уровней,
модельных метаданных, ASR/MT timings и JSON summary нужен --diagnostics.
Capture-only/--vad сохраняют диагностический вывод.

Новые VAD defaults: start/continue 0.65/0.50, непрерывное подтверждение начала
160 ms, min speech 300 ms, pre-roll 300 ms, silence 600 ms, trailing 100 ms.
Короткие/неподтверждённые новые кандидаты больше не проходят в ASR при Ctrl+C,
duration/EOF/gap. Хвост уже принятого max-duration продолжения сохранён.
CLI: --vad-threshold, --vad-continue-threshold, --vad-confirm-ms, --min-speech-ms.

Пользователь подтвердил далёкий телевизор. Добавлен опциональный --min-rms-db,
но по умолчанию он отключён: фиксированный -50 dBFS потерял 5 из 15 тихих WAV.
Без этого ограничения усиленная временная проверка обнаруживает речь во всех 15.
В --diagnostics есть rms_dbfs/energy_pass; порог подбирается между фоновым ТВ
и голосом у микрофона. Если уровни близки, VAD не отделяет целевого говорящего.
Это не шумоподавление/diarization и не обещание полного устранения фантомных фраз.
Исторические настройки и измерения ниже описывают прежние версии.

## Актуализация после Stage 2.3 — 2026-10-31

Пользователь подтвердил работу 2.2 и одобрил 2.3. Добавлен `--live`:

```powershell
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --live
```

`live_pipeline.py`: один Windows spawn-процесс, FastConformer INT8 и NLLB greedy
загружаются один раз до открытия микрофона. Очередь по умолчанию на 2 ожидающие фразы
плюс текущая обработка, drop incoming при full с предупреждением/счётчиком. Gap
фрагменты пропускаются явно. Результаты идут через bounded OS pipe, родитель печатает
`Me HY/EN` существующим formatter. VAD и захват не ждут ASR/MT.

Worker пишет один PCM16 mono 16 kHz WAV в `.cache/live/session-*/segment.wav`,
закрывает перед transcribe(Path), удаляет в finally. Родитель убирает точный файл
и пустой session-dir даже после kill. Постоянные аудио/транскрипты не сохраняются.
`ArmenianTranslator.split_text` добавлен для live token-aware разбиения по словам;
translate(str), WAV pipeline и decoder settings сохранены. Никаких новых пакетов.

Первый Ctrl+C в live устанавливает stop flag: закрыть микрофон, дренировать raw queue,
завершить VAD, предложить остаток очереди по обычной full-policy, затем закончить
принятые задачи за `--shutdown-timeout` (15 s). Worker игнорирует SIGINT; независимая
control pipe несёт итоговое число принятых jobs. На дедлайне/повторном Ctrl+C — kill,
счётчик незавершённых jobs и nonzero exit. Ошибки/неожиданный exit worker фатальны.

Опции: `--queue-size` (2), `--threads` (4), `--cache-dir`, `--asr-model`,
`--shutdown-timeout` (15). `--live` включает VAD и несовместим с отдельным `--vad`.
Нужно ждать `Inference worker ready`, затем `Microphone active`. Времена VAD и
`VAD-decision→output` не означают реальный speech-end; независимая проверка — 2.4.

**73 теста**, Ruff, poetry check прошли. Реальные 3 WAV через VAD→worker дали HY/EN,
один worker, 3/3 completed, без drops, временные WAV удалены. Тестовые команды:

```powershell
poetry run python -m scripts.check_live_pipeline --limit 3 --report reports/stage2_live_worker_replay.json
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/stage2_wav_regression.json
```

Полная WAV-регрессия: 15/15, WER/CER 6.67%/2.03%, mean/max 2.124/3.534 s,
sampled RSS 3072.64 MiB. Это новая отдельная запись, не live latency. Офлайн-пачка
worker имела queue wait до 4.051 s и decision→output до 9.549 s; низкую задержку
это не доказывает. Подробные реальные microphone/Ctrl+C проверки — TESTS.md.
В полном --live 30 s захват был без потерь; реальный CTRL_C_EVENT дал exit 130,
worker exit 0. Повторная проверка с ожиданием exit подтвердила выход обоих Python
и console host; остаток одной живой фразы был распознан/переведён после Ctrl+C.
Совместный тест известного WAV + 5 s микрофона: 3/3 jobs completed (2 от микрофона),
499 blocks без raw drops и queue drops. Вход микрофона независимо не размечался.
Проверка настоящего NLLB tokenizer: 578 tokens -> 512 + 68, все слова сохранены.
Следующий этап 2.4: независимые speech-end annotations/clock mapping, все стадии
задержки, распределения и превышения ≤5 s, а также разговорное качество.

Исходные изменения Stage 1 и 2.1–2.2 сохранены; новых коммитов нет. Git index со
staged deletion chats/README.md не изменён. Полные реальные экспорты чатов перед
сдачей остаются отдельным требованием. Ниже — исторические состояния.

## Актуализация после Stage 2.2 — 2026-10-31

Пользователь одобрил 2.2. Готовы `vad.py` (Silero ONNX + bounded Segmenter),
`live_vad.py` (PyAV resampling/окна/разрывы), `scripts/download_vad.py` и
`scripts/check_vad.py`. Добавлен опциональный `--vad` к существующему микрофону.
ASR/MT и очередь готовых фраз не подключены. **61 тест**, Ruff, poetry check проходят.

Модель Silero 6.2.3 и MIT license уже лежат в `.cache/models/silero/`. Пакет silero
не устанавливался; извлечён только ONNX из закреплённого wheel, проверяются SHA-256
wheel и модели. CPUExecutionProvider, один поток, одно состояние на поток аудио.
NumPy объявлен прямой зависимостью, прежние версии пакетов не менялись.

```powershell
poetry run python -m armenian_speech.microphone --list-devices
poetry run python -m armenian_speech.microphone --device 9 --sample-rate 48000 --vad
poetry run python scripts/check_vad.py --passes 2 --report reports/stage2_vad_screening.json
```

Capture callback не выполняет VAD. Consumer конвертирует mono/stereo PCM16 через
stateful PyAV в mono PCM16 16 kHz. Silero получает float32 окна 512 samples (32 ms).
Пороги 0.5/0.35, pre-roll 300 ms, min speech 250 ms, silence 600 ms (608 по окнам),
trailing 100 ms, максимум 12 s включая padding, продолжения без overlap.
Ctrl+C сначала закрывает stream, затем дренирует raw queue и обрабатывает остаток;
нули добавляются только на вход финального VAD-окна, в SpeechSegment их нет.

`SpeechSegment` хранит PCM bytes, локальные sample bounds и VAD-estimated bounds,
reason, decision_monotonic, epoch и исходные capture anchors. `.metadata()` даёт
числовой вывод `VAD phrase`. Это ещё не реальные speech-end timestamps:
clock_accuracy=unvalidated, WASAPI 10 ms anomaly сохраняется. При driver loss
последующая временная шкала помечается uncertain; queue loss имеет точный размер.
Разрывы сбрасывают resampler/VAD, завершая неполную фразу с reason=gap.

На 15 WAV в двух проходах речь найдена во всех, по 16 сегментов за проход;
на 5 s цифровой тишины — 0. Финальный offline mean/max VAD window 0.186/1.701 ms,
sampled RSS 90.92 MiB; это не live latency. Минута реального WASAPI+VAD прошла
без overflow/drop, Ctrl+C и повторное открытие проверены. Все факты и ограничения,
включая искусственную перегрузку, — в TESTS.md.
Последующий обычный 20 s live-тест дал 2 сегмента с reason=silence, тоже без потерь.
Содержание речи и фактические speech-end границы независимо не размечались.

Следующий шаг **2.3**: bounded очередь готовых сегментов, один ASR/MT worker,
однократная загрузка FastConformer INT8 и NLLB greedy, передача через временный WAV
и корректная остановка/ошибки/overflow. 12 s не гарантируют <=512 NLLB tokens:
нужна явная политика текста до translate(). До интеграции полная WAV-регрессия
повторно не запускалась; старые исходники и тесты сохранены. Коммитов нет, index
со staged deletion chats/README.md оставлен прежним. История ниже — прежние этапы.

## Актуализация после Stage 2.1 — 2026-10-30

Пользователь разрешил начать реализацию после изучения проекта. Выполнен только
**2.1 Microphone Capture**: `src/armenian_speech/microphone.py`, отдельная команда
`poetry run python -m armenian_speech.microphone`. Существующий WAV CLI и адаптеры
не изменялись. sounddevice 0.5.6, cffi 2.1.1, pycparser 3.12 установлены локально;
версии прежних пакетов не изменены. **34 теста**, Ruff и poetry check проходят.

Сначала `--list-devices`, затем обязательный `--device INDEX`. По умолчанию mono
int16 16 kHz, альтернативы — `--sample-rate` / `--channels`; `--duration` задаёт
ограниченный тест, иначе работа до Ctrl+C. На этой машине MME index=1 принимает
16 kHz, WASAPI index=9 требует явных 48 kHz. Автоконверсии/смены устройства нет.

RawInputStream callback копирует блоки в очередь на 32 блока; при заполнении
сбрасывается входящий блок с точным счётчиком. Главный поток считает peak и печатает.
Это очередь сырых диагностических блоков; очередь завершённых VAD-сегментов и
inference worker ещё не реализованы. На остановке остаток учитывается и отбрасывается.
Аудио не сохраняется, VAD и модели не загружаются. Микрофон проверен реально:
минута WASAPI — 59.99 с аудио без overflow/drop; реальные CTRL_C_EVENT закрывают
поток, после них устройство открывается повторно. Через Poetry родитель возвращает
1 после Ctrl+C, хотя приложение печатает успешное закрытие; прямой Python — 130.

Для 2.2 нужно отдельно проверить Silero VAD/CPU, конверсию 48→16 kHz, сегментацию
и временные метки. MME даёт нулевые timestamps; у WASAPI ADC time примерно на 10 ms
позже callback time. Есть диагностические счётчики этих аномалий, но калибровка и
точность speech-end не подтверждены. Live-задержка и качество речи не измерялись.
ASR по-прежнему принимает **путь WAV**, NLLB ограничен 512 входными токенами.

Исходная незакоммиченная очистка Stage 1 сохранена, staged deletion
`chats/README.md` не изменена. Новых коммитов нет. Полные реальные экспорты чатов
по-прежнему нужно сохранить перед сдачей. Подробности и команды — README.md и TESTS.md.

## Исходная передача после Stage 1 — исторический снимок

Далее сохранено состояние до реализации 2.1; актуальные изменения описаны выше.

Stage 1 завершён. Цель проекта: локальная армянская речь → английский перевод
в терминале, позднее микрофон + системный звук и стабильные метки говорящих.
Live-цель: ≤5 с от фактического окончания фразы. Stage 2 ещё не реализован.

## Состояние и стек

- Windows, Python 3.13.5, Poetry 2.5.1, i5-13420H, 16 ГБ RAM, без CUDA.
  Рабочая папка: `C:\Users\gorma\PycharmProjects\SpeechRecognition`.
- ASR: Vana-Labs FastConformer RNN-T INT8, onnx-asr 0.12.0 / ORT 1.31.1,
  CPUExecutionProvider, 4 потока, inter-op=1. Точнее и быстрее проверенного Whisper.
  Ревизия `ec92cef52199c3874681321b13853e8fe602d23f`.
- MT: NLLB-200 distilled 600M, torch 2.15.0+cpu / transformers 4.57.6,
  float32, greedy, `hye_Armn` → `eng_Latn`. Выбрана за качество на эталонах.
  Ревизия `f8d333a098d19b4fd9a8b18f94170487ad3f821d`.
- До очистки: ASR WER/CER 6,67%/2,03%, ASR-only 0,139 с; chrF++ 57,86;
  полная цепочка mean/max 1,660/2,805 с, RSS 3076,56 MiB, 22 теста.
- После очистки: **16 тестов**, Ruff и poetry check прошли; все 15 WAV офлайн:
  mean/max 2,102/3,432 с, RSS 3076,07 MiB, прежние WER/CER и chrF++.
  Это отдельный более медленный замер; повторный MT-тест шёл от батареи, прежний —
  от сети. Причины разницы целиком не установлены. Подробности в TESTS.md.
  Готовые WAV не доказывают live-задержку ≤5 с или качество разговорной речи.

## Структура и реальные интерфейсы

| Файл в `src/armenian_speech/` | Что переиспользовать |
| --- | --- |
| `asr.py` | `Segment(start: float, end: float, text: str)`, frozen dataclass |
| `asr_onnx.py` | `OnnxArmenianASR(directory: Path, threads: int)`; `transcribe(Path) -> tuple[list[Segment], float]`, float — длительность WAV |
| `translation.py` | `ArmenianTranslator(cache: Path, threads: int, offline: bool)`; `translate(str) -> str` |
| `pipeline.py` | Протоколы `Transcriber`, `Translator`; `process_wav(path, asr, translator) -> dict` с временами, RTF и ASR-текстом |
| `output.py` | `timestamp(seconds)`, `print_segment(start, speaker, armenian, english)` |
| `metrics.py` | `normalize_text`, `error_rates`, `MemorySampler` |
| `cli.py`, `__main__.py` | `parser`, `read_manifest`, `validate_wav`, `run`, `main`; WAV CLI |
| `benchmark.py` | ASR-only runner, `evaluate(asr, rows)` |

`scripts/`: download_asr.py, download_translation.py, prepare_samples.py,
check_translation.py. `tests/`: test_experiment.py, test_asr_benchmark.py,
test_cli_backends.py, test_translation.py. Конфигурация: pyproject.toml, poetry.lock,
poetry.toml, .gitignore. Планы/решения/проверки — PLAN.md, DECISIONS.md, TESTS.md;
исторические сравнения — ASR_COMPARISON.md и TRANSLATION_COMPARISON.md.
Локальные `.venv/`, `.cache/models/`, `data/local/fleurs/`, `reports/` вне Git.

## Запуск и загрузка

Из корня проекта, модели и 15 WAV уже подготовлены:

```powershell
poetry run armenian-speech --wav data/local/fleurs/001.wav --offline
poetry run armenian-speech --manifest data/local/fleurs/manifest.jsonl --offline --report reports/stage2_wav_regression.json
poetry run python -m pytest -q -p no:cacheprovider --basetemp .cache/pytest
poetry run ruff check .
poetry check
```

На чистой установке: `poetry install`, затем `poetry run python scripts/download_asr.py`
и `poetry run python scripts/download_translation.py`; подготовка данных отдельно.
CLI: `--wav` или `--manifest`, `--asr-model PATH`, `--cache-dir PATH`, `--threads`,
`--offline`, `--report`. Других backend/model selectors нет.
Для pytest нужны module-запуск и temp внутри проекта: обычный entry point не видит
namespace imports, а sandbox Windows Temp вызвал ошибки setup. Код под это не менялся.

`cli.run` создаёт обе модели один раз до цикла файлов. ONNX читает
`cache-dir/vana/PROVENANCE.json`; NLLB разрешает pinned snapshot из
`cache-dir/translation` локально и передаёт путь в Transformers, избегая metadata-запроса.
`process_wav` последовательно делает ASR → MT → печать HY/EN. Отчёт CLI без текстов.
Переиспользовать адаптеры, Segment, переводчик, вывод, метрики и WAV-регрессию.

## Ограничения и следующий шаг

- ASR сейчас принимает только путь к mono PCM16 16 kHz WAV. Метода для numpy/buffer
  нет. Он возвращает один сегмент на весь файл либо []; границы не определяют речь.
- NLLB: вход ≤512 токенов, max_new_tokens=256, EOS обязателен; длинные фразы
  требуют решения в плане сегментации. Есть ошибки смысла/имён/чисел.
  Лицензия CC-BY-NC 4.0, исследовательская модель. FLEURS — только 15 читаемых фраз.
- Нет захвата, выбора устройств, VAD, очереди, live worker, System Audio и diarization.
  sounddevice и Silero VAD не установлены. Только RSS измеряется фоновым потоком.
- Предварительная схема: Capture → VAD → Buffer → Bounded Queue → Worker → Terminal.
  Сначала изучить код и согласовать план. После одобрения начать **только 2.1 Capture**,
  затем 2.2 сегментация, 2.3 очередь/worker, 2.4 live-тесты. Критерии — в TESTS.md:
  непрерывность, отсутствие блокировки, явное переполнение, Ctrl+C, реальный speech-end
  timestamp, ≤5 с с учётом VAD/очереди, сохранение WAV pipeline.

Удалены ArmenianASR/Whisper, Marian/M2M100, старые selectors/beam override и их тесты;
из окружения — faster-whisper, ctranslate2, sacremoses, joblib, cloudpickle.
PyAV сохранён для подготовки FLEURS. Pipeline и ONNX adapter не переписаны.
История и данные сохранены; base HEAD `0aabc46`, очистка ожидает review без коммита.
Исходная staged deletion `chats/README.md` оставлена нетронутой; экспортов чатов на
диске не найдено. Все настоящие Codex-сессии нужно сохранить полностью в `chats/`
перед сдачей; этот handover их не заменяет. Не создавать реконструкции диалогов.
