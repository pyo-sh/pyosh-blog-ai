# Client Progress - 2026-04-25

## 완료된 작업

### #326 Category/Tag 한글 slug 라우트 404 + Category 입력 한글 IME 분해 버그 수정 (PR #327 머지)

카테고리/태그 공개 페이지가 한글 slug 직링크에서 404를 내고, 관리자 카테고리 모달의 이름 입력이 한글 IME 사용 시 자모 분해 형태로 남던 문제를 한 번에 정리했다. 이번 수정에서는 게시글 상세 slug 조회에서 이미 검증된 decode fallback + Unicode 정규화 패턴을 category/tag 경로에도 공통으로 적용하도록 `shared` slug 유틸을 추가했다. category slug lookup은 저장된 slug와 route param을 같은 기준으로 비교하도록 바꿨고, tag 페이지는 active tag 판별뿐 아니라 posts fetch에 넘기는 `tagSlug`도 정규화된 값으로 통일했다. 또한 카테고리 이름 입력은 composition 중간값을 그대로 두되, 합성이 끝나는 시점과 submit 직전에 NFC로 다시 정규화해 저장 시 `에이아이` 같은 합성형 문자열이 유지되도록 했다. PR `#327`은 동기 `codex` 리뷰 후 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/shared/lib/slug.ts`
  - slug decode/normalize/encode 공통 helper 추가
  - route param 비교와 API path 생성이 같은 Unicode 정규화 기준을 사용하도록 통일
- `src/entities/post/api.ts`
  - `fetchPostBySlug()`가 shared slug helper를 사용하도록 정리
  - 기존 decode fallback 동작은 유지하면서 path builder 중복 제거
- `src/entities/category/lib.ts`
  - `findCategoryBySlug()`가 route slug를 decode + `NFKC` 정규화한 뒤 재귀 탐색하도록 변경
- `src/app/(public)/tags/[slug]/page.tsx`
  - tag route param을 정규화한 값으로 `fetchPosts({ tagSlug })`를 호출
  - active tag 판별도 저장된 tag slug 정규화 후 비교
- `src/features/category-manager/ui/category-form-modal.tsx`
  - category name input에 composition state 추가
  - composition 종료 시점과 submit 시점에 `NFC` 정규화 적용

**검증:**

- `CI=true pnpm install --offline`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning은 기존 항목인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 2건만 남았다.
- issue worktree에는 의존성이 없어서 verify 전에 worktree-local `node_modules`를 다시 구성했다.

### #324 휴지통/관리자 화면에서 카테고리 NULL 글 표시 및 복원 UX 정리 (PR #325 머지)

카테고리 삭제 후 휴지통으로 이동한 글이 `categoryId/category = null` 상태로 내려올 수 있도록 서버가 바뀐 뒤, 클라이언트 관리 화면이 여전히 `post.category.name`을 직접 참조하던 문제를 정리했다. 이번 작업에서는 관리자 post 엔티티 타입에서 `categoryId`와 `category`를 nullable로 전환하고, 휴지통 및 관리자 목록에서 orphan 글을 `(카테고리 없음)`으로 표시하도록 수정했다. 또한 휴지통에서 복원할 때 카테고리 없는 글은 즉시 복원하지 않고 먼저 카테고리 선택 모달을 띄워 재지정 후 복원하도록 바꿨다. 단건 복원과 벌크 복원 모두 같은 규칙을 적용했고, public 단건 상세와 구조화 데이터도 nullable category를 방어하도록 정리했다. PR `#325`는 동기 `codex` 리뷰 후 suggestion 없이 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/entities/post/model.ts`
  - 관리자 post 타입의 `categoryId`를 `number | null`로 전환
  - `PostListItem.category`, `PostDetail.category`를 nullable로 전환
  - `PublishedPostListItem`은 public 경로 계약 유지를 위해 non-null category로 유지
- `src/app/manage/posts/page.tsx`
  - 카테고리 없는 글 복원 시 카테고리 선택 모달을 먼저 띄우는 restore flow 추가
  - 선택한 카테고리를 orphan 글에 먼저 patch한 뒤 restore를 실행하도록 단건/벌크 복원 경로 통합
- `src/widgets/admin-post-list/ui/post-table.tsx`
  - 휴지통/관리자 목록에서 null category를 `(카테고리 없음)`으로 표시
- `src/app/(public)/posts/[slug]/page.tsx`
  - breadcrumb, related posts 조회, 카테고리 badge 렌더를 optional access로 방어
- `src/shared/lib/structured-data.ts`
  - JSON-LD `articleSection` 생성 시 nullable category를 허용
- `src/features/category-manager/ui/category-delete-modal.tsx`
  - "휴지통 이동" 설명에 복원 시 카테고리 재지정이 필요하다는 안내 추가

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning은 기존 항목인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 2건만 남았다.
- issue worktree에는 의존성이 없어서 verify 전에 `pnpm install --frozen-lockfile`로 worktree 전용 `node_modules`를 구성했다.
