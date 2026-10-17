# LiteCraft — Implementation Plan

See [VISION.md](VISION.md) for the why. This document is the how, in phases we work against.

> Status markers: `[ ]` todo · `[x]` done · `[~]` in progress.
> Facts about LightCraft and Claude Code come from their docs at the time of writing and are marked **(verify)** until tested here.

**Two places work happens:**
1. **This repo (dev machine)** — build the plugin, skills and scripts. No client photos here.
2. **The user's Mac (initialisation run)** — a Claude Code instance installs the plugin and runs the **setup skill**, which does everything that needs the user's own files: installing LightCraft, preferences, the M50 colour profile, the lens correction, deriving the look from their before/after pairs, and a test job. See [Initialisation](#initialisation-users-mac).

---

## Architecture

```
Claude desktop app (Code tab)  ← user chats here: setup, start jobs, give feedback
  │
  └─ LiteCraft plugin  (plugin/)
       ├─ skills/setup   first-install initialisation (resumable)
       ├─ skills/edit    run a job: import → edit → crop → label → review → export
       ├─ .mcp.json      → bin/lightcraft-mcp → lightcraft-cli mcp --connect 127.0.0.1:<port>
       ├─ bin/litecraft-app   starts LightCraft with --control <port> if not running
       └─ scripts/lc.py  preferences, setup state, jobs, logs, crop candidates, image stats

LightCraft desktop app  (always running during a job)
  lightcraft --library ~/LiteCraft/Library --control 7980
  ← Claude drives it over MCP (connect mode); the user watches and tweaks in the same window
```

**Connect mode only.** Claude Code starts a plugin's MCP servers when the session starts and keeps them running. A headless server (`mcp --library`) would hold the library lock for the whole session, so the desktop app could never open it mid-session. Instead, the skill starts the desktop app with `--control` at the beginning of a job, and the MCP server always connects to it. In connect mode the server starts even when the app isn't running yet and connects on first call, so session start never fails. No lock conflicts; the user can watch edits happen live.

**One library, one album per job.** A single persistent library at `~/LiteCraft/Library`. Each job is an album, so the user browses jobs in LightCraft's sidebar. Presets live with the library.

**Turn-taking:** Claude and the user don't edit the same photo simultaneously. The skill announces hand-backs ("done with #12 — over to you").

**Auth:** user's own Claude Pro/Max login in the desktop app. Local, single-user. If this ever ships to other users, switch to Agent SDK + API key.

---

## Repo layout

```
LiteCraft/
├── README.md                   # user guide
├── CLAUDE.md                   # orientation for Claude Code instances (dev + initialisation)
├── VISION.md
├── IMPLEMENTATION.md
├── .claude-plugin/
│   └── marketplace.json        # the repo is a plugin marketplace
├── plugin/                     # the LiteCraft plugin
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json
│   ├── bin/
│   │   ├── lightcraft-mcp      # MCP launcher (reads ~/LiteCraft/litecraft.env)
│   │   └── litecraft-app       # start / status of the LightCraft app with control port
│   ├── scripts/lc.py           # stdlib-only helper CLI
│   ├── defaults/
│   │   ├── preferences.json    # defaults + first-run questions
│   │   └── looks/bright-natural.json   # seed look; refined during initialisation
│   └── skills/
│       ├── setup/SKILL.md      # initialisation
│       └── edit/
│           ├── SKILL.md        # job procedure
│           └── house-style.md  # measurable style + crop composition rules
├── dev/                        # dev-only tools (mcp_probe.py)
├── Samples/                    # gitignored: reference images
└── vendor/                     # gitignored: LightCraft built from source (dev only)
```

---

## User data (on the user's Mac)

Everything the user owns lives outside the plugin, so plugin updates never touch it. Root: `~/LiteCraft` (override with `LITECRAFT_HOME`).

```
~/LiteCraft/
├── litecraft.env          # paths written by setup: LIGHTCRAFT_CLI, LIGHTCRAFT_APP, LITECRAFT_PORT, LITECRAFT_LIBRARY
├── setup.json             # which initialisation steps are done (resumable)
├── preferences.json       # the user's answers
├── Library/               # the LightCraft library (one for all jobs)
├── presets/               # exported .lcpreset backups of camera/lens/look presets
├── references/            # the user's before/after pairs used to derive the look
└── Jobs/<job-name>/
    ├── job.json           # photo list + status
    ├── log/<n>.json       # every change + reason (audit + learning)
    └── export/            # finished photos
```

`litecraft.env` is plain `KEY=value` so both the shell launchers and `lc.py` can read it.

---

## Preferences

Asked during initialisation (and once, later, for any key added in a newer version). Each has a recommended default except the landscape crop.

| Key | Question | Options | Default |
|---|---|---|---|
| `crop.portrait` | Portrait shots — crop to? | `4:5` · `none` | `4:5` |
| `crop.landscape` | Landscape shots — crop to? | `4:5` (portrait) · `5:4` · `none` | ask |
| `look.default` | Default look | presets made during setup | `bright-natural` |
| `export.long_edge_px` | Export size (long edge) | number · `0` = full size | `0` |
| `export.format` | Export format | `jpeg` · `tiff` | `jpeg` (quality 90, sRGB) |
| `export.folder` | Where exports go | `null` = job `export/` · a path | `null` |
| `review.auto_open` | Bring LightCraft to the front when the batch finishes? | `true` · `false` | `true` |

Rules:
- **Change anytime in chat:** "from now on keep landscape shots uncropped" → `lc.py prefs set crop.landscape none`.
- **Per-job override** without changing defaults: stored in `job.json` `overrides`.
- **Resolution order:** job override → `preferences.json` → `plugin/defaults/preferences.json`.

---

## Jobs

`job.json`
```json
{
  "schema": 1,
  "name": "smith-kitchen",
  "source": "/Users/.../Smith Kitchen",
  "album_id": 4,
  "created": "2026-10-17T17:30:00Z",
  "stage": "editing | review | exported",
  "overrides": { "crop.landscape": "none" },
  "photos": [
    {
      "n": 12,
      "lc_id": 1342,
      "file": "IMG_0412.CR3",
      "slug": "kitchen-island",
      "orientation": "landscape",
      "status": "queued | editing | done | flagged | approved | rejected | exported",
      "iterations": 3,
      "flag_reason": null,
      "updated": "2026-10-17T17:42:10Z"
    }
  ]
}
```

`n` is the job-local photo number the user uses in chat (`#12`); `lc_id` is LightCraft's photo id.

`log/<n>.json` — one entry per pass:
```json
{
  "schema": 1,
  "n": 12,
  "entries": [
    {
      "at": "2026-10-17T17:40:02Z",
      "source": "preset | agent | feedback | user-tweak",
      "changes": [
        { "control": "light.exposure", "from": 0.0, "to": 0.4,
          "reason": "Room underexposed vs. reference; midtones at 38%, target 50%" }
      ],
      "feedback": null
    }
  ]
}
```

Writes are atomic (temp file + rename) via `lc.py`.

### Status inside LightCraft

Verified in connect mode against LightCraft 0.8.0.

| Status | LightCraft marker | Command |
|---|---|---|
| done (agent passed its checks) | green colour label | `photo.label {label: green, ids}` |
| flagged (needs human eyes) | red colour label | `photo.label {label: red, ids}` |
| approved (user OK'd) | pick flag | `photo.flag {flag: pick, ids}` |
| rejected (don't export) | reject flag | `photo.flag {flag: reject, ids}` |

Titles carry the photo number and slug (`#12 kitchen-island`); the caption carries Claude's plain-English summary of what changed and why — both via `photo.setMeta {ids, title, caption}`.

---

## Edit order (per photo)

Geometry before crop, crop before tone — tone is judged on what will actually be delivered.

1. Presets: camera base (if made) → lens base → look
2. Geometry: `geometry.upright {mode: auto}` (or `vertical`) → check verticals on a render
3. Crop to the target ratio (see below)
4. Tone + colour loop on the cropped frame: render → compare (visually and with `lc.py stats`) → adjust → log (cap: 6 passes)
5. Label, title, caption → log

## Crop step

M50 frames are 3:2. Target ratio per orientation comes from preferences.

| Source | Target | Effect |
|---|---|---|
| portrait 3:2 | 4:5 | trims ~17% of height — light |
| landscape 3:2 | 4:5 (portrait) | keeps ~53% of width — heavy; flag more readily |
| landscape 3:2 | 5:4 | trims ~17% of width — light |
| any | none | straighten only |

`lc.py crop --width W --height H --aspect 4:5` returns candidate normalised rects (centred, left/right thirds, top/bottom-weighted). Claude renders the strongest candidates, picks using the composition rules in `house-style.md`, applies with the MCP `crop` tool, and logs why. Flag when no candidate keeps the key elements whole.

---

## Initialisation (user's Mac)

Run by Claude Code on the user's machine via the **setup skill** (`/litecraft:setup`), after the plugin is installed. Resumable: each step is recorded in `~/LiteCraft/setup.json` and skipped once done. **This is where all tuning against the user's own photos happens — not in this repo.**

| # | Step | What happens | Needs from the user |
|---|---|---|---|
| 1 | `preflight` | Check macOS, Apple Silicon, `python3` | — |
| 2 | `install_lightcraft` | Download pinned release (DMG + CLI zip, verify `SHA256SUMS.txt`), install app to `/Applications`, CLI to `~/LiteCraft/bin`; write `litecraft.env`; start the app once to create the library; confirm MCP connect | approve downloads |
| 3 | `preferences` | Ask the preference questions; save | answers |
| 4 | `camera_profile` | Ask whether Auto Lighting Optimizer is off (recommend off). Run `lightcraft-cli calibrate --max 300 --out ~/Library/Application\ Support/LightCraft/camera-profiles <folders>` on past M50 CR3s | a folder of ≥ 5 (ideally 30–300) M50 CR3s |
| 5 | `lens` | Measure vignetting on a few wide-open frames of plain walls; save a lens preset (optics group) | a few f/1.4–f/2 CR3s (optional) |
| 6 | `look` | Copy before/after pairs into `~/LiteCraft/references/`; for each, match the final by driving LightCraft; derive a common look from the matched settings (start from `defaults/looks/bright-natural.json`); save as the `bright-natural` preset; export `.lcpreset` backup | 5–20 pairs: original CR3 + their edited final |
| 7 | `test_job` | Run the edit skill on 3–5 photos end-to-end; user reviews in LightCraft | a small test folder |
| 8 | `complete` | Summarise what was set up; mark setup complete | — |

Notes for the step 6 matching:
- Compare render vs. final at the same crop and size, side by side, and with `lc.py stats` (mean/percentile luminance, warmth, saturation).
- Match tone and colour only; crop and geometry are matched separately.
- Use the median across pairs for the look; per-pair outliers stay as per-image deltas, not the preset.

---

## Phase 0 — Feasibility (dev machine) — done

Verified against LightCraft **0.8.0** (commit `f34c7a8`) with `dev/mcp_probe.py`:

- [x] Build app + CLI from source (~3 min on M4 / 16 GB). Release assets for installs: `lightcraft-0.8.0-macos-universal.dmg`, `lightcraft-cli-0.8.0-macos-universal.zip`, `SHA256SUMS.txt`
- [x] Headless MCP: import, `set_develop`, `crop`, `get_develop`
- [x] `render_photo` returns image content Claude can see
- [x] Edits persist in the library; desktop app opened with `--control` shows them
- [x] Connect mode: edit live, `screenshot`, read the user's own slider changes via `get_develop`
- [x] Library lock: headless on an open library fails with a clear message
- [x] Status markers: `photo.label`, `photo.flag`, `photo.setMeta` (title, caption, keywords)

Moved to initialisation (needs the user's files): CR3 decode on real files, M50 profile, lens vignetting, colour vs. finals, look matching, quality and usage measurement.

Still to check on the dev machine:
- [x] `crop` rect is honoured by export (rects must be computed from each photo's real pixel size)
- [ ] How the caption renders in the app's info panel
- [x] `geometry.upright {mode: auto}` via `run_command` in connect mode
- [x] Presets: `preset.create` (groups `light`, `color`, `effects`, …), `apply_preset`, `preset.export`/`import`; presets are stored in the library (`presets.json`)
- [x] Albums: `import {album}` adds to an album; `library.source {kind: album, id}` scopes `query_photos` and the app view
- [x] New libraries need `--no-demo` or LightCraft seeds 24 demo photos

---

## Phase 1 — Plugin build (dev machine)

**Goal:** a plugin another Claude Code instance can install and run setup from.

- [x] `CLAUDE.md` orientation
- [x] Marketplace + plugin manifests; `claude plugin validate` passes
- [x] `bin/lightcraft-mcp` (connect + `--compact`: 28 tools / 24 KB vs 595 / 291 KB), `bin/litecraft-app`, `.mcp.json`
- [x] `scripts/lc.py`: paths, env, prefs, setup state, jobs, logs (validated), crop candidates, image stats — runs on macOS system Python 3.9
- [x] `defaults/preferences.json`, `defaults/looks/bright-natural.json`
- [x] `skills/setup/SKILL.md` (release download + checksums verified in scratch; not yet run end to end)
- [x] `skills/edit/SKILL.md` + `house-style.md`
- [x] Dry run: headless `claude -p --plugin-dir ./plugin` ran `/litecraft:edit` on 2 test images end to end — 71 turns, ~3 min, ~$1.5 usage-equivalent (~$0.75 / photo). Correct 4:5 crop, upright, labels, captions, export; flagged the heavy landscape crop. Found and fixed: free-text change logs (now validated). Noted: it cooled a warm vignette where the editor's final went warmer — expected to be corrected by the look step in setup
- [x] README updated for the real install flow

**Exit:** `claude plugin validate` passes; a scratch-home edit job works end to end here. ✅ Remaining before handover: run the setup skill's install step on a clean Mac (or user account), and install the plugin from the GitHub marketplace rather than `--plugin-dir`.

---

## Phase 2 — Initialisation run (user's Mac)

- [ ] Install Claude desktop app, sign in; open the Code tab
- [ ] Add the marketplace and install the plugin
- [ ] Run `/litecraft:setup` through to `complete`
- [ ] Record results in this repo (no photos): calibration stats, matched look settings, time and usage per photo

---

## Phase 3 — Learning loop hardening

- [ ] Periodic "what have we learned" pass over job logs → proposed preset / house-style changes (user approves)
- [ ] Per-job metrics: % approved without changes, user tweaks per photo, most-tweaked controls

---

## Phase 4 — Optional: simple viewer (only if needed)

Only if LightCraft proves too complex for the user: a read-only localhost web page that polls `job.json` / `log/` and shows a status grid, before/after and a "what changed" panel.

---

## Open questions

- Are any references shot on something other than the M50 (e.g. a phone)?
- Bracketed exposures (HDR merge) or single frames?
- Sharpening and watermark on export?
- Claude plan: Pro or Max? (measure during initialisation)
- Does LightCraft accept externally generated masks?
- Is the `calibrate` M50 profile + look preset close enough to the editor's colour? (answered during initialisation)

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-10-17 | Engine: LightCraft via MCP | Open source, scriptable, agent-ready, Lightroom-like controls |
| 2026-10-17 | Driver: Claude desktop app + skill, not Agent SDK | Single local user; uses their subscription; least to build |
| 2026-10-17 | Native presets derived from human finals, not ported XMP | Import is approximate; human finals are the benchmark |
| 2026-10-17 | ~~Custom LiteCraft viewer~~ → LightCraft desktop app is the review surface | Nothing to build; user can fine-tune directly; tweaks become learning signal |
| 2026-10-17 | ~~Headless batch → connect-mode review~~ → **connect mode only**, app running for the whole job | A plugin MCP server lives for the whole session; a headless one would hold the library lock and block the app |
| 2026-10-17 | One library at `~/LiteCraft/Library`, one album per job | Fixed MCP config; jobs browsable in LightCraft |
| 2026-10-17 | Crop after geometry, before tone | Tone judged on the delivered frame |
| 2026-10-17 | Crop ratio + export spec are user preferences | User's call; stored outside the plugin; changeable in chat |
| 2026-10-17 | All tuning against the user's photos happens in an initialisation run on their Mac | Their files stay local; one setup skill makes it repeatable and obvious |
| 2026-10-17 | Helper scripts are Python stdlib only | No pip installs on the user's Mac |
| 2026-10-17 | Kit: Canon M50 + Sigma 30mm F1.4 DC DN | M50 CR3/C-RAW listed as exact in LightCraft; low-distortion prime |
