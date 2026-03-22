# F-21: 글 관리 (목록, 필터, 삭제/복원)

**상태:** DRAFT
**최종 수정:** 2026-03-23

---

## 1. 개요

관리자 글 관리 페이지. 글 목록을 테이블 형태로 표시하며, 상태/공개여부/삭제 필터, 검색, 정렬, 벌크 선택/삭제, 공개여부 인라인 토글, 글 미리보기, 영구 삭제(연쇄 삭제 포함)를 제공한다. 라우트 경로는 `/manage/posts`(F-20에서 변경).

## 2. 배경 및 동기

현재 구현 상태:

- 글 목록 테이블 (제목, 상태, 가시성, 작성일, 작업)
- 상태 필터 (전체/초안/발행/보관), 삭제된 글 포함 체크박스
- 소프트 삭제, 복원 기능
- React Query 기반 데이터 패칭

개선이 필요한 부분:

- 조회수, 댓글 수 컬럼 누락
- 고정 글 토글 UI 누락
- 공개여부 필터 UI 없음, 인라인 토글 없음
- 검색 UI 없음 (서버 API에 `q` 파라미터 지원하나 UI 미구현)
- 정렬 옵션 UI 없음 (서버 API에 `sort`, `order` 지원하나 UI 미구현)
- 벌크 선택/삭제 없음
- 영구 삭제 UI 없음 (API는 존재)
- 영구 삭제 시 댓글, 조회수, 고아 태그 연쇄 삭제 미구현
- 글 미리보기 기능 없음
- 삭제된 글이 체크박스로만 필터링되고 별도 뷰가 없음

## 3. 목표

- 테이블에 조회수, 댓글 수, 고정 여부 컬럼을 추가한다
- 공개여부 필터 드롭다운을 추가한다
- 공개여부를 테이블에서 인라인 토글한다
- 고정 글 토글을 테이블에서 인라인으로 제공한다
- 검색 입력 UI를 추가한다 (제목/내용)
- 테이블 컬럼 헤더 클릭으로 정렬을 변경한다
- 벌크 선택 + 일괄 삭제를 지원한다
- 삭제된 글을 별도 "휴지통" 탭으로 분리한다
- 영구 삭제 버튼을 휴지통 탭에 추가한다
- 영구 삭제 시 댓글, 조회수, 고아 태그를 연쇄 삭제한다
- 글 미리보기 페이지를 추가한다

## 4. 비목표

- 벌크 상태 변경 (일괄 발행 등)
- 글 드래그 앤 드롭 정렬
- 글 내보내기/가져오기
- 글 버전 관리/히스토리

---

## 5. 상세 설계

### 5.1 테이블 컬럼 구성

#### 기본 탭 (활성 글)

| 컬럼 | 데이터 | 정렬 가능 | 비고 |
|---|---|---|---|
| ☐ (체크박스) | 벌크 선택 | - | 헤더에 전체 선택 |
| 📌 | `isPinned` | - | 토글 버튼 |
| 썸네일 | `thumbnailUrl` | - | 소형 썸네일 (40x40), 없으면 플레이스홀더 |
| 제목 + 요약 | `title` + `summary` + `category.name` | - | 카테고리 배지, 요약 1줄 truncate |
| 상태 | `status` | - | 배지 (초안/발행/보관) |
| 공개 | `visibility` | - | 토글 스위치 (공개/비공개) |
| 조회수 | `viewCount` | O | 숫자 |
| 댓글 | `commentCount` | O | 숫자 |
| 발행일 | `publishedAt` | O | ko-KR 포맷, null이면 `-` |
| 수정일 | `contentModifiedAt` | O | ko-KR 포맷, null이면 `-` |
| 작업 | - | - | 미리보기, 수정, 삭제 |

#### 휴지통 탭 (삭제된 글)

| 컬럼 | 데이터 | 비고 |
|---|---|---|
| ☐ (체크박스) | 벌크 선택 | |
| 제목 | `title` + `category.name` | |
| 삭제일 | `deletedAt` | ko-KR 포맷 |
| 작업 | - | 복원, 영구 삭제 |

### 5.2 탭 구조

"삭제된 글 포함" 체크박스를 제거하고 탭으로 분리한다.

```
┌─ 글 관리 ──────────────────────────────────────────┐
│                                          [새 글 작성] │
│                                                      │
│  [활성 글]  [휴지통 (3)]                              │
│                                                      │
│  상태: [전체 ▼]  공개: [전체 ▼]  [검색어 입력___] [🔍] │
│                                                      │
│  선택된 2개: [일괄 삭제]                               │
│                                                      │
│  ☐  📌  제목 ▲    상태  공개  조회↕ 댓글↕ 작성일↕ ...  │
│  ☑  📌  Next.js   발행  [🔘]  245   12   03.20  ...  │
│  ☑  ·   React     초안  [⚪]   0     0   03.18  ...  │
│  ☐  ·   CSS 팁    발행  [🔘]  189    5   03.15  ...  │
│                                                      │
│  총 42개 중 1-10              [이전] 1/5 [다음]       │
└──────────────────────────────────────────────────────┘
```

### 5.3 필터

#### 상태 필터

기존 구현 유지. 드롭다운: 전체 / 초안 / 발행 / 보관.

#### 공개여부 필터 (신규)

드롭다운: 전체 / 공개 / 비공개.

- URL 파라미터: `?visibility=public|private`
- 서버 API의 `visibility` 파라미터 활용 (이미 지원됨)
- 필터 변경 시 page 초기화

#### 검색 (신규)

```
[검색어 입력_______________] [🔍]
```

- 입력 후 Enter 또는 🔍 클릭 시 검색 실행
- 서버 API의 `q` 파라미터 활용 (이미 지원됨 - `title LIKE`, `contentMd LIKE`)
- 검색 중일 때 "'{검색어}' 검색 결과 (N건)" 표시
- 검색 해제 버튼 (X) 표시

### 5.4 정렬

테이블 컬럼 헤더를 클릭하면 정렬이 토글된다.

| 정렬 가능 컬럼 | 서버 파라미터 |
|---|---|
| 조회수 | `sort=viewCount` |
| 댓글 수 | `sort=commentCount` |
| 작성일 | `sort=created_at` |
| 발행일 | `sort=published_at` |

- 기본 정렬: 작성일 내림차순 (`created_at DESC`)
- 클릭 1회: 해당 컬럼 내림차순 (▼)
- 클릭 2회: 해당 컬럼 오름차순 (▲)
- 클릭 3회: 기본 정렬로 복귀
- 헤더에 현재 정렬 방향 화살표 표시 (▲/▼), 미정렬 시 ↕

#### 서버 변경

현재 서버는 `published_at`, `created_at`만 정렬 지원. `viewCount`, `commentCount` 정렬을 추가해야 한다.

### 5.5 벌크 선택/작업

#### 선택 UI

- 각 행에 체크박스
- 헤더에 전체 선택 체크박스 (현재 페이지 전체 선택/해제)
- 선택된 항목 수 표시: "선택된 N개"

#### 일괄 작업

| 탭 | 가능한 일괄 작업 |
|---|---|
| 활성 글 | [카테고리 변경 ▼] [일괄 삭제] |
| 휴지통 | [일괄 복원], [일괄 영구 삭제] |

#### 벌크 카테고리 변경

[카테고리 변경 ▼] 클릭 시 버튼 아래 popover 드롭다운이 열린다. F-23의 카테고리 트리 드롭다운(인덴트 표기)을 재사용한다.

```
  선택된 3개:  [카테고리 변경 ▼]  [일괄 삭제]
               ┌──────────────────────┐
               │ 개발                  │
               │   Frontend            │
               │   Backend             │
               │     (2) Node.js       │
               │ 일상                  │
               ├──────────────────────┤
               │ 3개 글을 'Frontend'   │
               │ (으)로 이동합니다     │
               │          [취소] [확인] │
               └──────────────────────┘
```

1. popover에서 카테고리 선택
2. 확인 영역 표시: "N개 글을 '{카테고리명}'(으)로 이동합니다 [취소] [확인]"
3. [확인] 클릭 → 벌크 API 호출
4. 성공 → 토스트 + 목록 갱신, 실패 → 에러 토스트

#### 벌크 API

모든 벌크 작업은 서버 단일 엔드포인트에서 트랜잭션으로 처리한다.

```
PATCH /api/admin/posts/bulk
{
  ids: [1, 2, 3],
  action: "update_category" | "soft_delete" | "restore" | "hard_delete",
  categoryId?: number  // update_category 시 필수
}
```

- 단일 트랜잭션: 전체 성공 or 전체 실패
- 네트워크 1회 (개별 `Promise.allSettled` 방식 대체)
- `hard_delete`: 연쇄 삭제 포함 (5.9 참조)
- 일괄 영구 삭제: 확인 다이얼로그 필수 ("N개의 글과 관련 댓글이 영구 삭제됩니다. 이 작업은 되돌릴 수 없습니다.")

#### 벌크 API 에러 처리

서버는 트랜잭션 실패 시 어떤 글이 문제인지 상세 에러를 반환한다.

```typescript
// 에러 응답 예시
{
  error: "bulk_action_failed",
  message: "일부 글 처리에 실패했습니다",
  details: [
    { id: 3, reason: "카테고리를 찾을 수 없습니다" },
    { id: 7, reason: "이미 삭제된 글입니다" }
  ]
}
```

클라이언트에서 에러 토스트에 상세 내용을 표시한다.

### 5.6 공개여부 인라인 토글

테이블의 "공개" 컬럼에 토글 스위치를 배치한다.

```
[🔘] 공개    →  클릭  →  [⚪] 비공개
```

- 클릭 시 `PATCH /api/admin/posts/:id` with `{ visibility: "public" | "private" }` 호출
- optimistic update: 즉시 UI 반영, 실패 시 롤백
- 토글 중 로딩 상태 표시 (스위치 비활성화)

### 5.7 고정 글 토글

테이블의 📌 컬럼에 토글 버튼을 배치한다.

- 고정됨: 📌 (채워진 핀 아이콘)
- 미고정: · (dot) 또는 빈 핀 아이콘
- 클릭 시 `PATCH /api/admin/posts/:id` with `{ isPinned: true | false }` 호출
- optimistic update

### 5.8 글 미리보기

#### 미리보기 페이지

`/manage/posts/[id]/preview` 경로에 별도 미리보기 페이지를 제공한다.

```
┌─ 글 미리보기 ─────────────────────────────────────────┐
│                                                        │
│  [← 목록]  [수정]  [삭제]  공개: [🔘]  고정: [📌]      │
│                                                        │
│  ┌─ 미리보기 영역 ──────────────────────────────────┐  │
│  │                                                   │  │
│  │  카테고리: Frontend                               │  │
│  │  2026.03.20 · 조회 245 · 댓글 12                  │  │
│  │                                                   │  │
│  │  # Next.js 가이드                                 │  │
│  │                                                   │  │
│  │  마크다운 렌더링된 본문...                          │  │
│  │                                                   │  │
│  │  태그: #react #nextjs                             │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

#### 컨트롤 바

미리보기 상단에 관리 기능을 제공한다.

| 버튼 | 동작 |
|---|---|
| ← 목록 | `/manage/posts`로 이동 |
| 수정 | `/manage/posts/[id]/edit`으로 이동 |
| 삭제 | 소프트 삭제 후 목록으로 이동 (확인 다이얼로그) |
| 공개 토글 | 인라인 토글 스위치 |
| 고정 토글 | 핀 토글 버튼 |
| 상태 변경 | 드롭다운 (초안/발행/보관) |
| 수정일 관리 | "수정일 제거" 또는 커스텀 날짜 설정 |

#### 미리보기 본문 렌더링

- F-02 글 상세의 마크다운 렌더링 컴포넌트(`PostContent`)를 재활용
- 초안/비공개 글도 관리자 세션에서 미리보기 가능
- 미리보기 영역은 Public 글 상세와 동일한 스타일링

### 5.9 영구 삭제 - 연쇄 삭제

#### 삭제 대상

글 영구 삭제 시 관련 데이터를 함께 삭제한다.

| 대상 | 테이블 | 삭제 방식 |
|---|---|---|
| 글-태그 관계 | `post_tag_tb` | 현재 구현됨 |
| 댓글 | `comment_tb` | 해당 글의 모든 댓글 영구 삭제 (신규) |
| 조회수 | `stats_daily_tb` | 해당 글의 모든 조회수 기록 삭제 (신규) |
| 고아 태그 | `tag_tb` | 사용 글이 0개인 태그 삭제 (신규) |

#### 서버 트랜잭션

```typescript
async hardDeletePost(id: number) {
  await db.transaction(async (tx) => {
    // 1. 해당 글의 태그 ID 목록 기억 (고아 태그 체크용)
    const tagIds = await getPostTagIds(tx, id);

    // 2. 글-태그 관계 삭제
    await tx.delete(postTagTable).where(eq(postTagTable.postId, id));

    // 3. 댓글 삭제
    await tx.delete(commentTable).where(eq(commentTable.postId, id));

    // 4. 조회수 삭제
    await tx.delete(statsDailyTable).where(eq(statsDailyTable.postId, id));

    // 5. 글 삭제
    await tx.delete(postTable).where(eq(postTable.id, id));

    // 6. 고아 태그 삭제 (다른 글에서 사용하지 않는 태그)
    for (const tagId of tagIds) {
      const usageCount = await tx
        .select({ count: count() })
        .from(postTagTable)
        .where(eq(postTagTable.tagId, tagId));

      if (usageCount[0].count === 0) {
        await tx.delete(tagTable).where(eq(tagTable.id, tagId));
      }
    }
  });
}
```

#### 확인 다이얼로그

영구 삭제 시 반드시 확인 다이얼로그를 표시한다.

```
┌─ 영구 삭제 ─────────────────────────────┐
│                                          │
│  "Next.js 가이드" 글을 영구 삭제합니다.  │
│                                          │
│  다음 데이터가 함께 삭제됩니다:           │
│  · 댓글 12개                             │
│  · 조회수 기록                           │
│  · 사용되지 않는 태그                    │
│                                          │
│  이 작업은 되돌릴 수 없습니다.           │
│                                          │
│        [취소]  [영구 삭제]               │
└──────────────────────────────────────────┘
```

### 5.10 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `manage/posts/page.tsx` | 글 관리 페이지 |
| `app` | `manage/posts/[id]/preview/page.tsx` | 글 미리보기 페이지 (신규) |
| `app` | `manage/posts/[id]/edit/page.tsx` | 글 수정 페이지 (기존, 경로 변경) |
| `app` | `manage/posts/new/page.tsx` | 새 글 작성 (기존, 경로 변경) |
| `widgets` | `admin-post-list/ui/post-table.tsx` | 글 테이블 (기존 리팩터링) |
| `widgets` | `admin-post-list/ui/post-filters.tsx` | 필터/검색 바 (신규) |
| `widgets` | `admin-post-list/ui/bulk-actions.tsx` | 벌크 액션 바 (신규) |
| `widgets` | `admin-post-preview/ui/post-preview.tsx` | 미리보기 위젯 (신규) |
| `features` | `post-editor/ui/post-form.tsx` | 글 작성/수정 폼 (기존) |
| `entities` | `post/api.ts` | Admin CRUD API (기존 확장) |
| `shared` | `ui/toggle-switch.tsx` | 토글 스위치 (공개여부용, 신규) |
| `shared` | `ui/confirm-dialog.tsx` | 확인 다이얼로그 (영구 삭제용, 신규) |

### 5.11 데이터 흐름

```
PostListPage
  ├─ 탭: [활성 글] [휴지통]
  │
  ├─ PostFilters
  │   ├─ 상태 드롭다운, 공개여부 드롭다운
  │   └─ 검색 입력
  │
  ├─ BulkActions (선택된 항목 > 0일 때 표시)
  │   └─ "선택된 N개: [일괄 삭제/복원/영구삭제]"
  │
  ├─ PostTable
  │   └─ useQuery(['admin-posts', tab, page, status, visibility, q, sort, order])
  │       → GET /api/admin/posts?page=1&status=draft&visibility=public&q=keyword&sort=created_at&order=desc&includeDeleted=false
  │       → 테이블 렌더링
  │       → 체크박스, 고정 토글, 공개 토글, 정렬 헤더
  │
  └─ Pagination
```

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/admin/posts` | 글 목록 | `viewCount`, `commentCount` 응답 추가, `sort` 옵션 확장 |
| PATCH | `/api/admin/posts/:id` | 글 수정 | `isPinned`, `visibility` 인라인 토글 |
| PATCH | `/api/admin/posts/bulk` | 벌크 작업 | **신규** - 카테고리 변경, 삭제, 복원, 영구 삭제 |
| DELETE | `/api/admin/posts/:id` | 소프트 삭제 | 기존 유지 |
| PUT | `/api/admin/posts/:id/restore` | 복원 | 기존 유지 |
| DELETE | `/api/admin/posts/:id/hard` | 영구 삭제 | 댓글, 조회수, 고아 태그 연쇄 삭제 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| Admin 글 목록 응답 | `viewCount`, `commentCount` 집계 포함 |
| `AdminPostListQuerySchema` | `sort` 옵션에 `viewCount`, `commentCount` 추가 |
| 글 목록 정렬 | `viewCount`, `commentCount` 정렬 시 집계 서브쿼리 또는 JOIN |
| `hardDeletePost()` | 댓글, 조회수, 고아 태그 연쇄 삭제 추가 |
| `PostDetailSchema` | `isPinned`, `contentModifiedAt` 필드 포함 (F-01에서 추가) |
| `contentModifiedAt` 자동 설정 | 글 수정 API 호출 시 명시적 값 없으면 현재 시각 자동 설정, null 명시 시 제거, 메타데이터만 변경(공개 토글, 핀 토글) 시 변경하지 않음 |

### 응답 데이터

Admin 글 목록 응답에 집계 필드를 추가한다.

```typescript
interface AdminPostListItem extends Post {
  viewCount: number;
  commentCount: number;
}
```

## 7. 수용 기준

- [ ] 글 관리 경로가 `/manage/posts`이다
- [ ] 테이블에 썸네일, 요약, 조회수, 댓글 수, 고정 여부, 발행일, 수정일 컬럼이 있다
- [ ] 상태 필터 드롭다운이 동작한다 (전체/초안/발행/보관)
- [ ] 공개여부 필터 드롭다운이 동작한다 (전체/공개/비공개)
- [ ] 검색 입력으로 제목/내용 검색이 동작한다
- [ ] 정렬 가능 컬럼 헤더 클릭 시 정렬이 변경된다 (ASC/DESC/기본)
- [ ] 공개여부 인라인 토글이 optimistic update로 동작한다
- [ ] 고정 글 토글이 optimistic update로 동작한다
- [ ] 체크박스로 여러 글을 선택할 수 있다
- [ ] 전체 선택 체크박스가 현재 페이지 전체를 선택/해제한다
- [ ] 활성 글 탭에서 벌크 카테고리 변경이 popover + 확인으로 동작한다
- [ ] 벌크 작업이 서버 벌크 API(`PATCH /api/admin/posts/bulk`)로 트랜잭션 처리된다
- [ ] 활성 글 탭에서 일괄 삭제가 동작한다
- [ ] "휴지통" 탭에 삭제된 글이 별도로 표시된다
- [ ] 휴지통에서 복원, 영구 삭제 버튼이 있다
- [ ] 휴지통에서 일괄 복원, 일괄 영구 삭제가 동작한다
- [ ] 영구 삭제 시 확인 다이얼로그가 표시된다
- [ ] 영구 삭제 시 댓글, 조회수, 고아 태그가 함께 삭제된다
- [ ] 미리보기 페이지(`/manage/posts/[id]/preview`)에서 마크다운 본문을 렌더링한다
- [ ] 미리보기 컨트롤 바에서 수정, 삭제, 공개 토글, 고정 토글, 상태 변경이 가능하다
- [ ] 초안/비공개 글도 미리보기가 가능하다
- [ ] 다크모드 자동 적용
- [ ] 접근성: 테이블 aria-label, 토글 aria-checked, 확인 다이얼로그 focus trap (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 공개 토글 실패 | optimistic rollback, 에러 토스트 |
| 고정 토글 실패 | optimistic rollback, 에러 토스트 |
| 벌크 작업 실패 | 서버 트랜잭션 전체 롤백, 에러 상세(글 ID + 사유) 토스트에 표시 |
| 벌크 카테고리 변경 시 이미 해당 카테고리인 글 포함 | 무시 (에러 아님, 그대로 유지) |
| 영구 삭제 대상 글에 댓글이 없는 경우 | 댓글 삭제 단계 무시 (에러 아님) |
| 영구 삭제 대상 글의 태그가 다른 글에서도 사용 중 | 해당 태그는 삭제하지 않음 (사용 수 > 0) |
| 검색어 없이 검색 버튼 클릭 | 필터 초기화 (전체 목록) |
| 정렬 + 필터 + 검색 복합 사용 | 모든 조건이 AND로 결합 |
| 휴지통이 비어 있을 때 | "삭제된 글이 없습니다" 빈 상태 |
| 미리보기 중 다른 관리자가 글 삭제 | 에러 처리, "글을 찾을 수 없습니다" 표시 |

## 9. 의존성

- F-19 관리자 로그인 (인증)
- F-01 홈 - 글 목록 (`isPinned`, `viewCount`, `commentCount`, `summary` 필드 - 서버 스키마 공유)
- F-02 글 상세 (`PostContent` 마크다운 렌더링 컴포넌트 - 미리보기 재활용)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
