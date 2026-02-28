# Feature Spec v1 Revision Design

> 날짜: 2026-02-28
> 영역: client
> 상태: approved

## 배경

`docs/client/feature_spec.md` (v1 초기 스펙)를 서버 API 현황과 대조 검토한 결과, 불일치/누락/불명확한 항목이 발견되어 인터뷰 기반으로 수정 방향을 확정함.

## 변경 사항 요약

| # | 항목 | 기존 spec | 변경 |
|---|------|-----------|------|
| 1 | OAuth | 게스트 전용, 후속 버전 | 유지 |
| 2 | 태그 API | `GET /api/posts` 집계 | `GET /api/tags` 전용 API로 수정 |
| 3 | 검색 | 제외 항목 | v1 Phase4에 추가 (헤더 검색바 + 결과 페이지) |
| 4 | 조회수 중복 | 서버 위임만 | 클라이언트 sessionStorage 중복 방지 추가 |
| 5 | 에디터 | textarea + 프리뷰 (후보 미확정) | 순수 textarea + 프리뷰 확정 |
| 6 | 에러/로딩 | 미언급 | 글로벌 loading.tsx + error.tsx + not-found.tsx 추가 |
| 7 | 이미지 | 미언급 | 썸네일에 next/image, 본문은 일반 img 추가 |
| 8 | 비밀 댓글 | 작성자+관리자 확인 | 관리자만 확인 (공개에서는 마스킹) |
| 9 | 코드 하이라이팅 | rehype-highlight 또는 shiki | shiki 확정 |
| 10 | Admin 댓글 관리 | 제외 항목 | v1 Phase4에 추가 (최소 관리) |
| 11 | 조회수 호출 | 미상세 | 클라이언트 useEffect 확정 |
| 12 | Phase 배치 | 기존 4단계 | 검색 + Admin 댓글관리 → Phase4 추가 |

## 상세 결정

### 1. 페이지 구조 추가

- `/search?q=keyword` — 검색 결과 페이지 (Public)
- `/dashboard/comments` — 댓글 관리 (Admin)
- `/dashboard/guestbook` — 방명록 관리 (Admin)

### 2. 기능 상세

**검색 (3.9 신규):**
- 헤더에 검색 아이콘/바 추가
- `GET /api/posts?q=keyword` 활용 (서버 사이드 검색)
- 결과 레이아웃: 홈 글 목록과 동일, 페이지네이션 지원

**비밀 댓글:**
- 공개 화면: "비밀 댓글입니다" 마스킹 표시
- 관리자 대시보드에서만 내용 확인 가능

**조회수:**
- 클라이언트 useEffect에서 `POST /api/stats/view` 호출
- sessionStorage로 이미 조회한 글 추적, 같은 세션 내 재방문 시 API 호출 생략

### 3. Admin 추가 기능

**댓글 관리 (4.7):**
- 전체 댓글 목록 (페이지네이션)
- 비밀 댓글 내용 확인 가능
- 강제 삭제 기능
- 필터: 게시글별, 비밀 여부

**방명록 관리 (4.8):**
- 전체 방명록 목록 (페이지네이션)
- 강제 삭제 기능

### 4. 기술 결정 확정

- 코드 하이라이팅: **shiki**
- 에디터: **순수 textarea + 프리뷰**
- 이미지: 썸네일 **next/image**, 본문 일반 img
- 에러/로딩: 글로벌 loading.tsx, error.tsx, not-found.tsx

### 5. 구현 우선순위

Phase 1-3은 기존 유지. Phase 4에 추가:
- 17. 검색 기능
- 18. Admin 댓글/방명록 관리

### 6. 제외 항목 수정

삭제:
- ~~검색 기능~~ → v1에 포함됨
- ~~관리자 댓글 관리~~ → v1에 포함됨

유지:
- OAuth 로그인, 검색 고급 기능, 글 시리즈, 뉴스레터, 관리자 사용자 관리, i18n

## 다음 단계

feature_spec.md를 인라인으로 수정하여 위 변경 사항 반영.
