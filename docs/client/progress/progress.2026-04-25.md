# Client Progress - 2026-04-25

## 완료된 작업

### #332 카테고리 관리 모달 한글 IME 조합 끊김 수정 (PR #333 머지)

카테고리 관리 모달의 이름 input에서 한글 IME 조합 중 자모 분리나 첫 글자 유실이 발생하던 문제를 수정했다. 직접 원인은 category input 자체보다 공용 `Modal`의 포커스 관리였다. `CategoryFormModal`이 매 렌더마다 새 `onClose` 함수를 `Modal`에 전달했고, `Modal`의 포커스 트랩 effect가 `[isOpen, onClose]`에 의존하면서 입력 중에도 cleanup과 재실행이 반복됐다. 그 cleanup에서 이전 활성 요소로 포커스를 돌리는 로직이 한글 조합 중간에 개입해 IME가 끊기고 있었다. 이번 수정에서는 `Modal`이 최신 `onClose`를 ref로 읽도록 바꾸고, 초기 포커스와 keydown 핸들러는 `isOpen` 기준으로만 설치되게 정리했다. 포커스 복원은 실제 모달 닫힘 전환에서만 실행되도록 분리했고, 카테고리 폼의 modal close handler도 `useCallback`으로 안정화했다. PR `#333`은 동기 `codex` 리뷰 1라운드 후 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/shared/ui/libs/modal.tsx`
  - 최신 `onClose`를 ref로 유지해 포커스 트랩 effect dependency에서 제거
  - 모달 open 시에만 초기 포커스와 ESC/Tab keydown 핸들러를 설치
  - 포커스 복원은 effect cleanup이 아니라 실제 close transition에서만 실행되도록 분리
- `src/features/category-manager/ui/category-form-modal.tsx`
  - modal에 전달하는 `onClose`를 `useCallback`으로 안정화
  - submit 중 close 차단 동작은 유지

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning은 기존 항목인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 2건만 남았다.
- issue worktree에는 의존성이 없어 verify 전에 `pnpm install --frozen-lockfile`로 worktree 전용 `node_modules`를 구성했다.

### #328 Category 이름 한글 IME 입력 시 manage error boundary 트립 회귀 수정 (PR #331 머지)

관리자 카테고리 모달에서 한글 IME 입력 중 화면이 `/manage/error.tsx` fallback으로 전환되던 회귀를 수정했다. 원인은 PR #327에서 추가한 composition 처리 패턴에 있었다. 카테고리 이름 입력이 `useState` 기반 composing 플래그에 의존하면서 `onChange` 클로저가 직전 렌더 상태를 참조했고, 동시에 composition 중 controlled input 값을 재기입하는 흐름이 섞여 있었다. 이번 수정에서는 ref 기반으로 composition 상태를 추적하는 `useImeSafeText()` 훅을 추가하고, composing 중에는 raw value를 그대로 state에 반영해 입력 표시를 유지하면서 transform은 일반 입력과 composition 종료 시점에만 적용하도록 정리했다. 같은 stale pattern이 있던 태그 입력도 함께 같은 훅으로 전환했다. PR `#331`은 동기 `codex` 리뷰 2라운드 후 clean 판정으로 머지됐다.

**주요 변경 사항:**

- `src/shared/hooks/use-ime-safe-text.ts`
  - ref 기반 IME-safe text hook 추가
  - composition 중에는 raw value를 유지하고, 일반 입력/`compositionend`에서는 caller transform을 적용
  - 모달 reopen 등 중간 종료 상황을 위한 composition reset 제공
- `src/features/category-manager/ui/category-form-modal.tsx`
  - 카테고리 이름 입력을 shared hook으로 전환
  - stale composing state 제거
  - NFC normalize를 commit 시점에만 적용
- `src/features/post-editor/ui/tag-chip-input.tsx`
  - 태그 입력의 composition 추적도 shared hook으로 통일
  - Enter/blur guard는 ref 기반 composing 상태를 직접 참조하도록 변경

**검증:**

- `pnpm install --offline --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning 2건은 기존 이슈로 유지됐다.
- `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 warning 1건
- `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 warning 1건

### #329 Public post list item 링크 구조 정리 (PR #330 머지)

public post list item이 `article` 내부에서 절대 위치 `Link` overlay와 실제 view 컨테이너가 형제 관계로 배치돼 있던 구조를 정리했다. 이번 수정에서는 overlay anchor를 제거하고, `Link`가 썸네일/메타/제목/요약을 포함한 실제 item view를 직접 감싸도록 마크업을 바꿨다. 바깥 `article`은 기존처럼 hover shift와 배경 hover shell로 유지하고, 기존 패딩과 클릭 영역은 `Link`로 옮겨 시각 구조와 DOM 의미론을 일치시켰다. PR `#330`은 동기 `codex` 리뷰 후 clean 판정으로 병합됐다.

**주요 변경 사항:**

- `src/features/post-list/ui/post-list-item.tsx`
  - 절대 위치 overlay `Link` 제거
  - `Link`가 실제 item view wrapper가 되도록 구조 변경
  - 기존 `px-4 py-5 sm:px-5` 클릭 영역을 `Link`로 이동
  - `article`의 hover animation/background 동작은 유지

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`

**메모:**

- `pnpm lint` warning은 기존 항목인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 2건만 남았다.
- issue worktree에는 의존성이 없어서 verify 전에 `pnpm install --frozen-lockfile`로 worktree 전용 `node_modules`를 구성했다.

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
