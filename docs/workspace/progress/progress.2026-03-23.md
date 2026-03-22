---
date: 2026-03-23
area: workspace
title: 와이어프레임 HTML 컴플라이언스 수정 및 Figma 캡처
status: done
---

# 와이어프레임 HTML 컴플라이언스 수정 및 Figma 캡처

## 작업 내용

### 1. HTML 컴플라이언스 검증 및 수정

`/workspace/.workspace/design/` 의 8개 HTML 와이어프레임 파일에 대해 컬러 토큰 및 타이포그래피 클래스 규정 준수 여부를 확인하고 수정했다.

**색상 수정 (3개 파일)**

- `guestbook.html` - `#e85757/#d44545` → `--negative2/1`, `#3b82f6` → `--tertiary1`, `#22c55e` → `--positive2`, `#fff` 버튼 텍스트 → `--background1`
- `error-page.html` - `#e07a5f` 계열 → `--yellow1`, 워닝 배경 color-mix → `--background3`, `--border3`
- `post-detail.html` - `#e5793a` → `--yellow1`, `#dc4545` 삭제 버튼 → `--negative2/1`

**타이포그래피 수정 (전체 8개 파일)**

기본 Tailwind 클래스를 캐노니컬 타이포그래피 클래스로 교체 (`fix_html_compliance.py` 스크립트):

| 교체 전 | 교체 후 |
|---------|---------|
| `text-xs` | `text-ui-xs` |
| `text-sm` | `text-body-sm` |
| `text-2xl` | `text-body-lg` |
| `text-3xl` | `text-h1` |
| `text-[10px]` | `text-ui-xs` |

총 교체 횟수: `text-ui-xs` 187×, `text-body-sm` 112×, `text-h1` 13×, `text-body-lg` 13×

### 2. 특수 상태 HTML 파일 생성

Figma 캡처를 위해 사이드바 오픈 상태와 빈 상태를 자동으로 표시하는 2개 파일 생성:

- `home-page-sidebar.html` - DOMContentLoaded 시 `#mobileSidebar.open` 자동 적용
- `loading-empty-states-empty.html` - DOMContentLoaded 시 `[data-view="empty"]` 탭 자동 클릭

### 3. Figma 캡처 (19개 프레임)

Playwright headless Chromium으로 19개 와이어프레임을 Figma 디자인 노드로 캡처했다.

**캡처 방법**: `generate_figma_design` MCP로 captureId 생성 → Playwright에서 `captureForDesign` POST → MCP polling으로 완료 확인

**완료된 프레임 (Figma 파일 `hnYsCJHxGz63zFW0rxMian`)**

| 프레임 | node-id |
|--------|---------|
| 홈 Desktop (1440px) | 70:2 |
| 홈 Mobile (375px) | 71:2 |
| 홈 Mobile 사이드바 (375px) | 72:2 |
| 글 상세 Desktop (1440px) | 73:2 |
| 글 상세 Mobile (375px) | 74:2 |
| 검색 Desktop (1440px) | 75:2 |
| 검색 Mobile (375px) | 76:2 |
| 카테고리 Desktop (1440px) | 77:2 |
| 카테고리 Mobile (375px) | 78:2 |
| 태그 Desktop (1440px) | 79:2 |
| 태그 Mobile (375px) | 80:2 |
| 방명록 Desktop (1440px) | 81:2 |
| 방명록 Mobile (375px) | 82:2 |
| 에러 Desktop (1440px) | 83:2 |
| 에러 Mobile (375px) | 84:2 |
| 로딩 Skeleton Desktop (1440px) | 85:2 |
| 로딩 Skeleton Mobile (375px) | 86:2 |
| 빈 상태 Empty Desktop (1440px) | 87:2 |
| 빈 상태 Empty Mobile (375px) | 88:2 |

**기술적 발견사항**: `captureForDesign`은 POST 전송 후 서버 측 상태 폴링에서 hang 발생 (status endpoint 404 반환). 실제 데이터 전송은 15초 이내 완료되며, 짧은 timeout 후 MCP polling으로 완료 확인하는 방식이 효과적.
