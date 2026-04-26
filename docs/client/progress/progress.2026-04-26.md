# Client Progress - 2026-04-26

## 완료된 작업

### #340 Public sidebar 카테고리 섹션 정리 및 active path auto-expand (PR #341 머지)

public sidebar의 category 섹션을 카테고리 탐색 중심 흐름으로 정리했다. 섹션 제목을 `카테고리 (N)`으로 단축하고 `/categories`로 이동하는 `전체보기` 액션을 추가했으며, category tree는 기본적으로 모두 접힌 상태에서 시작하도록 바꿨다. `/categories/[slug]`와 `/posts/[slug]`에서는 현재 카테고리 경로만 자동으로 펼쳐지도록 route별 sidebar seed 데이터를 내려 보내고, tree 내부에서는 그 seed를 초기 상태로만 사용해 사용자가 직접 토글한 이후 상태를 같은 렌더링 흐름에서 덮어쓰지 않도록 분리했다.

자동 리뷰 1차에서는 `CategoryTree`의 `initialExpandedSlugs = []` 기본값이 prop 생략 호출자에서 무한 렌더 루프를 만들 수 있다는 warning이 나왔다. 이에 따라 안정적인 module-level 빈 배열 fallback으로 수정하고, 다시 `compile:types`, `lint`, `build`를 확인한 뒤 재리뷰 clean 판정으로 PR `#341`를 머지했다.

**주요 변경 사항:**

- `src/widgets/public-sidebar/ui/public-sidebar.tsx`
  - category 섹션 제목을 `카테고리 (N)`으로 변경
  - `/categories`로 이동하는 `전체보기` 액션 추가
  - post/category page에서 주입한 sidebar category path JSON을 읽어 tree 초기 확장 slug를 계산
- `src/features/category-tree/ui/category-tree.tsx`
  - 토글 상태를 item local state에서 tree root state로 승격
  - route seed 기반 `initialExpandedSlugs` 지원
  - prop 생략 시 무한 렌더를 막는 stable empty fallback 추가
- `src/app/(public)/posts/[slug]/page.tsx`
  - 현재 글 category path slug를 sidebar용 JSON script로 주입
- `src/app/(public)/categories/[slug]/page.tsx`
  - 현재 category path slug를 sidebar용 JSON script로 주입

**검증:**

- `pnpm install`
- `pnpm build`
- `pnpm compile:types`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*

**메모:**

- `pnpm compile:types`는 이 저장소의 `.next/types` 포함 규칙 때문에 `pnpm build` 완료 후 순차 실행했다.
- 남아 있는 lint warning 2건은 기존 이슈와 동일하게 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용이다.

### #337 public 비밀글 안내 문구 한글화 (PR #339 머지)

public 댓글 비밀글이 영어 문구 `This comment is secret.` 으로 노출되던 문제를 client 이슈 `#337` 기준으로 정리했다. 클라이언트 코드 검색 결과 비밀글 마스크 판별은 `src/features/comment-section/ui/comment-list.tsx` 한 곳에서만 이뤄지고 있었고, 여기서는 한국어 sentinel `비공개 메시지입니다` 만 비밀글 마스크로 취급하고 있었다. 이번 수정으로 legacy 영어/한국어 마스크 문자열은 모두 비밀글로 인식하되, 실제 사용자 표시 문구는 항상 `비공개입니다.` 로 통일했다.

자동 리뷰 1차에서는 새 표시 문구 자체를 sentinel alias에 포함하면 실제 댓글 본문과 충돌할 수 있다는 suggestion이 나왔다. 이에 따라 판별 alias는 기존에 알려진 영어/이전 한국어 마스크만 유지하고, 렌더링 시에만 새 문구 `비공개입니다.` 를 사용하도록 보정했다. 재리뷰 후 clean 판정으로 PR `#339`를 머지했다.

**주요 변경 사항:**

- `src/features/comment-section/ui/comment-list.tsx`
  - 비밀글 표시 문구를 `비공개입니다.` 로 통일
  - legacy 영어 마스크 `This comment is secret.` 지원 추가
  - 이전 한국어 마스크 `비공개 메시지입니다` 도 계속 지원
  - 표시 문구와 비밀글 판별 sentinel을 분리해 실제 댓글 본문과의 충돌 가능성 축소

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`
- `pnpm compile:types`

**메모:**

- client 코드 기준 동일 런타임 판별 지점은 `comment-list.tsx` 한 곳뿐이었다.
- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
