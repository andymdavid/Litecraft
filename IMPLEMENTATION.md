# LiteCraft — Implementation Plan

See [VISION.md](VISION.md) for the why. This document is the how, in phases we work against.

> Status markers: `[ ]` todo · `[x]` done · `[~]` in progress.
> Facts about LightCraft and Claude Code come from their docs at the time of writing and are marked **(verify)** until tested here.

---

## Architecture

```
Claude desktop app (Code tab)  ← user chats here: start jobs, give feedback
  │
  └─ LiteCraft plugin
       ├─ skill: SKILL.md (procedure) + house-style.md (rules)
       ├─ MCP: lightcraft-cli mcp            (two modes, below)
       ├─ scripts: check-verticals, check-highlights, crop-suggest, job log
       └─ presets: camera/, lens/, looks/

Stage A — batch edit (headless)
  lightcraft-cli mcp --library <job>/library
  import → preset stack → per-photo loop → 4:5 crop → status labels → log

        ── hand-off: headless session ends, library lock released ──

Stage B — review (desktop app, shared session)
  lightcraft --control 7980 <job>/library          ← user inspects + tweaks
  lightcraft-cli mcp --connect 127.0.0.1:7980      ← Claude applies feedback,
                                                     reads user tweaks, screenshots
  → export
```

**Why this shape:** nothing to build for review — the user gets a real editor for subtle tinkering, and the user's tweaks become training signal. The Claude app is the job runner; the skill is the logic; LightCraft's library/XMP is the single source of truth for edits.

**Library lock (from LightCraft docs):** a library is open in one program at a time (`catalog.lock`). While the desktop app has it open, headless `--library` on the same folder fails; use connect mode instead. In connect mode Claude operates on the app's live session, so the user's edits are visible to `get_develop`. **(verify)**

**Turn-taking:** Claude and the user don't edit the same photo simultaneously. The skill announces hand-backs ("done with #12 — over to you").

**Auth:** user's own Claude Pro/Max login in the desktop app. Local, single-user. If this ever ships to other users, switch to Agent SDK + API key.

---

## Repo layout (target)

```
LiteCraft/
├── VISION.md
├── IMPLEMENTATION.md
├── plugin/                     # Claude Code plugin
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json               # lightcraft-cli mcp (headless / connect)
│   ├── skills/
│   │   └── interior-edit/
│   │       ├── SKILL.md        # procedure: first-run → setup → batch → hand-off → review → export
│   │       ├── house-style.md  # measurable style + crop composition rules
│   │       └── preferences.default.json  # defaults + the first-run questions
│   └── scripts/
│       ├── check_verticals.py  # OpenCV line-angle measurement
│       ├── check_highlights.py # clipped-window / blown-area check
│       ├── crop_suggest.py     # candidate 4:5 rects + composition scores
│       └── job.py              # create/update job.json + logs (atomic writes)
├── presets/
│   ├── camera/                 # canon-m50.lcpreset (colour base)
│   ├── lens/                   # sigma-30-f14-dcdn.lcpreset (vignette/CA)
│   └── looks/                  # bright-natural.lcpreset, … (derived from finals)
├── feasibility/                # Phase 0 spike: notes, results, comparisons
└── Samples/                    # gitignored: source images + human finals
```

---

## First-run setup + preferences

On first use (no preferences file found), the skill asks the user a short set of questions in chat, then saves the answers. Every later job reads them silently.

**Stored outside the plugin** so plugin updates never overwrite them:
`~/LiteCraft/preferences.json`

**First-run questions** (each with a recommended default, so the user can just say "defaults are fine"):

| Key | Question | Options | Default |
|---|---|---|---|
| `crop.portrait` | Portrait shots — crop to? | `4:5` · uncropped | `4:5` |
| `crop.landscape` | Landscape shots — crop to? | `4:5` portrait · `5:4` landscape · uncropped | ask (no default yet) |
| `look.default` | Default look | from `presets/looks/` | `bright-natural` |
| `export.long_edge_px` | Export size (long edge) | number · full-res | full-res |
| `export.format` | Export format | JPEG · TIFF | JPEG (quality 90, sRGB) |
| `export.folder` | Where exports go | job `export/` · custom path | job `export/` |
| `review.auto_open` | Open LightCraft automatically when the batch finishes? | yes · no | yes |

`preferences.json`
```json
{
  "schema": 1,
  "answered": "2026-10-17",
  "crop": { "portrait": "4:5", "landscape": "4:5" },
  "look": { "default": "bright-natural" },
  "export": { "long_edge_px": null, "format": "jpeg", "quality": 90, "color_space": "srgb", "folder": null },
  "review": { "auto_open": true }
}
```

Rules:
- **Change anytime in chat:** "from now on keep landscape shots uncropped" → Claude confirms and updates the file.
- **Per-job override** without changing defaults: "this job, leave landscapes uncropped" → stored in `job.json` only.
- **Resolution order:** job override → `preferences.json` → `preferences.default.json`.
- New preference keys added in later versions are asked once, the next time they're needed — not via a full re-onboarding.

---

## Job folder

```
~/LiteCraft Jobs/<job-name>/
├── library/                      # LightCraft library for this job (one job = one library)
├── job.json                      # photo list + status
├── log/<photo-id>.json           # every change + reason (audit + learning)
└── export/                       # final full-res 4:5 output
```

`job.json`
```json
{
  "schema": 1,
  "name": "smith-kitchen",
  "source": "/Users/.../Smith Kitchen",
  "look": "bright-natural",
  "crop": { "portrait": "4:5", "landscape": "4:5" },   // resolved from preferences + any job override
  "stage": "batch | review | exported",
  "photos": [
    {
      "id": "12",
      "slug": "kitchen-island",
      "file": "IMG_0412.CR3",
      "status": "queued | editing | done | flagged | approved | exported",
      "iterations": 3,
      "flag_reason": null,
      "updated": "2026-10-17T17:42:10Z"
    }
  ]
}
```

`log/<photo-id>.json`
```json
{
  "schema": 1,
  "id": "12",
  "entries": [
    {
      "iteration": 1,
      "at": "2026-10-17T17:40:02Z",
      "source": "preset | agent | feedback | user-tweak",
      "changes": [
        { "control": "light.exposure", "from": 0.0, "to": 0.4,
          "reason": "Room underexposed vs. reference; midtones at 38%, target 50%" },
        { "control": "crop", "from": "full", "to": { "aspect": "4:5", "rect": [0.12, 0.0, 0.66, 1.0], "angle": 0.0 },
          "reason": "Centred on window + chairs; full chair legs kept; mantel edge excluded" }
      ],
      "checks": { "verticals_deg": 0.2, "clipped_highlights_pct": 0.3 },
      "feedback": null
    }
  ]
}
```

`source: user-tweak` entries are written when Claude diffs the user's manual changes in review (via `get_develop`).

### Status inside LightCraft

So the user can filter to what needs attention without a separate app. Commands: `photo.label`, `photo.flag`, `photo.setMeta` (verified in connect mode).

| Status | LightCraft marker |
|---|---|
| done (agent passed all checks) | green colour label |
| flagged (needs human eyes) | red colour label |
| approved (user OK'd) | pick flag |
| reject (don't export) | reject flag |

Photo IDs and slugs go in the **title** (`#12 kitchen-island`) and a hierarchical keyword (`litecraft|#12`), via `photo.setMeta`. Claude's plain-English summary of what changed and why goes in the **caption**, so the audit trail is visible inside LightCraft. Keep keywords out of exports (`keyword.edit {includeOnExport: false}`).

---

## Edit order (per photo)

Geometry before crop, crop before tone — tone checks are measured on what will actually be delivered.

1. Preset stack: camera base → lens base → look
2. Geometry: Upright / straighten → vertical check
3. **4:5 crop** (see below)
4. Tone + colour loop on the cropped frame: render preview → checks → adjust → log (cap: 6 iterations)
5. Final checks → status label → log

## 4:5 crop step

Sources are full-frame (M50 = 3:2). The deliverable is mostly **4:5**. The target ratio per orientation comes from preferences (`crop.portrait`, `crop.landscape`) — set on first run.

- **Portrait 3:2 → 4:5:** trims ~17% of height — a light crop; mostly about ceiling/floor balance.
- **Landscape 3:2 → 4:5 portrait:** keeps ~53% of the width — a heavy crop; composition matters a lot, so flag more readily.
- **Landscape 3:2 → 5:4 landscape:** trims ~17% of width — light.
- **Uncropped:** skip this step (straighten-only).

Approach:
- `crop_suggest.py` proposes a few candidate 4:5 rects (centred on the dominant vertical symmetry, rule-of-thirds variants, subject-weighted) with simple scores: verticals stay parallel, no key object cut at the edge, balanced ceiling/floor.
- Claude renders the candidates, picks one using the house-style composition rules, applies it with the LightCraft `crop` tool (normalised rect + angle), and logs why.
- Flag for review when no candidate keeps the key elements whole.
- Crop is non-destructive — the user can drag it in LightCraft during review.

House-style composition rules (seed, refine from finals):
- Verticals perfectly vertical; architecture centred when the room is symmetrical.
- Don't amputate furniture, art, lamps or plants at the frame edge — include fully or crop decisively.
- Keep breathing room above the main subject; avoid large empty ceiling.
- Tabletop/vignette shots: subject on a third or centred, background softness preserved.

---

## Phase 0 — Feasibility spike

**Goal:** answer "production-viable, viable with caveats, or blocked?" on real images.

Inputs:
- [x] Camera + lens: Canon EOS M50, Sigma 30mm F1.4 DC DN (EF-M)
- [~] Reference pairs: 2 pairs as Lightroom screenshots (`Samples/Test-1`) — style direction only
- [ ] 10–20 original **CR3** files + the human finals for the same images, exported full-res from Lightroom
- [ ] Confirm the living-room reference was shot on the M50 (it looks wider/phone-like)

Tasks:
- [x] Build `lightcraft` + `lightcraft-cli` from source into `vendor/lightcraft` (gitignored) — source is **v0.8.0** (commit `f34c7a8`, 2026-10-15). For handover, use the macOS release assets instead (app + separate `lightcraft-cli-<version>-macos-<arch>.zip`, same version, verify `SHA256SUMS.txt`). Release build on M4 / 16 GB: ~3 min
- [x] Headless MCP: `lightcraft-cli mcp --library <dir>` — import, `set_develop`, `crop`, `get_develop` all work (tested with `dev/mcp_probe.py`)
- [x] `render_photo` returns image content Claude can see (JPEG/PNG, `size` = long edge)
- [ ] M50 CR3 + C-RAW decode on real files (docs list the M50 as exact for both) **(verify)**
- [x] **Hand-off:** headless edits persist in the library → `lightcraft --library <dir> --control 7980` shows them → `mcp --connect 127.0.0.1:7980` reads/edits the live app, `screenshot` works
- [x] Library lock: headless `--library` on an open library fails with a clear message pointing at `--control` / `--connect`
- [x] User slider tweaks in the app are visible live via `get_develop` in connect mode (tested: contrast 0 → −11, exposure +1.00 → +1.13 made by hand in the app)
- [x] Status markers via `run_command`: `photo.label {label, ids}`, `photo.flag {flag, ids}`, `photo.setMeta {ids, title, caption, addKeywords}` — label shows on the filmstrip; query by `filter: {label}`
- [ ] Check how the caption renders in the app's info panel (candidate audit surface: per-photo "what changed and why")
- [ ] `crop` tool: apply a 4:5 rect, confirm export honours it **(verify)**
- [ ] Colour test: M50 rendering (per-file JPEG fit) vs. human finals
- [ ] **M50 camera profile:** `lightcraft-cli calibrate --max 300 <folders of M50 CR3s>` pools many files against their embedded JPEGs into one per-model profile (needs ≥ 5 usable photos; CR3 supported). Targets Canon's own look, not Adobe's — the camera base preset bridges the rest. Note: Canon Auto Lighting Optimizer isn't modelled — recommend turning ALO off in camera
- [ ] Lens test: vignette at f/1.4–f/2.8; store correction
- [ ] Mask test: window pull with luminance range; test external mask import **(verify)**
- [ ] Match the reference pairs by hand-driving LightCraft via MCP; record settings
- [ ] Measure: time/photo, iterations/photo, Claude usage/photo, quality vs. human finals
- [ ] Write `feasibility/REPORT.md` with side-by-sides and a go/no-go

**Exit:** a decision, and a list of the LightCraft gaps that actually bite.

---

## Phase 1 — Presets

**Goal:** a native preset stack that gets every image ~80% of the way with no agent.

- [ ] `camera/canon-m50` — colour base tuned against human finals
- [ ] `lens/sigma-30-f14-dcdn` — vignette / CA (distortion likely negligible)
- [ ] `looks/bright-natural` — first look, seeded from the reference pairs: lifted exposure, neutral-to-warm whites, lifted shadows with true blacks, moderate vibrance (greens/yellows/wood), gentle contrast + slight clarity
- [ ] Further looks as finals arrive (e.g. moody/evening, mixed-tungsten)
- [ ] `presets/README.md` — stack order and how presets combine
- [ ] Script: apply stack + default centred 4:5 crop to a folder via `lightcraft-cli` and export — the "no agent" baseline

**Exit:** preset-only output measured against human finals; baseline numbers recorded.

---

## Phase 2 — Plugin + skill (the agent pipeline)

**Goal:** the user runs a whole job from the Claude desktop app and reviews it in LightCraft.

- [ ] `plugin/.mcp.json` wiring `lightcraft-cli mcp` (headless by default; connect mode for review)
- [ ] `house-style.md`: measurable rules — verticals ≤ 0.5°, clipped highlights ≤ 0.5% outside light sources, neutral whites, midtone target — plus crop composition rules
- [ ] `SKILL.md` procedure:
  0. **First run:** if `~/LiteCraft/preferences.json` is missing, ask the first-run questions and save answers
  1. **Setup:** load preferences (+ any per-job override from the user's request); create job folder + `job.json`; detect camera/lens from EXIF
  2. **Batch (headless):** import → preset stack → geometry → 4:5 crop → tone loop (cap 6) → status label + keywords → log
  3. **Summarise in chat:** N done, N flagged and why, what to look at first
  4. **Hand-off:** end headless session (release lock) → open LightCraft with `--control` on the job library → connect via MCP
  5. **Review loop:** apply chat feedback by photo ID; on request (or before export) diff user tweaks via `get_develop` → log as `user-tweak`
  6. **Learn:** propose preset / house-style updates from recurring feedback and tweaks (user approves)
  7. **Export:** full-res 4:5 to `export/`, skipping rejects
- [ ] `check_verticals.py`, `check_highlights.py`, `crop_suggest.py`
- [ ] `job.py` — atomic job/log writes so the skill stays declarative
- [ ] Previews at ~1200px long edge (enough to judge; keeps usage down)
- [ ] Preferences: first-run questions, save/load, change-in-chat, per-job override
- [ ] Recovery: if the desktop app is already open, go straight to connect mode; if connect fails, tell the user to open/close the app rather than fighting the lock
- [ ] Test on Phase 0 sample end-to-end

**Exit:** a non-technical user runs a job from chat, reviews and tweaks in LightCraft; quality ≥ Phase 1 baseline; usage per photo known.

---

## Phase 3 — Packaging + handover

- [ ] One-time setup checklist/script: Claude desktop app, Claude Code login, LightCraft app + CLI (pinned version), plugin install
- [ ] Pin LightCraft version; note upgrade procedure
- [ ] One-page user guide: start a job, review in LightCraft (filter by label), give feedback, tweak, export
- [ ] Usage-limit handling documented (what happens, how to resume)

---

## Phase 4 — Learning loop hardening

- [ ] Periodic "what have we learned" pass over `log/` across jobs → proposed preset/house-style diffs
- [ ] Track per-job metrics: % approved without changes, avg user tweaks per photo, most-tweaked controls

---

## Phase 5 — Optional: simple viewer (only if needed)

Build only if LightCraft proves too complex for the user. A read-only localhost web page (static HTML + vanilla JS, tiny local server) that polls `job.json` / `log/` and shows a status grid, before/after and a plain-English "what changed" panel. Claude starts it with `open http://localhost:<port>/?job=<name>`. The job folder contract above already supports it.

---

## Open questions

- ~~Landscape originals: 4:5 portrait, 5:4 landscape, or uncropped?~~ → asked on first run, saved to preferences
- Are any references shot on something other than the M50 (e.g. a phone)?
- Bracketed exposures (HDR merge) or single frames?
- Output spec: long-edge size, format, colour space → first-run preferences. Still open: sharpening, watermark?
- Claude plan: Pro or Max? (depends on Phase 0 usage numbers)
- Does LightCraft accept externally generated masks?
- Is `calibrate` (M50 profile from embedded JPEGs) + camera base preset good enough for colour?
- Is Auto Lighting Optimizer on in the M50? (affects colour fitting)

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-10-17 | Engine: LightCraft via MCP | Open source, scriptable, agent-ready, Lightroom-like controls |
| 2026-10-17 | Driver: Claude desktop app + skill, not Agent SDK | Single local user; uses their subscription; least to build |
| 2026-10-17 | Native presets derived from human finals, not ported XMP | Import is approximate; human finals are the benchmark |
| 2026-10-17 | ~~Custom LiteCraft viewer~~ → LightCraft desktop app is the review surface | Nothing to build; user can fine-tune directly; user tweaks become learning signal. Viewer deferred to optional Phase 5 |
| 2026-10-17 | Two-stage flow: headless batch → connect-mode review | Library lock allows one program at a time; connect mode shares the app's live session |
| 2026-10-17 | 4:5 crop is an agent step, after geometry, before tone | Deliverable is mostly 4:5; tone should be judged on the delivered frame |
| 2026-10-17 | Crop ratio + export spec are user preferences, asked on first run and saved to `~/LiteCraft/preferences.json` | User's call, not ours; outside the plugin so updates don't overwrite; changeable in chat |
| 2026-10-17 | Kit: Canon M50 + Sigma 30mm F1.4 DC DN | M50 CR3/C-RAW listed as exact in LightCraft; low-distortion prime simplifies lens correction |
