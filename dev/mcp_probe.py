#!/usr/bin/env python3
"""Minimal stdio MCP client for poking at lightcraft-cli during development.

Usage:
  dev/mcp_probe.py [--out DIR] -- <server command...>  < steps.jsonl

Each stdin line is {"tool": name, "args": {...}}. Text results are printed;
image results are saved to --out as <step>.<ext>.
"""
import base64
import json
import os
import subprocess
import sys


def main():
    argv = sys.argv[1:]
    out = "."
    if argv[:1] == ["--out"]:
        out, argv = argv[1], argv[2:]
    if argv[:1] == ["--"]:
        argv = argv[1:]
    os.makedirs(out, exist_ok=True)

    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    next_id = 0

    def call(method, params=None, notify=False):
        nonlocal next_id
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            next_id += 1
            msg["id"] = next_id
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        if notify:
            return None
        while True:
            line = proc.stdout.readline()
            if not line:
                raise SystemExit("server closed stdout")
            reply = json.loads(line)
            if reply.get("id") == next_id:
                return reply

    init = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "mcp_probe", "version": "0"}})
    print("server:", init["result"]["serverInfo"])
    call("notifications/initialized", notify=True)

    for step, line in enumerate(sys.stdin, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        req = json.loads(line)
        reply = call("tools/call", {"name": req["tool"], "arguments": req.get("args", {})})
        result = reply.get("result", {})
        flag = " ERROR" if result.get("isError") or "error" in reply else ""
        print(f"--- {step} {req['tool']}{flag}")
        if "error" in reply:
            print(json.dumps(reply["error"]))
        for item in result.get("content", []):
            if item["type"] == "text":
                text = item["text"]
                print(text if len(text) < 1500 else text[:1500] + " …")
            elif item["type"] == "image":
                ext = item["mimeType"].split("/")[-1]
                path = os.path.join(out, f"{step}-{req['tool']}.{ext}")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(item["data"]))
                print("image ->", path)

    proc.stdin.close()
    proc.wait(timeout=60)


if __name__ == "__main__":
    main()
