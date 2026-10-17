# CLAUDE.md

LiteCraft is a Claude Code plugin that edits interior photos by driving **LightCraft** (an open-source, Lightroom-like raw editor) over MCP. The user chats with Claude; edits happen live in the LightCraft desktop app, where the user reviews and fine-tunes.

Read [IMPLEMENTATION.md](IMPLEMENTATION.md) for architecture, file formats and status. [VISION.md](VISION.md) is the why; [README.md](README.md) is the user guide.

## Which situation are you in?

**1. You're on the user's Mac to set them up (initialisation run).**
The plugin is (or is about to be) installed and the user has their own photos. Your job is the setup skill: run `/litecraft:setup`. It is resumable — it reads `~/LiteCraft/setup.json` and continues from the first unfinished step. All tuning against the user's photos (camera profile, lens, look from their before/after pairs, test job) happens there, not by editing this repo. If the plugin isn't installed yet:

```
/plugin marketplace add andymdavid/Litecraft
/plugin install litecraft@litecraft
```

then restart the session so the plugin's MCP server and skills load.

**2. You're developing the plugin in this repo.**
Work against the phases in IMPLEMENTATION.md and tick items off as they're verified.

## Rules

- **Atomic commits.** One logical change per commit, pushed as you go. End messages with the attribution line from the session.
- **No client photos in git.** `Samples/` and `vendor/` are gitignored; keep it that way.
- **Connect mode only.** The plugin's MCP server always uses `lightcraft-cli mcp --connect`. Never configure a headless `--library` server in the plugin — it would hold the library lock for the whole session and block the desktop app.
- **Stdlib-only Python** in `plugin/scripts/` — the user's Mac has no pip packages.
- **User data lives in `~/LiteCraft`** (override with `LITECRAFT_HOME` for testing). Never write user state into the plugin directory.
- Mark unverified LightCraft behaviour **(verify)** in docs until tested.

## Dev setup

LightCraft is built from source into `vendor/lightcraft` (gitignored):

```sh
git clone --depth 1 https://github.com/storytold/lightcraft vendor/lightcraft
cd vendor/lightcraft && cargo build --release -p lightcraft -p lightcraft-cli
```

Dry-run the plugin against it with a scratch home:

```sh
export LITECRAFT_HOME=/tmp/litecraft-home
plugin/scripts/lc.py env init --cli vendor/lightcraft/target/release/lightcraft-cli --app vendor/lightcraft/target/release/lightcraft
plugin/bin/litecraft-app start
```

`dev/mcp_probe.py` drives an MCP server from a JSONL script — handy for checking LightCraft commands without a Claude session. `lightcraft-cli commands` lists every command and its params.
