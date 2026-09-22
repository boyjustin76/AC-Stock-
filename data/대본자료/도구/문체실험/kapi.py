# -*- coding: utf-8 -*-
"""한국어 대형 모델 두 곳을 부르는 얇은 층. 키는 ~/.secrets/ac_keys.env 에서만 읽고 출력하지 않는다."""
import io, os, json, ssl, uuid, urllib.request, urllib.error
import certifi

CTX = ssl.create_default_context(cafile=certifi.where())


def keys():
    d = {}
    for line in io.open(os.path.expanduser("~/.secrets/ac_keys.env"), encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            d[k.strip()] = v.strip()
    return d


K = keys()


def _post(url, body, headers, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP %d %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))


def clova(messages, model="HCX-005", temperature=0.0, max_tokens=50):
    r = _post("https://clovastudio.stream.ntruss.com/v3/chat-completions/%s" % model,
              {"messages": messages, "temperature": temperature, "maxTokens": max_tokens},
              {"Authorization": "Bearer " + K["CLOVA_STUDIO_API_KEY"],
               "X-NCP-CLOVASTUDIO-REQUEST-ID": uuid.uuid4().hex, "Content-Type": "application/json"})
    return r["result"]["message"]["content"]


def upstage(messages, model="solar-pro2", temperature=0.0, max_tokens=50):
    r = _post("https://api.upstage.ai/v1/chat/completions",
              {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
              {"Authorization": "Bearer " + K["UPSTAGE_API_KEY"], "Content-Type": "application/json"})
    return r["choices"][0]["message"]["content"]


def upstage_models():
    req = urllib.request.Request("https://api.upstage.ai/v1/models", headers={"Authorization": "Bearer " + K["UPSTAGE_API_KEY"]})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        return [m["id"] for m in json.loads(r.read().decode("utf-8")).get("data", [])]


if __name__ == "__main__":
    msg = [{"role": "user", "content": "'네' 한 글자로만 답하세요."}]
    for 이름, f in [("CLOVA HCX-005", lambda: clova(msg)), ("CLOVA HCX-007", lambda: clova(msg, "HCX-007")),
                    ("CLOVA HCX-DASH-002", lambda: clova(msg, "HCX-DASH-002"))]:
        try: print("%-20s OK  → %r" % (이름, f()[:20]))
        except Exception as e: print("%-20s 실패 %s" % (이름, str(e)[:160]))
    try:
        ms = upstage_models(); print("Upstage 모델:", [m for m in ms if "solar" in m][:15])
    except Exception as e: print("Upstage 목록 실패", str(e)[:160]); ms = []
    for m in [x for x in ("solar-pro3", "solar-pro2", "solar-mini") if not ms or x in ms][:2]:
        try: print("%-20s OK  → %r" % ("Upstage " + m, upstage(msg, m)[:20]))
        except Exception as e: print("%-20s 실패 %s" % ("Upstage " + m, str(e)[:160]))
