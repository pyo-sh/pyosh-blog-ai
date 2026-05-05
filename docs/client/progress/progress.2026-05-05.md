# Client Progress — 2026-05-05

## #376 Client 데이터 로딩 및 query key 정책 표준화

- Issue: pyo-sh/pyosh-blog-fe#376
- PR: pyo-sh/pyosh-blog-fe#386
- 상태: 머지 완료

### 작업 내용

- `src/entities/*/query-keys.ts`에 public/admin namespace가 분리된 query key factory를 추가했다.
- 관리자 글 목록/detail/pinned count, 관리자 카테고리 tree, 관리자 에셋 list, 관리자 댓글 list/recent dashboard, 관리자 방명록 list/settings, dashboard stats key를 공유 factory 기반으로 교체했다.
- public 글 목록과 public tag list key도 factory를 사용하도록 정리해 admin hidden 데이터 key와 공개 데이터 key가 root부터 섞이지 않도록 했다.
- 카테고리/방명록처럼 admin mutation이 public 화면에도 영향을 주는 경우에는 admin/public key를 각각 명시적으로 갱신하도록 분리했다.
- Post editor 태그 제안은 `publicTagKeys.list()`를 사용하되 input focus 또는 입력 이후에만 `/tags`를 조회하도록 지연했다.
- 객체형 query key params는 factory 내부에서 고정된 property 순서로 정규화하도록 했다.

### 검증

- `pnpm compile:types`
- `pnpm lint` (기존 unrelated warning 2건 유지)
- `pnpm build`
- 자동 리뷰: Critical 0, Warning 0, Suggestion 0
