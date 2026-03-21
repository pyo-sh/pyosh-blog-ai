# F-20: 대시보드 (통계 요약)

**상태:** DRAFT
**최종 수정:** 2026-03-21

---

## 1. 개요

관리자 대시보드 메인 페이지. 조회수 통계 카드, 글 상태 요약, 최근 댓글 미리보기를 제공한다. 라우트 경로를 `/dashboard`에서 `/manage`로 변경한다.

## 2. 배경 및 동기

현재 구현 상태:

- 5개 통계 카드(오늘/7일/30일 조회수, 총 글 수, 총 댓글 수)가 동작 중
- 최근 댓글 섹션이 "준비 중" 플레이스홀더
- Quick Actions 섹션이 "연결 예정" 상태이나, 사이드바에서 동일 기능을 제공하므로 불필요
- 라우트 경로가 `/dashboard`이나 `/manage`로 변경 필요
- 글 상태별 개수(초안/발행/보관)를 파악할 수 없음

## 3. 목표

- 라우트 경로를 `/dashboard`에서 `/manage`로 변경한다
- Quick Actions 섹션을 제거한다
- 최근 댓글 섹션을 구현한다
- 글 상태 요약 카드를 추가한다 (초안/발행/보관 개수)
- 대시보드 통계 API에 글 상태별 개수를 추가한다

## 4. 비목표

- 기간별 조회수 차트 (차트 라이브러리 도입 비용 과함)
- 인기 글 Top N 위젯
- 최근 방명록 위젯
- 전일 대비 변화량 표시
- 실시간 접속자 수
- 알림/뱃지 시스템

---

## 5. 상세 설계

### 5.1 라우트 경로 변경

`/dashboard` → `/manage`로 전체 변경한다.

| 변경 전 | 변경 후 |
|---|---|
| `/dashboard` | `/manage` |
| `/dashboard/login` | `/manage/login` |
| `/dashboard/posts` | `/manage/posts` |
| `/dashboard/posts/new` | `/manage/posts/new` |
| `/dashboard/posts/[id]/edit` | `/manage/posts/[id]/edit` |
| `/dashboard/comments` | `/manage/comments` |
| `/dashboard/categories` | `/manage/categories` |
| `/dashboard/assets` | `/manage/assets` |
| `/dashboard/guestbook` | `/manage/guestbook` |

변경 대상:
- `src/app/dashboard/` 디렉토리를 `src/app/manage/`로 이동
- 사이드바 메뉴 링크 경로 변경
- 인증 리다이렉트 경로 변경 (로그인 후 `/manage`로 이동)
- 내부 링크 (글 수정 링크 등) 경로 변경
- F-30의 robots.txt `disallow` 경로 변경 (`/manage/`)

### 5.2 대시보드 레이아웃

```
┌─ /manage ──────────────────────────────────────────┐
│ ┌─ Sidebar ─┐ ┌─ Main ────────────────────────────┐│
│ │ 대시보드   │ │                                    ││
│ │ 글 관리    │ │  [통계 카드 섹션]                    ││
│ │ 카테고리   │ │  오늘 조회 | 7일 조회 | 30일 조회    ││
│ │ 댓글      │ │                                    ││
│ │ 방명록    │ │  [글 상태 요약]                      ││
│ │ 에셋      │ │  총 N개 | 초안 N | 발행 N | 보관 N   ││
│ │           │ │                                    ││
│ │           │ │  [최근 댓글]                         ││
│ │           │ │  댓글 1 (🔒) - 작성자 - 날짜  [삭제] ││
│ │           │ │  댓글 2 - 작성자 - 날짜       [삭제] ││
│ │           │ │  댓글 3 - 작성자 - 날짜       [삭제] ││
│ │           │ │  ...                               ││
│ │           │ │  [댓글 관리 →]                       ││
│ └───────────┘ └────────────────────────────────────┘│
└────────────────────────────────────────────────────┘
```

### 5.3 통계 카드 섹션

기존 5개 카드에서 "총 글 수", "총 댓글 수"를 제거하고 조회수 3개만 유지한다. 글 관련 통계는 글 상태 요약 섹션으로 이동.

| 카드 | 값 | 아이콘/레이블 |
|---|---|---|
| 오늘 조회수 | `todayPageviews` | 오늘 |
| 7일 조회수 | `weekPageviews` | 최근 7일 |
| 30일 조회수 | `monthPageviews` | 최근 30일 |

### 5.4 글 상태 요약 섹션

글을 상태별로 분류하여 표시한다.

```
글 상태 요약
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ 전체 │ │ 초안 │ │ 발행 │ │ 보관 │
│  42  │ │   5  │ │  35  │ │   2  │
└──────┘ └──────┘ └──────┘ └──────┘
```

- 총 댓글 수는 최근 댓글 섹션 헤더에 표시
- 각 카드 클릭 시 해당 상태로 필터링된 글 관리 페이지로 이동 (`/manage/posts?status=draft` 등)

### 5.5 최근 댓글 섹션

최근 댓글 5개를 미리보기 형태로 표시한다.

#### 댓글 항목 구조

기존 `AdminCommentsPage`의 댓글 표시 컴포넌트를 재활용하되, 대시보드에 맞게 간소화한다.

```
┌─ 최근 댓글 (총 128개) ───────────────────────────────┐
│                                                       │
│  비회원 홍길동 · 글 제목 A · 3시간 전          [삭제]  │
│  안녕하세요, 좋은 글이네요...                          │
│                                                       │
│  🔒 비회원 김철수 · 글 제목 B · 5시간 전       [삭제]  │
│  비밀 댓글 내용이 보입니다...                          │
│                                                       │
│  회원 이영희 · 글 제목 A · 1일 전              [삭제]  │
│  ↳ @홍길동 대댓글 내용...                              │
│                                                       │
│                              [댓글 관리 →]             │
└───────────────────────────────────────────────────────┘
```

#### 표시 항목

| 항목 | 설명 |
|---|---|
| 작성자 유형 뱃지 | "회원" (OAuth) / "비회원" (Guest) - 기존 컴포넌트 재활용 |
| 작성자 이름 | `authorName` |
| 글 제목 | 해당 댓글이 달린 글 제목 (클릭 시 글 상세로 이동) |
| 작성 시간 | 상대 시간 (3시간 전, 1일 전) |
| 비밀 댓글 아이콘 | 🔒 아이콘으로 표시 (마스킹 없이 내용 노출) |
| 댓글 본문 | 2줄 이내로 truncate |
| 대댓글 표시 | `↳ @부모작성자` 형태로 관계 표시 |
| 삭제 버튼 | 기존 삭제 mutation 재활용 |

#### "댓글 관리 →" 링크

섹션 하단에 댓글 관리 페이지(`/manage/comments`)로 이동하는 링크.

#### 데이터

기존 댓글 목록 API를 활용한다.

```
GET /api/admin/comments?limit=5&sort=latest
```

- 정렬: 최신순 (작성일 내림차순)
- 삭제된 댓글 제외 (active 상태만)

### 5.6 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `manage/page.tsx` | 대시보드 페이지 |
| `app` | `manage/layout.tsx` | 관리자 레이아웃 |
| `app` | `manage/layout-shell.tsx` | 사이드바 + 메인 영역 |
| `widgets` | `dashboard/ui/dashboard-home.tsx` | 대시보드 메인 위젯 (기존 수정) |
| `widgets` | `dashboard/ui/stats-section.tsx` | 통계 카드 섹션 (기존에서 분리) |
| `widgets` | `dashboard/ui/post-status-section.tsx` | 글 상태 요약 섹션 (신규) |
| `widgets` | `dashboard/ui/recent-comments-section.tsx` | 최근 댓글 섹션 (신규) |
| `widgets` | `admin-sidebar/ui/admin-sidebar.tsx` | 사이드바 (경로 변경) |
| `entities` | `stat/api.ts` | `fetchDashboardStats` (기존) |
| `entities` | `comment/api.ts` | 관리자 댓글 목록 API (기존 활용) |

### 5.7 데이터 흐름

```
DashboardHome
  ├─ StatsSection
  │   └─ useQuery('dashboardStats')
  │       → GET /api/admin/stats/dashboard
  │       → 조회수 3개 카드 렌더링
  │
  ├─ PostStatusSection
  │   └─ useQuery('dashboardStats') ← 동일 쿼리 공유
  │       → 글 상태별 카드 렌더링
  │       → 카드 클릭 → /manage/posts?status={status}
  │
  └─ RecentCommentsSection
      └─ useQuery('recentComments')
          → GET /api/admin/comments?limit=5&sort=latest
          → 댓글 5개 렌더링 + 삭제 mutation
          → "댓글 관리 →" 링크
```

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/admin/stats/dashboard` | 대시보드 통계 | 글 상태별 개수 추가 |
| GET | `/api/admin/comments?limit=5&sort=latest` | 최근 댓글 | 기존 (변경 없음) |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `DashboardStatsResponseSchema` | `postsByStatus: { draft, published, archived }` 필드 추가 |
| `StatsService.getDashboardStats()` | status별 post count 쿼리 추가 |

### 응답 데이터 변경

```typescript
interface DashboardStats {
  todayPageviews: number;
  weekPageviews: number;
  monthPageviews: number;
  totalPosts: number;          // 기존 유지 (하위 호환)
  totalComments: number;       // 기존 유지
  postsByStatus: {             // 신규
    draft: number;
    published: number;
    archived: number;
  };
}
```

## 7. 수용 기준

- [ ] 모든 `/dashboard/*` 경로가 `/manage/*`로 변경되어 있다
- [ ] 사이드바, 인증 리다이렉트, 내부 링크가 `/manage` 경로를 사용한다
- [ ] Quick Actions 섹션이 제거되어 있다
- [ ] 통계 카드가 조회수 3개(오늘/7일/30일)만 표시한다
- [ ] 글 상태 요약에 전체/초안/발행/보관 개수가 표시된다
- [ ] 글 상태 카드 클릭 시 해당 상태로 필터링된 글 관리 페이지로 이동한다
- [ ] 최근 댓글 5개가 미리보기 형태로 표시된다
- [ ] 비밀 댓글이 🔒 아이콘과 함께 내용이 노출된다
- [ ] 대댓글이 `↳ @부모작성자` 형태로 표시된다
- [ ] 댓글 삭제 버튼이 동작한다
- [ ] "댓글 관리 →" 링크가 `/manage/comments`로 이동한다
- [ ] 최근 댓글 헤더에 총 댓글 수가 표시된다
- [ ] 로딩 시 스켈레톤이 표시된다
- [ ] 에러 시 재시도 가능한 에러 상태가 표시된다
- [ ] 다크모드 자동 적용
- [ ] 접근성: 카드에 적절한 heading 레벨, 삭제 버튼 aria-label (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 댓글이 0개 | "댓글이 없습니다" 빈 상태 표시 |
| 글이 0개 | 모든 상태 카드 0 표시 |
| 통계 API 실패 | 에러 메시지 + 재시도 버튼 (기존 패턴) |
| 댓글 API 실패 | 최근 댓글 섹션만 에러 표시 (통계와 독립) |
| 댓글 본문이 매우 긴 경우 | 2줄 truncate (`line-clamp-2`) |
| `/dashboard` 직접 접근 | `/manage`로 리다이렉트 (선택, 비목표로도 가능) |

## 9. 의존성

- F-19 관리자 로그인 (인증, 레이아웃)

## 10. 미해결 사항

- `/dashboard` → `/manage` 리다이렉트 필요 여부. 외부 북마크나 링크가 있을 수 있으나, v1 초기 단계이므로 불필요할 수 있다.
