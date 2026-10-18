#!/usr/bin/env python3
"""LiteCraft helper CLI — state, preferences, jobs, logs, crop candidates, image stats.

Stdlib only. All user state lives under LITECRAFT_HOME (default ~/LiteCraft).
Every command prints JSON on stdout; errors go to stderr with exit status 1.

  lc.py paths
  lc.py env init --cli PATH --app PATH [--port 7980] [--library DIR]
  lc.py env show | env check
  lc.py setup status | setup done STEP [--note TEXT] | setup skip STEP [--note TEXT] | setup reset STEP
  lc.py prefs show | prefs get KEY | prefs set KEY VALUE | prefs missing | prefs questions
  lc.py permissions show|sync|remove [--settings FILE]   LiteCraft's allow rules in Claude Code settings
  lc.py trash SHOOT_NAME_OR_PATH        move a folder inside ~/LiteCraft to the macOS Bin (never erases)
  lc.py source PATH_OR_SHOOT_NAME [--job NAME]   photo count + whether to edit in place or copy first
  lc.py job new NAME --source DIR | job list | job show NAME
  lc.py job add-photos NAME --json '[{"lc_id":..,"file":..,"orientation":..}, ...]'
  lc.py job photo NAME N [--status S] [--slug S] [--iterations N] [--flag-reason TEXT] [--lc-id N]
  lc.py job set NAME [--stage S] [--album-id N] [--source DIR]
  lc.py job override NAME KEY VALUE | job resolve NAME KEY
  lc.py log add NAME N --json ENTRY | log show NAME N
  lc.py crop --width W --height H --aspect 4:5|5:4|none
  lc.py stats IMAGE | compare IMAGE_A IMAGE_B
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PORT = 7980

SETUP_STEPS = [
    "preflight",
    "install_lightcraft",
    "permissions",
    "preferences",
    "camera_profile",
    "lens",
    "look",
    "test_job",
    "complete",
]


# ---------------------------------------------------------------- utilities

def fail(msg):
    print(f"lc.py: {msg}", file=sys.stderr)
    sys.exit(1)


def out(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def home():
    return os.path.expanduser(os.environ.get("LITECRAFT_HOME", "~/LiteCraft"))


def paths():
    h = home()
    return {
        "home": h,
        "env": os.path.join(h, "litecraft.env"),
        "setup": os.path.join(h, "setup.json"),
        "preferences": os.path.join(h, "preferences.json"),
        # LightCraft's own default library location, so opening LightCraft from the Dock shows the same photos.
        "library": os.path.expanduser(os.environ.get("LITECRAFT_LIBRARY", "~/Pictures/LightCraft Library")),
        "presets": os.path.join(h, "presets"),
        "references": os.path.join(h, "references"),
        "jobs": os.path.join(h, "Jobs"),
        "shoots": os.path.join(h, "Shoots"),
        "bin": os.path.join(h, "bin"),
        "plugin_root": PLUGIN_ROOT,
        "default_preferences": os.path.join(PLUGIN_ROOT, "defaults", "preferences.json"),
    }


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path, obj):
    """Atomic write: temp file in the same directory, then rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def parse_value(text):
    """JSON when it parses (numbers, true/false/null, objects), else the raw string."""
    try:
        return json.loads(text)
    except ValueError:
        return text


def get_dotted(obj, key):
    for part in key.split("."):
        if not isinstance(obj, dict) or part not in obj:
            raise KeyError(key)
        obj = obj[part]
    return obj


def set_dotted(obj, key, value):
    parts = key.split(".")
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = value


# ---------------------------------------------------------------- env

def read_env():
    env = {}
    try:
        with open(paths()["env"]) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        pass
    return env


def cmd_env(a):
    p = paths()
    if a.action == "init":
        for name, value in (("--cli", a.cli), ("--app", a.app), ("--library", a.library)):
            if value and re.search(r"[\"'`$\\\n\r]", value):
                fail(f"{name} path contains characters LiteCraft won't store (quotes, $, `, backslash or newlines): {value!r}")
        env = {
            "LIGHTCRAFT_CLI": os.path.abspath(os.path.expanduser(a.cli)),
            "LIGHTCRAFT_APP": os.path.abspath(os.path.expanduser(a.app)),
            "LITECRAFT_PORT": str(a.port),
            "LITECRAFT_LIBRARY": os.path.abspath(os.path.expanduser(a.library or p["library"])),
        }
        os.makedirs(p["home"], exist_ok=True)
        tmp = p["env"] + ".tmp"
        with open(tmp, "w") as f:
            f.write("# Written by lc.py env init — paths LiteCraft uses to run LightCraft.\n")
            for k, v in env.items():
                f.write(f'{k}="{v}"\n')
        os.replace(tmp, p["env"])
        for d in ("jobs", "shoots", "presets", "references"):
            os.makedirs(p[d], exist_ok=True)
        out(env)
    elif a.action == "show":
        out(read_env())
    elif a.action == "check":
        env = read_env()
        report = {"env_file": os.path.exists(p["env"]), "ok": True, "problems": []}
        for key in ("LIGHTCRAFT_CLI", "LIGHTCRAFT_APP"):
            path = env.get(key)
            if not path or not os.path.exists(path):
                report["ok"] = False
                report["problems"].append(f"{key} missing or not found: {path}")
        if env.get("LIGHTCRAFT_CLI") and os.path.exists(env["LIGHTCRAFT_CLI"]):
            try:
                v = subprocess.run([env["LIGHTCRAFT_CLI"], "--version"], capture_output=True, text=True, timeout=20)
                report["cli_version"] = v.stdout.strip()
            except (OSError, subprocess.TimeoutExpired) as e:
                report["ok"] = False
                report["problems"].append(f"cli did not run: {e}")
        report.update(env)
        out(report)


# ---------------------------------------------------------------- setup state

def load_setup():
    return read_json(paths()["setup"], {"schema": 1, "steps": {}})


def cmd_setup(a):
    state = load_setup()
    if a.action in ("done", "skip", "reset"):
        if a.step not in SETUP_STEPS:
            fail(f"unknown step {a.step!r}; steps: {', '.join(SETUP_STEPS)}")
        if a.action == "reset":
            state["steps"].pop(a.step, None)
        else:
            state["steps"][a.step] = {"status": "done" if a.action == "done" else "skipped",
                                      "at": now(), "note": a.note}
        write_json(paths()["setup"], state)
    steps = [{"step": s, **state["steps"].get(s, {"status": "todo"})} for s in SETUP_STEPS]
    nxt = next((s["step"] for s in steps if s["status"] == "todo"), None)
    out({"complete": state["steps"].get("complete", {}).get("status") == "done",
         "next": nxt, "steps": steps})


# ---------------------------------------------------------------- preferences

def default_prefs():
    d = read_json(paths()["default_preferences"])
    if d is None:
        fail(f"missing {paths()['default_preferences']}")
    return d


def resolved_prefs(overrides=None):
    d = default_prefs()
    user = read_json(paths()["preferences"], {})
    prefs = {}
    for q in d["questions"]:
        key = q["key"]
        try:
            value = get_dotted(user, key)
        except KeyError:
            value = q.get("default")
        if overrides and key in overrides:
            value = overrides[key]
        set_dotted(prefs, key, value)
    return prefs


def cmd_prefs(a):
    d = default_prefs()
    keys = {q["key"]: q for q in d["questions"]}
    user = read_json(paths()["preferences"], {"schema": 1})
    if a.action == "show":
        out(resolved_prefs())
    elif a.action == "questions":
        out(d["questions"])
    elif a.action == "get":
        if a.key not in keys:
            fail(f"unknown preference {a.key!r}")
        out({a.key: get_dotted(resolved_prefs(), a.key)})
    elif a.action == "set":
        if a.key not in keys:
            fail(f"unknown preference {a.key!r}; known: {', '.join(keys)}")
        value = parse_value(a.value)
        allowed = keys[a.key].get("options")
        if allowed and value not in allowed and not keys[a.key].get("free"):
            fail(f"{a.key} must be one of {allowed}")
        set_dotted(user, a.key, value)
        user["updated"] = now()
        write_json(paths()["preferences"], user)
        out({a.key: value})
    elif a.action == "missing":
        missing = []
        for q in d["questions"]:
            try:
                get_dotted(user, q["key"])
            except KeyError:
                missing.append(q)
        out(missing)


# ---------------------------------------------------------------- Claude Code permissions

MCP_RULE = "mcp__plugin_litecraft_lightcraft__*"
HOME_READ_RULE = "Read(~/LiteCraft/**)"
# lc.py subcommands that run without a prompt. Not here (they always ask): env init,
# permissions sync/remove and trash — they change what runs, what's allowed, or remove folders.
LC_ALLOWED = ["paths", "setup *", "prefs *", "source *", "job *", "log *", "crop *", "stats *",
              "compare *", "env show", "env check", "permissions show"]


def permission_rules():
    """Exact rules for LiteCraft's own scripts at this plugin version, plus LightCraft's tools.

    The plugin path contains its version, so rules are rewritten after an update (sync) rather
    than using a wildcard in the program position, which would match more than intended.
    """
    lc = os.path.join(PLUGIN_ROOT, "scripts", "lc.py")
    return ([MCP_RULE]
            + [f"Bash({lc} {sub})" for sub in LC_ALLOWED]
            + [f"Bash({os.path.join(PLUGIN_ROOT, 'bin', 'litecraft-app')} *)",
               HOME_READ_RULE,
               f"Read(/{PLUGIN_ROOT}/**)"])


def is_litecraft_rule(rule):
    if rule in permission_rules() or rule in (MCP_RULE, HOME_READ_RULE):
        return True
    if rule.startswith("Bash(") and ("/scripts/lc.py " in rule or rule.endswith("/bin/litecraft-app *)")):
        return True
    return rule.startswith("Read(//") and "/plugins/cache/litecraft/" in rule


def cmd_permissions(a):
    # Write through a symlinked settings file (dotfile managers) rather than replacing the link.
    path = os.path.realpath(os.path.expanduser(a.settings or "~/.claude/settings.json"))
    try:
        settings = read_json(path, {})
    except ValueError as e:
        fail(f"{path} isn't valid JSON ({e}); not changing it")
    if not isinstance(settings, dict) or not isinstance(settings.get("permissions", {}), dict) \
            or not isinstance(settings.get("permissions", {}).get("allow", []), list):
        fail(f"{path} has an unexpected shape; not changing it")
    allow = settings.get("permissions", {}).get("allow", [])
    wanted = permission_rules()
    current = [r for r in allow if is_litecraft_rule(r)]
    if a.action == "show":
        out({"settings": path, "wanted": wanted, "present": current,
             "in_sync": sorted(current) == sorted(wanted)})
        return
    others = [r for r in allow if not is_litecraft_rule(r)]
    new_allow = others + (wanted if a.action == "sync" else [])
    if new_allow == allow:
        out({"settings": path, "changed": False, "rules": current})
        return
    if os.path.exists(path) and not os.path.exists(path + ".litecraft-backup"):
        with open(path) as src, open(path + ".litecraft-backup", "w") as dst:
            dst.write(src.read())
    settings.setdefault("permissions", {})["allow"] = new_allow
    write_json(path, settings)
    out({"settings": path, "changed": True, "removed": [r for r in current if r not in new_allow],
         "added": [r for r in new_allow if r not in allow]})


# ---------------------------------------------------------------- source folders

PHOTO_EXTS = {".cr3", ".cr2", ".dng", ".arw", ".nef", ".raf", ".rw2", ".orf", ".pef",
              ".jpg", ".jpeg", ".tif", ".tiff", ".png", ".heic", ".webp"}
RAW_EXTS = {".cr3", ".cr2", ".dng", ".arw", ".nef", ".raf", ".rw2", ".orf", ".pef"}


def classify_source(path):
    """Where a shoot folder lives decides whether LightCraft edits it in place or copies it first.

    In-place ("add") references the originals, so they must stay put. Memory cards, Downloads,
    Desktop, Documents and iCloud Drive are copied into ~/LiteCraft/Shoots/<job>: cards get
    ejected, Downloads gets cleared, and Desktop/Documents may be iCloud-synced (files can be
    evicted to the cloud) and are privacy-protected folders on macOS.
    """
    real = os.path.realpath(path)
    user_home = os.path.realpath(os.path.expanduser("~"))
    shoots = os.path.realpath(paths()["shoots"])
    if real == shoots or real.startswith(shoots + os.sep):
        return "shoots", "add", "Already in the LiteCraft Shoots folder."
    if real == "/Volumes" or real.startswith("/Volumes/"):
        return "removable", "copy", "On a memory card or external drive — copy it to the Mac first."
    icloud = os.path.join(user_home, "Library", "Mobile Documents")
    if real.startswith(icloud + os.sep):
        return "icloud", "copy", "In iCloud Drive — files may only be stored in the cloud."
    for name in ("Downloads", "Desktop", "Documents"):
        base = os.path.join(user_home, name)
        if real == base or real.startswith(base + os.sep):
            return name.lower(), "copy", f"In {name} — may be iCloud-synced or cleared; copy for safety."
    return "local", "add", "A regular folder on this Mac — edit in place; don't move or rename it afterwards."


def cmd_source(a):
    path = os.path.abspath(os.path.expanduser(a.path))
    if not os.path.isdir(path):
        # A bare shoot name: look in Shoots.
        candidate = os.path.join(paths()["shoots"], a.path)
        if os.path.isdir(candidate):
            path = candidate
        else:
            fail(f"no folder at {path} (and no shoot named {a.path!r} in {paths()['shoots']})")
    counts, total, raws = {}, 0, 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in PHOTO_EXTS and not f.startswith("._"):
                counts[ext] = counts.get(ext, 0) + 1
                total += 1
                raws += ext in RAW_EXTS
    kind, mode, why = classify_source(path)
    result = {"path": path, "kind": kind, "import_mode": mode, "why": why,
              "photos": total, "raw": raws, "by_type": counts}
    if mode == "copy":
        name = a.job or os.path.basename(path.rstrip(os.sep)) or "Shoot"
        result["copy_to"] = os.path.join(paths()["shoots"], name)
        result["copy_exists"] = os.path.exists(result["copy_to"])
    if total == 0:
        result["warning"] = "No photos found in this folder."
    elif raws and raws < total:
        result["warning"] = "Mixed RAW and JPEG files — likely RAW+JPEG pairs; import only the RAWs."
    out(result)


# ---------------------------------------------------------------- trash

def cmd_trash(a):
    """Move a shoot (or job) folder to the Bin. Only folders inside LITECRAFT_HOME; the guard hook asks the user first."""
    p = paths()
    target = os.path.expanduser(a.target)
    if not os.path.isabs(target):
        target = os.path.join(p["shoots"], target)
    target = os.path.realpath(target)
    allowed = [os.path.realpath(p["shoots"]), os.path.realpath(p["jobs"])]
    if not any(target.startswith(root + os.sep) for root in allowed):
        fail(f"{target} is not a shoot or job folder inside {p['home']} — LiteCraft only moves its own folders to the Bin")
    if not os.path.isdir(target):
        fail(f"no folder at {target}")
    bin_dir = os.path.expanduser("~/.Trash")
    dest = os.path.join(bin_dir, os.path.basename(target))
    n = 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(bin_dir, f"{os.path.basename(target)} {n}")
    shutil.move(target, dest)
    out({"moved_to_bin": target, "bin_path": dest,
         "restore": "Open the Bin in the Dock and drag the folder back, or ask Claude to put it back."})


# ---------------------------------------------------------------- jobs

def job_dir(name):
    """Any name that works as a folder name: 1-100 characters, no / or :, no control characters,
    not starting with a dot or a space (so no hidden folders and no '..')."""
    if (not name or len(name) > 100 or name != name.strip() or name.startswith(".")
            or re.search(r"[/:\x00-\x1f\x7f]", name)):
        fail(f"job name {name!r}: use up to 100 characters, without / or : and not starting with a dot")
    return os.path.join(paths()["jobs"], name)


def load_job(name):
    job = read_json(os.path.join(job_dir(name), "job.json"))
    if job is None:
        fail(f"no job named {name!r}")
    return job


def save_job(job):
    write_json(os.path.join(job_dir(job["name"]), "job.json"), job)


def find_photo(job, n):
    for p in job["photos"]:
        if p["n"] == n:
            return p
    fail(f"job {job['name']!r} has no photo #{n}")


def cmd_job(a):
    if a.action == "new":
        d = job_dir(a.name)
        if os.path.exists(os.path.join(d, "job.json")):
            fail(f"job {a.name!r} already exists")
        for sub in ("log", "export", "previews"):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        job = {"schema": 1, "name": a.name, "source": os.path.abspath(os.path.expanduser(a.source)),
               "album_id": None, "created": now(), "stage": "editing", "overrides": {}, "photos": []}
        save_job(job)
        out({**job, "dir": d})
    elif a.action == "list":
        root = paths()["jobs"]
        jobs = []
        for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            j = read_json(os.path.join(root, name, "job.json"))
            if j:
                counts = {}
                for p in j["photos"]:
                    counts[p["status"]] = counts.get(p["status"], 0) + 1
                jobs.append({"name": j["name"], "stage": j["stage"], "created": j["created"], "counts": counts})
        out(jobs)
    elif a.action == "show":
        out({**load_job(a.name), "dir": job_dir(a.name)})
    elif a.action == "add-photos":
        job = load_job(a.name)
        n = max((p["n"] for p in job["photos"]), default=0)
        added = []
        for item in json.loads(a.json):
            n += 1
            photo = {"n": n, "lc_id": item.get("lc_id"), "file": item.get("file"),
                     "slug": item.get("slug"), "orientation": item.get("orientation"),
                     "status": "queued", "iterations": 0, "flag_reason": None, "updated": now()}
            job["photos"].append(photo)
            added.append(photo)
        save_job(job)
        out(added)
    elif a.action == "photo":
        job = load_job(a.name)
        photo = find_photo(job, a.n)
        for field in ("status", "slug", "iterations", "flag_reason", "lc_id"):
            value = getattr(a, field)
            if value is not None:
                photo[field] = value
        photo["updated"] = now()
        save_job(job)
        out(photo)
    elif a.action == "set":
        job = load_job(a.name)
        if a.stage:
            job["stage"] = a.stage
        if a.album_id is not None:
            job["album_id"] = a.album_id
        if a.source:
            job["source"] = os.path.abspath(os.path.expanduser(a.source))
        save_job(job)
        out({k: job[k] for k in ("name", "stage", "album_id", "source")})
    elif a.action == "override":
        job = load_job(a.name)
        job["overrides"][a.key] = parse_value(a.value)
        save_job(job)
        out(job["overrides"])
    elif a.action == "resolve":
        job = load_job(a.name)
        out({a.key: get_dotted(resolved_prefs(job["overrides"]), a.key)})


# ---------------------------------------------------------------- logs

LOG_SOURCES = ("preset", "agent", "feedback", "user-tweak")
LOG_ENTRY_EXAMPLE = {
    "source": "agent",
    "changes": [{"control": "light.exposure", "from": 0.0, "to": 0.75, "reason": "Room ~1 stop dark; midtones 58 vs target 72-80"}],
    "feedback": None,
    "settings_after": {"light": {}, "wb": {}, "color": {}, "effects": {}, "crop": {}, "geometry": {}},
}


def validate_entry(entry):
    """Changes must be structured so user tweaks and recurring corrections can be compared later."""
    problems = []
    if not isinstance(entry, dict):
        return ["entry must be a JSON object"]
    if entry.get("source") not in LOG_SOURCES:
        problems.append(f"source must be one of {list(LOG_SOURCES)}")
    changes = entry.get("changes")
    if not isinstance(changes, list):
        problems.append("changes must be a list")
    else:
        for i, c in enumerate(changes):
            if not isinstance(c, dict):
                problems.append(f"changes[{i}] must be an object, not {type(c).__name__}")
            elif not c.get("control") or "to" not in c or not c.get("reason"):
                problems.append(f"changes[{i}] needs control, to and reason")
    if not isinstance(entry.get("settings_after"), dict):
        problems.append("settings_after must be the develop settings after this pass")
    return problems


def cmd_log(a):
    load_job(a.name)
    path = os.path.join(job_dir(a.name), "log", f"{a.n}.json")
    log = read_json(path, {"schema": 1, "n": a.n, "entries": []})
    if a.action == "add":
        entry = json.loads(a.json)
        problems = validate_entry(entry)
        if problems:
            fail("log entry rejected: " + "; ".join(problems) + "\nexpected: " + json.dumps(LOG_ENTRY_EXAMPLE))
        entry.setdefault("at", now())
        log["entries"].append(entry)
        write_json(path, log)
        out(entry)
    else:
        out(log)


# ---------------------------------------------------------------- crop

def parse_aspect(text):
    m = re.fullmatch(r"(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)", text)
    if not m:
        fail(f"aspect {text!r}: use W:H, e.g. 4:5")
    return float(m.group(1)) / float(m.group(2))


def cmd_crop(a):
    w, h = float(a.width), float(a.height)
    if a.aspect == "none":
        out({"aspect": "none", "candidates": [{"name": "full", "rect": [0, 0, 1, 1], "keeps": 1.0}]})
        return
    target = parse_aspect(a.aspect)
    source = w / h
    candidates = []
    if target < source:
        # Narrower than the source: full height, slide horizontally.
        cw = target / source
        positions = {"centre": 0.5, "left-third": 1 / 3, "right-third": 2 / 3, "left": cw / 2, "right": 1 - cw / 2}
        for name, cx in positions.items():
            x0 = min(max(cx - cw / 2, 0.0), 1.0 - cw)
            candidates.append({"name": name, "rect": [round(x0, 4), 0.0, round(x0 + cw, 4), 1.0]})
        keeps = cw
    else:
        # Wider than (or equal to) the source: full width, slide vertically.
        ch = source / target
        positions = {"centre": 0.5, "lower": 0.5 + (1 - ch) / 4, "upper": 0.5 - (1 - ch) / 4,
                     "bottom": 1 - ch / 2, "top": ch / 2}
        for name, cy in positions.items():
            y0 = min(max(cy - ch / 2, 0.0), 1.0 - ch)
            candidates.append({"name": name, "rect": [0.0, round(y0, 4), 1.0, round(y0 + ch, 4)]})
        keeps = ch
    # Drop duplicates (small differences collapse at the edges).
    seen, unique = set(), []
    for c in candidates:
        key = tuple(c["rect"])
        if key not in seen:
            seen.add(key)
            c["keeps"] = round(keeps, 3)
            unique.append(c)
    out({"aspect": a.aspect, "source_aspect": round(source, 4), "keeps_fraction": round(keeps, 3),
         "heavy": keeps < 0.75, "candidates": unique})


# ---------------------------------------------------------------- image stats

def load_pixels(path, size=256):
    """Decode any image macOS can read via `sips` into a list of (r, g, b) 0..255."""
    if not os.path.exists(path):
        fail(f"no such image {path}")
    with tempfile.TemporaryDirectory() as tmp:
        bmp = os.path.join(tmp, "x.bmp")
        r = subprocess.run(["sips", "-s", "format", "bmp", "-Z", str(size), path, "--out", bmp],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(bmp):
            fail(f"sips could not read {path}: {r.stderr.strip()}")
        data = open(bmp, "rb").read()
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp not in (24, 32):
        fail(f"unsupported BMP depth {bpp}")
    step = bpp // 8
    row = (width * step + 3) & ~3
    pixels = []
    for y in range(abs(height)):
        base = offset + y * row
        for x in range(width):
            b, g, r_ = data[base + x * step: base + x * step + 3]
            pixels.append((r_, g, b))
    return pixels, width, abs(height)


def srgb_to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def image_stats(path):
    pixels, w, h = load_pixels(path)
    lin = [srgb_to_linear(i) for i in range(256)]
    lums, warmth, sats = [], [], []
    clip_hi = clip_lo = 0
    for r, g, b in pixels:
        y = 0.2126 * lin[r] + 0.7152 * lin[g] + 0.0722 * lin[b]
        lstar = 116 * (y ** (1 / 3)) - 16 if y > 0.008856 else 903.3 * y
        lums.append(lstar)
        warmth.append((r - b) / 255.0)
        mx, mn = max(r, g, b), min(r, g, b)
        sats.append(0.0 if mx == 0 else (mx - mn) / mx)
        if mx >= 250:
            clip_hi += 1
        if mx <= 5:
            clip_lo += 1
    n = len(lums)
    s = sorted(lums)

    def pct(p):
        return round(s[min(n - 1, int(p / 100 * n))], 1)

    return {
        "image": path, "sample_size": [w, h],
        "lightness_mean": round(sum(lums) / n, 1),
        "lightness_p5": pct(5), "lightness_p50": pct(50), "lightness_p95": pct(95),
        "clipped_highlights_pct": round(100 * clip_hi / n, 2),
        "crushed_shadows_pct": round(100 * clip_lo / n, 2),
        "warmth_mean": round(sum(warmth) / n, 3),
        "saturation_mean": round(sum(sats) / n, 3),
    }


def cmd_stats(a):
    out(image_stats(a.image))


def cmd_compare(a):
    sa, sb = image_stats(a.a), image_stats(a.b)
    keys = [k for k in sa if isinstance(sa[k], (int, float))]
    out({"a": a.a, "b": a.b, "delta_b_minus_a": {k: round(sb[k] - sa[k], 3) for k in keys},
         "a_stats": sa, "b_stats": sb,
         "hint": "lightness ~ exposure/tone, warmth ~ white balance temp, saturation ~ vibrance/saturation"})


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="lc.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("paths").set_defaults(fn=lambda a: out(paths()))

    e = sub.add_parser("env")
    e.add_argument("action", choices=["init", "show", "check"])
    e.add_argument("--cli")
    e.add_argument("--app")
    e.add_argument("--port", type=int, default=DEFAULT_PORT)
    e.add_argument("--library")
    e.set_defaults(fn=cmd_env)

    s = sub.add_parser("setup")
    s.add_argument("action", choices=["status", "done", "skip", "reset"])
    s.add_argument("step", nargs="?")
    s.add_argument("--note")
    s.set_defaults(fn=cmd_setup)

    p = sub.add_parser("prefs")
    p.add_argument("action", choices=["show", "get", "set", "missing", "questions"])
    p.add_argument("key", nargs="?")
    p.add_argument("value", nargs="?")
    p.set_defaults(fn=cmd_prefs)

    pm = sub.add_parser("permissions")
    pm.add_argument("action", choices=["show", "sync", "remove"])
    pm.add_argument("--settings")
    pm.set_defaults(fn=cmd_permissions)

    tr = sub.add_parser("trash")
    tr.add_argument("target")
    tr.set_defaults(fn=cmd_trash)

    so = sub.add_parser("source")
    so.add_argument("path")
    so.add_argument("--job")
    so.set_defaults(fn=cmd_source)

    j = sub.add_parser("job")
    j.add_argument("action", choices=["new", "list", "show", "add-photos", "photo", "set", "override", "resolve"])
    j.add_argument("name", nargs="?")
    j.add_argument("n_or_key", nargs="?")
    j.add_argument("value", nargs="?")
    j.add_argument("--source")
    j.add_argument("--json")
    j.add_argument("--status", choices=["queued", "editing", "done", "flagged", "approved", "rejected", "exported"])
    j.add_argument("--slug")
    j.add_argument("--iterations", type=int)
    j.add_argument("--flag-reason")
    j.add_argument("--lc-id", type=int)
    j.add_argument("--stage", choices=["editing", "review", "exported"])
    j.add_argument("--album-id", type=int)
    j.set_defaults(fn=cmd_job)

    lg = sub.add_parser("log")
    lg.add_argument("action", choices=["add", "show"])
    lg.add_argument("name")
    lg.add_argument("n", type=int)
    lg.add_argument("--json")
    lg.set_defaults(fn=cmd_log)

    c = sub.add_parser("crop")
    c.add_argument("--width", required=True, type=float)
    c.add_argument("--height", required=True, type=float)
    c.add_argument("--aspect", required=True)
    c.set_defaults(fn=cmd_crop)

    st = sub.add_parser("stats")
    st.add_argument("image")
    st.set_defaults(fn=cmd_stats)

    cp = sub.add_parser("compare")
    cp.add_argument("a")
    cp.add_argument("b")
    cp.set_defaults(fn=cmd_compare)

    a = ap.parse_args()

    # Validate per-action required arguments (argparse can't express these cleanly).
    if a.cmd == "env" and a.action == "init" and not (a.cli and a.app):
        fail("env init needs --cli and --app")
    if a.cmd == "setup" and a.action != "status" and not a.step:
        fail(f"setup {a.action} needs a STEP")
    if a.cmd == "prefs" and a.action in ("get", "set") and not a.key:
        fail(f"prefs {a.action} needs a KEY")
    if a.cmd == "prefs" and a.action == "set" and a.value is None:
        fail("prefs set needs a VALUE")
    if a.cmd == "job":
        if a.action != "list" and not a.name:
            fail(f"job {a.action} needs a NAME")
        if a.action == "new" and not a.source:
            fail("job new needs --source")
        if a.action == "add-photos" and not a.json:
            fail("job add-photos needs --json")
        if a.action == "photo":
            if not (a.n_or_key or "").isdigit():
                fail("job photo needs a photo number N")
            a.n = int(a.n_or_key)
        if a.action in ("override", "resolve"):
            if not a.n_or_key:
                fail(f"job {a.action} needs a KEY")
            a.key = a.n_or_key
            if a.action == "override" and a.value is None:
                fail("job override needs a VALUE")
    if a.cmd == "log" and a.action == "add" and not a.json:
        fail("log add needs --json")

    a.fn(a)


if __name__ == "__main__":
    main()
