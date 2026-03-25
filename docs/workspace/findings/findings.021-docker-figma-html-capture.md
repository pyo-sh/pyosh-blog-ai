# findings.021 - Docker 환경에서 HTML → Figma 캡처 방법

- **날짜**: 2026-03-20
- **태그**: #figma #playwright #docker #html-to-design #capture #mcp

---

## 요약

Docker 컨테이너 안에서 로컬 HTML 파일을 Figma로 업로드하는 방법을 실험적으로 확립했다.
`browser_run_code` + `waitForTimeout(8000)` 조합이 유일하게 안정적으로 작동한다.

---

## 환경

- Docker 컨테이너 (headless, 디스플레이 없음)
- Playwright MCP (`@playwright/mcp@latest`, npx 실행)
- Chromium: `/opt/ms-playwright/chromium-1208/chrome-linux/chrome`
- Python 3: 호스트 네트워크 스택으로 `mcp.figma.com` 접근 가능
- Chromium: `fetch()` GET/POST 모두 `mcp.figma.com` 접근 가능 (확인됨)

---

## 사전 조건

### 1. Chromium 권한 수정 (최초 1회)

```bash
sudo chmod 777 /opt/ms-playwright
```

Playwright MCP가 `/opt/ms-playwright/__dirlock` 파일을 생성해야 하는데, 기본 소유자가 `root`라 쓰기 권한이 없어 브라우저 실행이 실패한다.

### 2. 로컬 HTTP 서버 실행

```bash
cd /workspace   # HTML 파일이 있는 디렉토리
python3 -m http.server 8765 > /tmp/http-server.log 2>&1 &
```

`file://` URL은 Figma 캡처 도구가 지원하지 않으므로 반드시 `http://localhost` 로 서빙해야 한다.

### 3. HTML에 capture.js 포함

```html
<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script>
```

`async` 속성 때문에 스크립트가 DOM ready 이후 로드된다. 이 지연을 반드시 고려해야 한다.

---

## 작동하는 절차

### Step 1: captureId 발급

```
generate_figma_design(
  outputMode: 'existingFile',
  fileKey: '{figma-file-key}',
  nodeId: '0:1'     // 파일 루트 페이지
)
→ captureId: '{uuid}'
```

- `fileKey`: Figma URL `figma.com/design/{fileKey}/...` 에서 추출
- `nodeId`: `0:1` 은 Page 1 루트. 특정 페이지에 추가하려면 해당 node-id 사용

### Step 2: browser_run_code 단일 호출

```javascript
async (page) => {
  await page.goto(
    'http://localhost:8765/{file}.html' +
    '#figmacapture={captureId}' +
    '&figmaendpoint=https%3A%2F%2Fmcp.figma.com%2Fmcp%2Fcapture%2F{captureId}%2Fsubmit' +
    '&figmadelay=1000'
  );
  await page.waitForTimeout(8000);
  return { url: page.url() };
}
```

**8000ms 대기 이유:**
1. `async` capture.js 로드: ~1-2초
2. `window.figma` 초기화 및 hash 파싱: ~0.5초
3. `figmadelay=1000`: 1초 대기 후 캡처 시작
4. DOM 직렬화 (복잡한 와이어프레임): ~2-3초
5. POST 전송 및 서버 응답: ~1초

**중요**: 이 호출 중에 다른 browser_* 도구를 절대 실행하지 말 것. 컨텍스트 방해로 캡처가 실패한다.

### Step 3: poll

```
generate_figma_design(captureId: '{captureId}')
→ 5초 간격, 최대 10회 반복
→ status: 'completed' 확인
```

완료 시 Figma 파일에 새 프레임이 추가된 URL이 반환된다.

---

## 실패하는 방법들

| 방법 | 실패 이유 |
|------|-----------|
| `browser_navigate` + 즉시 poll | `async` 스크립트 로드 + DOM 직렬화 완료 전에 poll. captureId가 pending 상태 유지 |
| `browser_navigate` → `browser_take_screenshot` → poll | screenshot 호출이 페이지 컨텍스트를 방해해 캡처 중단 |
| `browser_navigate` → `browser_evaluate` → poll | evaluate 호출이 타이밍 방해 |
| `window.figma.captureForDesign()` 직접 호출 | capture.js의 내부 상태 초기화 전 호출 시 internal error |
| `xdg-open` (Step 1B 공식 방법) | Docker 컨테이너에 디스플레이 없음 |
| `fetch('https://mcp.figma.com', { method: 'HEAD' })` | 서버가 HEAD/root 미지원 → ERR_FAILED (네트워크 이상이 아님) |
| Step 1A `page.route` 프록시 방식 | 불필요 - Chromium이 mcp.figma.com에 직접 접근 가능하므로 과도한 방식 |

---

## 네트워크 진단 결과

처음에 `fetch('https://mcp.figma.com', { method: 'HEAD' })`가 `ERR_FAILED`를 반환해 Docker 네트워크 차단으로 오판했다. 실제로는:

| 레이어 | mcp.figma.com 접근 | 비고 |
|--------|-------------------|------|
| Python `urllib` | ✅ | DNS + TLS + HTTP 모두 정상 |
| Playwright `context.request.get()` | ✅ | Node.js 네트워크 스택 |
| Chromium `fetch()` GET/POST | ✅ | capture.js, submit endpoint 모두 접근 가능 |
| Chromium `fetch()` HEAD to root | ❌ `ERR_FAILED` | 서버 제한, 네트워크 문제 아님 |

Chromium 네트워크 자체는 정상이며, 실패 원인은 항상 타이밍 문제였다.

---

## 중복 프레임 주의

같은 파일에 여러 번 캡처를 시도하면 동일한 프레임이 canvas에 나란히 쌓인다.
성공한 captureId가 여러 개면 Figma에서 오래된 것을 수동으로 삭제해야 한다.
각 프레임은 node-id로 구분되므로 (예: `9:2`, `10:2`) Figma URL에서 확인 가능하다.

---

## 참고

- Figma file key: `hnYsCJHxGz63zFW0rxMian` (pyosh 프로젝트)
- 와이어프레임 소스: `/workspace/wireframe-home.html`
- Figma 캡처 완료 URL: `https://www.figma.com/design/hnYsCJHxGz63zFW0rxMian?node-id=10-2`
