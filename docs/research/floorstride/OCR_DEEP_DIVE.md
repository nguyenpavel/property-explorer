# Floorstride OCR: the software, how it is set up, and every feature

Companion to `FLOORSTRIDE_BLUEPRINT.md` §7. Release `/r/dcc61408d7/`, analysed 2026-11-10.

**Labels:**
- **[obs]** seen in code, on the server, or in a live run.
- **[inf]** inferred.

**Main source files:** `src/import/stages/ocr.js` (engine and parsers), `src/import/stages/text.js` (text finding and the mosaic), `src/import/stages/labels.js` (room-name dictionary), `src/import/index.js` (orchestration, scale vetting, digit fixes), `src/import/stages/snap.js` (fitting walls to printed sizes).

---

## 1. Which OCR software it uses

**Tesseract, through tesseract.js, self-hosted and unmodified.** Every vendored file matches the official npm release byte for byte (SHA-256 compared against jsdelivr) [obs].

| Component | Served from `vendor/tesseract/` | Identified as | Size |
|---|---|---|---|
| JS API (ES module) | `tesseract.esm.min.js` | **tesseract.js 7.0.0** (Apache-2.0), exact hash match | 63 KB |
| Worker script | `worker.min.js` | tesseract.js 7.0.0, exact hash match | 111 KB |
| WASM engine | `core/tesseract-core-{lstm,simd-lstm,relaxedsimd-lstm}.wasm.js` | **tesseract.js-core 7.0.0** (Apache-2.0), exact hash match on `simd-lstm`. The embedded engine tag reads `5.1.0-288-g2a9c1` (a git-describe of the Tesseract 5 source it was built from). It bundles Leptonica (Otsu/Sauvola binarisation), libpng 1.6.38 and zlib 1.2.12 | ~3.9 MB each, WASM embedded as base64 |
| Hebrew model | `lang/heb.traineddata.gz` | **@tesseract.js-data/heb 4.0.0_best_int**, exact hash match | 581 KB |
| English model | `lang/eng.traineddata.gz` | **@tesseract.js-data/eng 4.0.0_best_int**, exact hash match | 2.95 MB |

What the server shows:
- **Only LSTM builds are deployed.** The legacy, non-LSTM cores return 404, which matches `createWorker(..., 1, ...)`: OEM 1, LSTM neural net only.
- **Three CPU variants are deployed.** [inf] tesseract.js picks relaxed-SIMD, then SIMD, then plain, according to what the browser supports.
- **`4.0.0_best_int`** is Tesseract's "best" LSTM models converted to integer weights. tesseract.js uses this set by default in LSTM-only mode; the string is present in `worker.min.js`.
- **Nothing is fetched from a CDN at runtime.** `workerPath`, `corePath` and `langPath` all point at the site's own `vendor/tesseract/` [obs: `ocr.js:29`]. The live runs made no third-party requests [obs].
- **Licences:** tesseract.js and core are Apache-2.0; the models are Apache-2.0 (Tesseract tessdata).
- **No other OCR or ML** is used anywhere in the app [obs: full-source grep].

---

## 2. How the engine is configured (`ocr.js:12-59`) [obs]

**Two engine kinds**, each its own tesseract.js Web Worker:

| Kind | Languages | Parameters | Why |
|---|---|---|---|
| `text` | `heb` + `eng` | `tessedit_pageseg_mode=6` (one uniform block of text), `preserve_interword_spaces=1` | Room names (Hebrew and Latin) and general text |
| `digits` | `eng` | PSM 6, `tessedit_char_whitelist="0123456789/-.,"`, `classify_bln_numeric_mode=1` | Printed sizes. The comment says the general model "reads small bold 5s as 8s and drops 1s next to a slash" |

**Worker options:**
- `workerBlobURL:false`, so the worker loads from its own file rather than a blob.
- `gzip:true`, so models are fetched as `.traineddata.gz`.
- `cacheMethod:'none'`: models are **not** cached in IndexedDB. Each engine start downloads them again, though it is served from the HTTP cache because release files are `immutable`.
- The logger and error handler are silenced. Comments say "OCR text is never logged" (`ocr.js:8`).

**Lanes and lifetime:**
- **Parallel lanes:** `LANES = clamp(floor(cores/4), 1, 2)`. Each lane has a text engine and a digits engine; on a 16-core machine there are 2 lanes and 4 workers [obs live]. Lanes take mosaic pages until none are left; results come back in page order, so they don't depend on timing.
- **Warm start:** `ocrWarm()` starts every engine when an import begins, while the detection Worker is still tracing walls (`index.js:62`).
- **Memory release:** lane-0 engines stay alive for the session. Extra lanes ("each holds its models, some 50 MB") are terminated after **30 s** idle (`ocr.js:44-59`).
- **Graceful failure:** an engine that cannot start resolves to `null`. The import then continues with no labels or printed sizes and falls back to the scale priors. Reading never blocks an import (`index.js:63-70`).

---

## 3. What happens before OCR: finding the text (`text.js`) [obs]

The app does **not** run Tesseract on the whole sheet. Its own vision code first finds the text, then sends Tesseract a clean "mosaic" of crops. In practice this is the key to its accuracy on 6–7 px plan lettering.

1. **Glyph detection**, in the import Worker:
   - ink darker than the paper and **not** part of the wall mask;
   - connected components of glyph size (0.25–3% of the short side), aspect ≤ 12, density checks;
   - median glyph height `hT`; outliers (outside 0.45–1.8·hT) dropped.
2. **Text blocks:** grid-hashed union-find with a gap of 0.8·hT.
   - Punctuation up to 2.2·hT joins; narrow-stroke pairs ("1/1") merge.
   - Door arcs crossing a line of text are trimmed off.
   - Each block is classed as horizontal or vertical.
3. **Keep only plan text:**
   - a block must sit inside walls on at least 3 of 4 ray directions, **or** on a ticked **dimension line** (long thin line, ticks or extension lines);
   - title blocks, legends and logos fall out.
4. **Measure around each block** (rays at 9 offsets):
   - the clear room box (interior face to interior face), which is what a printed W/L size measures;
   - the clear spans through the block, which is what a dimension string measures.

   These pixel measurements are what the printed numbers are later compared with.
5. **Build the OCR mosaic** (`text.js:268-343`):
   - crops padded by 0.6·hT, upscaled (bilinear, ×1.5–8) so a glyph is **about 34 px tall** (`GLYPH_PX`, "the engine's sweet spot");
   - **contrast-stretched** using an Otsu threshold, *not* binarised (the comment says Tesseract binarises better itself);
   - vertical blocks are cut **twice**, turned 90° and 270°;
   - on an upright-looking sheet, a few horizontal "probe" blocks are also cut turned 180°;
   - one crop per row with gaps of about 41 px; pages at most 6,000 px tall; at most **140 crops**, prioritised by glyph count and room box;
   - two variants: `mosaicAlt` (upright crops first) and `mosaicClean` (foreign big ink, e.g. a door curve, painted out of the margins).
6. **Early hand-off:** the mosaic is posted to the page as PNG blobs **as soon as it is cut** (`{id, mosaic}` message). The OCR therefore runs while the Worker is still tracing walls.

---

## 4. Reading the mosaic (`ocr.js:62-123`) [obs]

- Per page, `recognize(blob, {}, {text:false, blocks:true})` runs on the text and digits engines **side by side**.
- The output hierarchy (blocks → paragraphs → lines → words) is walked. Each word goes back to its crop cell by the centre of its bounding box (±4 px), and a line spanning several cells is split per cell.
- Per cell: lines sorted top to bottom, text joined with `\n`, confidence = mean word confidence / 100.
- The result per cell is `{block, rot, text, conf, digits:{text, conf}}`.
- An unreadable page leaves its cells empty and is counted as `failed`. Nothing throws.

### Rereads (`index.js:111-130`, `ocr.js:132-164`)
| When | What |
|---|---|
| Fewer than half the upright crops parse as anything useful (`weakReading`) | Read `mosaicAlt` too (upright crops first) |
| A block gave nothing useful and a curve ran past it | Re-read from `mosaicClean`, alone on a page, **with** the digits pass |
| A word of 3 or more letters reads as **no known room name** (`misreadWords`, e.g. "jonn" for מחסן) | Re-read just those crops alone, ×1.3 larger (at most 24 crops). The comment says Tesseract sizes its lines on the surroundings, so a word read alone often comes out right |

Rereads only **add** readings; `blockReads()` keeps the useful ones.

---

## 5. Parsing the text (`ocr.js:166-225`) [obs]

**Character fixes inside numbers:** `O o °`→0, `I l | !`→1, `S s $`→5, `Z z`→2, `B`→8, `G b`→6, `g`→9.

| Pattern | Example | Result |
|---|---|---|
| Room W/L | `335/285`, `335\285`, `335\|285` | Two sizes. Whole numbers 50–2000 are **cm**; decimals 0.5–30 are **m**; each side must be 0.6–20 m |
| Dimension run | `-615-`, `~615~`, `_615_`, `+615+`, or a bare `615` | One length (0.6–30 m) |
| Chain integer | `3375`, `229` | A whole number. Later tried as both **mm and cm** against the ticked stretch it sits on |
| Area | `19.1 m²`, `m2`, `m?`, `m'`, `qm`, Hebrew `מ"ר`, `sq m` | m². A run is dropped when an area is present ("19.1 m2 is an area, not a 19 m run") |
| Imperial area | `213 sq ft`, `ft²`, `sf` | Converted to m², flagged `imperial` |
| Feet-inches | `12'6"`, `12' - 6"`, `12'6" x 10'2"` | One run, or W×L, in metres, flagged `imperial` |
| Room name | any line with 2 or more letters (Hebrew, Latin or Cyrillic) | `matchLabel()` against the dictionary (§6) |

**How the two engines are merged** (`blockReads`, `ocr.js:328-354`):
- Numbers from the **digits** engine replace the text engine's sizes, unless the cell is plain words or imperial (the whitelist drops `'` and `"`).
- The digit confidence becomes `numConf`.
- For vertical blocks, the turn that parses (and reads with more confidence) wins. If both parse, both are kept as alternatives.

---

## 6. Room-name dictionary (`labels.js`) [obs]

**Entries:**
- **19 Hebrew rows**, with the vocabulary of Israeli developer plans:
  - rooms: entrance, corridor, living (`ח. דיור`, `סלון`…), dining, kitchen, master bedroom (`ח. הורים`), **safe room** (`ממ"ד`, tagged `safe-room`), bedroom, study, bathroom, guest WC, utility;
  - **laundry niche** (`מסתור כביסה`), storage, walk-in closet, covered, **service** and plain balconies;
  - **common areas excluded** from the apartment: lift, stairwell, floor lobby, shaft, parking.
- **About 24 Latin and Cyrillic rows:** English, French, German and Russian words. Examples: master/primary, great room, den, nook, pantry, mudroom, garage → excluded, patio/deck, chambre, Schlafzimmer, спальня, кухня-гостиная, salle de bains, санузел, buanderie, Abstellraum, Flur, прихожая, балкон, кабинет…

**Normalisation:** NFC, lowercase, bidi marks stripped, niqqud removed, quotes unified, Hebrew final letters folded, abbreviations `ח.` `ת.` `ש.` `פ.` expanded, spaces and punctuation removed.

**Matching, in order:**
1. Exact substring, longest first, preferring the more specific tag. Latin words must match whole words.
2. Approximate substring edit distance for non-Latin text: ≤ 1 for keys of 4+ characters, ≤ 2 for 8+.
3. For Latin: whole-word edit distance 1 (5+ letters), or a prefix match (≥ 60%, first two letters exact).

**Output:** type, English display name, tags. The stored `label` is the row's canonical Hebrew form. In the live run, `סלון` was stored as `ח. דיור`. Several labels inside one room combine into an open-plan name.

> **Caveat [inf]:** the dictionary has Russian, French and German words, but only the **heb + eng** OCR models are loaded. Cyrillic text cannot be recognised by those models, so Russian labels on a sheet are unlikely to read. French and German mostly can, since they use Latin script.

---

## 7. Scale from the text: the main purpose of the OCR [obs]

**Observations, per block** (`scaleObservations`, `ocr.js:234-270`):

| Source | Candidate scale (px per m) | Weight |
|---|---|---|
| Room W/L | Measured room box ÷ printed size. W/L order is never trusted: it takes the orientation where both sides agree, and requires agreement within 6% (log) | 1.5 × conf (2 candidates) |
| Area | √(box area ÷ printed area). Only 1.5–80 m², and only when there is no W/L | 0.5 × conf |
| Dimension chain integer | Ticked stretch ÷ value, offered as **both** mm and cm | 3 × conf |
| Dimension run | Each candidate clear span ÷ value | 3 × conf |

**Fusion** (`fuseObservations`, `ocr.js:276-316`):
- Every candidate is tried as a hypothesis, deterministically.
- Inliers are within **±2.5%** in log scale, at most one per group.
- When there are 3 or more room-size groups, only room sizes may propose.
- The best hypothesis by weight is refined by 3 weighted-median passes.
- **Confidence:**
  - 0.9: 4 or more inliers from 2 or more blocks, spread ≤ 1.5%;
  - 0.7: 3 or more inliers, spread ≤ 2.5%;
  - 0.5: 2 or more inliers;
  - otherwise 0.3.
  - Area-only results are capped.
- At least 2 observations must be used.

**Vetting** (`index.js`):
- The text scale is checked against priors derived from the drawing itself: median door gap about 0.80 m, thinnest common wall about 0.10 m, thickest about 0.25 m.
- Strong agreement only needs to pass a gross 0.4–2.5× check. Weaker results must land within 0.6–1.6× and give plausible doors (0.55–1.3 m) and walls (4–20 cm).
- **Priority:** the user's 2-click calibration > vetted text > area vs prior > priors alone (flagged as "about ±15%").

**One-digit misread repair** (`fixDigits`, `index.js:403-438`):
- The code notes that 5, 6, 8, 3 and 0, and also 1 and 7, look alike at 6–7 px.
- A printed W/L value that misses both drawn spans by more than 6%, or that breaks the sheet's **5 cm step** convention (detected when 70% or more of the sizes are multiples of 5), is swapped for the single-digit alternative that lands within 1.5% (4% when off-step) of the drawn span.
- The swap is recorded as evidence, e.g. "128 read as 125 (a digit the text reader confuses)".
- Dimension strings get the same alternatives.

**Then the walls are fitted to the numbers** (`snap.js`): a least-squares fit of the wall lines to every printed size, applied automatically only when confident. See the blueprint §7.2 and the wizard's "Set size" / "Set all" rows.

---

## 8. Orientation detection from text [obs]

- **Sideways sheets.** A probe pass checks glyph votes: vertical ≥ 12 **and** more than 1.5× horizontal stops detection early. The 16 biggest vertical blocks are read turned 90° and 270°, and `orientationVote` scores each reading by confidence × usefulness (sizes and names count extra). The turn with a 1.15× margin wins and detection runs again.
- **Upside down.** `flipVote` uses **room names only**, because "335/285 upside down still parses". 180° wins if 3 or more probe blocks are read, the names score at least 1.2, and that is at least twice the upright score.
- The 180° probe readings only vote; they never name a room or set a size.

---

## 9. Live verification (Chrome, WebGPU machine, 16 cores) [obs]

Test input: a synthetic 1600×1120 px plan drawn in the page at exactly **100 px/m**. It had:
- three rooms with printed clear sizes `569/850`, `769/469` and `769/369`;
- labels `סלון` (Hebrew), `Bedroom` and `Kitchen`;
- a deliberately **wrong** area `12.4 m²` in the 48 m² living room;
- doors, a window and solid walls.

It was imported through the app's own `__app.api.importImage(url, {accept:false})`, which produces a draft only; the user's plan is untouched.

| Run | Scale found | Rooms named | OCR time | Notes |
|---|---|---|---|---|
| Upright, cold engines | **100.0 px/m**, room sizes, conf 0.9, 6/6 used | Living room, Bedroom, Kitchen | engines read 1,060 ms; 114 ms on top of detection | 4 tesseract workers started; walls "moved to the printed sizes of 3 rooms (0 cm)" |
| Upright, warm | 100.0, conf 0.9 | all 3 | read 559 ms; +72 ms | – |
| Turned 90° | 100.0, conf 0.9 | all 3 | probe pass 2.7 s | "Turned 270° so the text reads upright"; the wrong area was **rejected** ("1 printed size did not match the walls") |
| Turned 180° | 100.0, conf 0.9 | all 3 | probe pass 2.4 s | "Turned 180° so the text reads upright" |
| `ocr:false` (control) | **112.5** (prior, conf 0.25, ±15%) | none (3 × "other") | – | "Scale guessed from wall and door sizes" |

No third-party requests at any point. Fetches made inside the tesseract workers (models, WASM) are not visible to page-level instrumentation; their paths are confirmed by the code and the server.

---

## 10. Privacy and safety properties [obs]
- All recognition runs on the user's device in WASM workers. Images and text are never uploaded, and no telemetry exists.
- OCR text is never logged. Engine errors are reduced to a short message.
- The source image saved in the plan is the rectified JPEG (≤ 2000 px), stored only locally (autosave, recent plans, the saved file).

---

## 11. Limitations (stated in code, or seen) [obs/inf]
- **Models:** only Hebrew + English. There is no Russian, French or German OCR model despite the dictionary words [inf].
- **PDFs:** rasterised (page 1 at 300 dpi) and then OCR'd. A vector PDF's **text layer is not read**, although pdf.js could extract it exactly. The code calls this "the next step".
- **Page segmentation:** PSM 6 per crop works because of the crop mosaic. Free-form text elsewhere on the sheet is deliberately ignored.
- **Digits engine:** its whitelist cannot read `'`/`"`, so imperial sizes come from the text engine only. No handwriting support.
- **Re-downloads:** `cacheMethod:'none'` means every engine start re-downloads the models, about 3.5 MB per engine with 2–4 engines. The HTTP cache usually absorbs this.
- **Tuning corpus:** [inf] tuned on a small set of Israeli developer sheets ("the owner's sheet"), so the accuracy elsewhere is unknown.

---

## 12. Rebuilding this OCR stage yourself (your own code)

**Minimum:**
1. `npm i tesseract.js@7`. Self-host `worker.min.js`, the `tesseract.js-core` LSTM builds and the `.traineddata.gz` files for your languages (`@tesseract.js-data/<lang>/4.0.0_best_int`).
2. `createWorker(langs, 1 /* LSTM only */, { workerPath, corePath, langPath, gzip: true })`.
3. Make two workers: a text one, and a digits one with a numeric whitelist plus `classify_bln_numeric_mode`.
4. Never OCR the whole sheet:
   - find glyph components;
   - group them into blocks;
   - keep the blocks inside rooms or on dimension lines;
   - crop, upscale to about 30–35 px glyphs, contrast-stretch;
   - pack the crops into a mosaic;
   - `recognize(..., {blocks: true})`, then map the words back to their crops.
5. Parse W/L, runs and areas, with digit-confusion fixes and unit rules. Fuse the scale robustly in log space. Vet it against door and wall priors. Always offer 2-click calibration.

**Improvements over Floorstride:**
- Read the **PDF text layer** first, and use OCR only for scans.
- Load the OCR models for every language your dictionary supports.
- Keep the default IndexedDB model cache.
- Consider a newer or larger model (e.g. PaddleOCR via ONNX Runtime Web) only if small-digit accuracy is still a problem. It costs more download and complexity.
