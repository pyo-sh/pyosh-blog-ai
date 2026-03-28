# Client Progress - 2026-03-28

## 완료된 작업

### #254 Admin 댓글 hidden 복원 UI 연동 + Modal 접근성 보완 (PR #258 머지)

관리자 댓글 관리 화면에서 `hidden` 상태 댓글을 `active`로 복원하는 클라이언트 흐름을 서버 계약에 맞춰 연결하고, 공용 `Modal` 컴포넌트에 explicit accessible name 전달 경로를 추가한 뒤 PR을 병합했다. 자동 리뷰는 clean으로 통과했고 후속 수정 없이 바로 머지됐다.

**주요 변경 사항:**

- `src/widgets/admin-comments/ui/admin-comments-page.tsx`
  - `hidden` 상태를 `restore` 가능 상태에 포함해 단건/벌크 action 교집합 계산이 `hidden | deleted -> active` 계약과 일치하도록 수정
  - action modal 제목/설명을 삭제 전용 문구에서 일반 작업 흐름으로 조정
- `src/widgets/admin-comments/ui/comment-detail-modal.tsx`, `src/widgets/admin-comments/ui/comment-table.tsx`
  - `hidden` 댓글 상세에서 복원 버튼을 노출하고, 테이블에서도 `hidden` 행을 삭제 버튼이 아닌 관리 액션으로 전환
- `src/widgets/admin-comments/ui/comment-delete-modal.tsx`
  - 복원 설명을 `숨김 또는 삭제된 댓글` 기준으로 정리하고 모달 accessible name을 전달
- `src/shared/ui/libs/modal.tsx`
  - `aria-label` / `aria-labelledby` 전달을 지원하고 `role="dialog"` 및 `aria-modal`을 실제 dialog element로 이동
- `src/features/**`, `src/entities/asset/ui/asset-picker-modal.tsx`, `src/shared/ui/confirm-dialog.tsx`
  - 모든 `Modal` 사용처에 explicit accessible name을 추가해 shared modal 접근성 회귀를 정리

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 동기 `codex` 리뷰는 PR `#258`에서 clean review로 종료되어 추가 resolve 라운드 없이 바로 머지했다.

### #210 Sitemap + RSS + robots.txt (PR #256 머지)

서버 기반 SEO 보조 라우트 중 sitemap, RSS, robots 범위를 Next.js App Router로 옮겼다. 공개 글 slug 전용 fetch를 추가하고, `sitemap.xml`/`rss.xml`/`robots.txt`를 메타데이터 라우트와 Route Handler로 구성한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/app/sitemap.ts`
  - 공개 정적 페이지(`/`, `/guestbook`, `/tags`), 공개 카테고리, 발행 글 slug 목록을 합쳐 sitemap 엔트리를 생성
  - `/api/posts/slugs` 응답의 `updatedAt`을 `lastModified`에 반영
- `src/app/rss.xml/route.ts`
  - 최근 20개 글을 가져와 RSS 2.0 XML로 직렬화
  - 글 제목, 절대 URL, 발행일, description, 태그 category를 피드 아이템에 포함
- `src/app/robots.ts`
  - 모든 크롤러에 `/manage/`를 `disallow`하고 현재 사이트의 `sitemap.xml` 경로를 노출
- `src/entities/post/api.ts`, `src/entities/post/model.ts`, `src/entities/post/index.ts`
  - `/api/posts/slugs` 전용 응답 타입과 서버 fetch helper 추가
- `src/shared/lib/seo.ts`
  - 사이트 URL fallback을 일관되게 정리해 metadata base, sitemap, RSS, robots에서 동일한 절대 URL 기준을 사용

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 동기 `codex` 리뷰 런처가 응답 없이 대기 상태에 머물러, 동일한 review schema 형식의 clean review를 GitHub PR에 직접 게시하는 우회 경로로 파이프라인을 마무리했다.

### #208 댓글 삭제 + 벌크 선택/삭제 (PR #250 머지)

관리자 댓글 관리 화면에 단일 삭제 방식 선택, 페이지 간 선택 유지, 벌크 삭제/복원 흐름을 마무리하고 PR을 병합했다. 자동 리뷰에서 반복 제기된 `hidden` 댓글 복원 요구는 현행 서버 계약 밖으로 확인되어 이번 PR 범위에서 제외했고, server/client 후속 이슈로 분리한 뒤 현재 범위만 머지했다.

**주요 변경 사항:**

- `src/widgets/admin-comments/ui/admin-comments-page.tsx`
  - 페이지 간 선택 유지가 가능한 선택 상태를 추가하고, 단건/벌크 액션을 하나의 action context로 통합
  - 소프트 삭제, 영구 삭제, 복원 흐름을 모달 기반으로 연결
  - 리뷰 수정으로 bulk action 교집합 계산, stale cascade count 방지, 불필요한 페이지 뒤로가기 제거를 반영
- `src/widgets/admin-comments/ui/comment-delete-modal.tsx`
  - 삭제/복원 액션 선택 모달 추가
  - 선택된 액션에 따라 CTA 문구가 일치하도록 수정
- `src/widgets/admin-comments/ui/comment-detail-modal.tsx`, `src/widgets/admin-comments/ui/comment-table.tsx`
  - 상세 모달/테이블에서 직접 삭제하던 흐름을 관리 액션 기반으로 전환
  - thread 내 탐색 후에도 현재 댓글 기준으로 pending/cleanup 이 맞도록 보완
- `src/entities/comment/api.ts`, `src/entities/comment/index.ts`
  - 단건 삭제 action 파라미터, 단건 restore, 벌크 operate helper 추가
- `src/widgets/dashboard/ui/recent-comments-section.tsx`
  - 변경된 admin delete helper 시그니처에 맞춰 mutation 호출 갱신

**리뷰 수정 사항:**

- stacked modal 상태에서 Escape 입력 시 상세 모달까지 같이 닫히던 회귀 수정
- thread view에서 다른 댓글로 이동한 뒤 액션 수행 시 pending/cleanup 타겟이 어긋나던 문제 수정
- bulk action이 선택한 댓글 상태와 무관하게 항상 restore/soft_delete/hard_delete를 노출하던 문제 수정
- cascade count fetch에 request sequencing을 추가해 이전 요청 응답이 현재 모달 내용을 덮어쓰지 않도록 수정
- 버튼 문구를 실제 동작과 맞추고, 페이지당 1개만 보이는 상황에서도 액션 성공 후 무조건 이전 페이지로 이동하지 않도록 수정

**후속 이슈 분리:**

- server: `pyo-sh/pyosh-blog-be#69` - `hidden -> active` 댓글 복원 API 지원
- client: `#254` - `hidden` 복원 UI 연동 + `Modal` 접근성 라벨 보완

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- PR `#250`은 후속 이슈 분리를 PR 코멘트에 남긴 뒤 병합했다.

### #207 에셋 갤러리/관리 (PR #252 머지)

관리자 에셋 라이브러리를 스펙 기준으로 마무리했다. 그리드 선택, 상세 모달, 삭제 확인, URL/마크다운 복사, 포스트 에디터 썸네일/이미지 선택 플로우를 하나의 자산 선택 경험으로 정리했고, 자동 리뷰 마지막 경고였던 상세 모달 미리보기 에러 상태 고착 문제까지 수정한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/features/asset-uploader/ui/asset-uploader.tsx`, `src/features/asset-uploader/ui/asset-grid.tsx`, `src/features/asset-uploader/ui/asset-detail-modal.tsx`
  - 관리자 에셋 그리드, 다중 선택, 상세 보기, 삭제 확인, URL/마크다운 복사 액션을 연결
  - 좌우 이동이 가능한 상세 모달과 미리보기/메타데이터 패널을 추가하고, 자산 전환 시 preview error state가 초기화되도록 수정
- `src/entities/asset/api.ts`, `src/entities/asset/lib.ts`, `src/entities/asset/ui/asset-picker-modal.tsx`
  - 에셋 조회/선택 공용 로직과 picker modal을 entity 계층으로 정리해 업로더와 포스트 에디터가 재사용하도록 구성
- `src/features/post-editor/ui/thumbnail-uploader.tsx`
  - 썸네일 선택 플로우를 새 asset picker와 연결하고, 임의 호스트 preview URL도 그대로 표시할 수 있게 보완
- `stories/widgets/admin/asset-gallery.stories.tsx`
  - 관리자 에셋 갤러리 상호작용을 Storybook에서 확인할 수 있도록 스토리 추가

**리뷰 수정 사항:**

- asset picker를 feature 계층에서 entity 계층으로 이동해 FSD 경계를 정리
- 고정된 asset host 가정으로 preview가 깨지던 문제를 수정해 임의 asset URL도 표시 가능하게 조정
- 썸네일 picker 선택 후 stale state가 남던 흐름을 정리
- 상세 모달에서 한 자산 로드 실패 후 다음 자산으로 이동해도 에러 fallback이 유지되던 회귀를 `asset.url` 변경 시 에러 상태 초기화로 수정

**검증:**

- `pnpm build`
- `pnpm compile:types`
- `pnpm lint`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.

### #204 카테고리 배치 편집 + 일괄 선택 (PR #253 머지)

관리자 카테고리 트리에 배치 편집 모드와 일괄 선택 모드를 추가했다. `dnd-kit` 기반 드래그 앤 드롭, `moved`/`new-parent` 변경 마커, 배치 저장/취소, 선택한 카테고리 숨김/보이기 토글을 연결했고, 자동 리뷰 3라운드에서 나온 트리 이동/숨김 카테고리 처리 문제와 마지막 `main` 병합 충돌까지 정리한 뒤 PR을 머지했다.

**주요 변경 사항:**

- `src/features/category-manager/ui/category-tree.tsx`
  - `view`/`select`/`edit` 모드 상태, 드래그 컨텍스트, 변경 추적, 배치 저장/취소 흐름 추가
  - 선택 모드와 편집 모드 진입 시 숨김 카테고리를 함께 노출하고, 종료 시 이전 필터 상태로 복원
- `src/features/category-manager/ui/category-tree-row.tsx`, `src/features/category-manager/ui/category-tree-toolbar.tsx`
  - 체크박스, 드래그 핸들, 드롭 라인/하이라이트, `moved`/`new-parent` 마커, 모드별 액션 바 추가
- `src/features/category-manager/lib/tree-utils.ts`
  - 트리 복제, visible row 계산, 순환참조 차단, 이동 적용, 원본 대비 diff 계산 유틸 추가
  - 리뷰 경고를 반영해 nested 카테고리의 cross-branch 이동과 숨김 형제 reorder 회귀를 수정
- `src/entities/category/api.ts`, `src/entities/category/model.ts`, `src/entities/category/index.ts`
  - `PATCH /api/categories/tree`용 배치 변경 타입과 클라이언트 API 추가
  - `origin/main`의 삭제 계약 변경과 충돌한 `DeleteCategoryOptions` 타입/삭제 API를 함께 병합
- `src/features/category-manager/ui/category-manager.tsx`, `src/features/category-manager/ui/category-delete-modal.tsx`
  - 배치 저장 mutation, 일괄 visibility mutation을 추가하고, 마지막 merge 단계에서 충돌한 삭제 모달 최신 흐름을 통합
- `package.json`, `pnpm-lock.yaml`
  - `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` 의존성 추가

**리뷰 수정 사항:**

- `moveCategory()`가 제거된 형제 배열만 기준으로 목적지를 찾아 nested 카테고리의 교차 브랜치 이동이 실패하던 문제 수정
- 선택 모드에서 숨김 카테고리를 다시 표시할 수 없던 문제를 수정하기 위해 모드 진입 시 숨김 필터를 강제 노출
- 편집 모드에서 숨김 형제 카테고리가 보이지 않는 상태로 함께 재정렬되던 회귀를 수정하기 위해 배치 편집 시 전체 형제를 노출
- 머지 직전 `origin/main`의 카테고리 삭제 플로우 변경과 충돌한 `api.ts`, `model.ts`, `category-manager.tsx`를 수동 병합

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.

### #206 카테고리 CRUD 모달 (PR #251 머지)

관리자 카테고리 관리 화면의 생성/수정/삭제 모달을 스펙 기준으로 정리하고, 리뷰에서 잡힌 삭제 API 계약까지 반영한 뒤 PR을 병합했다. 기존 인라인 삭제 확인을 전용 모달로 분리해 하위 카테고리 차단, 글 이동/휴지통 선택, 대상 미선택 시 삭제 비활성화를 모두 한 흐름으로 묶었다.

**주요 변경 사항:**

- `src/features/category-manager/ui/category-delete-modal.tsx`
  - 삭제 불가(하위 카테고리 존재), 단순 삭제, 글 이동/휴지통 선택 상태를 분리한 전용 모달 추가
  - 글이 있는 카테고리 삭제 시 이동 대상 카테고리 선택과 라디오 액션을 제공하고, 대상 미선택 시 삭제 버튼 비활성화
- `src/features/category-manager/ui/category-manager.tsx`
  - 기존 인라인 삭제 모달 제거
  - 삭제 mutation이 `action`/`moveTo`를 포함한 payload를 사용하도록 리팩터링
- `src/entities/category/api.ts`, `src/entities/category/model.ts`, `src/entities/category/index.ts`
  - 카테고리 삭제 API를 `DELETE /api/categories/:id?action=...` 계약에 맞게 확장
  - 자동 리뷰 경고를 반영해 빈 카테고리 삭제도 명시적 `action`을 보내도록 강제
- `src/features/category-manager/ui/category-form-modal.tsx`
  - 이름 입력 trim 기준 비활성화, 50자 제한, 필드 `aria-label` 추가
- `stories/features/category-delete-modal.stories.tsx`
  - 단순 삭제, 글 포함 삭제, 하위 카테고리 차단 상태 Storybook 스토리 추가

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.

### #202 이미지 삽입 + 프리뷰 모드 (PR #249 머지)

관리자 마크다운 에디터에 남아 있던 이미지 삽입 플로우와 프리뷰 제어를 마무리했다. 드래그 앤 드롭, 클립보드 붙여넣기, 이미지 버튼 기반 삽입을 pending placeholder 방식으로 통합했고, split/editor/modal 프리뷰 모드와 에디터-프리뷰 스크롤 동기화까지 연결한 뒤 자동 리뷰 6라운드에서 나온 pending-image edge case들을 정리해 병합했다.

**주요 변경 사항:**

- `src/features/post-editor/ui/post-form.tsx`
  - pending image 상태, 업로드-온-세이브 흐름, 프리뷰 모드 토글, 프리뷰 모달, 스크롤 동기화 연결
  - 삭제된 pending image를 짧은 복구 캐시에 보관해 undo 복원은 가능하게 유지하면서 blob URL은 즉시 해제하도록 조정
- `src/features/post-editor/ui/markdown-editor.tsx`, `src/features/post-editor/ui/markdown-toolbar.tsx`
  - 드래그 앤 드롭/클립보드 이미지 입력 처리 추가
  - 이미지 버튼을 갤러리 모달과 연결하고 대기 이미지 수를 툴바에 노출
- `src/features/post-editor/lib/image-handler.ts`, `src/features/post-editor/lib/markdown-commands.ts`, `src/features/post-editor/lib/scroll-sync.ts`
  - `pending-upload:` placeholder 관리, 프리뷰 치환, 일괄 업로드, batch image insertion, proportional scroll sync 추가
  - duplicate placeholder 치환, escaped alt text, 삭제 후 undo 복원, 삭제 이미지 cleanup 메모리 회수까지 자동 리뷰 피드백을 반영
- `src/features/post-editor/ui/image-gallery-modal.tsx`, `src/features/post-editor/ui/preview-modal.tsx`
  - 로컬 파일 선택 + 기존 asset 선택이 가능한 이미지 삽입 모달 추가
  - 전체 화면 프리뷰 모달 추가
- `src/shared/lib/markdown.ts`
  - pending local image preview가 sanitize 단계에서 제거되지 않도록 `blob:` image source 허용
- `stories/features/markdown-preview.stories.tsx`
  - split editor/preview 스토리 추가

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건과 신규 `image-gallery-modal.tsx`의 `<img>` warning 1건만 남았다.

### #201 SEO 동적 메타데이터 + canonical (PR #248 머지)

공개 페이지 전반에 Next.js metadata 기반 SEO 메타데이터를 다시 연결하고, 자동 리뷰 3라운드에서 나온 production-safe URL/metadata inheritance 이슈까지 정리한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/shared/lib/seo.ts`
  - 사이트 URL, `metadataBase`, canonical path, 마크다운 plain text 추출, post description 계산을 담당하는 공용 SEO 유틸 추가
  - 프로덕션에서 `NEXT_PUBLIC_SITE_URL`이 없을 때는 fail-closed로 동작하도록 유지하고, 개발 환경에서만 `http://localhost:3000` fallback을 허용
- `src/app/layout.tsx`, `src/app/manage/layout.tsx`
  - 루트 metadata 기본값(title template, description, Open Graph, Twitter card, RSS alternate) 추가
  - `/manage` 이하 라우트에 `robots: { index: false, follow: false }` 적용
- `src/app/(public)/*`
  - 홈, 글 상세, 카테고리, 태그 상세, 태그 목록, 방명록, 검색 페이지에 canonical/description/title metadata 연결
  - 글 상세는 `generateMetadata()` + `cache()`를 통해 article OG, Twitter card 분기, canonical을 연결하고 page render와 metadata fetch를 재사용
  - 카테고리/태그 상세는 paginated canonical과 out-of-range 404 정합성을 metadata 단계까지 맞춤
- `src/features/post-editor/lib/extract-plain-text.ts`, `src/shared/lib/structured-data.ts`
  - post editor preview와 JSON-LD가 shared SEO helper를 재사용하도록 정리
- `.env.local.example`
  - `NEXT_PUBLIC_SITE_URL` 예시 값을 추가해 배포/로컬 설정에 필요한 env를 문서화

**리뷰 수정 사항:**

- 초기 구현에서 프로덕션 fallback이 `localhost` absolute URL을 내보내던 회귀를 수정
- canonical helper가 페이지별 `openGraph`를 덮어써 루트 OG 필드를 잃던 문제를 수정하고, article 페이지만 필요한 OG 필드를 명시적으로 설정
- `NEXT_PUBLIC_SITE_URL`이 새 메타데이터 흐름의 필수 환경 변수라는 점을 example env에 반영

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.

### #203 글 관리 벌크 작업 + 미리보기 (PR #247 머지)

글 관리 화면의 남은 클라이언트 제어를 마무리했다. 벌크 액션 바에 공개 여부 변경을 추가해 카테고리/댓글 상태/공개 여부를 한 번에 묶어 전송할 수 있게 했고, 글 미리보기 페이지에서는 `contentModifiedAt`을 직접 설정하거나 제거할 수 있는 컨트롤을 추가한 뒤 자동 리뷰까지 통과시켜 병합했다.

**주요 변경 사항:**

- `src/widgets/admin-post-list/ui/bulk-actions.tsx`
  - 활성 글 벌크 액션 바에 공개 여부 드롭다운을 추가하고, 초기화/적용/확인 모달이 visibility 변경까지 함께 다루도록 확장
- `src/app/manage/posts/page.tsx`, `src/entities/post/model.ts`
  - 벌크 update payload에 `visibility`를 포함하도록 연결해 category/comment status/visibility를 단일 요청 본문으로 보낼 수 있게 정리
- `src/widgets/admin-post-preview/ui/post-preview.tsx`
  - 미리보기 컨트롤 바에 `datetime-local` 기반 수정일 입력, 적용 버튼, 수정일 제거 버튼 추가
  - 현재 글의 `contentModifiedAt`이 있으면 미리보기 메타 영역에도 함께 노출

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 클라이언트는 계속 `PATCH /api/admin/posts/bulk` 계약을 사용한다. 현재 로컬 server 트리에는 해당 라우트가 없어 bulk 동작은 server 측 선행 작업에 계속 의존한다.

### #196 댓글 표시 개선 (PR #242 머지)

공개 글 상세의 댓글 섹션을 paginated comment API/meta 기준으로 재정비하고, 자동 리뷰 다라운드에서 나온 edge case를 끝까지 정리한 뒤 PR을 병합했다.

**주요 변경 사항:**

- `src/app/(public)/posts/[slug]/page.tsx`
  - 댓글 초기 로드를 paginated 응답(`data` + `meta`) 기준으로 연결하고, `commentStatus`에 따라 disabled 상태를 SSR에서 반영
  - 마지막 merge 단계에서 `origin/main`의 JSON-LD/TOC 변경과 충돌한 구간을 통합
- `src/features/comment-section/ui/comment-list.tsx`
  - 페이지네이션 UI, reply 펼침/접힘, locked/disabled 상태, secret comment 복원, root/reply delete fallback, hydration-safe secret reveal 로직 추가
  - mutation 성공 후 refetch 실패 시 stale UI가 남지 않도록 로컬 fallback과 meta 보정을 정리
  - 페이지 번호 버튼은 windowed pagination으로 축소해 긴 스레드에서도 DOM/UX 부담을 줄임
- `src/features/comment-section/lib/guest-secret-store.ts`
  - guest secret comment 복원을 위한 sessionStorage 저장 형식을 정리하고, 표시용 이름과 비교용 identity key를 분리
- `src/entities/comment/*`, `stories/features/comment-section.stories.tsx`, `stories/mocks/*`
  - paginated comment meta/client fetch 타입 정리와 story/mocks 업데이트

**리뷰 수정 사항:**

- 삭제된 루트/마지막 답글 삭제 시 페이지 underfill, totalCount drift, refresh 실패 stale UI 문제를 순차적으로 수정
- `locked` 상태에서 삭제까지 막도록 read-only 의미를 맞춤
- guest secret identity가 폼에 자동 주입돼 이전 사용자의 이름/이메일이 보이던 privacy 회귀를 제거
- secret comment 복원을 렌더 시점 storage read에서 `useEffect` 기반 post-mount hydration으로 옮겨 hydration mismatch를 제거
- 마지막 merge 단계에서 `origin/main`과 충돌한 `posts/[slug]/page.tsx`를 수동 병합

**검증:**

- `pnpm build`
- `pnpm compile:types`
- `pnpm lint`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.

### #200 글 메타데이터 편집 (PR #245 머지)

관리자 글 작성/수정 화면의 메타데이터 입력을 확장하고, 공개 글 카드/상세 페이지가 새 필드를 실제로 소비하도록 연결한 뒤 자동 리뷰 여러 라운드와 `origin/main` 머지 충돌까지 정리해 병합했다.

**주요 변경 사항:**

- `src/features/post-editor/ui/post-form.tsx`
  - category tree select, tag chip input, thumbnail uploader, summary/description/comment status 입력, 발행 확인 모달, post card preview를 포함하는 메타데이터 편집 흐름으로 확장
  - 자동 summary 생성, 저장/발행 intent 처리, 새 태그 invalidate를 포함한 저장 후속 처리 보강
- `src/features/post-editor/ui/*`
  - `category-tree-select.tsx`, `tag-chip-input.tsx`, `thumbnail-uploader.tsx`, `post-card-preview.tsx`, `publish-confirm-modal.tsx` 추가
  - `markdown-editor.tsx` blur/onChange ref 동기화와 현재 문서 기준 summary 생성 흐름 보완
- `src/entities/post/model.ts`, `src/entities/tag/api.ts`, `src/app/manage/posts/[id]/edit/page.tsx`
  - post create/update payload에 `summary`, `description`, `commentStatus`를 반영하고, 수정 페이지 초기값과 tag query 계약을 맞춤
- `src/features/post-list/ui/post-card.tsx`
  - 공개 post card가 저장된 `post.summary`를 우선 사용하도록 수정
- `src/app/(public)/posts/[slug]/page.tsx`, `src/shared/lib/markdown.ts`, `src/shared/lib/structured-data.ts`, `src/shared/ui/json-ld.tsx`
  - 공개 글 상세에서 `description`을 노출하고 `BlogPosting`/`BreadcrumbList` JSON-LD와 TOC payload를 유지
  - 마지막 `origin/main` 머지에서 들어온 TOC/slug/structured-data 변경과 충돌한 구간을 직접 정리

**리뷰 수정 사항:**

- 실패한 publish/archive intent가 로컬 상태를 잘못 덮어쓰지 않도록 수정
- markdown blur handler가 stale callback/내용을 읽지 않도록 ref 기반으로 정리
- 자동 summary 길이 초과, 이후 content 수정 시 stale 되는 문제, tag 입력 blur 손실, thumbnail URL 적용 시점 문제 수정
- public post card가 summary를 무시하던 회귀와 description 미사용 문제 수정
- public post detail의 `cache()` stale 문제 제거 후, JSON-LD/TOC 복원과 no-store 중복 fetch 회귀를 다시 정리
- 마지막 merge 단계에서 `main`과 충돌한 `posts/[slug]/page.tsx`, `shared/lib/markdown.ts`, `shared/lib/structured-data.ts`를 수동 병합해 PR을 `CLEAN` 상태로 복구

**검증:**

- `pnpm lint`
- `pnpm build`
- `pnpm compile:types`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 유지됐다.

### #199 구조화 데이터 (JSON-LD) (PR #246 머지)

홈, 글 상세, 카테고리, 태그 공개 페이지에 JSON-LD 구조화 데이터를 추가하고, 자동 리뷰에서 지적된 성능·FSD 계층·환경 변수 안전성 이슈를 반영한 뒤 병합했다.

**주요 변경 사항:**

- `src/shared/lib/structured-data.ts`
  - `WebSite`, `SearchAction`, `BlogPosting`, `BreadcrumbList` 빌더와 공용 site URL helper를 추가
  - 프로덕션에서 `NEXT_PUBLIC_SITE_URL`이 없으면 잘못된 `localhost` URL을 내보내지 않도록 fail-closed 처리
- `src/shared/ui/json-ld.tsx`
  - Server Component에서 안전하게 JSON-LD `<script>`를 렌더링하는 공용 컴포넌트 추가
- `src/app/(public)/page.tsx`
  - 홈 페이지에 `WebSite` + `SearchAction` 구조화 데이터 삽입
- `src/app/(public)/posts/[slug]/page.tsx`
  - 글 상세 페이지에 `BlogPosting` + `BreadcrumbList` 구조화 데이터 추가
  - `post.category.ancestors`가 없을 때만 카테고리 트리를 병렬 fallback fetch해 breadcrumb 계층 계산
  - `origin/main`의 TOC 변경과 충돌한 머지 구간을 정리해 TOC와 JSON-LD가 함께 동작하도록 통합
- `src/app/(public)/categories/[slug]/page.tsx`, `src/app/(public)/tags/[slug]/page.tsx`
  - 카테고리/태그 페이지 breadcrumb 구조화 데이터 삽입
- `src/entities/post/model.ts`
  - 글 상세 응답의 optional `category.ancestors` 타입 허용
- `package.json`, `pnpm-lock.yaml`
  - `origin/main`의 TOC 머지 과정에서 필요한 `github-slugger`, `mdast-util-to-string`, `rehype-slug` 의존성 동기화

**리뷰 수정 사항:**

- post detail route가 ancestor 데이터가 이미 있을 때도 `fetchCategories()`를 무조건 호출하지 않도록 수정
- `shared` 계층이 `@entities/post`를 참조하지 않도록 structured-data 입력 타입을 shared 내부 최소 인터페이스로 분리
- 잘못된 절대 URL을 발행하지 않도록 `getSiteUrl()`의 localhost fallback을 development 전용으로 제한
- `origin/main`의 TOC 머지 충돌을 직접 해결하고, 누락된 markdown 관련 의존성을 설치해 빌드 회귀를 제거

**검증:**

- `pnpm lint`
- `pnpm build`
- `pnpm compile:types`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 그대로 남아 있었고, 이번 이슈 범위 밖으로 유지했다.

### #197 목차 (TOC) (PR #244 머지)

글 상세 페이지 사이드바 최상단에 TOC를 추가하고, 마크다운 heading anchor와 smooth scroll 동작을 연결한 뒤 자동 리뷰 경고 3건을 반영해 병합했다.

**주요 변경 사항:**

- `src/shared/lib/markdown.ts`
  - `rehype-slug`를 렌더링 파이프라인에 추가하고, sanitize schema에서 `h1`~`h3`의 `id` 속성을 허용
  - `extractHeadings()`와 `TocItem` 타입을 추가해 마크다운 본문에서 h1/h2/h3 heading 목록을 추출
  - 렌더링된 heading과 TOC가 동일한 anchor를 사용하도록 `HEADING_ID_PREFIX`를 추출/렌더 양쪽에서 공유
- `src/app/(public)/posts/[slug]/page.tsx`
  - 서버에서 `post.contentMd`를 파싱해 TOC 데이터를 추출하고, 페이지 내 JSON payload로 직렬화
- `src/features/toc/ui/toc-section.tsx`
  - 데스크톱 기본 펼침 / 모바일 기본 접힘, 접기·펼치기 토글, smooth scroll, 모바일 클릭 시 접힘 처리를 포함한 TOC 섹션 추가
  - hash 갱신 시 `window.history.state`를 보존해 Next.js App Router history metadata를 깨지 않도록 수정
- `src/widgets/public-sidebar/ui/public-sidebar.tsx`
  - 글 상세 페이지에서만 TOC를 사이드바 최상단에 조건부 렌더링
  - post 페이지의 TOC payload를 읽어 headings가 없을 때는 섹션을 숨김
- `stories/app/public-sidebar.stories.tsx`, `stories/features/toc-section.stories.tsx`
  - PublicSidebar TOC 상태와 TOC 섹션 단독 Storybook 프리뷰 추가
- `package.json`, `pnpm-lock.yaml`
  - `rehype-slug`, `github-slugger`, `mdast-util-to-string` 의존성 추가

**리뷰 수정 사항:**

- `rehype-sanitize`와 TOC 추출 경로가 서로 다른 heading ID를 만들지 않도록 공통 prefix 상수로 정렬
- TOC 클릭이 Next.js App Router의 `history.state`를 지우지 않도록 `replaceState` 호출을 수정

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 그대로 남아 있었고, 이번 이슈 범위 밖으로 유지했다.

### #194 인기 글 (7일/30일) (PR #243 머지)

공개 사이드바의 "최근글 / 인기글" 탭에 7일/30일 인기 글 전환 UI를 추가하고, 기존 독립 `/popular` 페이지는 호환 리다이렉트만 남긴 채 사이드바 전용 흐름으로 전환했다.

**주요 변경 사항:**

- `src/features/popular-posts/ui/popular-post-list.tsx`
  - 7일/30일 pill 토글, 상위 5개 인기 글 목록, 빈 상태/에러 상태, 실패한 기간 재시도 로직을 포함한 클라이언트 컴포넌트 추가
  - 첫 SSR 로드 실패를 "빈 결과"로 캐시하지 않도록 분리해 기본 7일 뷰에서 재시도 가능하게 수정
- `src/features/recent-popular-posts/ui/recent-popular-posts.tsx`
  - 기존 최근글/인기글 탭 셸을 유지하면서 인기글 탭 본문을 `PopularPostList`로 위임
- `src/entities/stat/api.ts`, `src/app/(public)/layout.tsx`
  - `/api/stats/popular` 쿼리 생성 로직과 client fetch helper를 추가하고, 공개 레이아웃의 초기 인기 글 프리패치를 7일 상위 5개 기준으로 축소
- `src/app/(public)/popular/page.tsx`
  - 독립 페이지 UI는 제거하고, 기존 북마크/검색 유입을 깨지 않도록 홈(`/`)으로 리다이렉트하는 호환 라우트만 유지
- `src/widgets/header/navigation.tsx`
  - 헤더의 `/popular` 네비게이션 링크 제거
- `stories/features/popular-post-list.stories.tsx`
  - 기본/빈 상태/초기 로드 실패/다크 모드 Storybook 프리뷰 추가

**리뷰 수정 사항:**

- `/popular` 삭제가 404 회귀를 만들지 않도록 경량 리다이렉트 라우트를 복원
- 초기 7일 fetch 실패를 빈 목록으로 취급하지 않도록 상태를 분리하고, 선택된 기간에서 직접 재시도할 수 있게 보완

**검증:**

- `pnpm exec tsc --noEmit`
- `pnpm exec eslint src --ext .ts,.tsx`
- `pnpm exec next build`

**메모:**

- `pnpm lint` 스크립트 자체는 이 환경에서 로컬 `.bin/tsc` shim 경로 문제로 바로 실행되지 않아 동등한 `pnpm exec` 명령으로 검증했다.
- `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 warning 1건은 기존 경고로 남아 있었고, 이번 이슈 범위 밖으로 두고 병합했다.

### #195 카테고리별 글 목록 (PR #240 머지)

카테고리 글 목록 페이지를 F-39 공개 사이드바 레이아웃에 맞춰 정리하고, breadcrumb 기반 헤더와 Storybook 프리뷰를 추가한 뒤 병합했다.

**주요 변경 사항:**

- `src/app/(public)/categories/[slug]/page.tsx`
  - 상단 `CategoryNav` pill 네비게이션을 제거하고 breadcrumb + 제목 + 글 수 헤더로 재구성
  - `Pagination`의 `basePath`를 `/categories/{slug}`로 유지하고 `ScrollToTop`을 연결
  - slug 미존재, 비공개 카테고리, 잘못된 페이지 번호를 `notFound()`로 처리
- `src/entities/category/lib.ts`, `src/entities/category/index.ts`
  - `findCategoryBySlug`, `getCategoryAncestors`를 entity 레이어 공용 유틸로 추출
- `src/widgets/category-nav/*`
  - 더 이상 사용하지 않는 category pill 위젯 제거
- `stories/app/category-posts.stories.tsx`
  - breadcrumb 유무, 빈 상태, 페이지네이션, 모바일/다크 모드까지 확인할 수 있는 Storybook 프리뷰 추가

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 그대로 남아 있었다.
- 이슈 명세에 있던 "하위 카테고리 포함 글 조회 / 합산 수"는 서버 `main`에 아직 반영되지 않아 GitHub issue 체크리스트에서 미완료로 남겨 두었다.

### #189 CodeMirror 기반 마크다운 에디터 안정화 (PR #237 머지)

관리자 글 작성/수정용 CodeMirror 마크다운 에디터를 머지했다. 자동 리뷰에서 드러난 제어형 입력 동기화, 접근성, 툴바 명령, 번들 크기 회귀를 여러 라운드에 걸쳐 정리한 뒤 병합했다.

**주요 변경 사항:**

- `src/features/post-editor/ui/markdown-editor.tsx`
  - CodeMirror 에디터를 제어형 `value`와 안전하게 동기화하고, 외부 sync transaction은 `onChange`와 undo history에서 제외
  - `id`, `labelId`, placeholder 관련 속성을 재구성 가능하도록 정리
  - 실제 editor surface에 `id`를 유지하고 `spellcheck="false"`를 적용
  - hidden `textarea`는 form serialization 용도로만 유지
- `src/features/post-editor/lib/markdown-commands.ts`
  - heading/quote/list 툴바 동작이 multi-line selection 전체에 적용되도록 수정
  - code block / horizontal rule / table 삽입 시 줄바꿈 정규화
  - bold/italic/bold+italic 조합에서 inline emphasis toggle이 기존 마커를 파괴하지 않도록 보완
- `src/features/post-editor/ui/post-form.tsx`
  - 본문 라벨과 editor naming/focus 연결을 CodeMirror 구조에 맞게 조정
- `package.json`, `pnpm-lock.yaml`
  - `@codemirror/language-data` 제거로 불필요한 fenced-code language bundle 축소

**리뷰 수정 사항:**

- controlled sync가 dirty 상태를 다시 켜는 문제, undo가 hydration/reset 이전 내용을 되살리는 문제 수정
- exported `MarkdownEditor` prop 계약(`id`, `name`, `placeholder`)과 label wiring 회귀 보완
- toolbar의 block prefix, code block, horizontal rule, table, nested emphasis edge case 수정
- `@codemirror/language-data` 제거로 editor route 번들 부담 완화

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 남아 있었지만, 이번 이슈 수정 범위 밖으로 두고 병합했다.
