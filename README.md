# LiteCraft

**Edit interior photos by chatting with Claude.**

You point Claude at a folder of photos from a shoot. Claude edits them in your house style — brightness, white balance, straight lines, window detail and the 4:5 crop — in **LightCraft**, a free photo editor like Lightroom, so you can watch, check every photo and fine-tune anything by hand. When you're happy, Claude exports the finished images.

You never have to touch a slider unless you want to.

<details>
<summary>Instructions for Claude Code (you can skip this)</summary>

If you've been asked to install LiteCraft from this repo:

1. Run `claude plugin marketplace add andymdavid/Litecraft` then `claude plugin install litecraft@litecraft` (the repo is public; no clone needed).
2. Tell the user to **start a new Claude Code session** (the plugin's skills and LightCraft connection only load in a new session) and type **"Set up LiteCraft"** there.
3. Don't try to do the setup from these files in the current session — the `/litecraft:setup` skill handles installing LightCraft, permissions, preferences and tuning, and resumes if interrupted.

</details>

---

## What you need

- A **Mac** (Apple Silicon recommended, 16 GB memory or more for big shoots)
- The **Claude desktop app**, signed in with a **Claude Pro or Max** plan (Max recommended for large shoots). Already using Claude Code in Terminal? That works too.
- Space for your photos — see [Disk space](#disk-space)

LightCraft (the photo editor) and the LiteCraft plugin are installed for you during setup — you don't need to download anything yourself.

Currently tuned for a **Canon EOS M50** with a **Sigma 30mm F1.4** lens. Other cameras work too; colours just need a little more adjusting until LiteCraft has learned that camera.

---

## One-time setup — about 10 minutes

You only do this once. If someone has set it up for you, skip to [Teach LiteCraft your style](#teach-litecraft-your-style).

### 1. Open Claude's Code tab

**Already have the Claude app?** Make sure it's up to date (**Claude → Check for Updates…**) and that you're signed in.

**Don't have it yet?** Download the **Claude desktop app** from [claude.ai/download](https://claude.ai/download), install it and sign in.

Then open the **Code** tab — LiteCraft runs there, because it works with files on your Mac. When asked for a folder to work in, choose your **home folder** (the one with your name), and use the same one each time.

### 2. Install the LiteCraft plugin

In the Code tab, type:

> Install LiteCraft from github.com/andymdavid/Litecraft

Claude installs it and tells you when it's done. Then **start a new session** so Claude picks it up — use the new session button, or quit and reopen the Claude app.

<details>
<summary>Or install it yourself</summary>

Type these two lines one at a time, pressing Return after each, then start a new session:

```
/plugin marketplace add andymdavid/Litecraft
/plugin install litecraft@litecraft
```

</details>

### 3. Run setup

In the new session, type:

> Set up LiteCraft

Claude:

1. **Installs LightCraft**, the photo editor LiteCraft uses. It asks before downloading, then puts it in your **Applications** folder — so it's in **Launchpad** like any other app.
2. **Offers to stop the permission questions** for LiteCraft's own tools — see below.
3. **Asks how you like things** — crop shape, export size and so on (see [The questions Claude asks](#the-questions-claude-asks)).

That's it — you can start editing now. Results get much closer to your style once you've done the next part.

### About permission questions

Claude normally asks *"Allow Claude to …?"* before it runs anything on your Mac. A single job would mean dozens of those, so setup offers to let LiteCraft's own tools — and controlling LightCraft — run without asking. Everything else still asks first: downloads, installs, and anything outside LiteCraft.

If you said no, or a question still appears: read it, and if it's LiteCraft or LightCraft doing its job, choose **"Yes"** (or **"Yes, and don't ask again"**). If you're unsure, choose **"No"** and ask Claude what it was trying to do.

---

## Teach LiteCraft your style — about 20–30 minutes

Also once, straight after setup or whenever you're ready. Claude does the work; you point it at a few folders. Say *"carry on with setup"* to start.

1. **Learns your camera's colours** from a folder of past photos straight off the camera.
2. **Corrects your lens** (optional) — see [Lens photos](#lens-photos).
3. **Learns your look** from **before/after pairs** — an original photo and your finished edit of it from Lightroom. This is the longest step: roughly a minute or two per pair.
4. **Runs a test job** on 3–5 new photos so you can try reviewing and giving feedback.

### What to have ready

Copies are fine; nothing is changed or moved.

- **Past shoot photos:** a folder of `.CR3` files straight off the camera — any subjects. 30 or more is ideal (at least 5).
- **Before/after pairs:** 5–10 is a good start; you can add more later. See [Getting before/after pairs out of Lightroom](#getting-beforeafter-pairs-out-of-lightroom).
- **Test photos:** 3–5 new `.CR3`s that aren't in your pairs.

If you stop partway, just say *"carry on with setup"* — it picks up where it left off.

**Tip:** in your Canon M50's menu, turn **Auto Lighting Optimizer** off for future shoots. Claude will explain why.

### Getting before/after pairs out of Lightroom

For each pair, Claude needs the **original** `.CR3` and the **finished** edit as a JPEG, **with the same file name** (e.g. `IMG_0412.CR3` and `IMG_0412.jpg`).

In **Lightroom Classic**:

1. Select 5–10 finished photos that show your usual style — a mix of rooms and close-up details, bright and dim.
2. **File → Export.** Choose a new folder (e.g. *Desktop/Pairs*). Set **File Naming** to the original filename, **Image Format** to JPEG with Quality 90 or more, and turn **Resize** off. Click **Export**.
3. For the originals: with the same photos selected, right-click one → **Show in Finder**, and copy the `.CR3` files into the same folder.

In **Lightroom** (the cloud version), use **Export → JPEG, Full size** for the finished photos, and copy the originals from wherever you keep your camera files.

### Lens photos

Optional. Set the lens to its widest aperture (**f/1.4**) and take 2–3 photos of a plain, evenly lit white wall. Claude uses them to correct the slight darkening in the corners.

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

## Editing a shoot

### 1. Put your photos in your Shoots folder

LiteCraft keeps a **Shoots** folder for you, inside the **LiteCraft** folder in your home folder. In Finder: **Go → Home**, then **LiteCraft → Shoots**. (Tip: drag **Shoots** into Finder's sidebar so it's always one click away.)

Make a new folder in there for each shoot — e.g. **Smith Kitchen** — and copy the photos into it straight from the camera (the `.CR3` files).

**Why there?** LiteCraft edits your photos where they are and never changes the originals, so they need to stay put. The Shoots folder isn't synced to iCloud, so files are never moved off your Mac, and Claude and LightCraft can open it without macOS asking for permission.

**Photos somewhere else?** That's fine too:

- **Still on the memory card, or in Downloads, Desktop or Documents:** Claude copies them into your Shoots folder first. Your originals are left exactly where they were.
- **Another folder on your Mac:** Claude edits them in place. Just don't move, rename or delete that folder while you still need the edits.
- If macOS asks whether LightCraft or Claude can access a folder, click **Allow**.

### 2. Ask Claude to edit them

In the Claude app's **Code** tab, type something like:

> Edit the Smith Kitchen shoot

or point it at any folder or your memory card:

> Edit the photos on my memory card — call the job Smith Kitchen

Not sure where the folder is? Drag it from Finder into the chat box — that pastes its location for Claude.

### 3. Let Claude work

Claude opens **LightCraft** and goes through each photo — applying your look, straightening lines, cropping, and checking its own work. You can watch it happen in the LightCraft window.

**How long it takes:** about **1–2 minutes per photo**, so a 30-photo shoot takes roughly 45 minutes. You can use your Mac for other things meanwhile — just don't edit in LightCraft until Claude says it's done.

**Keep your Mac awake:** if it goes to sleep (for example, you close the lid), Claude pauses. Keep it plugged in with the lid open. If it does stop, say *"carry on with the Smith Kitchen job"* and it picks up where it left off.

When it's done, Claude tells you in the chat:

- how many photos are **done**
- which ones are **flagged** for you to look at, and why

### 4. Check the photos in LightCraft

Each job is an album in LightCraft's sidebar. Each photo is marked so you can see where things stand:

| Mark in LightCraft | Meaning |
|---|---|
| 🟢 Green label | Claude is happy with it |
| 🔴 Red label | Flagged — please take a look |
| ⭐ Pick flag | You've approved it |
| ✖ Reject flag | Don't export this one |

- **Photo numbers:** each photo's **title** has its number and a short name, like *#12 kitchen-island*. Use the number when talking to Claude.
- **What Claude did:** the photo's **caption** says, in plain words, what Claude changed and why. Open the info panel (the ⓘ button) to read it.
- **Only the ones that need you:** use the filter button (the funnel next to *Search Photos*) to show only red-labelled photos.
- **Approve or reject:** tell Claude (*"approve #5"*, *"drop #9"*), or in LightCraft press **P** to approve (pick), **X** to reject, **U** to clear.

You don't need to open LightCraft yourself — ask Claude to *"open LightCraft"*. If you do open it from the Dock, that's fine: it shows the same photos. Claude may ask to reopen it when it needs to make changes; nothing is lost.

### 5. Give feedback — two ways

**Tell Claude** in the chat, in your own words:

> #12 is a bit too warm
> #15 — the window is too bright
> #8 crop is too tight on the left
> #3, #4 and #9 could all be a touch brighter

Claude makes the change and you'll see it update in LightCraft.

**Or adjust it yourself** in LightCraft — drag any slider, move the crop, whatever looks right to you. Claude notices what you changed and learns from it.

> ⚠️ Work on a different photo from the one Claude is changing. Claude will tell you when it's finished with a photo ("Done with #12 — over to you").

To start a photo again: *"reset #12 and redo it"*.

### 6. Export

When you're happy, tell Claude:

> Export them

Claude saves the finished photos and opens the folder in Finder. By default that's **LiteCraft → Jobs → Smith Kitchen → export**. Rejected photos are skipped.

---

## Changing your preferences

Just tell Claude. For example:

> From now on, keep landscape photos uncropped
> Change the default export size to 2048 pixels
> What are my current settings?

**For one job only**, say so:

> Edit the Beach House shoot, but leave the landscape photos uncropped this time

That job uses the different setting; your normal defaults stay the same.

---

## How LiteCraft gets better over time

Every change — whether you asked for it or did it yourself — is recorded with a reason. Every so often, Claude will suggest updating your look, for example:

> You've brightened shadows on most photos in the last three jobs. Shall I make that part of the Bright Natural look?

Nothing changes unless you say yes.

---

## Disk space

Camera files are big: each M50 `.CR3` is about 25–30 MB, so a 200-photo shoot is around 5–6 GB, and finished JPEGs add a little more. If Claude copies a shoot from a memory card, that's another copy on your Mac.

Once a shoot is delivered and backed up, you can free space by deleting its folder from **LiteCraft → Shoots**. Ask Claude first (*"I've delivered Smith Kitchen — what can I delete?"*), because LightCraft needs the originals to re-export or change those photos.

---

## Where things are

| What | Where |
|---|---|
| Your photos from each shoot | **LiteCraft → Shoots → *shoot name*** (in your home folder) |
| Finished photos | **LiteCraft → Jobs → *shoot name* → export** |
| What was changed on each photo, and why | **LiteCraft → Jobs → *shoot name* → log** |
| Backups of your look and lens presets | **LiteCraft → presets** |
| Copies of your before/after pairs | **LiteCraft → references** |
| Your answers to the setup questions | **LiteCraft → preferences.json** |
| LightCraft's library (your edits) | **Pictures → LightCraft Library** |

**Your original photos are never modified.** All editing is non-destructive.

---

## Updating LiteCraft

Ask Claude to *"update the LiteCraft plugin"*, then start a new session. Your settings, look and photos are kept.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| Claude says LightCraft is already open | It was probably opened from the Dock. Let Claude reopen it when it asks — nothing is lost. |
| Claude keeps asking permission | Say *"set up LiteCraft permissions"*, or choose **"Yes, and don't ask again"** on LiteCraft's questions. |
| Claude stopped partway through a shoot | Your Mac may have gone to sleep, or you've hit your Claude plan's usage limit. Wait a while if it's the limit, then say *"carry on with the Smith Kitchen job"* — it picks up where it left off. |
| A photo looks wrong after Claude's edit | Tell Claude what's wrong in plain words, or adjust it yourself in LightCraft. |
| Colours look a bit off for a different camera | Expected — LiteCraft is tuned for the Canon M50. Tell Claude what looks wrong; it can learn the new camera too. |
| You want to start a photo again | Say *"reset #12 and redo it"*. |

---

## For developers

- [CLAUDE.md](CLAUDE.md) — orientation and repo rules
