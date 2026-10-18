#!/usr/bin/env python3
"""LiteCraft originals guard — a Claude Code PreToolUse hook.

Anything that could move, rename, overwrite or delete the user's original photos —
or write files beside them, or write files outside LiteCraft's own folders — needs
the user's own confirmation: this hook answers "ask", which makes Claude Code show
its permission prompt even when LiteCraft's allow rules would otherwise let the call
run. Everything else is left to the normal permission flow (no output).

Protected locations: ~/LiteCraft/Shoots, every LiteCraft job's source folder, and
anything under /Volumes (memory cards, external drives).

Stdlib only. Reads the hook input JSON on stdin; prints a decision JSON or nothing.
Run through guard.sh, which falls back to asking if Python isn't available.
"""
import json
import os
import re
import shlex
import sys
import tempfile

HOME = os.path.expanduser("~")
LITECRAFT_HOME = os.path.realpath(os.path.expanduser(os.environ.get("LITECRAFT_HOME", "~/LiteCraft")))
MCP_PREFIX = "mcp__plugin_litecraft_lightcraft__"

# LightCraft commands that move/rename originals, or write files beside them. Always ask.
ALWAYS_ASK_COMMANDS = {
    "photo.moveToFolder": "moves photo files to another folder",
    "photo.rename": "renames photo files on disk",
    "folder.move": "moves a folder of photos on disk",
    "folder.rename": "renames a folder of photos on disk",
    "photo.saveMetadataToFile": "writes metadata files next to the originals",
    "library.toggleAutoWriteXmp": "turns on writing metadata files next to the originals",
    "library.retrySidecars": "writes metadata files next to the originals",
    "photo.convertToDng": "writes DNG files next to the originals and relinks the photos to them",
    "merge.hdrBatch": "writes merged files next to the originals",
    "photo.duplicate": "copies photo files next to the originals",
    "profile.deleteImported": "deletes imported camera profiles",
}
# LightCraft commands that write output files to a path in their params: param keys to check.
WRITER_COMMANDS = {
    "app.export": ("dir", "path"),
    "preset.export": ("path",),
    "keyword.export": ("path",),
    "curve.exportPresets": ("path",),
    "mask.exportEffects": ("path",),
    "export.contactSheet": ("path",),
    "print.exportPdf": ("path",),
    "slideshow.export": ("path",),
    "slideshow.preview": ("path",),
    "slideshow.templates.export": ("path",),
    "library.smartPreviewsLocation": ("path",),
    "photo.editExternal": ("dir",),
    "folder.create": ("parent",),
}
# Helper tools that write output files: param keys to check.
WRITER_TOOLS = {
    "render_photo": ("path",),
    "screenshot": ("path",),
    "ui_screenshot": ("path",),
    "export": ("dir", "path"),
}
# Tools that drive LightCraft's interface directly (clicks, keys) — they could trigger anything.
UI_TOOLS = {"click", "press_key", "type_text", "pointer_gesture", "clipboard"}

# Shell programs that only read (programs with write flags are handled separately).
READONLY_PROGRAMS = {
    "ls", "du", "df", "stat", "file", "shasum", "md5", "mdls", "mdfind", "head", "tail", "cat",
    "wc", "open", "echo", "printf", "test", "[", "true", "pwd", "cd", "basename", "dirname",
    "realpath", "readlink", "grep", "less",
}
SHELL_PREFIXES = ("sudo", "nohup", "time", "command", "builtin", "exec", "env", "nice", "timeout", "noglob")


# ---------------------------------------------------------------- locations

def real(path):
    return os.path.realpath(os.path.expanduser(expand(str(path)))).rstrip("/") or "/"


def protected_roots():
    roots = [os.path.join(LITECRAFT_HOME, "Shoots")]
    jobs = os.path.join(LITECRAFT_HOME, "Jobs")
    try:
        for name in os.listdir(jobs):
            try:
                with open(os.path.join(jobs, name, "job.json")) as f:
                    source = json.load(f).get("source")
                if source:
                    roots.append(source)
            except (OSError, ValueError, AttributeError):
                pass
    except OSError:
        pass
    out = []
    for r in roots:
        r = real(r)
        if r not in ("/", real(HOME)):
            out.append(r)
    return out


def safe_write_roots():
    roots = [LITECRAFT_HOME, "/tmp", "/private/tmp", "/var/folders", "/private/var/folders", tempfile.gettempdir()]
    try:
        with open(os.path.join(LITECRAFT_HOME, "preferences.json")) as f:
            folder = (json.load(f).get("export") or {}).get("folder")
        if folder:
            roots.append(folder)
    except (OSError, ValueError, AttributeError):
        pass
    return [real(r) for r in roots]


def expand(text):
    return text.replace("${HOME}", HOME).replace("$HOME", HOME).replace("~/", HOME + "/")


def under(path, root):
    return path == root or path.startswith(root + "/")


def is_protected(path, roots):
    if not path:
        return False
    p = real(path)
    return under(p, "/Volumes") or any(under(p, r) for r in roots)


def mentions(text, roots):
    """Does the command text name a protected folder? Also matches the unresolved /tmp, /var forms."""
    text = expand(text)
    if "/Volumes/" in text:
        return True
    for r in roots:
        if r in text or (r.startswith("/private/") and r[len("/private"):] in text):
            return True
    return False


def is_safe_write(path):
    p = real(path)
    return any(under(p, r) for r in safe_write_roots())


def ask(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": f"LiteCraft originals guard: {reason}. Only allow this if you asked for it.",
    }}))
    sys.exit(0)


def check_write_target(target, roots, what="this"):
    if not target or not isinstance(target, str):
        return
    if is_protected(target, roots):
        ask(f"{what} writes into a folder of original photos ({target})")
    if not is_safe_write(target):
        ask(f"{what} writes a file outside LiteCraft's folders ({target})")


# ---------------------------------------------------------------- LightCraft (MCP)

def check_command(command, params, roots):
    params = params if isinstance(params, dict) else {}
    if command in ALWAYS_ASK_COMMANDS:
        ask(f"this {ALWAYS_ASK_COMMANDS[command]}")
    if command == "library.xmpPreferences" and params.get("autoWrite"):
        ask("this turns on writing metadata files next to the originals")
    if command == "library.import":
        check_import(params, roots)
    if command == "app.export" and params.get("conflict") == "overwrite":
        ask("this export may overwrite existing files")
    if command == "photo.editExternal" and not params.get("dir"):
        ask("this writes edited copies next to the originals")
    for key in WRITER_COMMANDS.get(command, ()):
        check_write_target(params.get(key), roots, f"`{command}`")


def check_import(args, roots):
    if args.get("mode") == "move":
        ask("this import moves the original files (removing them from where they are now)")
    dest = args.get("destination")
    if dest and args.get("mode") == "copy":
        # Copying into the Shoots folder is how memory cards are brought in; never overwrites.
        if not under(real(dest), os.path.join(LITECRAFT_HOME, "Shoots")):
            check_write_target(dest, roots, "this import")


def check_mcp(tool, args, roots):
    name = tool[len(MCP_PREFIX):]
    args = args if isinstance(args, dict) else {}
    if name in UI_TOOLS:
        ask("this drives LightCraft's interface directly (clicks or keys)")
    if name == "import":
        check_import(args, roots)
    elif name == "export" and args.get("conflict") == "overwrite":
        ask("this export may overwrite existing files")
    elif name in ("run_command", "command_run"):
        check_command(args.get("command") or args.get("id"), args.get("params"), roots)
    elif name == "command_batch":
        for step in args.get("steps") or []:
            if isinstance(step, dict):
                check_command(step.get("id") or step.get("command"), step.get("params"), roots)
    elif name.startswith("cmd_"):
        # Per-command tools (only listed without --compact): cmd_photo_moveToFolder -> photo.moveToFolder
        check_command(name[4:].replace("_", "."), args, roots)
    for key in WRITER_TOOLS.get(name, ()):
        check_write_target(args.get(key), roots, f"`{name}`")


# ---------------------------------------------------------------- shell

SEPARATORS = re.compile(r"\|\||&&|;|\||\n|&")


def lc_subcommand(words):
    """('env', 'init') etc. when words invoke LiteCraft's lc.py, else None."""
    for i, w in enumerate(words[:2]):
        if w.endswith("lc.py"):
            rest = [x for x in words[i + 1:] if not x.startswith("-")]
            return tuple(rest[:2])
    return None


def check_bash(command, cwd, roots):
    # LiteCraft's own commands that change configuration or remove folders — checked by name.
    for m in re.finditer(r"lc\.py\s+(trash|env\s+init|permissions\s+(?:sync|remove))\b", command):
        what = m.group(1).split()[0]
        ask({"trash": "this moves a shoot folder to the Bin",
             "env": "this changes which programs LiteCraft runs",
             "permissions": "this changes what Claude may do without asking"}[what])

    # fd duplications like 2>&1 or >&2 aren't file writes; drop them before splitting on '&'.
    command = re.sub(r"\d*>&\d+", " ", command)
    parts = []
    here = cwd or HOME
    touches = mentions(command, roots)
    for raw in SEPARATORS.split(command):
        raw = raw.strip()
        if not raw:
            continue
        try:
            words = shlex.split(raw)
        except ValueError:
            if touches:
                ask("this shell command touches a folder of original photos and couldn't be checked")
            continue
        while words and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]) or words[0] in SHELL_PREFIXES):
            words = words[1:]
        if not words:
            continue
        # Resolve relative arguments against the working folder (following `cd`).
        for w in words[1:]:
            if w.startswith("-") or "=" in w and not w.startswith(("/", ".", "~")):
                continue
            path = expand(w) if w.startswith(("/", "~", "$")) else os.path.join(here, w)
            if is_protected(path, roots):
                touches = True
        if os.path.basename(words[0]) == "cd" and len(words) > 1:
            here = real(words[1] if words[1].startswith(("/", "~", "$")) else os.path.join(here, words[1]))
            if is_protected(here, roots):
                touches = True
        parts.append((raw, words))

    for target in re.findall(r"(?<![<\d])>{1,2}\s*([^\s;&|<>]+)", command):
        t = target.strip("'\"")
        if is_protected(t if t.startswith(("/", "~", "$")) else os.path.join(cwd or HOME, t), roots):
            ask("this writes into a folder of original photos")
    if not touches:
        return

    for raw, words in parts:
        prog = os.path.basename(words[0])
        if lc_subcommand(words) is not None or (prog.startswith("python") and lc_subcommand(words[1:]) is not None):
            continue  # LiteCraft's helper only reads protected folders (writing subcommands handled above)
        args = words[1:]
        if prog == "find":
            if any(w in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls") for w in args):
                ask("this `find` deletes files or runs commands in a folder of original photos")
            continue
        if prog == "sips":
            if "--out" not in args and "-o" not in args and any(w.startswith("-") and w not in ("-g", "--getProperty") for w in args):
                ask("sips without --out changes the image file itself")
            continue
        if prog == "xattr":
            if any(w in ("-w", "-d", "-c", "-r") for w in args):
                ask("this changes file attributes on original photos")
            continue
        if prog == "exiftool":
            if any("=" in w or w.lower().startswith(("-o", "-overwrite", "-tagsfromfile", "-geotag", "-delete", "-w", "-@")) for w in args):
                ask("this `exiftool` command writes into photo files")
            continue
        if prog in READONLY_PROGRAMS:
            continue
        ask(f"`{prog}` may change or remove files in a folder of original photos")


# ---------------------------------------------------------------- main

def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    tool = data.get("tool_name") or ""
    args = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    roots = protected_roots()
    if tool.startswith(MCP_PREFIX):
        check_mcp(tool, args, roots)
    elif tool == "Bash":
        check_bash(args.get("command") or "", data.get("cwd"), roots)
    elif tool in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        if is_protected(args.get("file_path") or args.get("notebook_path"), roots):
            ask("this writes a file inside a folder of original photos")


if __name__ == "__main__":
    main()
