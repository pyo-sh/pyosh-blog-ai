# Client Progress - 2026-03-29

## 완료된 작업

### #260 PostListItem 디자인 리뉴얼 (PR #261 머지)

공개 글 목록 전반에서 재사용하는 `PostListItem`을 와이어프레임 `post-item` 패턴에 맞게 전면 개편했다. 홈, 카테고리, 태그, 검색 목록이 같은 리스트 구조를 공유하도록 카드형 보더 레이아웃을 걷어내고, `article + absolute Link overlay` 구조와 모바일 썸네일, 카테고리 pill, pin float, Solar 아이콘 메타 행을 적용한 뒤 자동 리뷰 clean 상태로 PR을 병합했다.

**주요 변경 사항:**

- `src/features/post-list/ui/post-list-item.tsx`
  - 루트를 `<article>`로 바꾸고 내부 absolute `<Link>` overlay로 전체 클릭 영역을 구성
  - `next/image`/`supportsNextImage` 분기와 커스텀 SVG 아이콘을 제거
  - 모바일 포함 `w-20 h-16`, `sm:w-32 sm:h-24` 썸네일 규격과 hover scale을 적용
  - 상단 메타 행을 pin 아이콘 + 카테고리 badge + 날짜 구조로 정리
  - 하단 메타 행을 Solar `eye` / `chat` 아이콘 + 숫자 구조로 변경
  - 하단 태그 배지와 수정일 표시는 제거
- `src/features/post-list/ui/post-list-item-skeleton.tsx`
  - 새 목록 레이아웃에 맞춰 썸네일, 메타 행, 제목, 요약, 통계 스켈레톤 구조를 갱신
- `src/app-layer/style/animation.css`
  - 리스트 hover `translateX(4px)`, 카테고리 shimmer, pin float 애니메이션을 추가
- `package.json`, `pnpm-lock.yaml`
  - Iconify React + Solar 아이콘 의존성을 추가

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
- 자동 `codex` 리뷰는 PR `#261`에서 `critical/warning/suggestion = 0`으로 종료되어 추가 resolve 라운드 없이 병합됐다.
