# Floorstride: how it works, and how to build one like it

**Target:** https://floorstride.com/, release folder `/r/dcc61408d7/`, last-modified 2026-11-10 19:15 GMT
**Analysed:** 2026-11-10
**Method:**
- The site ships unbundled, unminified ES modules. I mirrored all 114 app modules (~59k lines; vendored three.js, pdf.js and tesseract.js excluded).
- REA 6.4.0 static JavaScript analysis was run on the mirror.
- Six parallel code-level reads were done, one per subsystem.
- A live session in Chrome measured network, timings and GPU stats.

**Confidence labels:**
- **[obs]** directly observed, in code, headers or the live session.
- **[inf]** inferred from comments or indirect evidence.
- **[unk]** not determinable from what the site ships.

**File references** are `src/...:line` in the shipped source, as it existed at this release.

---

## 1. Executive summary

- **What it is.** You draw a floor plan or import one (image or PDF). You furnish it in one click. Then you walk through it in 3D in the browser: WebGPU, falling back to WebGL2. It also has a random apartment generator, an interactive tutorial, and an English/Russian interface. The Hebrew OCR and the defaults point at the Israeli market: Tel Aviv coordinates, a safe room (mamad), and Hebrew room labels.
- **There is no backend.**
  - Everything runs client-side, including the computer vision and OCR for import.
  - Nothing is uploaded. Persistence is localStorage, IndexedDB and `.plan.json` files.
  - No analytics or third-party requests were found, in either the code or the live session.
- **Infrastructure.**
  - Static files from a Python `serve.py` on a **Raspberry Pi on a home connection** [inf: source comments], behind **Cloudflare** [obs: headers].
  - Each release lives in a content-addressed folder (`/r/<hash>/`) with year-long immutable caching. Only `index.html` is uncached.
- **No build step.**
  - Native ES modules plus an import map. Vendored copies of three.js r187 (WebGPU build + TSL), pdf.js 6.5.438 and tesseract.js 7.
  - Heavy code loads lazily: the 2D editor is about 0.5 MB, and three.js and 3D assets load only when needed.
- **One immutable plan JSON** (graph of nodes → walls → openings; rooms are seed points) is the single source of truth.
  - Every edit is a command: `op → normalize → validate`, rolled back on any hard error.
  - Undo and redo restore exact snapshots.
  - All geometry (room faces, mitred walls) comes from one memoised `derive()`.
- **Algorithms are classical and hand-tuned; there is no ML** except Tesseract's LSTM:
  - import: a computer-vision pipeline, OCR scale fusion, then a least-squares fit to the printed dimensions;
  - auto-furnish: rule programs plus beam search with hard constraints and reachability grids;
  - 3D: procedural geometry and procedural furniture;
  - people: procedural animation and A* navigation.
- **Engineering quality is high and test-driven.** Comments cite design docs, "skills" and a Python/Node bench (none of them shipped). There are probes used as regression oracles, a capture/test URL API, a GPU pipeline counter and leak probes. Module headers name an "owner" area. [inf] It is almost certainly built with AI coding agents (references to `.claude/skills/apartment-planner-build/...`).

---

## 2. Infrastructure and delivery

### 2.1 Hosting and caching [obs unless marked]
| Item | Finding |
|---|---|
| Edge | `Server: cloudflare`, HTTP/2, `alt-svc h3`, NEL reporting. `cf-cache-status` HIT on most release files |
| Origin | [inf] Python `serve.py` on a Raspberry Pi over a home uplink (`index.html` comments: "the Pi's home uplink"; `src/core/url.js`: "serve.py --lite-only, the public site"). Whether it is a Cloudflare Tunnel or proxied DNS is [unk] |
| `index.html` | `Cache-Control: no-cache`. Contains `<base href="/r/dcc61408d7/">` |
| Release files `/r/<hash>/…` | `Cache-Control: public, max-age=31536000, immutable`. All carry the same `last-modified`, i.e. a whole-folder deploy |
| Stable assets | `/assets/ui/og-image.jpg` lives outside the release folder, with `max-age=86400`, so link previews survive releases |
| Deploy model | [inf] Upload a new `/r/<hash>/` folder, then swap `index.html`. The switch is atomic, and old releases stay cached for open tabs |
| Directory listing | None (`/r/` returns 404). `docs/`, `README.md` and `package.json` are not deployed |
| Graphics tiers | `<meta name="ap-tiers" content="lite">`. The public site deploys only the lite tier's files; high and photo assets are not served |
| robots.txt | Only the Cloudflare content-signal boilerplate, with no signals actually set |

### 2.2 Live session measurements (Chrome with WebGPU, sample plan `f3-2br`) [obs]
| Phase | Requests | Transfer | Notes |
|---|---|---|---|
| 2D boot | 66 | ~486 KB | src/core 115 KB, editor2d 109 KB, ui 106 KB, i18n 60 KB, catalog 46 KB, css 15 KB. TTFB 221 ms, `main.js` done at 704 ms |
| Background prefetch (before Build 3D) | 35 | ~750 KB | `three.webgpu.js` 258 KB, `three.core.js` 283 KB, `three.tsl.js` 206 KB, plus `view3d.js` and the furnish modules. Trigger [unk] |
| Auto-furnish | – | – | Worker, **932 ms**: room typing 37, placement 625, decor 5, paths 69, verify 196 ms. 5,534 candidates, 668 reach checks, 43 items placed. 51 items and 10 lights afterwards. Algorithm `furnish-9` |
| Build 3D | 85 | ~1.84 MB | textures/lite 15 WebP files (590 KB), people/lite 3 files (520 KB: `cast.json` plus 2 characters at about 245 KB each), furniture/lite 18 rug/art WebP files (216 KB), JS modules |
| Session total | – | **~3.3 MB** | `__progressBytes` |

**Build 3D stats** (`__app.stats()`), WebGPU backend, lite tier:
- Scene: 76 draw calls, 135,237 triangles, 34 GPU programs, 26 textures, 112 geometries.
- Memory: about 66 MB GPU (56 MB of it textures), 97 MB JS heap.
- Build time **8.4 s** in total:

| Stage | ms |
|---|---|
| prepare | 1680 |
| shell | 338 |
| materials | 5 |
| furniture | 462 |
| decor | 65 |
| lighting | 10 |
| figures | 1 |
| walk | 626 |
| npc | 1466 |
| warm-up | 3399 (2531 of it shader compile) |

- 2 people rendered.

Note: the "start-up is taking longer than expected" console warning in that session was an automation artefact. The tab was in the background and the app waits for animation frames.

### 2.3 Client storage [obs]
| Key / store | Purpose |
|---|---|
| `localStorage ap.autosave.v1` | `{t, base, json}`. Autosave debounced 1 s plus idle callback, and on `pagehide`/hidden; max 2 MB. On a later visit it is restored as an undoable "Restore last session" |
| `IndexedDB apartment-planner / recent` | The last 8 edited plans: `{key,id,name,t,net,rooms,json}` |
| `ap.lang`, `ap.quality`, `ap.scene.v1` (time, lamps, people), `ap.random.v1`, `ap.tutorial.v1`, `ap.welcome` | Preferences. None of these are written in capture mode |
| Files | Save writes `{slug}.plan.json` (canonical JSON). Open accepts `.json` or a dropped file. Export writes an **A3 PNG at 300 dpi** with a title block, the scale, and a `pHYs` chunk so it prints at true scale |

There are **no share links, accounts or cloud sync** [obs]. A random apartment's address (`?plan=rnd-…`) does reproduce it deterministically.

### 2.4 Third-party and vendored code [obs]
- three.js r187 (MIT), using its WebGPU build and TSL. Example add-ons used: `RoomEnvironment`, `BufferGeometryUtils`, `RoundedBoxGeometry`.
- pdf.js 6.5.438 (Apache-2.0). Loaded on the first PDF only.
- tesseract.js 7 (Apache-2.0) with heb+eng LSTM models. Loaded on the first import only. The comments say "nothing leaves the machine".
- Textures: CC0 scans from Poly Haven and ambientCG, post-processed by an unshipped `tools/textures/cc0_post.py`.
- People: 45 CC0 MakeHuman characters, ported from the author's earlier "street crowd" project (MIT, same owner).

### 2.5 The scriptable app API (`window.__app`) [obs]
- URL parameters are documented as "the test API of every agent":
  - `plan`, `planUrl`, `import`, `calib`, `mode`, `seed`, `furnish=auto|none|keep`, `vp`, `view`;
  - `time`, `date`, `lights`, `people`, `pseed`, `freeze`, `quality`, `rscale`;
  - `only`, `skip`, `debug`, `capture`, `gputime`, `ui`, `rec`, `peopletest`, `tour`;
  - `backend=webgl2`, `eye`, `fov`, `tone`, `lang`.
- `__app.api`: loadPlan, getPlan, serialize, cmd, cmds, undo, redo, viewpoints, probe, dryRun, furnish, setQuality, build3d, setMode, setView, getView, tour, importImage.
- `__app.test`: beforeShot, afterShot, planToScreen, derive, debugMaterial, people, peopleState, simPeople, importDraft, rebuilds (leak probe), imageToScreen, i18n.
- Other members: `check()` (probe counts), `stats()`, `idle()`, `ready`. `window.__ready`, `__fatal`, `__progress` and `__gpuPrograms` exist for capture tools.

This is worth copying. It makes the whole app drivable by Playwright or an AI agent, and testable against numeric probes.

---

## 3. Architecture

### 3.1 Module map (lines of code) [obs]
| Area | Lines | Main files |
|---|---|---|
| core (plan model, app, URL, i18n, random plans, viewpoints, 3D host) | 6,606 | `core/plan/*`, `commands.js`, `app.js`, `probes.js`, `randomplan.js`, `view3d.js` |
| editor2d | 5,748 | `index.js` (220 KB), `draw.js`, `labels.js`, `snap.js`, `dims.js` |
| import | 7,358 | `stages/detect.js` (122 KB), `ocr.js`, `text.js`, `snap.js`, `emit.js`, `ui/wizard.js` |
| furnish | 3,704 | `program.js`, `beam.js`, `hard.js`, `kitchen.js`, `paths.js`, `decor.js` |
| catalog (58 items; 2D symbols and 3D models) | 4,402 | `catalogue.json`, `params.js`, `symbols.js`, `models3d.js`, `kit3d.js`, `furniture3d.js`, `decor3d.js` |
| scene3d (shell, materials, lighting) | 5,927 | `shell/*`, `materials/index.js`, `lighting/index.js` |
| people (figures + npc) | 11,032 | `figures/figure.js`, `anim.js`, `material.js`, `npc/schedule.js`, `life.js` |
| walk | 4,946 | `walk/index.js`, `collide.js`, `nav.js`, `views.js`, `minimap.js` |
| ui | 5,385 | `ui/index.js` (shell), `properties.js`, `tutorial.js`, `issues.js` |
| i18n dictionaries | 3,556 | `en.js` (~1,675 keys), `ru.js` (~1,733) |

### 3.2 Boot, threads and lazy loading [obs]
- **Before any module loads**, `index.html` installs four things:
  - a GPU pipeline counter (it wraps `createRenderPipeline*`/`createProgram`);
  - a `fetch` wrapper that streams bytes into a progress counter;
  - a start-up watchdog that shows reload UI on errors or 60 s with no progress;
  - the import map.
- **`main.js` boot order:** parse URL → `createApp` → dynamic import of UI and editor → load the plan (fixture, `planUrl`, or generated `rnd-…`) → optional furnish or 3D → fit → idle → remove the loading veil.
- **Frame loop:** one rAF loop. In 2D it redraws only when dirty. In 3D it runs update, render, GPU timing and render scale.
- **Workers:** import detection, import emission, furnish, the issues panel, editor probes, and texture-strip decode for people. Each one uses `{id, …} → {id, result|error}` with one request in flight, and falls back to the main thread.
- **3D modules** load on the first Build 3D, through a module contract (§10.2).

### 3.3 Cross-cutting design rules [obs]
1. **One source of truth.** The plan JSON drives everything; the shell and UI keep no plan state.
2. **Pure plan-core.** No DOM and no three.js, so it runs in Node, Workers and the bench. The Python bench reads the same `catalogue.json`.
3. **Determinism.** Content never uses `Math.random`. It uses `rng(planId, seed, purpose)`: an FNV-1a + murmur-avalanche hash into mulberry32. "Again" means seed + 1.
4. **The preview is the commit.** Drags use the same solver as the command, and one gesture makes one history entry.
5. **Zero new GPU pipelines per rebuild.** See §10.
6. **Probes as oracles.** overlap, doorSwing, windowBlock, clearance, reach, fit3d, leak and programs are all numeric counts that must be 0.

---

## 4. Data model: plan JSON v1 [obs] (`core/plan/schema.js`)

Units are metres and degrees; x points right and y points down. Topology tests run on integer millimetres.

| Collection | Fields (canonical order) and notes |
|---|---|
| top level | `version, id, name, units, settings, source, nodes, walls, openings, rooms, items, lights, furnish` |
| settings | `ceiling` 2.65 (range 2.20–4.00), `northDeg`, `latitude` 32.0, `longitude` 34.8, `style` (modern-warm, scandinavian, minimal-white), `seed`. Also `floorHeightM` and `finishes` (estate-light, local-dark) |
| source | `image` (a data URL of the import's rectified JPEG), `pxPerM`, `transform` (affine metres → image px), `rotation`, `homography` (3×3, original → rectified px) |
| node | `id, x, y` |
| wall | `id, a, b` (node ids), `thickness`, `height`, `kind` (exterior, interior, partition, virtual), `structural`, `colorPlus`/`colorMinus` (per-face paint) |
| opening | `id, wall, type` (door, window, balcony-door, passage), `offset` (from node a to the centre), `width, sill, head, hinge` (a/b), `swing` (derived), `side` (+/−), `style` (sliding, tilt-turn, casement-in/out, fixed, blast, entrance, pocket…) |
| room | `id, seed{x,y}` (**a point, not a polygon**), `type` (14 types), `name, label, tags` (master, safe-room, en-suite, laundry-niche, service-balcony, open-plan, external-access), `typeSource` (user, label, auto), `floor, walls` (finish ids), `wallColor, locked` |
| item | `id, cat` (catalogue id), `variant, x, y` (footprint centre), `rot` (degrees, clockwise), `mirror, locked, source` (user, auto, plan, import), `attach{wall, side, gap}` |
| light | `id, cat, x, y, h, room, source` |
| furnish | `seed, version` (e.g. `furnish-9`) |

- **IDs:** a prefix plus an integer (n, w, o, r, i, l). The next id is the maximum + 1, computed each time and never stored.
- **Canonical serialisation:** schema key order, collections sorted by id, numbers rounded (rot to 0.01), no `-0`, two-space JSON. It is idempotent.
- **Migration:** a chain of pure steps v(n) → v(n+1). The chain is empty at v1.

---

## 5. Plan core: geometry, edits and history [obs]

### 5.1 `derive(plan)` (memoised per plan object in a WeakMap)
- **Half-edge graph.** Each wall gives two half-edges.
  - Outgoing edges at each node are sorted with an **exact angular comparator on integer-mm vectors**, with a tie-break for overlapping edges during drag previews.
  - Faces are traced by `next`; signed area in exact integer mm² separates bounded faces from outer boundaries.
  - Union-find finds connected components. Island components become holes of the smallest enclosing face.
- **Mitred joins** (offset the centrelines by half-thickness, intersect).
  - Free ends get square caps.
  - Thickness steps on straight runs get a two-point step.
  - Reflex corners whose mitre exceeds 4× the half-thickness get a **bevel**.
  - Room net polygons and wall polygons share the same join points, which lets `validate` check area conservation.
- **Room ↔ face:** a room belongs to the smallest bounded face containing its seed point.
- **Other outputs:**
  - clear spans per wall;
  - opening transforms (jambs, door leaf geometry);
  - face adjacency through openings and virtual walls;
  - the building outline;
  - lazy label anchors (pole of inaccessibility) and W×L for rectangular rooms.

### 5.2 `normalize()`: pure, idempotent, a fixed point on integer mm
Steps, in order:
1. Clamp settings and round to 1 mm.
2. Record the world anchors of openings and attached items.
3. Loop, at most 64 passes:
   - merge nodes within 1 mm (spatial hash);
   - drop zero-length walls;
   - split T-contacts (keeping the original id on the stable piece, so a move and its reverse restore ids);
   - split proper crossings;
   - merge duplicate walls (ranked structural > non-virtual > thicker > lower id);
   - dissolve collinear degree-2 nodes with identical wall properties;
   - drop orphan nodes.
4. Re-host openings on the parallel wall at their anchor. Failing that is a hard error.
5. Clamp openings into the clear span, 5 cm from the ends.
6. Room re-matching:
   - sample each old room polygon at about 400 points;
   - vote by area for the new faces, with greedy one-to-one assignment;
   - fall back to seed containment;
   - merges add the loser's type as a tag;
   - any new face of 1 m² or more gets a room;
   - a seed moves only if it left its face.
7. Derive the door swing from hinge + side (DIN 107).

### 5.3 `validate()`
- **Hard errors:**
  - NaN values; settings out of range;
  - graph integrity: Euler check, leftover overlaps or crossings, thickness 0.05–1.0, height 0.3–10, opening width 0.3–6.0;
  - rooms: one per face, non-simple polygons, **area conservation** within 0.1% (Σ room net + Σ wall polygons = outline);
  - openings: host wall missing, overlap, sill ≥ head, disappeared without being deleted.
- **Soft notes:** sliver faces, open outline, opening-fit, walls under 5 cm, rooms without a door, items outside a room.

### 5.4 Commands and history
- **17 commands:**
  - walls: addWalls, moveWall (wall-run solver), moveNode, splitWall, setWall, deleteWalls;
  - openings: addOpening, moveOpening, setOpening, deleteOpenings;
  - rooms: setRoom;
  - items: addItem, moveItems, setItem, deleteItems, moveSelection;
  - plan: setSettings, setFurnishing (replaces the unlocked auto items and lights in one step), replacePlan.
- **Transaction:** deep clone → op → normalize → validate. Refusal codes are `invalid`, `structural`, `blocked` and `normalize`. A guard refuses edits that would move a plumbing fixture into another room.
- **History:**
  - entries `{label, args, before, after}`, capped at 200, with snapshots stored as full immutable plans;
  - `coalesce` merges edits within 1 s that share a key (arrow nudges, for example);
  - `dry` reuses the preview's result;
  - an edit that changes nothing adds no entry.
- **Wall-run solver** (`moverun.js`):
  - Moves the maximal collinear chain, sliding T-junctions along their lines.
  - The allowed interval is the intersection of many limits: minimum wall lengths, 0.80 m passages, openings still fitting, structural lines, pushed fixtures and furniture groups, door-swing landings.
  - Limits are rounded to whole mm so moves are reversible.

### 5.5 Probes (`core/probes.js`), shared by the editor, furnish, the bench and the Issues panel
| Probe | What it checks |
|---|---|
| overlap | Item pairs with more than 1 cm of z-overlap and more than 1 cm² of plan overlap, unless allowed to nest. Items in walls or outside rooms |
| doorSwing | 90° leaf sectors (radius = width − 0.10). Landings of leaf × 0.60 m on both sides |
| windowBlock | A keep-clear zone of (width + 0.20) × max(0.60, half the width for inward sashes), applied to items taller than sill − 0.02 |
| clearance | Each catalogue zone may overlap blockers by at most 25 cm², with exemption lists (chairs at a table, and so on) |
| reach | A 2 cm grid with an exact Felzenszwalb distance transform (0.30 m walker) and a flood fill from inside the entrance. Checks room, door-landing, seat-approach and stand reachability |

### 5.6 Catalogue (`catalog/catalogue.json`, 58 items, 11 categories)
- Each entry has:
  - `variants {key:{w,d,h,seats}}`, `mount` (floor, wall, ceiling, surface), `z0`;
  - `zones` (per side, with hard and target depth and a kind: walk, aisle, seat, fixture, bed, chairs…);
  - `nest` (what may overlap it);
  - `seats[]` and `stands[]` (used by people and the reach probe);
  - `top`/`worktop`; `sources` (provenance notes).
- **One definition feeds everything:** the 2D symbol (`symbols.js`) and the 3D builder (`models3d.js`) both read `params.js`, so plan and model agree. Furnish, probes and moverun use the same index helpers.

---

## 6. 2D editor and app shell [obs]

### 6.1 Rendering
- Canvas2D with a dpr-scaled backing store.
- `planSpace()` draws in metres; line widths are in pixels × 1/scale; line weight scales with zoom.
- Zoom 5–800 px/m. A pure `drawPlan(g, plan, derived, view, state)` function.
- **Layer order:** paper and grid → underlay → room fills → wall colour bands → furniture → door leaves → **wall poché** → virtual walls → openings → highlights → labels and dimensions → snap glyph → scale bar and north arrow.
- **Poché:** all wall polygons go into one path with rectangular cut-outs at openings (even-odd). The path is stroked at twice the width and then filled, so the inner seams disappear and only the outer faces are outlined.
- **Exterior dimension chains:** segment breakpoints come from outline edges facing each side. Numbers are rounded so the chain always sums to the overall length.
- **Room labels** (`labels.js`):
  - the floor is rasterised at about 5 cm, with obstacles for walls, furniture (+5 cm) and door swings;
  - summed-area tables answer "is this box clear?" in O(1);
  - candidates are sorted outward from the pole of inaccessibility;
  - cascade: name + area + W×L → over furniture outlines → without W×L → turned 90° → name only → a label in a neighbouring room with a leader line.
- **Caches:** offscreen layers for furniture and annotations; symbols cached per item; labels solved in idle slices (4–12 ms) per zoom bucket.

### 6.2 Tools and gestures
- **Tools:** V select, W wall, B rectangular room, D door, N window, G balcony door, P passage. Keys use `KeyboardEvent.code`, so they work on any keyboard layout.
- **Gesture model:** pointer-down → 4 px threshold → preview plan (only the moving parts patched) → exactly **one command on release**.
  - If committing a wall move would push a door off its wall, the editor bisects in 1 cm steps to the furthest valid position.
- **Snapping order:** endpoint → wall hit along a 15° step → perpendicular foot → midpoint → centreline → angle step → alignment → grid (1, 5 or 10 cm by zoom). Ctrl turns snapping off. A wall end inside an opening span is **refused**, not slid.
- **Openings:**
  - The ghost follows the pointer onto walls and slides or narrows to fit, with minimums: door 70, window 40, balcony door 120 cm.
  - Structural exterior walls ask for confirmation. Safe-room openings are locked.
- **Furniture:**
  - Placed by click-to-arm or drag-and-drop from the catalogue.
  - The ghost tries a wall-snapped pose, then the plain pose, then the nearest clear pose within 30 cm. It turns red on overlap or clearance violations; Ctrl places it anyway.
  - Dragging slides along walls and pushes other pieces aside.
  - The rotate knob steps 15°, 45° with Shift, 1° with Ctrl.
- **Typed exact values:** while a tool is active, digits plus Enter or an arrow give exact lengths (`400x300` for rooms). Clicking a dimension text edits it.
- **Guards:**
  - wall-run move: openings still fit, at least 60 cm between parallel walls, walked in 10 cm steps then bisected;
  - corners: walls at least 30 cm, angles at least 15°, no crossings, rooms at least 1 m²;
  - structural walls are refused, with an "Unprotect" confirm.
- **Touch:** 22 px targets, 500 ms long press opens properties, two-finger pinch, cursor pill lifted 44 px above the finger. It synthesises mouse events into the same handlers.
- **Keyboard:**
  - complete coverage, including Tab cycling room → walls → openings → items;
  - Esc cascade; Ctrl+S, O, I; Ctrl+Shift+F to furnish; Ctrl+Enter for 3D; F1 for help; F6 to cycle regions.

### 6.3 Shell
- **CSS grid layout:** top bar 56 px, tool rail 68 px, side panel 328 px. The right panel has tabs: Properties, Catalogue, Issues.
- **Responsive:** many breakpoints. At ≤760 px the panel becomes a bottom sheet; on coarse pointers, targets are 44 px. Light theme only, with no dark mode.
- **Feedback:** toasts (at most 2, deduplicated by key), focus-trapping modals, and a Build 3D progress card that learns stage durations and shows megabytes received.
- **Issues panel:** probes and validation run in a worker 300 ms after the last change. "Show" zooms to the problem.
- **Tutorial:** 13 steps on the sample plan, with the user's plan and history swapped out and back.
  - A spotlight cut out of an SVG overlay.
  - It detects the user's actions by polling history labels, selection and walk metrics every 100 ms.
  - Presses outside the target are blocked. Resume state is in `ap.tutorial.v1`.
- **i18n:**
  - flat dotted keys, `{var}` placeholders, plurals via `Intl.PluralRules` (Russian has 4 forms), case variants, decimal comma in Russian;
  - language priority: `?lang` > stored choice > browser > en;
  - `fromEnglish()` reverse-translates English refusal messages;
  - a pseudo-locale and a missing-key report for testing.
- **Accessibility:** focus traps; `aria-live` toasts; roving tabindex; `role=toolbar`; the canvas does not trap Tab (WCAG 2.1.2); single-key shortcuts are disabled while typing (WCAG 2.1.4); reduced-motion support.

---

## 7. Import: image or PDF to an editable plan, all on-device [obs]

> **OCR deep dive:** see `OCR_DEEP_DIVE.md`. It covers the exact versions (tesseract.js 7.0.0 and core 7.0.0, verified by hash), the heb+eng `4.0.0_best_int` models, the engine setup, the mosaic, the parsers, the label dictionary, scale fusion, the orientation votes, and live test results.

### 7.1 Pipeline
```
pick file → (PDF: pdf.js page 1 at 300 dpi, ≤3000 px) → Detection Worker:
  decode (EXIF-aware) → ≤3000 px → rotate 90°·n → paper-sheet isolation (Otsu, flood from border)
  → illumination flatten (max-filter + blur, divide) → stroke width s0
  → wall threshold sweep scored by "wallness" (long-thin runs good, fat blobs bad) → refine
  → wall mask (drop dark-thin text ink over light poché) → open/close → keep main structure
  → deskew (projection-profile sharpness, joint ±10° search, then per-family shear ±0.5°)
  → split pixels into H/V families → Manhattan run tracking → sub-pixel faces
  → junction snapping → collinear line assembly (+ gap candidates) → stray removal
  → angled walls (20–70° connectors) → bridge free ends (rays; "glazed" gap test) → doorways past Ts
  → classify gaps: door arc (sampled arc + leaf score) / glazing lines → window / passage
  → [OCR mosaic posted early, so text is read while walls are traced]
Main thread: tesseract (text engine heb+eng PSM 6; digits engine with whitelist), rereads,
  orientation vote (90°/180°)
Emission Worker: scale fusion → pixels→metres → wall thickness classes → openings → repair loop
  (normalize+validate until clean) → classify exterior/structural → labels → balconies/kitchen
  → least-squares snap to printed sizes → confidence per element
Wizard: Crop/rotate/straighten → Calibrate (2 clicks + typed length) → Review (one-click fixes) → Accept
  = one undoable replacePlan; rectified image kept as a 20% underlay for tracing
```

### 7.2 Key techniques
- **Every pixel parameter is derived from the image itself:** stroke width `s0` and median glyph height `hT`. Nothing is tuned to one plan.
- **Hollow (outlined) walls:** a separate mask built from paired parallel thin lines, rejecting glazing triples, dimension lines and fixture rings. **Hatched poché:** a diagonal-texture density mask.
- **Door detection:** the hinge is tried at both ends and both sides, with radius × {0.92, 1, 1.08}. Arc samples are taken every 3° from 8° to 82°, scored 0.7·arc + 0.3·leaf. A precise arc-cover test (≥ 0.6) confirms it. Fallbacks: `doorInGap` and `swingAcross`.
- **Text:**
  - glyph components grouped by grid-hashed union-find;
  - a block must sit inside walls on 3 of 4 ray directions, or on a ticked dimension line;
  - rays measure the clear room box and spans through each block;
  - crops are upscaled to about 34 px glyph height and packed into a mosaic (at most 140 crops).
- **Parsers:** W/L sizes (`335/285`, cm or m), dimension strings (`-615-`), areas (m², Hebrew מ"ר, sq ft), and common letter-for-digit OCR fixes.
- **Scale fusion:**
  - every candidate scale is tried as a hypothesis (deterministic, not random RANSAC);
  - inliers are within |Δ ln k| ≤ 0.025, at most one per text block;
  - three weighted-median refinements follow;
  - the result is vetted against priors: median door about 0.80 m, thinnest wall class 0.10 m, thickest 0.25 m;
  - priority: user calibration > vetted text > priors.
- **Least-squares snap** (`snap.js`):
  - variables are the axis-aligned wall-line positions;
  - observations: the drawn position (σ 1.5 px) and printed sizes (σ 0.5 mm);
  - a size more than 6% off the drawing is gated out;
  - iterative rejection of the worst residual, with structural or exterior lines pinned;
  - openings, seeds and items are warped piecewise-linearly;
  - auto-applied only if 3 or more sizes fit and no line moved more than 25 cm.
- **Room semantics:**
  - a multilingual label dictionary (Hebrew developer vocabulary plus English, French, German, Russian) with Hebrew normalisation (final letters, niqqud, abbreviations) and fuzzy matching;
  - balcony closing, kitchen hob detection with a guessed sink, safe-room heuristics, corridor and laundry detection.
- **The output is never invalid:** a repair loop attributes each hard error and drops or fixes the offending element. Drafts that are too broken fall back to "Trace": an empty plan over the image.
- **Confidence per element:** walls start at 0.92 and are capped by width ratio, mask support and dangling ends. The wizard colours them green, amber or red.

### 7.3 What the code admits it can't do
- Perspective/keystone correction (only rotation plus shear).
- Multi-page PDFs and PDF vector paths.
- HEIC input.
- Sink detection.
- Angled walls, beyond straight connectors.
- Mixed hollow and solid walls.
- [inf] The constants are tuned on a small corpus of Israeli developer plans ("the owner's sheet").

---

## 8. Auto-furnish [obs]

### 8.1 Pipeline (`furnish/index.js`, version `furnish-9`, runs in a Worker)
1. Analyse each room: edges mapped to walls, opening intervals, door landings, portals on open edges, free wall intervals per item class, wall slots (ends, centre, window centre…).
2. Type each room. Evidence order: user/label type → service-balcony tag → plumbing fixtures inside → geometry (entrance → hall, aspect or width → corridor, area and windows → storage, bedroom…). The master is the largest bedroom.
3. Place rooms in a fixed order: dining → living → kitchen → bedroom → … → bathroom.
4. For each room:
   - curtains first (their stacks constrain the layout);
   - beam search over the room's **program** of groups;
   - the seed picks a layout;
   - fallbacks;
   - "dress" swaps.
5. Decor, then main-path repair, then global verification with the core probes, then lights.
6. Write-back: one `setFurnishing` command, which is undoable. Locked and user items are kept.

### 8.2 Programs (examples)
- **Living:**
  - kitchen run if plumbing is present; island from 28 m²;
  - seating group (TV console → sofa at a viewing distance of 2.3 m or more → coffee table 0.45 m in front → armchairs → rug);
  - dining table (4 seats; 6/4 from 20 m²; 8/6 from 40 m²), trying both orders: table-first and seating-first;
  - sideboard from 24 m².
- **Master bedroom:** bed size by area (180/160/140 from 14 m²), nightstands, a wardrobe run up to 3.0 m, then a dresser or desk.
- **Other rooms:** bathrooms get tub/shower, WC and vanity as must-haves; kitchens get the run, an island from 14 m² and a table from 8.5 m²; halls get a shoe cabinet and console; balconies an outdoor table and lounge chair; service balconies a drying rack and washer.
- **Candidate scoring:** hand-tuned weights. Examples:
  - bed head opposite the door wall +0.8;
  - +0.25 per metre from the door;
  - desk within 1.6 m of a window +1.2;
  - TV wall square to the main glazing +1.8;
  - −1.2 for each door-to-door line crossing the seating group.

### 8.3 Search and constraints
- **Beam:** width 6 by default (up to 20 for beds), 3 per state, candidates cached.
  - Skip states cost 20 for must-haves and 6 for required groups.
  - Ranking: fewest missing → fewest cannot-fit notes → fewest last resorts → score.
  - A layout that only fits by narrowing the main path first tries a shift of 5–30 cm, else takes a penalty of 7.
- **Hard checks** (`hard.js`, mirroring the probes and stricter where the 3D view needs it):
  - overlap with z ranges and nest rules; inside the room;
  - door sectors, landings, a swing corridor and the leaf-tip box;
  - window zones; wall-mounted items kept off opening spans;
  - catalogue clearance zones with exemptions; curtain stacks.
- **Room reachability:** a 5 cm grid, an exact distance transform, a 0.66 m walker, flood fill from a door. Targets are door landings, portals, seat approaches, stands and bed sides. The main path between doors is a 0.80 m way.
- **Variety:**
  - "acceptable" layouts are those within a tolerance of the best, with no more missing groups;
  - "distinct skeletons" are those where an anchor moved more than 0.6 m or turned;
  - the seed rotates through them with a per-room phase; for the living room and master bedroom (`skeletonPick`) the anchor always moves;
  - 10 "taste" bits per room (round coffee table, island yes/no, smaller bed…) via `((seed−1)·725) mod 1024`;
  - Gray-code dress swaps, so consecutive seeds differ by exactly one piece.
- **Kitchen packer:** the sink and hob never move.
  - The run extends up to 2.2 m past the fixtures.
  - The fridge closes a run end on a full-height wall, at least 0.95 m from the hob.
  - Base modules are fitted exhaustively (60, 80, 45, 40, 30 cm), minimising leftover, then count.
  - The dishwasher goes beside the sink; wall cabinets and a hood go above.
  - The island is 280×100 or smaller, with a 1.15–1.25 m aisle and stools at 0.6 m each.
- **Repairs:**
  - path repair nudges by 3–6 cm, shrinks the anchor one size, nudges by 10–20 cm, then drops loose pieces in priority order;
  - global verification runs up to 40 rounds of dropping the lowest-priority offender.
- **Lights:**
  - pendants over dining tables (1–2) and islands (2–3);
  - ceiling fittings per room: a pair in front of the sofa, one about every 3 m in corridors, otherwise at the label point;
  - each at least 0.35 m from walls and 0.6 m from each other.
- **TODO in the code:** an annealing pass ("Merrell terms"), L and U kitchen runs, a work triangle, a bar counter.

---

## 9. Random apartment generator [obs] (`core/randomplan.js`)
- **Id:** `rnd-<1–6>[b][x][v]-<uint32>`. b = balconies, x = extra baths, v = portrait. N rooms = the living room + (N−1) bedrooms.
- **Skeletons:** 13 hand-designed ones, each a grid of room tokens with metre ranges per column and row. Each also lists door links, optional rooms with probabilities, the entry, the safe room and the balcony priority.
- **Attempt:** for each attempt:
  1. Draw sizes on a 5 cm grid until area, minimum side and aspect pass.
  2. Mirror or rotate.
  3. Extract the walls (exterior/core structural 0.25–0.30 m).
  4. Place, in order: the entrance; balconies; doors (avoiding the entrance axis and doors facing each other); windows (about 11% of floor area as glazing).
  5. Place fixtures by greedy search.
  6. normalize, validate and the probes must all be clean.
  7. `checkPlan` musts: counts, area bands, circulation at most 14–15%, glazing at least 10%, cross-ventilation, access BFS (private rooms reachable only from shared space), corridor caps, door-leaf conflicts.
- **Retries:** up to 60 attempts per skeleton, then the other skeletons. The result is deterministic per seed.

---

## 10. 3D renderer [obs]

### 10.1 Renderer
- **Backend:** `WebGPURenderer`, or `forceWebGL` when `navigator.gpu` is missing or `backend=webgl2` is set.
- **Output:** AgX tone mapping, exposure 1.5 (a stated placeholder), sRGB output. Camera near/far 0.05/200 m, 60° FOV.
- **Tiers:**

| | lite (default) | high / photo |
|---|---|---|
| MSAA | 0 | 4 |
| Pixel ratio | ≤1 | ≤2 |
| Shadows | none; sun patches instead | 4096² sun shadow map |
| Materials | Lambert, albedo only, ≤512 px | Physical + normal/ORM, room reflection probes, planar mirrors |
| Lamps | 3 lamp slots following the camera | 16 lamps |

- **Dynamic render scale** (lite): levels 1 → 0.5. It steps down below 26 fps and up above 45 fps, with hysteresis, a ceiling after a failed step up, and doubling backoff, so it never oscillates.

### 10.2 Module contract and Build 3D
- **Contract:** `{name, init, build(plan, ctx) → {object3d, stats}, update, dispose, check?, onView?}`. Modules: materials, shell, furniture, decor, lighting, figures, npc, walk. Each one's errors are isolated.
- **Build:** stages in order, each timed, with one paint between stages. Then warm-up: `compileAsync`, then draw every group, then draw with culling off, so every pipeline is made before the user sees the scene.
- **The "zero new pipelines per rebuild" toolkit:**
  - fixed named material library created once, with all parameters as uniforms;
  - one shared vertex layout (position, normal, uv in metres);
  - wall paint as vertex colour on one material;
  - view switches as layer masks;
  - a fixed light pool;
  - hidden 2 mm "swatch" triangles per material for warm-up;
  - `pinPipelines`, which bumps the private three.js pipeline caches before disposal.

  Checked live: 34 programs.
- **Leak probe:** per-tier baselines of textures, GPU MB and heap. From the third rebuild of the same plan, growth over 8 MB counts as a leak.

### 10.3 Geometry
- **Walls:** built from core's mitred polygons, cut into slabs at opening edges. Solid slabs run floor to top; opening slabs keep a sill and a head. The slab end faces *are* the reveals, so there is **no CSG**.
  - Per-room finishes on each face; tiles centred per face.
  - Black top caps so the top view matches the 2D poché (checked at IoU ≥ 0.98).
  - Exterior walls of 1.3 m or less become a glass railing.
- **Floors and ceilings:**
  - Floors are one polygon per room. Planks and tiles are laid out in a frame shared by connected rooms.
  - Ceilings drop to 2.40 m in wet rooms and halls, with bulkheads where they meet higher ceilings.
  - Thresholds and skirting are real geometry.
- **Openings:**
  - door frames, architraves and leaves open 85° on the 2D swing side;
  - windows with sashes by style, double glazing (seeded micro-tilt), stone sills, roller shutters set by time of day;
  - safe-room steel doors and windows.
- **Details:** switches at 1.05 m on the latch side, sockets every 3.5 m at 0.30 m, AC diffusers, safe-room vents.
- **Dollhouse:** everything is split at a 1.0 m cut. Exterior walls facing the camera are lowered (with hysteresis), eased over 0.12 s. Lite rewrites vertex ranges inside merged buffers instead.
- **The outside world** is procedural, cached and about 95% of the shell's triangles:
  - a street grid, low buildings near and towers far, with rooftop solar heaters and AC units;
  - trees made of alpha-tested leaf cards from a seeded canvas atlas, with coverage-preserving mips;
  - a skyline;
  - lite budget of about 12 draw calls.
- **Furniture:** about 55 parametric builders: lathe, sweep, rounded box, cushions, drape, tube.
  - UVs are in metres; AO is baked into vertex colours.
  - Parts are merged per (room × material) in high and per material in lite.
  - A per-item geometry cache.
  - A fit check: each body box must be within 1 cm of the catalogue size.
  - Rug and art images (generated pools) are packed into canvas atlases.
  - The decor layer adds cushions, books, props and towels.

### 10.4 Materials and lighting
- **Materials:**
  - about 90 named definitions with target albedo and roughness, plus aliases;
  - procedural planks, herringbone, tiles (random lippage and grout) and wood staves, all in TSL;
  - textures are WebP albedo/normal/ORM per set, with a manifest giving real-world repeat size and measured mean albedo;
  - **no KTX2 yet** (a TODO).
- **Sun:** NOAA fractional-year equations → azimuth and elevation, mapped through `northDeg`.
  - Bug: the UTC offset is hard-coded to 3 while config says 2.
  - High: a shadowed sun plus hemisphere, with a shadow map frozen at night.
  - Lite: an unshadowed sun plus "sun patches", window shapes projected onto the floor and blended multiplicatively.
- **Lamps:** placed at the plan's light fittings. Their intensities are placeholder units, pending "the lighting decision".
- **Contact shading:** one merged mesh of soft dark rectangles under furniture and along wall bases.

---

## 11. Walkthrough [obs] (`walk/*`)
- **Controls:**
  - WASD/arrows at 1.2 m/s (accelerate 4 m/s², decelerate 6 m/s²); Q/E turn at 90°/s;
  - mouse look with pointer lock, or drag-look;
  - touch: a joystick, and tap-to-walk along the nav path;
  - eye height 1.50–1.80 m and FOV 50–75° are user settings.
- **Collision:**
  - the walker is a 0.25 m circle;
  - static polygons: walls with doorways cut out, furniture 0.30–1.75 m tall, open door leaves;
  - people are circles;
  - sub-steps of at most r/2, push-out over 4 iterations;
  - door assist (pull toward the middle of a doorway) and a wall slow-down.
- **Navigation:** a 5 cm grid, A* with a wall-proximity cost, string pulling that never reduces clearance, Chaikin corner rounding.
- **Reachability:** flood fill from the entry. Door leaves that block a room are dropped greedily and shown nearly closed. Teleports into unreachable rooms are refused.
- **Views:**
  - named viewpoints (entry, living, kitchen, bed1, bath, window), framed like an interior photographer would: a 72-bin ray panorama scored per yaw, vetoes for nearby walls, door leaves and people, and lens shift instead of tilt;
  - dollhouse orbit and top view, a room tour and an auto tour, a minimap with teleport.

---

## 12. People: a household for scale [obs] (`people/*`, 11k lines)
- **Cast:** 45 CC0 MakeHuman characters.
  - Quantised binary: Int16 positions, Int8 normals plus AO, Uint8 skin weights. Texture-array strips in WebP.
  - Lite: per-character files of about 245 KB, LOD 1, 512 px albedo, no normal maps.
  - Load-time fixes: heel reskinning, hem weights, skin pushed under garments, beard shells.
- **Rendering:**
  - one `SkinnedMesh` per person with a 22-bone skeleton; skin matrices are written directly;
  - **one shared TSL material**, with a per-person "look row" in a 44×16 float texture: tints, face-shape coefficients, light-probe SH;
  - skin, hair (Kajiya-Kay), eye and garment-pattern shading;
  - contact shadows under the soles, all people in one draw.
- **Animation:** procedural, no mocap.
  - Walk: heel→toe roll, 2-bone IK, inverted-pendulum pelvis, step length from speed; loops baked every 5 cm/s and blended.
  - Footstep-scheduled start, stop and turn-on-the-spot transitions.
  - A foot lock with IK, so feet never skate.
  - Sitting fitted to each seat's height and backrest using the character's own mesh; counter work with the palm on the worktop.
- **Simulation:**
  - The household is decided by `pseed`: 1–8 people (lite caps it at 2), at most about 1 per 15 m².
  - Roles (cook, sitter, walker, talker). Anchors from furniture seats and stands, kitchen spots and windows, with reservations.
  - Activities are picked by weighted roulette, with durations (sofa 30–90 s and so on).
  - Navigation: a 5 cm grid, A* with a clearance cost, string pulling, door squaring, corner arcs.
  - Visitor avoidance: halt, re-plan, step aside.
- **Budgets:** planning 0.35–0.6 ms per frame on lite. Seat fits are time-sliced, and texture decode runs in workers.

---

## 13. Bugs and inconsistencies found (useful lessons) [obs]
- The sun uses a hard-coded UTC+3, while `CONFIG.site.utcOffset` is 2 (`scene3d/lighting/index.js:111`).
- `view3d.js` calls `lighting.photoSamples()` and lighting calls `shell.setOutdoor()`; neither function exists. The photo tier is unfinished.
- Corner sofas are never offered: the catalogue lacks the `lshape` flag that `program.js` requires.
- `keepLocked` is passed to furnish but never read. Several `P` constants in `program.js` are unused.
- The tag `'sealed'` is used, but it is missing from the `ROOM_TAGS` enum. The category `'dressing'` is referenced, but no catalogue item has it.
- The default furnish version differs: `furnish-1` (schema) vs `furnish-0` (randomplan). The fallback ceiling is 2.6 vs 2.65 in config.
- Some comments are stale: the serialize precision, `emit.js` still says "main thread", and `text.js` says crops are "binarised" when they are actually stretched.
- The people foot-contact turn gate is deliberately disabled, pending re-tuning (dated 2026-11-07).

---

## 14. Building your own: recommended plan

### 14.1 Stack
- **Language and build:** TypeScript with Vite (or no-build ESM, like Floorstride). Define the plan schema as types plus a runtime validator (zod or valibot).
- **Plan-core:** pure TypeScript, unit-tested in Node with Vitest. Property and fuzz tests on commands, using `commandList()`-style arg schemas, and invariants (Euler, area conservation, serialize round-trip) as oracles.
- **2D:** Canvas2D (consider an SVG/PDF export backend from the same display list; Floorstride lists that as a TODO).
- **3D:** three.js `WebGPURenderer` with WebGL2 fallback. Start with standard materials and add TSL later. Use **KTX2/Basis** textures from day one (they haven't).
- **Workers:** Comlink, or the same `{id}` message pattern.
- **Import:** pdf.js plus tesseract.js (or an OCR/vision API if you accept server costs and privacy trade-offs). OpenCV.js is optional, but their pipeline shows typed-array kernels are enough.
- **Hosting:** any static CDN (Cloudflare Pages/R2, Netlify) with **content-hashed release folders** and an uncached `index.html`. Add a backend only for accounts, share links or cloud saves.
- **Testing:** Playwright driving a `window.__app`-style API and URL params (`capture=1`). Golden screenshots. Probe counts must equal 0.

### 14.2 Phases (rough single-developer estimates [inf])
| Phase | Scope | Est. |
|---|---|---|
| P0 Plan-core | schema, canonical JSON, integer-mm normalize, half-edge faces and mitres, validate, commands and undo | 3–5 weeks |
| P1 2D editor MVP | walls, rooms, openings, furniture placement; snapping; preview-then-commit; save, open, autosave; PNG export | 4–6 weeks |
| P2 3D MVP | wall slabs with reveals, floors and ceilings, 6–10 materials, sun and hemisphere, walk with collision, dollhouse, top view | 4–6 weeks |
| P3 Catalogue | 20–30 parametric items (2D symbol and 3D builder from one definition), clearance zones | 3–4 weeks |
| P4 Auto-furnish v1 | room typing, programs for 5 room types, beam search, hard checks, reach grid, seed variants | 6–10 weeks |
| P5 Import v1 | **trace-over-image**: upload, rotate and straighten, 2-point calibrate, 45% underlay | 1 week |
| P6 Import v2 | solid-poché CAD plans: threshold, deskew, run tracking, bridging, door/window classification, repair loop | 2–3 months |
| P7 Polish | random plans, tutorial, i18n, people (use off-the-shelf rigged glTF plus Mixamo clips first), quality tiers, mobile | ongoing |

Their hardest-won parts are worth budgeting for:
- room identity across topology edits;
- the wall-run solver;
- automatic import (hundreds of tuned constants);
- furnish weights, which need a calibration bench of real plans;
- WebGPU pipeline stability, which depends on three.js private internals and breaks across upgrades;
- foot-locked people animation.

### 14.3 Where you could beat them
- Share links or cloud saves (they have none), and a dark theme.
- Multi-page and vector PDF import, perspective correction for phone photos, angled walls.
- Markets other than Israel: imperial units, other wall standards, more label languages.
- KTX2 textures, furniture level of detail, a physically based lighting pass (all are TODOs in their code).

### 14.4 Legal and ethical notes
- **Do not copy their source.** No licence file is served, so assume all rights are reserved. Re-implement from the algorithms described here.
- **Assets:** download CC0 textures yourself from Poly Haven and ambientCG, and MakeHuman characters from MakeHuman. Do **not** reuse their generated rug and art images, fixture plans or the owner's private plans.
- **Branding:** don't use the Floorstride name or replicate its look-and-feel 1:1.

---

## 15. Coverage ledger
| Question | Status | Evidence |
|---|---|---|
| Hosting, CDN, caching, deploy model | Answered | Headers [obs]. Pi and `serve.py` [inf] from comments. Tunnel vs DNS [unk] |
| Backend, APIs, analytics | Answered: none | Grep over the full source, live network capture, REA (its 3 "endpoint" nodes are false positives from URL-param reads) |
| CI, build pipeline, repo, tests | Partial | Bench and harness are referenced (`tools/bench/*`, `.claude/skills/*`, Python tools) but not shipped [unk] |
| Data model and plan-core | Answered | Code |
| 2D editor and UI | Answered | Code |
| Import | Answered (algorithms) | Code. Accuracy is unmeasured |
| Auto-furnish | Answered | Code, plus one live timing (0.93 s on this machine) |
| 3D, walk, people | Answered | Code, plus live stats on WebGPU / lite |
| High and photo tiers | Partial | Code only. Their assets aren't served publicly |
| Asset pipelines (texture post-processing, people build, art/rug generation) | Unresolved | Scripts not shipped |
| `docs/ARCHITECTURE.md` (§1–18) | Unresolved | Not deployed |
| Mobile, WebGL2 fallback behaviour | Not tested | Code paths exist |

**REA evidence:**
- Full mirror: `ev_205ad144a60a1f41f5a295e4373cb47fc1a8028117f3d9aa1f39e5c8ff858b8a` (114 files, 0 parse failures, 302 module nodes, 915 relations).
- Summary view: `ev_9349fa2aee95b587414432db5f9eb68e089a9bf913e6f53500f185217e724907`.
- First 72 files: `ev_09ee4d96cc9254a6fd075b7af12f1578ef097d7bb55b8d7ceaed8a9e5f289f5b`.
- REA's semantic coverage is *partial*: per-file relation expansion hit its result budget. The code-level reads above fill that gap. REA's `build-reconstruction-obligation-ledger` can later check your rebuild against the original, once you have one with test cases.

The working files (source mirror, REA evidence JSON) were kept locally and are not part of this repository.
