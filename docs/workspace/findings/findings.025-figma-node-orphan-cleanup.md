# Findings 025 - Figma plugin node orphan 방지 패턴

- **날짜**: 2026-03-25
- **태그**: #figma #figma-execute #node-lifecycle #orphan #try-catch #plugin-api

## 요약

`figma.createFrame()` 등 Figma Plugin API 생성 함수는 호출 즉시 **페이지 루트에 노드를 등록**한다. `figma_execute` 스크립트가 중간에 실패하면 생성된 노드가 루트에 고아(orphan)로 남는다. 2026-03-20 세션에서 4개의 orphan 노드가 발생한 사례를 바탕으로 안전한 노드 생성 패턴을 정리한다.

---

## 문제 원인

Figma Plugin API에서 `figma.createFrame()` / `figma.createText()` 등의 생성 함수는 `appendChild()` 를 호출하기 전까지 노드를 **페이지 루트**에 둔다. `figma_execute` 스크립트가 생성 후 append 전에 오류로 중단되면 노드가 루트에 고아 상태로 잔류한다.

```
페이지 루트
  ├── 의도한 프레임 (Section 내부)
  ├── [orphan] Container   ← createFrame() 후 appendchild() 전에 실패
  ├── [orphan] 태그        ← createText() 후 appendchild() 전에 실패
  └── ...
```

2026-03-20 세션에서 4개의 orphan 노드 (`Container`, `태그` 등)가 Page 1 루트에 누적됐다.

---

## 해결 패턴

### 1. clone 우선 - create 는 최후 수단

기존 노드와 동일한 구조가 필요하다면 `create` 대신 `clone()` 을 사용한다. clone은 부모를 그대로 상속하므로 루트 등록 문제가 발생하지 않는다.

```javascript
// 기존 템플릿 노드를 복제
const template = figma.currentPage.findOne(n => n.name === 'Template');
const copy = template.clone(); // 부모 유지, 루트 등록 없음
copy.name = 'New Item';
```

### 2. 생성 즉시 appendChild

노드를 생성한 뒤 프로퍼티 설정 전에 **반드시 target parent에 먼저 append** 한다.

```javascript
const frame = figma.createFrame();
parent.appendChild(frame);  // 생성 직후, 프로퍼티 설정 전에 append
frame.resize(400, 300);     // append 이후에 설정
frame.name = 'MyFrame';
```

### 3. try/catch + 생성 목록 롤백

여러 노드를 생성하는 스크립트는 생성된 노드를 배열로 추적하고, catch 블록에서 전량 제거한다.

```javascript
const created = [];
try {
  const frame = figma.createFrame();
  created.push(frame);
  parent.appendChild(frame);

  const label = figma.createText();
  created.push(label);
  frame.appendChild(label);

  // ... 이후 작업
} catch (e) {
  created.forEach(n => {
    try { n.remove(); } catch (_) {}
  });
  throw e;
}
```

### 4. 사후 audit

`figma_execute` 실행 후 페이지 루트의 직계 자식을 확인해 orphan 노드를 제거한다.

```javascript
// 루트 자식 중 Section이 아닌 노드 = orphan 후보
const orphans = figma.currentPage.children.filter(
  n => n.type !== 'SECTION' && n.type !== 'FRAME'
);
orphans.forEach(n => n.remove());
```

실제 의도한 최상위 노드 타입(`SECTION`, `FRAME` 등)을 화이트리스트로 정의하고, 해당 타입이 아닌 노드를 orphan으로 처리한다.

### 5. 배치 생성 금지 - 하나씩 생성 후 즉시 attach

"10개 생성 → 10개 이동" 패턴은 생성-이동 사이에 오류가 발생하면 대량 orphan을 유발한다. 반드시 생성 1건 → attach 1건 순서를 유지한다.

---

## 원칙 요약

| 규칙 | 이유 |
|------|------|
| clone 우선 | 루트 등록 없이 부모 상속 |
| 생성 즉시 appendChild | 루트 체류 시간 0으로 단축 |
| try/catch 롤백 | 오류 시 orphan 자동 제거 |
| 사후 audit | 누락된 orphan 사후 정리 |
| 배치 생성 금지 | 대량 orphan 방지 |

---

## 참고

- findings.022: captureForDesign hang 및 Section 배치 패턴
- findings.024: HTML 와이어프레임 Figma DOM 업로드 전체 가이드
- 발생 세션: 2026-03-20 wireframe upload session
