# LiteCraft

**Edit interior photos by chatting with Claude.**

You point Claude at a folder of photos from a shoot. Claude edits them in your house style — brightness, white balance, straight lines, window detail and the 4:5 crop — then opens them in **LightCraft** so you can check every photo and fine-tune anything by hand. When you're happy, Claude exports the finished images.

You never have to touch a slider unless you want to.

> **For Claude Code, if you've been asked to install LiteCraft from this repo:**
> 1. Run `claude plugin marketplace add andymdavid/Litecraft` then `claude plugin install litecraft@litecraft` (the repo is public; no clone needed).
> 2. Tell the user to **start a new Claude Code session** (the plugin's skills and LightCraft connection only load in a new session) and type **"Set up LiteCraft"** there.
> 3. Don't try to do the setup from these files in the current session — the `/litecraft:setup` skill handles installing LightCraft, preferences and tuning, and resumes if interrupted.

> **Status: early version.** The plugin is built; the first real setup on a user's Mac is next. See [IMPLEMENTATION.md](IMPLEMENTATION.md) for progress.

---

## What you need

- A **Mac** (Apple Silicon recommended, 16 GB memory or more for big shoots)
- The **Claude desktop app**, signed in with a **Claude Pro or Max** plan (Max recommended for large shoots)
- **LightCraft** — a free photo editor, similar to Lightroom
- The **LiteCraft plugin** for Claude

Currently tuned for a **Canon EOS M50** with a **Sigma 30mm F1.4** lens. Other cameras will work, but colours may need a little more adjusting until a preset is made for them.

---

## One-time setup

You only do this once. Allow **about an hour** (up to two with lots of reference pairs). Only around 20 minutes of that needs you — the rest is Claude working while you get on with something else. If someone has set it up for you, skip to [Your first job](#your-first-job).

### 1. Install the Claude app

Install the **Claude desktop app** and sign in. Open the **Code** tab — LiteCraft runs there, because it works with files on your Mac. Choose a folder to work in when asked (any folder is fine, e.g. your home folder).

### 2. Install the LiteCraft plugin

In the Code tab, type these two lines one at a time:

```
/plugin marketplace add andymdavid/Litecraft
/plugin install litecraft@litecraft
```

Then start a new session so Claude picks it up.

### 3. Run setup

Type:

> Set up LiteCraft

Claude walks you through it, one step at a time:

1. **Installs LightCraft**, the free photo editor LiteCraft uses (it asks before downloading).
2. **Asks how you like things** — crop shape, export size and so on (see below).
3. **Learns your camera's colours** from a folder of past photos straight off the camera.
4. **Corrects your lens** (optional) from a couple of photos of a plain wall at a wide aperture.
5. **Learns your look** from **before/after pairs** — the original photo and your finished edit from Lightroom. This is the longest step: a few minutes per pair.
6. **Runs a test job** on 3–5 new photos so you can try reviewing and giving feedback.

Have these ready (copies are fine, nothing is changed):
- a folder of past shoot photos (`.CR3` files), the more the better
- your before/after pairs: each original `.CR3` and its final edited JPEG — **5–10 pairs is a good start** (each takes Claude a few minutes to learn from); you can add more later
- 3–5 new photos for the test

If you stop partway, just say *"carry on with setup"* — it picks up where it left off.

**Tip:** in your Canon M50's menu, turn **Auto Lighting Optimizer** off for future shoots. Claude will explain why during setup.

### The questions Claude asks

Each has a sensible default — you can just say *"defaults are fine"*.

| Claude will ask | What it means |
|---|---|
| **Portrait photos — crop to 4:5?** | Tall photos get a light trim to the 4:5 shape, or stay as shot. |
| **Landscape photos — how should they be cropped?** | Wide photos can become a **4:5 tall** crop (cuts a lot of the sides), a **5:4 wide** crop (light trim), or stay **uncropped**. |
| **Which look?** | The house style to use, e.g. *Bright Natural*. |
| **Export size and format** | Full size or smaller; JPEG is usual. |
| **Where should finished photos go?** | Inside the job folder, or somewhere you choose. |
| **Bring LightCraft to the front when editing is done?** | Usually yes. |

Claude saves your answers, so it won't ask again.

---

## Your first job

### 1. Put your photos in a folder

Copy the photos from the shoot (straight from the camera, the `.CR3` files) into a folder — for example `Desktop/Smith Kitchen`.

### 2. Ask Claude to edit them

In the Claude app's **Code** tab, type something like:

> Edit the photos in Desktop/Smith Kitchen

### 3. Let Claude work

Claude opens **LightCraft** and goes through each photo — applying the house style, straightening lines, cropping, and checking its own work. You can watch it happen in the LightCraft window. When it's done, it tells you in the chat:

- how many photos are **done**
- which ones are **flagged** for you to look at, and why

### 4. Check the photos in LightCraft

Each job appears as an album in LightCraft's sidebar. Each photo is marked so you can see where things stand:

| Mark in LightCraft | Meaning |
|---|---|
| 🟢 Green label | Claude is happy with it |
| 🔴 Red label | Flagged — please take a look |
| ⭐ Pick flag | You've approved it |
| ✖ Reject flag | Don't export this one |

Each photo's **title** has its number (like *#12 kitchen-island*) and its **caption** says, in plain words, what Claude changed and why.

**Tip:** filter by the red label to see only the photos that need you.

Each photo has a number (like **#12**) so you can talk about it with Claude.

### 5. Give feedback — two ways

**Tell Claude** in the chat, in your own words:

> #12 is a bit too warm
> #15 — the window is too bright
> #8 crop is too tight on the left
> #3, #4 and #9 could all be a touch brighter

Claude makes the change and you'll see it update in LightCraft.

**Or adjust it yourself** in LightCraft — drag any slider, move the crop, whatever looks right to you. Claude notices what you changed and learns from it.

> ⚠️ Work on a different photo from the one Claude is changing. Claude will tell you when it's finished with a photo ("Done with #12 — over to you").

### 6. Export

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

Everything LiteCraft keeps is in the **LiteCraft** folder in your home folder:

```
~/LiteCraft/
├── Library/              LightCraft's library: your edits (originals are never changed)
├── Jobs/Smith Kitchen/
│   ├── log/              what was changed on each photo, and why
│   └── export/           your finished photos
├── presets/              backups of your look and lens presets
├── references/           copies of the before/after pairs from setup
└── preferences.json      your answers to the setup questions
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
