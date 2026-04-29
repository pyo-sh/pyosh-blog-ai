# Progress: 2026-04-29

## Completed

- [x] #365 Windows에서 `NanumSquareNeo` UI 폰트 렌더링이 더 예측 가능하도록 variable WOFF2를 static weight WOFF2 구성으로 교체하고 PR #366 머지
- [x] #363 블로그 전역/UI 폰트를 자체 호스팅 `NanumSquareNeo`로 전환하고 게시글 제목/본문 및 관리자 미리보기에 `MaruBuri`를 적용한 뒤 PR #364 머지
- [x] #360 관리자 카테고리 일괄 선택 모드에 삭제 액션을 추가하고 PR #362 머지
- [x] #359 관리자 카테고리 배치 편집에서 3-depth 하위 노드를 상위 부모로 이동할 때 중간 노드가 working tree UI에서 사라지는 문제를 수정하고 PR #361 머지

## Discoveries

- `NanumSquareNeo` static 배포본은 300/400/700/800/900 weight만 제공하므로 앱에서 널리 쓰는 Tailwind `font-medium`(500), `font-semibold`(600)을 별도 `@font-face` alias로 명시해야 브라우저별 synthetic matching 차이를 줄일 수 있다.
- Google Fonts import 제거 후에는 CSP report-only 정책의 `fonts.googleapis.com`/`fonts.gstatic.com` allowlist도 함께 제거해야 자체 호스팅 폰트 모델과 정책이 일치한다.
- 게시글 본문 클래스인 `.post-markdown`을 에디터 preview와 관리자 post preview에도 붙여야 실제 공개 상세와 미리보기 사이의 마크다운 렌더링 차이가 줄어든다.
- 카테고리 벌크 삭제 서버 계약은 `DELETE /categories/bulk` + JSON body `{ ids, action, moveTo? }`이며, 단건 삭제와 동일한 move/trash 정책을 클라이언트에서 먼저 안내해야 한다.
- `removeCategory()`는 대상의 직접 부모 `children` 배열을 `splice()`로 이미 갱신하므로, 재귀 복귀 중 `result.tree`를 상위 조상의 `children`에 다시 대입하면 조상 트리 구조가 손상된다.

## Issues & Resolutions

- **Issue**: `NanumSquareNeo-Variable.woff2` 단일 파일은 Windows에서 UI 텍스트가 macOS보다 딱딱하게 보이고 렌더링 차이가 크게 체감됨
- **Resolution**: `NanumSquareNeoTTF-aLt/bRg/cBd/dEb/eHv.woff2` static 파일로 교체하고 300/400/700/800/900을 weight별 `@font-face`로 등록
- **Issue**: 자동 리뷰에서 static 전환 후 앱의 500/600 weight 요청이 등록되지 않아 브라우저별 synthetic matching으로 흐를 수 있다고 지적
- **Resolution**: 500은 Regular static 파일, 600은 Bold static 파일에 명시적으로 alias 등록해 기존 `font-medium`/`font-semibold` 요청을 deterministic하게 처리
- **Issue**: 전역 UI와 게시글 본문이 모두 `Gothic A1` Google Fonts import와 산세리프 fallback에 의존해 역할 기반 타이포그래피를 분리하지 못함
- **Resolution**: `public/fonts/**`에 `NanumSquareNeo`/`MaruBuri` woff2 파일을 추가하고 `--font-ui`, `--font-serif`, `--font-mono` 토큰을 정의해 UI/목록/관리자 숫자 표기는 UI 토큰으로, 게시글 제목/본문과 미리보기는 serif 토큰으로 정리
- **Issue**: 자동 리뷰에서 자체 호스팅 폰트 전환 뒤에도 CSP report-only 정책에 Google font origin이 남아 있다고 지적
- **Resolution**: `src/middleware.ts`의 `style-src`/`font-src`에서 `fonts.googleapis.com`과 `fonts.gstatic.com`을 제거해 self-hosted font 정책과 CSP를 맞춤
- **Issue**: 일괄 선택 하단 액션 바에 선택한 카테고리를 한 번에 삭제하는 액션이 없고, 글이 있거나 하위 카테고리가 있는 선택 조합을 안전하게 처리할 UI가 없음
- **Resolution**: `deleteCategories(ids, options)` API helper를 추가하고, 선택 모드 삭제 버튼 + 벌크 삭제 모달을 연결해 하위 카테고리 포함 시 차단, 글 포함 시 move/trash 선택, 이동 대상에서 삭제 대상을 제외하도록 구현
- **Issue**: `테스트1 > 테스트2 > 테스트3`에서 `테스트3`을 `테스트1`의 자식으로 이동하면 재귀 복귀 중 `테스트1.children`이 `테스트2.children` 결과로 덮여 `테스트2`가 UI에서 누락됨
- **Resolution**: `removeCategory()` 반환값을 제거된 카테고리만 담도록 축소하고, 상위 재귀 호출에서 직접 부모의 child list를 조상에게 재대입하지 않도록 정리

## Verification

- #365: `fc-scan`으로 NanumSquareNeo static WOFF2가 non-variable TrueType 기반임을 확인, `pnpm compile:types`, `pnpm lint` (기존 warning 2건 유지), `pnpm build`, 자동 리뷰 warning 1건 반영 후 재리뷰 clean, PR #366 머지
- #363: `pnpm compile:types`, `pnpm lint` (기존 warning 2건 유지), `pnpm build`, 자동 리뷰 suggestion 1건 반영 후 재검증, PR #364 머지
- #360: `pnpm compile:types`, `pnpm lint` (기존 warning 2건 유지), `pnpm build`, 자동 리뷰 clean
- `node --experimental-strip-types` one-off fixture: 3-depth inside 이동, cross-level before 이동, 동일 부모 before 이동, `calculateTreeChanges()` 결과 확인
- `pnpm compile:types`
- `pnpm lint` (기존 warning 2건 유지)
- `pnpm build`
