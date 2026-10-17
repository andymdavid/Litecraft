---
name: setup
description: First-time LiteCraft setup on the user's Mac — install LightCraft, ask the user's preferences, build their camera colour profile, lens correction and house look from their own photos and before/after references, then run a test job. Resumable. Use on a new install, when the user says "set up LiteCraft", when the edit skill reports setup is incomplete, or to redo one setup step (e.g. "redo the look from my new references").
---

# LiteCraft — initialisation

This is the one-time setup run on the **user's own Mac**. Everything that depends on their photos happens here, using files that stay on their machine. It is **resumable**: every step is recorded, and you always continue from the first unfinished one.

**Paths.** Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if that isn't expanded, it's two folders above this file). Helpers:
- `"${CLAUDE_PLUGIN_ROOT}/scripts/lc.py"` — state, prefs, stats (prints JSON)
- `"${CLAUDE_PLUGIN_ROOT}/bin/litecraft-app" start|status|front`

User data lives in `~/LiteCraft` (`lc.py paths` shows every location).

**Tone.** The user isn't technical. Explain each step in a sentence before doing it, ask for one thing at a time, and say what you need in plain words ("a folder of photos from past shoots, straight off the camera"). Don't show JSON or tool names.

## Start

1. `lc.py setup status` → `next` is the step to do. If everything is done, say so and offer to redo a step.
2. On a first run, briefly explain what setup does — about an hour in total (up to two with many reference pairs), of which ~20 minutes needs them; the look step is the longest (a few minutes per pair) — and what you'll ask for:
   - a folder of past shoot photos straight off the camera (`.CR3`), for the camera colour profile
   - optionally a few photos taken wide open of a plain wall, for the lens
   - **before/after pairs**: the original `.CR3` and the finished edit exported from Lightroom (full-size JPEG) — recommend starting with 5–10; more can be added later by redoing the look step
   - 3–5 new photos for a test run
3. Do the steps below in order. After each: `lc.py setup done STEP --note "…"` (or `setup skip STEP --note "why"` for optional steps the user declines). To redo a step: `lc.py setup reset STEP`.

## 1. `preflight`

- macOS on Apple Silicon (`uname -m` → `arm64`; Intel works but is slower). Note RAM (`sysctl -n hw.memsize`); 16 GB+ is comfortable.
- `python3 --version` works. If macOS offers to install developer tools, tell the user to accept, then continue.
- Free space in home: at least 2 GB plus room for exports.

## 2. `install_lightcraft`

Pinned version: **0.8.0**. Only upgrade when the LiteCraft repo says a newer version is tested.

If `lc.py env check` already reports `ok` with `lightcraft-cli 0.8.0`, mark done and move on.

Otherwise (ask before downloading ~210 MB):

```bash
VER=0.8.0
DL=~/LiteCraft/downloads; mkdir -p "$DL" ~/LiteCraft/bin; cd "$DL"
BASE=https://github.com/storytold/lightcraft/releases/download/v$VER
curl -fsSLO "$BASE/lightcraft-$VER-macos-universal.dmg"
curl -fsSLO "$BASE/lightcraft-cli-$VER-macos-universal.zip"
curl -fsSLO "$BASE/SHA256SUMS.txt"
shasum -a 256 -c SHA256SUMS.txt --ignore-missing      # both must say OK — stop if not
```

- **App:** if `/Applications/LightCraft.app` exists and LightCraft is running, ask the user to quit it first. Then:
  `M=$(hdiutil attach -nobrowse -readonly "lightcraft-$VER-macos-universal.dmg" | tail -1 | awk -F'\t' '{print $NF}')` → `ditto "$M/LightCraft.app" /Applications/LightCraft.app` → `hdiutil detach "$M"`.
- **CLI:** `unzip -oq "lightcraft-cli-$VER-macos-universal.zip" -d "$DL"` → `cp "$DL/lightcraft-cli-$VER-macos-universal/lightcraft-cli" ~/LiteCraft/bin/` → `chmod +x ~/LiteCraft/bin/lightcraft-cli`.
- `lc.py env init --cli ~/LiteCraft/bin/lightcraft-cli --app /Applications/LightCraft.app`
- `lc.py env check` → must be `ok` with version `lightcraft-cli 0.8.0`.
- `litecraft-app start` → the LightCraft window opens on an empty LiteCraft library.
- **Connect Claude to it:** the `lightcraft` MCP server only finds LightCraft once installed. Ask the user to type `/mcp` and reconnect **lightcraft** (or restart this Claude session — setup will resume where it left off). Confirm with the MCP `doc_inspect` tool.
- Remove `~/LiteCraft/downloads` once everything works.

## 3. `preferences`

`lc.py prefs missing` → ask each question in turn using its `question` and `explain` text, with the default as the recommendation (except `crop.landscape`, which has none — explain the trade-off and let them choose). Save each with `lc.py prefs set KEY VALUE`. Read the result back in one friendly sentence.

## 4. `camera_profile`

Builds a colour profile for their camera from past photos, so colours start close to the camera's own.

1. **Auto Lighting Optimizer.** Ask whether it's on in their Canon M50 (Menu → shooting tab → *Auto Lighting Optimizer*). Recommend **Off** for future shoots: LightCraft doesn't model it, and it brightens the camera's preview in ways that skew colour fitting. Record the answer in the step note.
2. Ask for one or more folders of past photos **straight off the camera** (`.CR3`, any subjects, ideally 30–300 photos, at least 5). Read-only — nothing is moved or changed.
3. Run (can take a few minutes):
   ```bash
   source ~/LiteCraft/litecraft.env
   "$LIGHTCRAFT_CLI" calibrate --max 300 --out "$HOME/Library/Application Support/LightCraft/camera-profiles" FOLDER [FOLDER…]
   ```
4. Check a profile file appeared for their camera model (e.g. `Canon EOS M50.json`) and report how many photos it used. If it says too few usable photos, ask for more.
5. Restart LightCraft so it loads the profile (**(verify)** whether this is needed): ask the user to quit LightCraft (⌘Q), then `litecraft-app start`.

If they shoot more than one camera, repeat for each.

## 5. `lens` (optional)

Corrects the slight darkening in the corners at wide apertures (Sigma 30mm F1.4 on the M50).

1. Ask for 2–3 `.CR3`s shot at f/1.4–f/2 of something plain and evenly lit (a white wall). If they have none, `setup skip lens --note "no wide-open frames"` and move on.
2. `album.create {name: "LiteCraft Setup"}`; `import {paths, album, mode: "add"}`.
3. On one: render (`render_photo`, size 1200) and adjust `optics.vignetting` (positive brightens corners) until the corners match the centre. Check on the others.
4. `preset.create {name: "LiteCraft · Lens · Sigma 30mm F1.4", group: "LiteCraft", groups: ["optics"]}` from that photo.
5. Back up: `preset.export {path: "~/LiteCraft/presets/lens-sigma-30.lcpreset", ids: [id]}` (expand `~`).

## 6. `look`

The heart of setup: learn the user's house look from their own before/after pairs.

1. **Collect pairs.** Ask for the folder(s). For each pair you need the **original** `.CR3` and the **final** JPEG exported from Lightroom. Match them by file name (Lightroom usually keeps the base name, e.g. `IMG_0412.CR3` ↔ `IMG_0412.jpg`); if names don't match, ask. Copy each pair into `~/LiteCraft/references/<base name>/` (`original.CR3`, `final.jpg`). Aim for 5–10 pairs to start, covering their usual scenes (rooms and vignettes, bright and dim); each takes a few minutes to match. Tell the user roughly how long it will take before starting, and give a short progress line after each pair.
2. **Seed preset.** `album.create {name: "LiteCraft References"}`, import the originals into it. Select the first; `set_develop {settings: <the "settings" object from ${CLAUDE_PLUGIN_ROOT}/defaults/looks/bright-natural.json>}`; `preset.create {name: "LiteCraft · Bright Natural", group: "LiteCraft", groups: ["light", "color", "effects"]}`.
3. **Match each pair.** For each original:
   - `apply_preset` the look; match the final's **framing** first (`crop`; finals are usually 4:5) and straighten if the final is straightened.
   - Loop up to 10 passes: `render_photo {size: 1200, format: "jpeg", path: ".../references/<name>/render.jpg"}` → `lc.py compare render.jpg final.jpg` → adjust with `set_develop`: lightness percentiles → exposure/whites/blacks/highlights/shadows; warmth → `wb.temp`; saturation → vibrance. Also look at both images side by side — the numbers guide, your eye decides.
   - Save the matched settings: `get_develop` (light, wb, color, effects) into `~/LiteCraft/references/<name>/match.json`, plus `lc.py stats final.jpg` into `final-stats.json`, and note the scene type (room / vignette / exterior).
4. **Derive the look.** Across all pairs, take the **median** of each light (except exposure), color and effects control. Apply those to one reference photo and `preset.update {id}` the Bright Natural preset. Per-pair exposure and white balance stay per-photo, not in the preset.
5. **Update house-style targets.** From `final-stats.json` per scene type, update the midtone (`lightness_p50`) ranges, blacks (`lightness_p5`) and warmth in `${CLAUDE_PLUGIN_ROOT}/skills/edit/house-style.md` — **show the user the old → new numbers in plain words and ask before writing.** Note: plugin updates can overwrite this file, so also save the numbers to `~/LiteCraft/house-style.local.md` and mention it in the step note.
6. **Show the user.** Pick 2–3 pairs, apply the final preset plus per-photo exposure/WB, and show them side by side with the finals. Ask if it's their look. If not, ask what's off, adjust, repeat.
7. Back up: `preset.export {path: "~/LiteCraft/presets/bright-natural.lcpreset", ids: [id]}`.

If they have distinct styles (e.g. a moody evening look), repeat with those pairs as a second look (`LiteCraft · <Name>`), add it as an option for `look.default`.

## 7. `test_job`

1. Ask for a small folder of 3–5 photos **not** used as references.
2. Run the edit skill on it as a normal job (name it `Test`).
3. Walk the user through reviewing in LightCraft: labels, captions, giving feedback by number, adjusting a slider themselves, exporting.
4. Ask how it felt and what they'd change. Feed real issues back into the presets or house style (with their OK).
5. Note in the step: time taken, passes per photo, anything flagged.

## 8. `complete`

Summarise in plain words: what's installed, their preferences, camera profile, lens preset, the look and where backups are (`~/LiteCraft/presets`). Tell them how to start a job ("Edit the photos in Desktop/Smith Kitchen") and that they can change any preference by just saying so. `lc.py setup done complete`.

## Rules

- Never modify, move or delete the user's original photos — import with `mode: "add"`; copy references, don't move them.
- Ask before downloads, installs into `/Applications`, and any change to presets or the house style.
- If something fails, explain it simply, record it with `setup` notes, and offer to retry or skip (optional steps only).
