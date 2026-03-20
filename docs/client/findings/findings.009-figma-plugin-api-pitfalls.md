# Figma plugin API pitfalls for wireframe automation

## Metadata
- **Date**: 2026-03-20

## Problem

Figma wireframe 자동화 작업 중 `figma_execute`(MCP)로 노드를 생성/수정할 때 반복적으로 발생한 문제들을 정리한다. 향후 Figma 와이어프레임 작업 시 동일한 실수를 방지하기 위한 참고 자료이다.

## Findings

### 1. 고아 노드 (orphaned nodes)

`figma.createFrame()` / `figma.createText()`는 호출 즉시 **현재 페이지 루트**에 노드를 생성한다. `parent.appendChild(node)`로 원하는 부모에 이동시키기 전에 스크립트가 에러로 중단되면, 노드가 페이지 루트에 고아로 남는다.

**발생 사례:** 모바일 사이드바 태그 섹션을 생성하던 중 `setBoundVariable` 에러로 스크립트가 중단되어 `Container`, `태그` 등 4개 고아 노드가 Page 1 루트에 남았다.

**방지책:**
- `existingNode.clone()` 우선 사용 - 부모 컨텍스트가 유지됨
- 생성 직후 즉시 `parent.appendChild()` 호출, 속성 설정은 그 이후
- 여러 노드를 생성하는 스크립트에서는 생성한 노드를 배열로 추적하고, catch 블록에서 일괄 삭제
- 실행 후 페이지 루트의 자식 목록을 점검

### 2. `setBoundVariable` vs paint `boundVariables`

Frame의 fills/strokes에 변수를 바인딩할 때 `node.setBoundVariable('fills', ...)` 는 동작하지 않는다. 대신 paint 객체에 직접 `boundVariables` 속성을 포함해야 한다:

```js
// 잘못된 방법
badge.setBoundVariable('fills', 0, 'color', variable);

// 올바른 방법
badge.fills = [{
  type: 'SOLID',
  color: { r, g, b },
  boundVariables: { color: { type: 'VARIABLE_ALIAS', id: variable.id } }
}];
```

### 3. `clipsContent`와 부모 프레임 크기

자식 노드의 높이가 변경되면 부모 체인 전체의 높이를 수동으로 조정해야 한다. `clipsContent: true`인 부모는 넘치는 콘텐츠를 잘라내므로, 콘텐츠 추가 후 부모 resize를 빠뜨리면 내용이 보이지 않는다.

**발생 사례:** 모바일 사이드바에 태그 섹션을 추가한 후 부모 컨테이너(14:649) 높이를 늘리지 않아 총 조회수 섹션이 잘렸다.

### 4. `resize()`와 Vector 노드

Vector 노드에 `resize()`를 호출하면 path 좌표가 정규화되어 의도치 않은 변형이 발생한다. Vector의 크기를 변경할 때는 resize 대신 정확한 좌표로 path를 새로 작성해야 한다.

### 5. 섹션 간 스타일 일관성

동일한 UI 패턴(분류 섹션, 태그 섹션 등)을 여러 뷰포트에 적용할 때, 하나를 수동으로 재구축하면 border/background/font 등 세부 스타일이 불일치하기 쉽다. Desktop에서 완성된 섹션을 `clone()`하여 모바일에 적용하고, 너비만 조정하는 것이 안전하다.

## Recommendations

| 상황 | 접근 방식 |
|---|---|
| 기존 패턴과 동일한 요소 추가 | `clone()` 후 텍스트/위치만 수정 |
| 새로운 요소를 처음 생성 | 생성 즉시 `appendChild`, 속성 설정은 이후 |
| 여러 뷰포트에 동일 섹션 | Desktop 완성 후 `clone()` → 모바일 적용 |
| 색상 변수 바인딩 | paint 객체의 `boundVariables` 속성 사용 |
| 콘텐츠 추가/제거 후 | 부모 체인 전체 높이 재계산 |
| 스크립트 실행 후 | 페이지 루트의 고아 노드 점검 |
