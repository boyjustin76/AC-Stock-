"""TypeSafe Jev 얇은 클라이언트 — 글을 만들지 않고 **판단만** 받는다.

문서(docs.typesafe.ai) 실측 형식:

    POST https://api.typesafe.ai/v1/systemone
    {"state": "<우리 자료>", "model": "jev-latest",
     "questions": {"<이름>": {"type": "score|choice|noul",
                              "instructions": "<질문>",
                              "criteria": [...] 또는 {이름: 설명}}}}

    응답 {"model": "jev-1.13.0",
          "answers": {"<이름>": {"type": "choice", "choice": "...",
                                 "confidence": 0.95, "probabilities": {...}}}}
      · score  → score(가중평균) · probabilities · confidence · legend
      · choice → choice · probabilities · confidence

키는 `TYPESAFE_API_KEY` (환경변수 또는 `~/.secrets/ac_keys.env`).

**보내지 않는 것**: 미공개 대본·이미지. 이 모델은 텍스트만 받고, 보관은 된다(ZDR 은 기업 고객만).
**시키지 않는 것**: 셈·날짜·좌표. 문서가 못 한다고 적어 둔 것은 코드가 한다.
"""
import json
import os
import urllib.error
import urllib.request

URL = os.environ.get('TYPESAFE_URL', 'https://api.typesafe.ai/v1/systemone')
SECRETS = os.path.join(os.path.expanduser('~'), '.secrets', 'ac_keys.env')
MODEL = os.environ.get('TYPESAFE_MODEL', 'jev-latest')


def key():
    k = os.environ.get('TYPESAFE_API_KEY')
    if k:
        return k
    if os.path.exists(SECRETS):
        for line in open(SECRETS, encoding='utf-8'):
            if line.startswith('TYPESAFE_API_KEY=') and '=' in line:
                return line.split('=', 1)[1].strip()
    raise SystemExit('TYPESAFE_API_KEY 가 없다 — 환경변수나 ~/.secrets/ac_keys.env 에 넣어라')


def choice(instructions, options):
    """options: {이름: 설명} 또는 [이름…]."""
    if isinstance(options, (list, tuple)):
        options = {o: o for o in options}
    return {'type': 'choice', 'instructions': instructions, 'criteria': options}


def score(instructions, criteria):
    """criteria: 낮은 단계부터 높은 단계까지 2~10개."""
    return {'type': 'score', 'instructions': instructions, 'criteria': list(criteria)}


def noul(instructions):
    return {'type': 'noul', 'instructions': instructions}


def ask(state, questions, model=MODEL, timeout=60):
    """한 번에 질문 여러 개(병렬). 돌려주는 것은 응답의 answers."""
    body = {'state': state, 'model': model, 'questions': questions}
    req = urllib.request.Request(
        URL, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key()},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Jev HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}')


def pick(ans, name):
    """답 하나에서 (고른 것, confidence) 만."""
    a = ans['answers'][name]
    if a['type'] == 'choice':
        return a['choice'], a.get('confidence')
    if a['type'] == 'score':
        return a['score'], a.get('confidence')
    return a.get('value', a.get('noul')), a.get('confidence')


if __name__ == '__main__':
    # 붙는지·한국어를 읽는지만 본다 (E 시험 ①과 같은 확인)
    r = ask('이 잡은 컴포지션 20개를 만들고 mogrt 20개를 내보냈다. 오류는 없었다.',
            {'ok': noul('이 로그는 잡이 정상으로 끝났음을 보여 준다'),
             'kind': choice('이 글이 말하는 것은 무엇인가',
                            {'성공': '할 일을 끝냈다', '실패': '중간에 멈췄다', '모름': '알 수 없다'})})
    print(json.dumps(r, ensure_ascii=False, indent=1)[:1200])
