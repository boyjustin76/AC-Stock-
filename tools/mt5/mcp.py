"""MetaTrader 5 내장 MCP 서버 클라이언트.

MT5 빌드 5955 부터 터미널 안에 MCP 서버가 들어 있다 (도구 > 옵션 > MCP, '내부 서버 활성화').
거기서 주소와 API 키를 보고 아래 환경변수에 넣는다.

    MT5_MCP_URL   기본 http://127.0.0.1:22346/mcp
    MT5_MCP_KEY   API 키 — **저장소에 적지 않는다**. `C:\\Users\\user\\.secrets\\ac_keys.env` 에 둔다.

실측으로 알아낸 규칙 (2026-09-18):
  · 인증은 `Authorization: Bearer <키>` 하나뿐이다. X-API-Key 류는 401 이다.
  · `initialize` 응답의 `Mcp-Session-Id` 헤더를 이후 모든 요청에 실어야 한다.
  · 그 다음 `notifications/initialized` 를 **id 없이**(알림 형식으로) 보내야 세션이 열린다.
    id 를 붙이면 서버가 요청으로 보고 `MCP session is not initialized` 를 돌려준다.

거래 도구(trade_*)는 부르지 않는다. 우리 일은 화면과 값을 읽는 것뿐이다.
"""
import json
import os
import urllib.error
import urllib.request

SECRETS = os.path.join(os.path.expanduser('~'), '.secrets', 'ac_keys.env')


def _key():
    k = os.environ.get('MT5_MCP_KEY')
    if k:
        return k
    if os.path.exists(SECRETS):
        for line in open(SECRETS, encoding='utf-8'):
            if line.startswith('MT5_MCP_KEY=') and '=' in line:
                return line.split('=', 1)[1].strip()
    raise SystemExit('MT5_MCP_KEY 가 없다 — 환경변수나 ~/.secrets/ac_keys.env 에 넣어라')


class MT5:
    def __init__(self, url=None, key=None):
        self.url = url or os.environ.get('MT5_MCP_URL', 'http://127.0.0.1:22346/mcp')
        self.key = key or _key()
        self.sid = None
        hdr, _ = self._post('initialize', {
            'protocolVersion': '2025-06-18', 'capabilities': {},
            'clientInfo': {'name': 'chartmyeongga', 'version': '1.0'}}, mid=1)
        self.sid = hdr.get('Mcp-Session-Id') or hdr.get('mcp-session-id')
        self._post('notifications/initialized', {}, mid=None)   # id 없이 — 위 설명 참고

    def _post(self, method, params=None, mid=1):
        body = {'jsonrpc': '2.0', 'method': method}
        if mid is not None:
            body['id'] = mid
        if params is not None:
            body['params'] = params
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json, text/event-stream',
                   'Authorization': 'Bearer ' + self.key}
        if self.sid:
            headers['Mcp-Session-Id'] = self.sid
        req = urllib.request.Request(self.url, data=json.dumps(body).encode('utf-8'),
                                     headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode('utf-8', 'replace')
                return dict(r.headers), (json.loads(raw) if raw.strip() else {})
        except urllib.error.HTTPError as e:
            raise SystemExit(f'MCP {method} 실패: HTTP {e.code} '
                             f'{e.read().decode("utf-8", "replace")[:200]}')

    def tools(self):
        return self._post('tools/list', {}, 3)[1].get('result', {}).get('tools', [])

    def call(self, name, args=None):
        """도구를 부르고 본문(JSON 문자열)을 파싱해 돌려준다."""
        r = self._post('tools/call', {'name': name, 'arguments': args or {}}, 4)[1]
        res = r.get('result', {})
        if res.get('isError'):
            raise SystemExit(f'{name} 오류: {res}')
        text = res['content'][0]['text']
        try:
            return json.loads(text)
        except ValueError:
            return text

    def open_charts(self):
        return self.call('list_open_charts')['charts']

    def history(self, symbol, period, dt_from, dt_to, limit=5000):
        return self.call('get_chart_history', {
            'symbol': symbol, 'period': period, 'datetime_from': dt_from,
            'datetime_to': dt_to, 'limit': limit})['history']


if __name__ == '__main__':
    m = MT5()
    for c in m.open_charts():
        print(f"{c['symbol']} {c['period']} · 보이는 봉 {c['page_bars']} · "
              f"창 {c['rect_right']}x{c['rect_bottom']} · 지표 {len(c['indicators'])}개")
    print(f'도구 {len(m.tools())}개')
