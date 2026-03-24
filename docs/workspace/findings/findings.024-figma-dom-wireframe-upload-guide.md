# Findings 024 - HTML 와이어프레임을 Figma에 DOM 방식으로 업로드하는 가이드

- **날짜**: 2026-03-25
- **태그**: #figma #playwright #html-to-design #dom-capture #wireframe #mcp #admin

## 요약

로컬 HTML 와이어프레임 파일을 PNG 스크린샷이 아닌 DOM 기반으로 Figma에 임포트하는 전체 워크플로. `mcp__figma-remote__generate_figma_design` + Playwright MCP 조합으로 디자인 토큰/레이어가 포함된 Figma 프레임을 생성한다.

---

## 1. 전제 조건

| 항목 | 내용 |
|------|------|
| MCP 서버 | `figma-remote`, `figma-console`, `plugin_playwright` 세 가지 모두 필요 |
| HTTP 서버 | 로컬 HTML은 `file://` 프로토콜 불가 - 반드시 HTTP 서버로 서빙 |
| Figma 파일 | 대상 fileKey와 삽입할 nodeId 사전 확인 |

### HTTP 서버 시작

```bash
cd /workspace/.workspace/design
python3 -m http.server 8899 &
# 또는 백그라운드로 유지
```

서버 확인: `curl -s http://127.0.0.1:8899/` 로 응답 여부 체크.

---

## 2. 전체 흐름

```
1. 기존 프레임 삭제 (재업로드 시)
2. generate_figma_design → captureId 발급
3. browser_resize → viewport 설정 (Desktop: 1440×900, Mobile: 375×812)
4. browser_run_code → 페이지 준비 + captureForDesign 실행 (fire-and-forget)
5. generate_figma_design(captureId) → polling 완료 확인
6. 다음 페이지로 반복
```

---

## 3. captureId 발급

```
mcp__figma-remote__generate_figma_design({
  outputMode: "existingFile",
  fileKey: "<FIGMA_FILE_KEY>",
  nodeId: "<TARGET_NODE_ID>"
})
```

- `outputMode: "existingFile"` → 기존 파일에 추가
- `nodeId` → 삽입 대상 페이지/프레임 노드 ID (Figma URL의 `node-id` 파라미터)
- 반환값: `captureId` (UUID)
- **단일 사용**: 하나의 captureId는 하나의 페이지에만 사용 가능. 재사용 시 409 에러

---

## 4. Playwright 캡처 스크립트 - 핵심 패턴

### viewport 설정

```
mcp__plugin_playwright_playwright__browser_resize({ width: 1440, height: 900 })  // Desktop
mcp__plugin_playwright_playwright__browser_resize({ width: 375, height: 812 })   // Mobile
```

### browser_run_code 코드 구조

```javascript
async (page) => {
  // 1. CSP 헤더 제거 (로컬 서버에서도 필요)
  await page.route('**/*', async (route) => {
    const response = await route.fetch();
    const headers = { ...response.headers() };
    delete headers['content-security-policy'];
    delete headers['content-security-policy-report-only'];
    await route.fulfill({ response, headers });
  });

  // 2. 페이지 로드
  await page.goto('http://127.0.0.1:8899/admin/<PAGE>.html', { waitUntil: 'networkidle' });

  // 3. Light 모드 강제 + 사이드바/모달 닫기
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'light');

    // Mobile: 사이드바 닫기
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.remove('open');
    const backdrop = document.getElementById('sidebar-backdrop') || document.querySelector('.sidebar-backdrop');
    if (backdrop) { backdrop.style.display = 'none'; backdrop.classList.remove('active'); }

    // 모달이 기본 open인 페이지 (category, asset, comment, guestbook)
    document.querySelectorAll('.modal, [class*="modal"], [id*="modal"]').forEach(el => {
      el.style.display = 'none';
      el.classList.remove('active', 'open', 'show');
    });
    document.querySelectorAll('.modal-backdrop, .overlay, [class*="backdrop"]').forEach(el => {
      el.style.display = 'none';
      el.classList.remove('active', 'show');
    });
    document.body.style.overflow = 'auto';
  });

  // 4. 전체 스크롤 - IntersectionObserver lazy rendering 트리거
  await page.evaluate(async () => {
    await new Promise(resolve => {
      let totalHeight = 0;
      const distance = 300;
      const timer = setInterval(() => {
        window.scrollBy(0, distance);
        totalHeight += distance;
        if (totalHeight >= document.body.scrollHeight) {
          clearInterval(timer);
          window.scrollTo(0, 0);
          resolve();
        }
      }, 100);
    });
  });
  await page.waitForTimeout(1500);

  // 5. capture.js 주입
  const r = await page.context().request.get('https://mcp.figma.com/mcp/html-to-design/capture.js');
  const captureScript = await r.text();
  await page.evaluate((s) => {
    const el = document.createElement('script');
    el.textContent = s;
    document.head.appendChild(el);
  }, captureScript);
  await page.waitForTimeout(500);

  // 6. captureForDesign - FIRE AND FORGET (절대 await 하지 말 것)
  await page.evaluate(() => {
    window.figma.captureForDesign({
      captureId: '<CAPTURE_ID>',
      endpoint: 'https://mcp.figma.com/mcp/capture/<CAPTURE_ID>/submit',
      selector: 'body'
    });
  });

  // 7. 제출 시작을 위한 brief wait 후 즉시 반환
  await page.waitForTimeout(3000);
  return 'capture submitted';
}
```

---

## 5. CRITICAL - fire-and-forget 패턴

**`captureForDesign`을 절대 `await` 하거나 `return` 하지 말 것.**

| 방식 | 결과 |
|------|------|
| `return await page.evaluate(() => window.figma.captureForDesign(...))` | **20분+ hang** - DOM 직렬화 + 서버 전송 동안 browser_run_code 전체 블로킹 |
| `await page.evaluate(() => { window.figma.captureForDesign(...); })` | **즉시 반환** - 백그라운드에서 전송 계속 |

`page.evaluate()` 콜백이 Promise를 return하면 Playwright가 그 Promise를 기다린다. `captureForDesign()`은 DOM 직렬화 + 네트워크 전송으로 오래 걸리므로 반환값을 무시해야 한다.

---

## 6. Polling - 완료 확인

`browser_run_code`가 'capture submitted'를 반환한 즉시 polling 시작:

```
generate_figma_design({ captureId: "<ID>" })
```

- 상태 `processing` → 5초 후 재시도
- 상태 `completed` → 완료. 반환된 `node-id` 기록

**주의**: 이전 세션에서 이미 완료된 captureId도 polling으로 확인 가능. browser_run_code가 hang/interrupt 되어도 서버 쪽 처리는 계속 진행됨 - 항상 polling으로 먼저 확인할 것.

---

## 7. 페이지별 주의사항

### 모달이 기본 open인 페이지

다음 페이지는 HTML 로드 시 모달이 열려있다. 위 스크립트의 modal 닫기 코드가 필수:

- `admin-category.html` - 카테고리 추가 모달
- `admin-asset.html` - 에셋 상세 모달
- `admin-comment.html` - 댓글 스레드 모달
- `admin-guestbook.html` - 방명록 상세 모달

### Mobile 사이드바

모든 페이지에서 Mobile(375px) 캡처 시 사이드바 오버레이가 열린 상태일 수 있다. `#sidebar` 클래스에서 `open` 제거 + backdrop 숨김 처리 필수.

### IntersectionObserver lazy rendering

와이어프레임은 스크롤 시 요소가 fade-in되는 staggered animation을 사용한다. 스크롤 없이 캡처하면 뷰포트 아래 요소들이 `opacity: 0` 상태로 캡처된다. 전체 스크롤 → 맨 위 복귀 → 1.5초 대기 패턴으로 해결.

---

## 8. 기존 프레임 삭제

재업로드 전 기존 프레임을 모두 삭제하려면 `figma_execute` 사용:

```javascript
// figma_execute로 실행
const adminPage = figma.root.children.find(p => p.name === 'Admin');
if (!adminPage) throw new Error('Admin page not found');
const frames = adminPage.children.filter(n => n.type === 'FRAME');
const deleted = frames.map(f => f.name);
frames.forEach(f => f.remove());
return { deleted: deleted.length, names: deleted };
```

**주의**: `figma-remote` MCP는 rate limit이 빠르다. 노드 조회/삭제 같은 배치 작업은 `figma-console`의 `figma_execute`로 Plugin API를 직접 실행하는 것이 안전하다.

---

## 9. 전체 캡처 체크리스트

각 HTML 파일당 Desktop + Mobile 2회 캡처:

```
□ generate_figma_design(existingFile, fileKey, nodeId) → captureId 발급
□ browser_resize(1440×900)
□ browser_run_code: goto → light mode → 스크롤 → inject → fire-and-forget captureForDesign
□ generate_figma_design(captureId) → polling 완료
□ generate_figma_design(existingFile, fileKey, nodeId) → 새 captureId 발급
□ browser_resize(375×812)
□ browser_run_code: goto → light mode + sidebar close → 스크롤 → inject → fire-and-forget
□ generate_figma_design(captureId) → polling 완료
```

---

## 10. 결과 예시 (Admin 와이어프레임 - 2026-03-25)

| 페이지 | Desktop node-id | Mobile node-id |
|--------|----------------|----------------|
| Login | 106-2 | 108-2 |
| Dashboard | 110-2 | 111-2 |
| Post List | 112-2 | 113-2 |
| Post Editor | 114-2 | 115-2 |
| Category | 116-2 | 117-2 |
| Asset | 118-2 | 119-2 |
| Comment | 120-2 | 121-2 |
| Guestbook | 122-2 | 123-2 |

파일: `https://www.figma.com/design/hnYsCJHxGz63zFW0rxMian/pyosh` Admin 페이지 (27:725)

---

## 관련 findings

- findings.021 - Docker headless 환경 Figma 캡처 기본 패턴
- findings.022 - captureForDesign hang 원인, Section 배치, Dialog 판별
- findings.023 - color-mix() 미해석, inline 요소 높이 불일치
