# -*- coding: utf-8 -*-
"""stdio MCP 서버 자가점검 — 띄우고 initialize → tools/list → (선택) tools/call 까지 해 본다.

    python mcp_probe.py "<명령줄>" [도구이름] [인자JSON]
설정 파일에 등록하지 않고 그 자리에서만 띄워 보는 용도다.
"""
import json
import subprocess
import sys
import threading

cmd = sys.argv[1]
tool = sys.argv[2] if len(sys.argv) > 2 else None
args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}

p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
err = []
threading.Thread(target=lambda: [err.append(l) for l in p.stderr], daemon=True).start()


def send(obj):
    p.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
    p.stdin.flush()


def read(timeout=60):
    box = {}

    def rd():
        for line in p.stdout:
            line = line.strip()
            if line.startswith("{"):
                box["v"] = json.loads(line)
                return
    t = threading.Thread(target=rd, daemon=True)
    t.start()
    t.join(timeout)
    return box.get("v")


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "probe", "version": "0"}}})
r = read()
if not r:
    print("initialize 응답 없음. stderr:", "".join(err[-8:])[:800])
    p.kill()
    sys.exit(1)
info = (r.get("result") or {}).get("serverInfo", {})
print("서버:", info.get("name"), info.get("version"), "· 프로토콜", (r.get("result") or {}).get("protocolVersion"))
send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
r = read()
tools = ((r or {}).get("result") or {}).get("tools", [])
print("도구:", [t["name"] for t in tools])
for t in tools:
    print("  -", t["name"], "·", (t.get("description") or "")[:90])
    print("    입력:", json.dumps(t.get("inputSchema", {}).get("properties", {}), ensure_ascii=False)[:200])
if tool:
    send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    r = read(120)
    print("\n호출 결과:", json.dumps(r, ensure_ascii=False)[:1500])
p.kill()
