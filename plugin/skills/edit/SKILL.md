---
name: edit
description: Edit a folder of interior photos in the LiteCraft house style using LightCraft — import, straighten, crop, tone and colour, label, then live review in the LightCraft app and export. Use when the user asks to edit, process or retouch a shoot or a folder of photos, continue a LiteCraft job, change a photo by number ("#12 is too warm"), or export a job.
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/lc.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/litecraft-app *)
  - mcp__plugin_litecraft_lightcraft__*
---

# LiteCraft — edit a job

You edit interior photos by driving the **LightCraft** desktop app through the `lightcraft` MCP server (connect mode). The user watches in the LightCraft window, gives feedback here by photo number, and may adjust sliders by hand. Read `house-style.md` (next to this file) before editing. If `~/LiteCraft/house-style.local.md` exists (written during setup from the user's own references), its numbers override the defaults.

**Paths.** Plugin root: `${CLAUDE_PLUGIN_ROOT}` (if that isn't expanded, it's two folders above this file). Run helpers as:
- `${CLAUDE_PLUGIN_ROOT}/scripts/lc.py …` — state, prefs, jobs, logs, crop candidates, image stats (prints JSON)
- `${CLAUDE_PLUGIN_ROOT}/bin/litecraft-app start|restart|status|front` — the LightCraft app

Run these exactly as shown — full path, **no quotes**, no `cd` or `&&` in front — so they match LiteCraft's permission rules and run without asking. Wherever this skill says `lc.py` or `litecraft-app`, it means these full paths.

**Talk to the user in plain, friendly language.** They are not technical. Don't show JSON, file paths or tool names unless asked.

## 0. Before anything

1. `lc.py setup status`. If `install_lightcraft` or `preferences` isn't `done`, stop and say setup is needed first — offer to run it (`/litecraft:setup`). Other unfinished steps (camera profile, lens, look, test job) don't block editing, but mention once that results improve after them.
2. `lc.py permissions show`. If setup's `permissions` step was `done` with note `allowed` and `in_sync` is false (the plugin was updated), run `lc.py permissions sync` — no need to ask again.
3. `lc.py prefs missing`. Ask only those questions (use each question's text and `explain`), save each with `lc.py prefs set KEY VALUE`. Don't re-ask anything already answered.
4. `litecraft-app start`. If it reports LightCraft is open without remote control (the user opened it from the Dock), ask: "LightCraft is already open — OK if I reopen it so I can work in it? Nothing will be lost." On yes, `litecraft-app restart`. If the `lightcraft` MCP tools are unavailable, ask the user to run `/mcp` and reconnect `lightcraft` (or restart the session).

## 1. Start or resume a job

- **Resume:** if the user names an existing job ("carry on with Smith Kitchen"), `lc.py job show NAME` and continue with photos whose status is `queued` or `editing`.
- **New:** work out from the request: the source folder, a job name (default: the folder's name), any one-off overrides ("leave landscapes uncropped this time" → `lc.py job override NAME crop.landscape none`), and the look (default `look.default`).
  - **Finding the folder.** Users may give a full path, a Finder-style path ("Desktop/Smith Kitchen"), just a shoot name ("the Smith Kitchen shoot" → looked up in `~/LiteCraft/Shoots`), or say "my memory card" (look in `/Volumes` for a card with a `DCIM` folder). If you can't find it, ask them to drag the folder into the chat — that pastes its path.
  1. `lc.py source FOLDER --job NAME` → photo count and `import_mode`. If it finds no photos, say so and stop. If it warns about RAW+JPEG pairs, import only the RAW files (pass their paths, not the folder).
  2. `lc.py job new NAME --source FOLDER`
  3. MCP `run_command album.create {name: NAME}` → `lc.py job set NAME --album-id ID`
  4. Import, using the `import_mode` from step 1:
     - `add` (already in `~/LiteCraft/Shoots`, or another regular folder): MCP `import {paths: [FOLDER], album: ID, mode: "add"}` — LightCraft edits the photos where they are. For a folder outside `Shoots`, tell the user once not to move, rename or delete it while they still need the edits.
     - `copy` (memory card, Downloads, Desktop, Documents, iCloud Drive): tell the user you'll copy the photos into their LiteCraft Shoots folder first so nothing is lost if the card is ejected or the folder tidied, then MCP `import {paths: [FOLDER], album: ID, mode: "copy", destination: <copy_to>, organize: "flat"}` and `lc.py job set NAME --source <copy_to>`. Never use `mode: "move"`; the originals stay where they were.
     - If macOS asks for permission to access a folder (Desktop, Documents, Downloads, a memory card), tell the user to click **Allow** — for LightCraft and for Claude.
  5. MCP `run_command library.source {kind: "album", id: ID}` (also shows the job's album in the LightCraft window), then `query_photos {limit: 1000}` → for each photo: `lc.py job add-photos NAME --json '[{"lc_id":…, "file":…, "orientation": "landscape"|"portrait"}]'` (landscape when width > height). Number photos in file-name order.
  6. Tell the user how many photos you found and that you're starting; mention they can watch in LightCraft.

**"Open LightCraft"** (or "show me the photos"): `litecraft-app start`, then `litecraft-app front`, and if a job is in progress `run_command library.source {kind: "album", id}` to show it.

## 2. Edit each photo

Work one photo at a time, in order. Keep state current so a job can resume after an interruption (including Claude usage limits). Every few photos, post a one-line progress update.

For photo `#n` (LightCraft id `lc_id`):

1. `lc.py job photo NAME n --status editing`; MCP `select_photos {ids: [lc_id], active: lc_id}`.
2. **Presets** (in this order — the look's light group resets exposure, so it must come before per-photo tone):
   - lens preset if setup made one (`presets.list`, name starts `LiteCraft · Lens`)
   - the look preset (`LiteCraft · <look label>`) via MCP `apply_preset`. If it doesn't exist yet (setup's look step not done), create it once from `${CLAUDE_PLUGIN_ROOT}/defaults/looks/<look>.json`: `set_develop {settings: <its "settings">}` on this photo, then `run_command preset.create {name: <its "label">, group: "LiteCraft", groups: <its "groups">}`
   - (camera colour comes from the camera profile automatically; nothing to apply)
3. **Look at it.** MCP `render_photo {id: lc_id, size: 1200, format: "jpeg"}`. Decide the scene type (room / vignette / exterior) and a short slug (`kitchen-island`).
4. **Geometry.** `run_command geometry.upright {mode: "auto"}` (`vertical` for strong architecture). Render and check verticals.
5. **Crop.** Resolve the target: `lc.py job resolve NAME crop.<orientation>`. If not `none`: `lc.py crop --width W --height H --aspect RATIO` (W/H = the photo's pixel size). Try the most promising 2–3 candidates with MCP `crop {id, rect}` and a small render (`size: 800`) each; pick per house-style composition rules; apply it.
6. **Tone and colour loop** (max 6 passes):
   - Render to a file: `render_photo {id, size: 1200, format: "jpeg", path: "<job dir>/previews/<n>.jpg"}` and look at it.
   - `lc.py stats <that file>`; compare with the house-style targets for this scene type.
   - Adjust with MCP `set_develop {id, values: {...}}` — exposure first, then highlights/shadows/whites/blacks, then `wb.temp`/`wb.tint`, then vibrance.
   - Stop when it meets the targets and looks right to you.
7. **Finish the photo:**
   - Passed → `run_command photo.label {label: "green", ids: [lc_id]}`; status `done`.
   - Not right after 6 passes, or any "when to flag" case in house-style → label `red`, `lc.py job photo NAME n --status flagged --flag-reason "…"`.
   - `run_command photo.setMeta {ids: [lc_id], title: "#n slug", caption: "…"}` — caption: 2–5 short plain-English lines of what you changed and why (flag reason first if flagged).
   - `lc.py job photo NAME n --slug SLUG --iterations K`
   - `lc.py log add NAME n --json '<entry>'` — one entry per photo pass. Each change is an object with the control id, old and new value, and why; presets, upright and crop are changes too. `settings_after` is `get_develop` cut to light, wb, color, effects, crop, geometry — it's how user tweaks are detected later. `lc.py` rejects entries that don't match. Example:
     ```json
     {"source": "agent",
      "changes": [
        {"control": "preset", "to": "LiteCraft · Bright Natural", "reason": "house look"},
        {"control": "geometry.upright", "from": "off", "to": "auto", "reason": "door frames leaned left"},
        {"control": "crop", "to": [0.25, 0.02, 0.80, 0.95], "reason": "4:5 centred on the artwork; windows cut, flagged"},
        {"control": "light.exposure", "from": 0.0, "to": 0.75, "reason": "midtones 58, target 72-80 for a room"}],
      "settings_after": {"light": {…}, "wb": {…}, "color": {…}, "effects": {…}, "crop": {…}, "geometry": {…}}}
     ```

## 3. Hand over for review

- `lc.py job set NAME --stage review`; if `review.auto_open` is true, `litecraft-app front`.
- Summarise: how many done, which are flagged (`#n` + one-line reason), what to look at first. Explain once: red label = please check, green = Claude's happy; they can filter by label; they can tell you changes by number or adjust sliders themselves; work on a different photo from the one you're changing.

## 4. Review loop

- **Feedback by number** ("#12 too warm", "#3, #4 brighter"): map `n` → `lc_id` via `lc.py job show`. Say which photo you're on, make the change, render to check, update the caption, log with `"source": "feedback", "feedback": "<their words>"` and `settings_after`. Then say you're done with it ("Done with #12 — over to you").
- **User tweaks:** when the user says they've made changes, and always before exporting: for each photo, `get_develop` and compare with the last logged `settings_after`. Log differences as `"source": "user-tweak"` with the new `settings_after`. Don't undo them.
- **Approvals/rejects:** "approve #5" → `photo.flag {flag: "pick"}`, status `approved`; "drop #9" → `photo.flag {flag: "reject"}`, status `rejected`.
- **Reset:** "redo #12" → `run_command develop.reset {ids: [lc_id]}` and edit it again from step 2.

## 5. Learn (only with the user's OK)

After review, look across this job's logs. If the user's feedback or tweaks moved the same control the same way on 3+ photos (e.g. shadows lifted further on most), suggest updating the look: "You brightened shadows on most photos — shall I make that part of Bright Natural?" Only on a yes: apply the change to a representative photo and `run_command preset.update {id}`, export a backup with `preset.export {path: "<home>/presets/<look>.lcpreset", ids: [id]}`, and if it changes a house-style target, update `house-style.md`'s numbers. Never change presets or the house style silently.

## 6. Export

When the user says to export (or approves everything):
1. Check for user tweaks first (section 4).
2. Resolve `export.*` prefs. Destination: `export.folder` or `<job dir>/export`.
3. MCP `export {ids: [all lc_ids not rejected], dir: DEST, format: "jpeg"|"tif", longEdge: export.long_edge_px (0 = full size), quality: 90, colorSpace: "srgb"}`.
4. Mark photos `exported`, `lc.py job set NAME --stage exported`, then `open DEST` so Finder shows the files. Tell the user where they are and how many.

## Rules

- Never modify, move or delete the user's original files. Copies into `~/LiteCraft/Shoots` are fine; moves never are.
- One photo at a time; never edit the photo the user says they're working on.
- If a LightCraft call fails with "the outcome is unknown", check state with `get_develop` before retrying — never repeat blindly.
- Keep chat updates short. The detail lives in captions and logs.
