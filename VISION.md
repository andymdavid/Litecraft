# LiteCraft — Vision

> **Naming:** **LiteCraft** is this project — the editing pipeline, packaged as a Claude Code plugin + skill. **LightCraft** is the open-source raw developer it drives ([getartcraft.com/apps/lightcraft](https://getartcraft.com/apps/lightcraft), [github.com/storytold/lightcraft](https://github.com/storytold/lightcraft)).

## The problem

Interior design photography is currently edited by hand in Adobe Lightroom. The current editor is not a Lightroom specialist and uses a small subset of its features. The work is repetitive (consistent look, white balance, exposure, straight verticals, window detail, a 4:5 crop) but each image still needs per-photo judgement, so a preset alone never finishes the job.

## The idea

An agent-driven editing pipeline that a non-technical user runs from the **Claude desktop app**:

- **Claude** (Claude Code, in the desktop app's Code tab) does the editing, guided by a **house-style skill**.
- **LightCraft runs headless** as the editing engine during the batch pass — Claude drives it over MCP: presets, per-photo corrections, and the **4:5 crop**.
- **LightCraft's desktop app is the review surface.** When the batch is done, Claude opens the same library in LightCraft and connects to the running app. The user inspects every photo, and can **fine-tune any slider directly** for subtle changes.
- **Feedback goes back to Claude in plain language** ("#12 is too warm", "#15 the window's blown") — Claude applies it live in the open app. Claude also **reads the user's own slider tweaks** and learns from them.

The user directs, reviews and nudges. Claude does the heavy lifting and explains what it did in chat.

## Principles

1. **The human editor's finals are the benchmark** — not Lightroom's full feature set. We match their taste, then improve on consistency.
2. **Part script, part agent.** Deterministic steps (import, base presets, export) are scripts. Judgement (per-image WB, exposure, verticals, windows, crop composition) is the agent, in a bounded render → inspect → adjust loop.
3. **Native presets, not ported ones.** We build our own LightCraft presets, derived from before/after pairs, layered as: camera base → lens base → look → per-image deltas.
4. **Everything explainable.** Every adjustment is logged with a reason in the job log; Claude summarises in chat.
5. **The user can always take the wheel.** Any edit is adjustable by hand in LightCraft; nothing is locked or hidden.
6. **Local and simple.** Runs on one MacBook, one user, their own Claude subscription. No servers, no API keys, no accounts, no custom app to install.
7. **Bounded autonomy.** The agent has a capped number of iterations per photo; anything that doesn't pass is flagged for the human, not forced.
8. **Ask once, remember.** User choices (crop ratio, export spec, default look) are asked on first use and saved — never re-asked every job.
9. **The system learns.** Recurring corrections — typed feedback *and* the user's own slider tweaks — are proposed back into presets and the house-style skill.

## Who it's for

A single, non-technical user on a MacBook who currently hands photos to (or is) a Lightroom editor.

## Current kit and output

- **Camera:** Canon EOS M50 (CR3 raw).
- **Lens:** Sigma 30mm F1.4 DC DN (EF-M; ≈ 48mm full-frame equivalent — low distortion).
- **Output:** mostly **4:5** crops from the full frame. Crop ratio per orientation and export spec are asked once on first use and saved as the user's preferences (changeable anytime in chat).
- **Look (from first reference pairs):** bright, clean and natural — lifted exposure, neutral-to-warm whites, warm wood, lifted shadows while keeping true blacks, moderate vibrance (greens, yellows, wood), gentle contrast with a touch of clarity.

## What success looks like

- **Quality:** blind side-by-side, the agent's output is judged on par with the current human edits for ≥ 80% of images; remaining images need only one round of feedback or a small manual nudge.
- **Time:** a typical shoot is edited end-to-end with < 15 minutes of human attention.
- **Consistency:** a shoot reads as one coherent set (WB, tone, look, crop).
- **Usability:** the user can run a job without opening a terminal.

## Out of scope (for now)

- Replacing Lightroom for general photography.
- Multi-user, cloud, or client-facing distribution (would require moving to API-key auth — see IMPLEMENTATION.md).
- Retouching beyond global/local tone, colour and crop (object removal, virtual staging, sky replacement).
- A custom viewer app — deferred; built only if LightCraft proves too complex for the user (see IMPLEMENTATION.md, Phase 5).

## Known risks

| Risk | Why it matters | Planned mitigation |
|---|---|---|
| LightCraft raw colour is estimated, not measured; no bundled M50 profile; no external `.dcp` | Colour won't match Lightroom out of the box | One camera → one camera base preset tuned against human finals; optionally contribute an M50 calibration upstream; DNG pre-conversion as a fallback |
| No lens profile database | Vignetting/distortion correction is manual | Single low-distortion prime → solve once, store in a lens base preset |
| Library lock: headless and desktop can't open the same library at once | Hand-off between batch pass and review must be clean | Explicit hand-off step in the skill; connect mode for review **(verify)** |
| LightCraft's UI is Lightroom-like | May overwhelm a non-technical user | Use flags/colour labels for status so they can filter to "needs review"; fall back to a simple viewer (Phase 5) |
| Automated 4:5 crop composition | A bad crop is very visible | Composition rules in the house style; crop reasons logged; easy manual adjust in LightCraft |
| Smart masks are heuristic | Window pulls may be weaker | Luminance-range + gradient masks; test external mask import |
| LightCraft is young (v0.6.0) | Bugs, API changes | Pin a version; keep the integration surface small |
| Subscription usage limits | Large shoots may hit Claude plan caps | Measure per-photo usage; Max plan; pause/resume on limits |
