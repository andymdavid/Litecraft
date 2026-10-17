# LiteCraft

**Edit interior photos by chatting with Claude.**

You point Claude at a folder of photos from a shoot. Claude edits them in your house style — brightness, white balance, straight lines, window detail and the 4:5 crop — then opens them in **LightCraft** so you can check every photo and fine-tune anything by hand. When you're happy, Claude exports the finished images.

You never have to touch a slider unless you want to.

> **Status: in development.** This guide describes how LiteCraft will work. Steps marked 🚧 aren't built yet. See [IMPLEMENTATION.md](IMPLEMENTATION.md) for progress.

---

## What you need

- A **Mac** (Apple Silicon recommended, 16 GB memory or more for big shoots)
- The **Claude desktop app**, signed in with a **Claude Pro or Max** plan (Max recommended for large shoots)
- **LightCraft** — a free photo editor, similar to Lightroom
- The **LiteCraft plugin** for Claude

Currently tuned for a **Canon EOS M50** with a **Sigma 30mm F1.4** lens. Other cameras will work, but colours may need a little more adjusting until a preset is made for them.

---

## One-time setup 🚧

You only do this once. If someone has set it up for you, skip to [Your first job](#your-first-job).

1. **Install the Claude desktop app** and sign in.
2. **Install LightCraft** — the setup steps will install the right version for you.
3. **Install the LiteCraft plugin** in Claude.
4. Open the **Code** tab in the Claude app. LiteCraft runs there, because it needs to work with files on your Mac.

---

## Your first job

### 1. Put your photos in a folder

Copy the photos from the shoot (straight from the camera, the `.CR3` files) into a folder — for example `Desktop/Smith Kitchen`.

### 2. Ask Claude to edit them

In the Claude app's **Code** tab, type something like:

> Edit the photos in Desktop/Smith Kitchen

### 3. Answer a few questions (first time only)

The first time you use LiteCraft, Claude asks a few quick questions so it knows how you like things. Each has a sensible default — you can just say *"defaults are fine"*.

| Claude will ask | What it means |
|---|---|
| **Portrait photos — crop to 4:5?** | Tall photos get a light trim to the 4:5 shape, or stay as shot. |
| **Landscape photos — how should they be cropped?** | Wide photos can become a **4:5 tall** crop (cuts a lot of the sides), a **5:4 wide** crop (light trim), or stay **uncropped**. |
| **Which look?** | The house style to use, e.g. *Bright Natural*. |
| **Export size and format** | Full size or smaller; JPEG is usual. |
| **Where should finished photos go?** | Inside the job folder, or somewhere you choose. |
| **Open LightCraft automatically when editing is done?** | Usually yes. |

Claude saves your answers, so it won't ask again.

### 4. Let Claude work

Claude goes through each photo — applying the house style, straightening lines, cropping, and checking its own work. When it's done, it tells you in the chat:

- how many photos are **done**
- which ones are **flagged** for you to look at, and why

### 5. Check the photos in LightCraft

Claude opens **LightCraft** with your photos. Each photo is marked so you can see where things stand:

| Mark in LightCraft | Meaning |
|---|---|
| 🟢 Green label | Claude is happy with it |
| 🔴 Red label | Flagged — please take a look |
| ⭐ Pick flag | You've approved it |
| ✖ Reject flag | Don't export this one |

**Tip:** filter by the red label to see only the photos that need you.

Each photo has a number (like **#12**) so you can talk about it with Claude.

### 6. Give feedback — two ways

**Tell Claude** in the chat, in your own words:

> #12 is a bit too warm
> #15 — the window is too bright
> #8 crop is too tight on the left
> #3, #4 and #9 could all be a touch brighter

Claude makes the change and you'll see it update in LightCraft.

**Or adjust it yourself** in LightCraft — drag any slider, move the crop, whatever looks right to you. Claude notices what you changed and learns from it.

> ⚠️ Work on a different photo from the one Claude is changing. Claude will tell you when it's finished with a photo ("Done with #12 — over to you").

### 7. Export

When you're happy, tell Claude:

> Export them

Finished photos are saved to the export folder (by default, `export` inside the job folder). Photos marked *Reject* are skipped.

---

## Changing your preferences

Just tell Claude. For example:

> From now on, keep landscape photos uncropped
> Change the default export size to 2048 pixels
> What are my current settings?

**For one job only**, say so:

> Edit Desktop/Beach House, but leave the landscape photos uncropped this time

That job uses the different setting; your normal defaults stay the same.

Your preferences are stored in `~/LiteCraft/preferences.json`.

---

## How LiteCraft gets better over time

Every change — whether you asked for it or did it yourself — is recorded with a reason. Every so often, Claude will suggest updating the house style, for example:

> You've brightened shadows on most photos in the last three jobs. Shall I make that part of the Bright Natural look?

Nothing changes unless you say yes.

---

## Where things are

Each job gets its own folder:

```
~/LiteCraft Jobs/Smith Kitchen/
├── library/   LightCraft's copy of the edits (your original photos are never changed)
├── log/       what was changed on each photo, and why
└── export/    your finished photos
```

**Your original photos are never modified.** All editing is non-destructive.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| Claude says LightCraft is already open | Close LightCraft and ask Claude to carry on — or just say *"connect to LightCraft"* if you want to keep it open. |
| A photo looks wrong after Claude's edit | Tell Claude what's wrong in plain words, or adjust it yourself in LightCraft. |
| Claude stops partway through a big shoot | You may have hit your Claude plan's usage limit. Wait a while, then say *"carry on with the Smith Kitchen job"* — it picks up where it left off. |
| Colours look a bit off for a different camera | Expected — presets are tuned for the Canon M50. Tell Claude what looks wrong; it can build a preset for the new camera. |
| You want to start a photo again | Say *"reset #12 and redo it"*. |

---

## For developers

- [VISION.md](VISION.md) — goals, principles, risks
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — architecture, file formats, phased build plan
