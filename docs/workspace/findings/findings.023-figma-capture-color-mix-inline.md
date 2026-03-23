---
date: 2026-03-23
area: workspace
title: captureForDesign color-mix() 미해석 및 inline 요소 높이 불일치 패턴
tags: [figma, captureForDesign, color-mix, inline-block, rgba, html-to-design]
---

# captureForDesign color-mix() 미해석 및 inline 요소 높이 불일치 패턴

## 요약

Figma `captureForDesign`이 HTML을 Figma 노드로 변환할 때 두 가지 구조적 한계가 있다.
CSS `color-mix()` 함수는 fill로 캡처되지 않고, `display:inline` 요소는 frame 높이가 텍스트 높이보다 작게 잡힌다.

## 발견 1 - color-mix() 배경이 투명으로 캡처됨

### 현상

```css
/* 이 스타일은 Figma에 fill: none (투명)으로 캡처됨 */
background: color-mix(in srgb, var(--primary1) 12%, transparent);
```

캡처 후 Figma 노드의 `fills` 배열이 `[]` 또는 `white@0%`로 저장된다.

### 원인

`captureForDesign`은 DOM 직렬화 시 `getComputedStyle()`로 배경색을 읽는데,
Chromium이 `color-mix()` 결과를 computed value로 반환하지 않고
함수 문자열 그대로 반환하는 경우가 있다.
CSS 변수(`var(--X)`) 참조가 포함된 `color-mix()`에서 특히 발생한다.

특수 사례: `.nav-glass`의 `color-mix(in srgb, var(--background1) 80%, transparent)`는
`white@0%` (완전 투명)으로 저장된다.

### 해결책

HTML에서 `color-mix()` 를 pre-computed `rgba()` 값으로 교체한다.
RGB 값은 light 테마 기준 `figma_tokens.json`과 정확히 일치해야 Figma 변수 자동 연결이 가능하다.

```css
/* Before */
background: color-mix(in srgb, var(--primary1) 12%, transparent);

/* After - light theme: #8a6fe0 = rgb(138,111,224) */
background: rgba(138, 111, 224, 0.12);
```

**교체 매핑표 (light theme 기준)**

| color-mix 패턴 | rgba 대체값 | Figma 토큰 |
|---|---|---|
| `var(--primary1) N%, transparent` | `rgba(138,111,224, N/100)` | color/light/primary/1 |
| `var(--tertiary1) N%, transparent` | `rgba(141,158,255, N/100)` | color/light/tertiary/1 |
| `var(--positive2) N%, transparent` | `rgba(65,214,155, N/100)` | color/light/positive/2 |
| `var(--negative1) N%, transparent` | `rgba(226,18,35, N/100)` | color/light/negative/1 |
| `var(--yellow1) N%, transparent` | `rgba(255,190,61, N/100)` | color/light/yellow/1 |
| `var(--background1) 80%, transparent` | `rgba(249,249,250, 0.80)` | color/light/background/1 |
| `var(--border3) 50%, transparent` | `rgba(219,221,224, 0.50)` | color/light/border/3 |

**순수 토큰으로 대체 불가능한 파생색 처리**

- `color-mix(in srgb, var(--primary1) 85%, black)` (hover) → `var(--secondary1)` (#6b49b5)
- `color-mix(in srgb, var(--yellow1) 28%, var(--border3))` (border) → `rgba(255,190,61,.28)`

## 발견 2 - display:inline 요소의 frame 높이 불일치

### 현상

`<mark>`, `<code>` 같은 `display:inline` 인라인 요소를 캡처하면:
- Figma FRAME `height` = em-box 높이 (~font-size px)
- TEXT 자식 노드 `height` = line-height (~font-size × 1.6)

결과적으로 frame이 text보다 5-10px 작아 텍스트가 frame 밖으로 넘침.

예시 (post-detail 인라인 코드):
- FRAME `h = 19px` (font-size: 13px × ~1.46)
- TEXT child `h = 24px` (line-height: 13px × 1.6 + padding)

예시 (search-highlight mark):
- FRAME `h = 18px`
- TEXT child `h = 28px` (font-size: 15px × ~1.6 + padding)

### 해결책

HTML에서 해당 요소에 `display:inline-block; vertical-align:baseline` 추가.
`inline-block`은 box 높이를 line-height 기준으로 계산해서 frame과 TEXT 높이가 일치한다.

```css
/* Before */
.search-highlight { background: ...; padding: 0 1px; }

/* After */
.search-highlight { background: ...; padding: 0 1px;
                    display: inline-block; vertical-align: baseline; }
```

### 구조적 한계

`inline-block` 처리로 frame 높이는 정확해지지만,
captureForDesign은 인라인 요소를 주변 텍스트와 분리된 독립 FRAME으로 변환한다.
따라서 Figma에서 주변 텍스트와의 흐름 배치는 완전히 일치하지 않는다.
이는 HTML inline layout을 Figma frame 트리로 변환하는 구조적 제약이다.

## 발견 3 - figma_capture_screenshot이 REST API 대비 rate limit 없음

Figma REST API (`figma_take_screenshot`)는 분당 호출 한도가 낮아 429 에러가 자주 발생한다.
`figma_capture_screenshot`은 Desktop Bridge 플러그인의 `exportAsync` API를 직접 호출하므로
REST API rate limit 없이 즉시 캡처 가능하다. Figma 변경 직후 검증에는 이 도구를 우선 사용할 것.

## 관련 파일

- `/workspace/.workspace/design/*.html` - 수정된 HTML 와이어프레임 10개
- `/workspace/docs/client/figma_tokens.json` - 색상 토큰 RGB 정의

## 관련 findings

- findings.021 - Docker 환경 HTML→Figma 캡처 방법
- findings.022 - captureForDesign hang 및 Section 배치 패턴
