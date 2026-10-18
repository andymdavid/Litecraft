#!/usr/bin/env python3
"""LiteCraft originals guard — a Claude Code PreToolUse hook.

Anything that could move, rename, overwrite or delete the user's original photos
needs the user's own confirmation: this hook answers "ask", which makes Claude Code
show its permission prompt even when LiteCraft's allow rules would otherwise let the
call run. Everything else is left to the normal permission flow (no output).

Protected locations: ~/LiteCraft/Shoots, every LiteCraft job's source folder, and
anything under /Volumes (memory cards, external drives).

Stdlib only. Reads the hook input JSON on stdin; prints a decision JSON or nothing.
"""
import json
import os
import re
import shlex
import sys

HOME = os.path.expanduser("~")
LITECRAFT_HOME = os.path.expanduser(os.environ.get("LITECRAFT_HOME", "~/LiteCraft"))
MCP_PREFIX = "mcp__plugin_litecraft_lightcraft__"

# LightCraft commands that move or rename files on disk, or write files next to originals.
MOVING_COMMANDS = {
    "photo.moveToFolder": "moves photo files to another folder",
    "photo.rename": "renames photo files on disk",
    "folder.move": "moves a folder of photos on disk",
    "folder.rename": "renames a folder of photos on disk",
    "photo.saveMetadataToFile": "writes metadata files next to the originals",
    "library.toggleAutoWriteXmp": "turns on writing metadata files next to the originals",
    "library.retrySidecars": "writes metadata files next to the originals",
}
# Tools that drive LightCraft's interface directly (clicks, keys) — they could trigger any of the above.
UI_TOOLS = {"click", "press_key", "type_text", "pointer_gesture", "clipboard"}

# Shell programs that only read.
READONLY_PROGRAMS = {
    "ls", "du", "df", "stat", "file", "shasum", "md5", "mdls", "mdfind", "head", "tail", "cat",
    "wc", "open", "echo", "printf", "test", "[", "true", "pwd", "cd", "basename", "dirname",
    "realpath", "readlink", "exiftool", "sort", "uniq", "grep", "tree", "less", "xattr",
}


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
            except (OSError, ValueError):
                pass
    except OSError:
        pass
    norm = []
    for r in roots:
        r = os.path.realpath(os.path.expanduser(r)).rstrip("/")
        if r and r != "/" and r != os.path.realpath(HOME):
            norm.append(r)
    return norm


def expand(text):
    return text.replace("${HOME}", HOME).replace("$HOME", HOME).replace("~/", HOME + "/")


def is_protected(path, roots):
    if not path:
        return False
    p = os.path.realpath(os.path.expanduser(expand(str(path)))).rstrip("/")
    if p == "/Volumes" or p.startswith("/Volumes/"):
        return True
    return any(p == r or p.startswith(r + "/") for r in roots)


def mentions_protected(text, roots):
    text = expand(text)
    if "/Volumes/" in text:
        return True
    for r in roots:
        if r in text:
            return True
        # Also match the unresolved form, e.g. /tmp vs /private/tmp.
        if r.startswith("/private/") and r[len("/private"):] in text:
            return True
    return False


def ask(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": f"LiteCraft originals guard: {reason}. Only allow this if you asked for it.",
    }}))
    sys.exit(0)


# ---------------------------------------------------------------- LightCraft (MCP)

def check_command(command, params, roots):
    params = params or {}
    if command in MOVING_COMMANDS:
        ask(f"this {MOVING_COMMANDS[command]}")
    if command == "library.xmpPreferences" and params.get("autoWrite"):
        ask("this turns on writing metadata files next to the originals")
    if command == "library.import":
        check_import(params)
    if command == "app.export":
        check_export(params, roots)


def check_import(args):
    if (args or {}).get("mode") == "move":
        ask("this import moves the original files (removing them from where they are now)")


def check_export(args, roots):
    args = args or {}
    if args.get("conflict") == "overwrite":
        ask("this export may overwrite existing files")
    dest = args.get("dir") or (os.path.dirname(args["path"]) if args.get("path") else None)
    if dest and is_protected(dest, roots):
        ask(f"this exports into a folder of original photos ({dest})")


def check_mcp(tool, args, roots):
    name = tool[len(MCP_PREFIX):]
    args = args or {}
    if name in UI_TOOLS:
        ask("this drives LightCraft's interface directly (clicks or keys)")
    if name == "import":
        check_import(args)
    elif name == "export":
        check_export(args, roots)
    elif name in ("run_command", "command_run"):
        check_command(args.get("command") or args.get("id"), args.get("params"), roots)
    elif name == "command_batch":
        for step in args.get("steps") or []:
            check_command(step.get("id") or step.get("command"), step.get("params"), roots)
    elif name.startswith("cmd_"):
        # Per-command tools (only listed without --compact): cmd_photo_moveToFolder -> photo.moveToFolder
        check_command(name[4:].replace("_", "."), args, roots)


# ---------------------------------------------------------------- shell

SEPARATORS = re.compile(r"\|\||&&|;|\||\n|&")


def check_bash(command, roots):
    # Checked first: lc.py trash takes a bare shoot name, not a path.
    if re.search(r"lc\.py\s+trash\b", command):
        ask("this moves a shoot folder to the Bin")
    if not mentions_protected(command, roots):
        return
    # fd duplications like 2>&1 or >&2 aren't file writes; drop them before splitting on '&'.
    command = re.sub(r"\d*>&\d+", " ", command)
    for target in re.findall(r"(?<![<\d])>{1,2}\s*([^\s;&|<>]+)", command):
        if is_protected(target.strip("'\""), roots):
            ask("this writes into a folder of original photos")
    for part in SEPARATORS.split(command):
        part = part.strip()
        if not part:
            continue
        try:
            words = shlex.split(part)
        except ValueError:
            ask("this shell command touches a folder of original photos and couldn't be checked")
        while words and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0]) or words[0] in ("sudo", "nohup", "time", "command", "builtin", "exec", "env", "nice")):
            words = words[1:]
        if not words:
            continue
        prog = os.path.basename(words[0])
        if prog.endswith("lc.py") or (prog.startswith("python") and len(words) > 1 and words[1].endswith("lc.py")):
            continue  # LiteCraft's helper only reads protected folders (trash is handled above)
        if prog == "find" and not any(w in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprintf", "-fls") for w in words):
            continue
        if prog == "sips" and "--out" not in words and "-o" not in words and any(w.startswith("-") and w not in ("-g", "--getProperty") for w in words[1:]):
            ask("sips without --out changes the image file itself")
        if prog == "sips":
            continue
        if prog == "xattr" and any(w in ("-w", "-d", "-c", "-r") for w in words[1:]):
            ask("this changes file attributes on original photos")
        if prog in READONLY_PROGRAMS:
            continue
        ask(f"`{prog}` may change or remove files in a folder of original photos")


# ---------------------------------------------------------------- main

def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    tool = data.get("tool_name") or ""
    args = data.get("tool_input") or {}
    roots = protected_roots()
    if tool.startswith(MCP_PREFIX):
        check_mcp(tool, args, roots)
    elif tool == "Bash":
        check_bash(args.get("command") or "", roots)
    elif tool in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        if is_protected(args.get("file_path") or args.get("notebook_path"), roots):
            ask("this writes a file inside a folder of original photos")


if __name__ == "__main__":
    main()
