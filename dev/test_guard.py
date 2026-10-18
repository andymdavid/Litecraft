#!/usr/bin/env python3
"""Table test for plugin/hooks/guard.py: which tool calls must ask the user, which pass.

Run: python3 dev/test_guard.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "plugin", "hooks", "guard.sh")
MCP = "mcp__plugin_litecraft_lightcraft__"


def run(home, tool, tool_input, cwd=None):
    env = dict(os.environ, LITECRAFT_HOME=home)
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": cwd or os.path.dirname(home)}
    r = subprocess.run(["/bin/bash", GUARD], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, timeout=20)
    if r.returncode != 0:
        return f"error {r.returncode}: {r.stderr.strip()}"
    if not r.stdout.strip():
        return "pass"
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        home = os.path.join(tmp, "LiteCraft")
        shoots = os.path.join(home, "Shoots")
        elsewhere = os.path.join(tmp, "Clients", "Beach House")
        os.makedirs(os.path.join(shoots, "Smith Kitchen"))
        os.makedirs(elsewhere)
        os.makedirs(os.path.join(home, "Jobs", "Beach House"))
        with open(os.path.join(home, "Jobs", "Beach House", "job.json"), "w") as f:
            json.dump({"name": "Beach House", "source": elsewhere}, f)
        sk = os.path.join(shoots, "Smith Kitchen")
        export = os.path.join(home, "Jobs", "Smith Kitchen", "export")
        lc = "/x/plugins/cache/litecraft/litecraft/0.1.0/scripts/lc.py"
        previews = os.path.join(home, "Jobs", "Smith Kitchen", "previews")
        user_home = os.path.dirname(home)   # the session's working folder in these tests

        cases = [
            # --- LightCraft: normal editing passes
            ("pass", MCP + "set_develop", {"values": {"light.exposure": 0.5}}),
            ("pass", MCP + "render_photo", {"id": 3, "size": 1200}),
            ("pass", MCP + "import", {"paths": [sk], "mode": "add", "album": 1}),
            ("pass", MCP + "import", {"paths": ["/Volumes/EOS_DIGITAL/DCIM"], "mode": "copy", "destination": sk}),
            ("pass", MCP + "export", {"ids": [1], "dir": export, "format": "jpeg"}),
            ("pass", MCP + "run_command", {"command": "photo.label", "params": {"label": "green"}}),
            ("pass", MCP + "run_command", {"command": "photo.delete", "params": {"ids": [3]}}),
            ("pass", MCP + "run_command", {"command": "library.xmpPreferences", "params": {}}),
            # --- LightCraft: anything that moves, renames, overwrites or writes beside originals asks
            ("ask", MCP + "import", {"paths": ["/Volumes/EOS_DIGITAL/DCIM"], "mode": "move", "destination": sk}),
            ("ask", MCP + "run_command", {"command": "library.import", "params": {"paths": [sk], "mode": "move"}}),
            ("ask", MCP + "run_command", {"command": "photo.moveToFolder", "params": {"folder": "/tmp"}}),
            ("ask", MCP + "run_command", {"command": "photo.rename", "params": {"template": "{date}"}}),
            ("ask", MCP + "command_run", {"id": "folder.rename", "params": {"path": sk, "name": "x"}}),
            ("ask", MCP + "command_batch", {"steps": [{"id": "photo.label", "params": {}}, {"id": "folder.move", "params": {}}]}),
            ("ask", MCP + "cmd_photo_moveToFolder", {"folder": "/tmp"}),
            ("ask", MCP + "run_command", {"command": "photo.saveMetadataToFile", "params": {}}),
            ("ask", MCP + "run_command", {"command": "library.xmpPreferences", "params": {"autoWrite": True}}),
            ("ask", MCP + "export", {"ids": [1], "dir": export, "conflict": "overwrite"}),
            ("ask", MCP + "export", {"ids": [1], "dir": sk}),
            ("ask", MCP + "export", {"ids": [1], "path": os.path.join(elsewhere, "a.jpg")}),
            ("ask", MCP + "run_command", {"command": "app.export", "params": {"dir": "/Volumes/EOS_DIGITAL"}}),
            ("ask", MCP + "press_key", {"key": "Delete"}),
            ("ask", MCP + "click", {"widget": "x"}),
            # --- Shell: reading protected folders passes
            ("pass", "Bash", {"command": f"ls -la '{sk}'"}),
            ("pass", "Bash", {"command": f"du -sh '{sk}' 2>/dev/null"}),
            ("pass", "Bash", {"command": f"find '{sk}' -name '*.CR3' | wc -l"}),
            ("pass", "Bash", {"command": f"{lc} source '{sk}' --job 'Smith Kitchen'"}),
            ("pass", "Bash", {"command": f"{lc} job new 'Beach House 2' --source '{elsewhere}' 2>&1"}),
            ("pass", "Bash", {"command": f"sips -g pixelWidth '{sk}/IMG_1.CR3'"}),
            ("pass", "Bash", {"command": "rm -rf /tmp/scratch-render"}),          # not a protected folder
            ("pass", "Bash", {"command": f"open '{export}'"}),
            # --- Shell: changing protected folders asks
            ("ask", "Bash", {"command": f"rm -rf '{sk}'"}),
            ("ask", "Bash", {"command": f"mv '{elsewhere}/IMG_1.CR3' /tmp/"}),
            ("ask", "Bash", {"command": f"cd '{sk}' && rm *.CR3"}),
            ("ask", "Bash", {"command": f"find '{sk}' -name '*.JPG' -delete"}),
            ("ask", "Bash", {"command": f"sips -Z 2000 '{sk}/IMG_1.jpg'"}),
            ("ask", "Bash", {"command": f"echo hi > '{sk}/note.txt'"}),
            ("ask", "Bash", {"command": f"cp /tmp/a.CR3 '{sk}/IMG_1.CR3'"}),
            ("ask", "Bash", {"command": "rm -rf ~/LiteCraft/Shoots/Smith\\ Kitchen".replace("~/LiteCraft", home)}),
            ("ask", "Bash", {"command": "mv /Volumes/EOS_DIGITAL/DCIM/100CANON/IMG_1.CR3 ~/Desktop"}),
            ("ask", "Bash", {"command": f"{lc} trash 'Smith Kitchen'"}),
            ("ask", "Bash", {"command": f"python3 -c \"import shutil; shutil.rmtree('{sk}')\""}),
            # --- Write targets on LightCraft tools and commands
            ("pass", MCP + "render_photo", {"id": 3, "size": 1200, "path": os.path.join(previews, "3.jpg")}),
            ("pass", MCP + "render_photo", {"id": 3, "size": 800, "path": "/tmp/render.jpg"}),
            ("ask", MCP + "render_photo", {"id": 3, "path": os.path.join(sk, "IMG_1.CR3")}),
            ("ask", MCP + "render_photo", {"id": 3, "path": os.path.join(elsewhere, "IMG_1.jpg")}),
            ("ask", MCP + "screenshot", {"path": os.path.expanduser("~/Library/LaunchAgents/x.png")}),
            ("pass", MCP + "run_command", {"command": "preset.export", "params": {"path": os.path.join(home, "presets", "look.lcpreset")}}),
            ("ask", MCP + "run_command", {"command": "preset.export", "params": {"path": os.path.expanduser("~/.zshrc")}}),
            ("ask", MCP + "run_command", {"command": "export.contactSheet", "params": {"path": os.path.join(sk, "sheet.pdf")}}),
            ("ask", MCP + "run_command", {"command": "photo.editExternal", "params": {"ids": [1]}}),
            ("pass", MCP + "run_command", {"command": "photo.editExternal", "params": {"ids": [1], "dir": export}}),
            ("ask", MCP + "run_command", {"command": "photo.convertToDng", "params": {"ids": [1]}}),
            ("ask", MCP + "run_command", {"command": "photo.duplicate", "params": {"ids": [1]}}),
            ("ask", MCP + "run_command", {"command": "merge.hdrBatch", "params": {"ids": [1, 2, 3]}}),
            ("ask", MCP + "import", {"paths": ["/Volumes/EOS_DIGITAL/DCIM"], "mode": "copy", "destination": os.path.expanduser("~/Documents/x")}),
            ("ask", MCP + "export", {"ids": [1], "dir": os.path.expanduser("~/Documents/Elsewhere")}),
            # --- Shell: relative paths, cd, write-capable "read" tools, LiteCraft config
            ("ask", "Bash", {"command": "rm -rf LiteCraft/Shoots/Smith\\ Kitchen"}, user_home),
            ("ask", "Bash", {"command": "cd LiteCraft/Shoots && rm -r 'Smith Kitchen'"}, user_home),
            ("ask", "Bash", {"command": "mv IMG_1.CR3 /tmp/"}, sk),
            ("pass", "Bash", {"command": "ls -la"}, sk),
            ("ask", "Bash", {"command": f"exiftool -Artist=x -overwrite_original '{sk}/IMG_1.CR3'"}),
            ("pass", "Bash", {"command": f"exiftool -s -Model '{sk}/IMG_1.CR3'"}),
            ("ask", "Bash", {"command": f"sort -o '{sk}/list.txt' /tmp/a"}),
            ("ask", "Bash", {"command": f"{lc} env init --cli /tmp/x --app /tmp/y"}),
            ("ask", "Bash", {"command": f"{lc} permissions sync"}),
            ("ask", "Bash", {"command": f"{lc} permissions remove"}),
            ("pass", "Bash", {"command": f"{lc} permissions show"}),
            ("pass", "Bash", {"command": f"{lc} prefs set crop.landscape 4:5"}),
            ("pass", "Bash", {"command": "git status && npm test 2>&1 | tail -5"}),
            # --- File tools
            ("ask", "Write", {"file_path": os.path.join(sk, "x.txt"), "content": "x"}),
            ("ask", "Edit", {"file_path": os.path.join(elsewhere, "x.xmp"), "old_string": "a", "new_string": "b"}),
            ("pass", "Write", {"file_path": os.path.join(home, "Jobs", "Smith Kitchen", "notes.txt"), "content": "x"}),
            ("pass", "Read", {"file_path": os.path.join(sk, "IMG_1.CR3")}),
        ]
        failures = 0
        for case in cases:
            expected, tool, tool_input = case[:3]
            got = run(home, tool, tool_input, case[3] if len(case) > 3 else None)
            ok = got == expected
            failures += not ok
            label = tool.replace(MCP, "lightcraft:")
            detail = tool_input.get("command") if isinstance(tool_input.get("command"), str) else json.dumps(tool_input)[:90]
            print(f"{'ok  ' if ok else 'FAIL'} {expected:4} {got:5} {label:24} {detail.replace(tmp, '$TMP')[:100]}")
        print(f"\n{len(cases) - failures}/{len(cases)} passed")
        sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
