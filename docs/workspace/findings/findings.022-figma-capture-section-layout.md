# findings.022 - Figma captureForDesign hang 원인과 Section 배치 패턴

- **날짜**: 2026-03-23
- **태그**: #figma #playwright #captureForDesign #section #layout #dialog #mcp

---

## 요약

19개 HTML 와이어프레임을 Figma에 캡처하고 Section으로 배치하는 과정에서 발견한 6가지 핵심 문제와 해결책.

---

## 1. captureForDesign 이 항상 120s timeout 되는 문제

### 원인

`window.figma.captureForDesign()` 은 내부적으로 두 단계를 수행한다.

1. DOM 직렬화 → `/mcp/capture/{id}/submit` 로 POST (빠름, 보통 5-10초)
2. `/mcp/capture/{id}` 폴링으로 서버 처리 완료 대기 (서버가 404를 반환하므로 무한 대기)

서버가 처리 완료 전까지 status endpoint를 404로 반환하기 때문에 함수가 반환하지 않는다. captureId가 Figma 파일에 노드로 추가된 이후에야 200을 반환한다.

### 해결책: 15s 타임아웃 + POST 관찰

```javascript
let postStatus = null;
page.on('response', resp => {
  if (resp.url().includes('/mcp/capture/') && resp.url().includes('/submit')) {
    postStatus = resp.status();
  }
});

try {
  await page.evaluate(({ captureId, endpoint }) =>
    Promise.race([
      window.figma.captureForDesign({ captureId, endpoint, selector: 'body' }),
      new Promise((_, rej) => setTimeout(() => rej(new Error('timeout 15s')), 15000))
    ]),
    { captureId, endpoint }
  );
  console.log('done within 15s');
} catch (e) {
  if (postStatus !== null) {
    // POST가 전송됐으면 타임아웃이어도 캡처 성공
    console.log(`timed out but POST sent (status=${postStatus})`);
  } else {
    console.error(`ERROR: ${e.message} (no POST observed)`);
  }
}
```

**핵심 판단 기준**: POST response가 관찰됐으면 (200 또는 409) 타임아웃 에러를 무시하고 poll 단계로 진행.

---

## 2. 409 CAPTURE_ID_ALREADY_SUBMITTED

### 원인

`generate_figma_design` 으로 발급한 captureId는 한 번만 제출할 수 있다. 이전 세션에서 발급한 captureId를 재사용하거나, 같은 captureId로 두 번 submit을 시도하면 409가 반환된다.

409 응답 body: `{"success":false,"errorCode":"CAPTURE_ID_ALREADY_SUBMITTED"}`

### 해결책

세션 시작 시 **모든 captureId를 새로 발급**한다. 이전 세션 captureId 재사용 금지.

```
generate_figma_design(outputMode: 'existingFile', fileKey: '...', nodeId: '0:1')
→ 새 captureId 반환
```

- 19프레임 캡처 시 19번 호출해 19개의 captureId를 확보한 뒤 한 번에 실행

---

## 3. Section.resize() is not a function

### 원인

Figma Plugin API에서 `SECTION` 타입 노드는 `resize()` 메서드가 없다.

```javascript
// 실패
section.resize(width, height);  // TypeError: section.resize is not a function

// 성공
section.resizeWithoutConstraints(width, height);
```

`FRAME`, `COMPONENT` 등 다른 컨테이너 타입에는 `resize()` 가 있지만 SECTION에는 없음.

---

## 4. appendChild 후 x/y 설정

### 원인

`section.appendChild(frame)` 를 호출하면 frame의 x/y 좌표가 **section 내부 상대 좌표**로 바뀐다. appendChild 이전에 설정한 절대 좌표는 무의미해진다.

```javascript
// 잘못된 순서
frame.x = 0;
frame.y = 0;
section.appendChild(frame);   // x/y가 내부 좌표로 재계산됨

// 올바른 순서
section.appendChild(frame);   // 먼저 reparent
frame.x = 0;                   // 이후 상대 좌표 설정
frame.y = 0;
```

---

## 5. Dialog / 메뉴 노드 판별 패턴

모바일 레이아웃에는 화면 오른쪽 밖에 위치한 navigation drawer(사이드바 메뉴)가 있다. 이 노드는 캡처된 프레임 하위에 포함되지만 실제 가시 영역 밖에 위치한다.

### 판별 기준

```
노드 이름이 "Dialog" 또는 "Container"
AND
노드의 x >= 부모 프레임의 width
```

이 조건을 충족하면 오버레이 메뉴 노드 - 삭제 대상.

### 예외: 사이드바 프레임 자체

홈 화면 모바일 사이드바는 **별도 프레임**으로 캡처된 화면이다. 이 프레임 내부의 Dialog 노드는 사이드바 콘텐츠 자체이므로 삭제 금지.

```
72:2 (홈 Mobile 사이드바, w:375)
  └── 72:367 (Dialog, x:56) ← 사이드바 내용, 삭제 금지
```

판별식: `x < frame.width` 이면 가시 영역 내부 → 유지.

---

## 6. figma-remote MCP rate limit

### 문제

`figma-remote` MCP (`get_metadata`, `get_design_context` 등) 는 API rate limit이 빠르게 도달한다. 대량 배치 작업 중 `429 Too Many Requests` 또는 timeout 발생.

### 해결책

배치 Figma 조작에는 `figma-console` MCP의 `figma_execute` 를 사용한다.

```javascript
// figma_execute로 직접 Plugin API 실행 (rate limit 없음)
figma_execute({
  code: `
    const page = figma.currentPage;
    const section = page.findOne(n => n.type === 'SECTION' && n.name === '...');
    // ... 배치 조작
  `
})
```

- `figma-remote` MCP: 읽기 전용 메타데이터, 단발성 정보 조회에 적합
- `figma-console` MCP `figma_execute`: 노드 생성/이동/삭제/리사이즈 등 모든 배치 조작에 적합

---

## 전체 캡처 워크플로 (권장)

```
1. 세션 시작 시 captureId 전부 새로 발급 (generate_figma_design x N)

2. Playwright 스크립트 실행
   - capture.js를 한 번 fetch 후 inline inject (async 태그 미사용)
   - 각 프레임: navigate → 2.5s wait → scrollFull → inject → captureForDesign(15s 타임아웃)
   - POST 관찰 → 타임아웃이어도 POST 확인됐으면 성공으로 처리

3. figma_execute로 배치 배치
   - 프레임을 Section에 appendChild (x/y는 반드시 appendChild 이후 설정)
   - Section 리사이즈는 resizeWithoutConstraints 사용
   - Dialog 삭제: x >= parentFrame.width 조건으로 필터

4. 폴링으로 완료 확인 (generate_figma_design(captureId))
```

---

## 참고

- findings.021: Docker Figma HTML 캡처 방법 (browser_run_code + waitForTimeout 패턴)
- 캡처 스크립트: `/tmp/figma_capture_fast.mjs`
- Figma file key: `hnYsCJHxGz63zFW0rxMian` (pyosh 프로젝트)
- 캡처 완료 노드: 70:2 ~ 88:2 (19개 프레임)
