# LiteCraft house style

The look we're matching: **bright, clean and natural.** Rooms feel airy and daylit; whites are clean and slightly warm; wood stays rich; blacks stay truly black; nothing looks processed.

The numbers below are **starting targets** measured with `lc.py stats` (L\* lightness 0–100; warmth = mean (R−B)/255; saturation = mean HSV saturation). They were seeded from two reference pairs and are refined during initialisation — when the user's own references disagree with this file, the references win and this file should be updated (with the user's OK).

## Scene types

Decide which one a photo is before editing; targets differ.

| Scene | What it looks like | Midtone target (`lightness_p50`) | Notes |
|---|---|---|---|
| **Room** | A space: walls, floor, furniture, windows | 72–80 | Bright and airy. White walls read white, not grey. |
| **Vignette** | Close styled detail: tabletop, shelf, bedside, with a soft background | 35–45 | Lift ~1 stop from a dark original but keep the mood; don't force it bright. |
| **Exterior / dusk** | Outside, or interior at night/dusk with lamps on | judge by eye | Keep warm lamp glow; don't neutralise it. |

## Tone

- **Exposure first** to hit the midtone target, then shape with highlights/shadows.
- **Highlights:** windows keep visible detail (frames, sky/foliage outside). Near-white pixels (`clipped_highlights_pct`) are fine on white walls and light sources, but if a **window** is pure white, pull highlights (−30 to −70) or whites before lowering exposure.
- **Shadows:** lifted so furniture, rugs and corners are readable (+15 to +40).
- **Blacks:** keep true blacks (`lightness_p5` roughly 5–16). Black furniture, leather, and dark tables must look black, not grey. If shadows lift makes blacks milky, lower blacks (−5 to −15).
- **Contrast:** gentle (−5 to +10). Clarity a touch (+5 to +10). Never crunchy, never HDR-looking.

## Colour

- **White balance:** neutral to slightly warm. After editing, warmth should be about **+0.03 to +0.05 warmer** than a neutral render of the same frame. Walls should look white or the paint's true colour — never blue, green or magenta.
- Mixed light (daylight + tungsten): balance for the dominant daylight; let lamps glow warm.
- **Vibrance** +10 to +20 for natural richness (greens, yellows, wood). Avoid saturation boosts above +5.
- Wood tones warm and rich, not orange.

## Geometry

- **Verticals must be vertical.** Run Upright (`auto`, or `vertical` for strong architecture), then check door frames, window edges and wall corners on a render. Tilted verticals are the most visible mistake in interior photos.
- Level horizon/lines in symmetrical rooms.

## Crop composition

Target ratio comes from preferences (`crop.portrait`, `crop.landscape`).

- Architecture centred when the room is symmetrical (a window, fireplace, bed or artwork on the centre line).
- **Don't amputate:** furniture, art, lamps and plants are either fully in frame or decisively cropped — never sliced at the edge by a few percent.
- Keep breathing room above the main subject; avoid large empty ceiling or floor bands.
- Vignettes: subject centred or on a third; keep the background softness.
- Heavy crops (landscape → 4:5 portrait keeps ~53% of the width): choose the strongest single subject and flag the photo for review if the room no longer reads.

## When to flag (red label) instead of forcing it

- No crop candidate keeps the key elements whole.
- A window can't hold detail without making the room look dark.
- Verticals still visibly off after Upright.
- Colour cast you can't clear without the walls going grey.
- Anything you're unsure of after 6 passes.

Flagging is not failure — the user reviews flagged photos first.
