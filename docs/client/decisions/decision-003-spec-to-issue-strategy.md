# SPEC 기반 Client Issue 생성 전략

## Metadata

- **Date**: 2026-03-26
- **Status**: draft
- **Related**: `docs/client/specs/*.md`, `docs/client/feature_spec.md`, `docs/feature-index.md`

## Background

Client repo(`pyo-sh/pyosh-blog-fe`)의 SPEC을 GitHub Issue로 변환한다. SPEC이 개발 완료의 기준이며, 기존 구현은 참고만 한다. 각 Issue는 AI가 해당 이슈만 보고 독립적으로 개발할 수 있는 최소 단위로 구성한다.

Client는 35개의 개별 spec 파일(`docs/client/specs/*.md`)이 이미 기능 단위로 작성되어 있으므로, 1:1로 Issue에 매핑한다. 추가로 공유 deployment spec(F-33, F-34, F-35)의 client 부분이 3개 Issue로 생성된다.

## Decision

### 원칙

1. **SPEC이 권위**: 기존 코드는 참고만 하며, SPEC 기준으로 재구현한다
2. **1:1 매핑**: 1 spec 파일 = 1 GitHub Issue
3. **자기 완결**: Issue 본문에 SPEC 수용 기준 + 서버 API 연동 정보를 모두 포함한다
4. **별도 Issue**: 공유 spec(F-33, F-34, F-35)의 client 부분은 client repo에 별도 Issue로 생성한다

### Issue 목록

#### Public 기능

| Feature # | Issue 제목 | SPEC 파일 | 의존성 |
|---|---|---|---|
| F-01 | 홈 - 글 목록 (페이지네이션) | `client/specs/home-post-list.md` | - |
| F-02 | 글 상세 (마크다운 렌더링, 코드 하이라이팅) | `client/specs/post-detail.md` | F-01 |
| F-03 | 카테고리별 글 목록 | `client/specs/category-post-list.md` | F-01, F-39 |
| F-04 | 태그 목록 | `client/specs/tag-list.md` | - |
| F-05 | 태그별 글 목록 | `client/specs/tag-post-list.md` | F-01, F-04 |
| F-06 | 인기 글 (7일/30일) | `client/specs/popular-posts.md` | F-01, F-39 |
| F-07 | 댓글 표시 (계층형 목록, 비밀글 마스킹) | `client/specs/comment-display.md` | F-02 |
| F-08 | 댓글 작성/삭제 (게스트 폼, 대댓글) | `client/specs/comment-interaction.md` | F-07 |
| F-09 | 방명록 | `client/specs/guestbook.md` | - |
| F-10 | 조회수 기록 | `client/specs/view-counter.md` | F-02 |
| F-11 | 검색 | `client/specs/search.md` | F-01 |

#### UI/UX 기능

| Feature # | Issue 제목 | SPEC 파일 | 의존성 |
|---|---|---|---|
| F-12 | 에러 페이지 (404, 글로벌 에러) | `client/specs/error-pages.md` | - |
| F-13 | 로딩/빈 상태 | `client/specs/loading-empty-states.md` | - |
| F-14 | Toast 알림 | `client/specs/toast.md` | - |
| F-15 | 맨 위로 버튼 | `client/specs/scroll-to-top.md` | - |
| F-16 | 목차 (TOC) | `client/specs/toc.md` | F-02, F-39 |
| F-17 | 다크 모드 | `client/specs/dark-mode.md` | - |
| F-18 | 반응형 레이아웃 | `client/specs/responsive-layout.md` | - |
| F-36 | Footer 콘텐츠 | `client/specs/footer.md` | - |
| F-39 | Public 사이드바 레이아웃 | `client/specs/public-sidebar.md` | F-01, F-04, F-06, F-10, F-17, F-18 |

#### Admin 기능

| Feature # | Issue 제목 | SPEC 파일 | 의존성 |
|---|---|---|---|
| F-19 | 관리자 로그인 | `client/specs/admin-login.md` | - |
| F-20 | 대시보드 (통계 요약) | `client/specs/admin-dashboard.md` | F-19 |
| F-21 | 글 관리 (목록, 필터, 삭제/복원) | `client/specs/admin-post-list.md` | F-19 |
| F-22 | 마크다운 에디터 (편집 + 실시간 프리뷰) | `client/specs/admin-markdown-editor.md` | F-19 |
| F-23 | 글 메타데이터 폼 (제목, 카테고리, 태그, 상태, 썸네일) | `client/specs/admin-post-meta-form.md` | F-19, F-22 |
| F-24 | 카테고리 트리 표시 | `client/specs/admin-category-tree.md` | F-19 |
| F-25 | 카테고리 CRUD (생성/수정/삭제 모달) | `client/specs/admin-category-crud.md` | F-24 |
| F-26 | 에셋 업로드 (드래그&드롭, 파일 검증) | `client/specs/admin-asset-upload.md` | F-19 |
| F-27 | 에셋 갤러리/관리 (그리드, 선택, 삭제) | `client/specs/admin-asset-gallery.md` | F-26 |
| F-28 | 댓글 관리 (목록, 비밀글 확인, 강제 삭제) | `client/specs/admin-comment-manager.md` | F-19 |
| F-29 | 방명록 관리 (목록, 강제 삭제) | `client/specs/admin-guestbook-manager.md` | F-19 |

#### SEO / 웹 표준

| Feature # | Issue 제목 | SPEC 파일 | 의존성 |
|---|---|---|---|
| F-30 | SEO 메타 (메타태그, OG, sitemap, RSS, robots.txt) | `client/specs/seo-meta.md` | F-01, F-02 |
| F-31 | 구조화 데이터 (JSON-LD) | `client/specs/seo-jsonld.md` | F-02 |
| F-32 | Favicon / Web Manifest | `client/specs/favicon-manifest.md` | F-17 |

#### 개발 도구

| Feature # | Issue 제목 | SPEC 파일 | 의존성 |
|---|---|---|---|
| F-38 | Storybook 환경 구성 | `client/specs/storybook-setup.md` | - |

#### 배포 준비 (공유 spec의 client 부분)

| Feature # | Issue 제목 | SPEC 소스 | 의존성 |
|---|---|---|---|
| F-33 (client) | Client 환경 변수 설정 | `docs/specs/deploy-env.md` > 5.3 (Client 환경 변수) | - |
| F-34 (client) | CSP 설정 (nonce 기반) | `docs/specs/deploy-security.md` > 5.4 (CSP) | - |
| F-35 (client) | Error boundary + API 에러 로깅 | `docs/specs/deploy-monitoring.md` > 5.4 (클라이언트 에러 수집) | F-12 |

**총 38개 Issue** (spec 파일 35 + 공유 spec client 부분 3)

### 의존성 순서

```
Layer 0 (기반 - 의존성 없음, 병렬 가능)
├── F-01  홈 - 글 목록
├── F-04  태그 목록
├── F-09  방명록
├── F-12  에러 페이지
├── F-13  로딩/빈 상태
├── F-14  Toast
├── F-15  맨 위로 버튼
├── F-17  다크 모드
├── F-18  반응형 레이아웃
├── F-19  관리자 로그인
├── F-32  Favicon
├── F-36  Footer
├── F-38  Storybook
├── F-33c 환경 변수
└── F-34c CSP

Layer 1 (F-01 기반)
├── F-02  글 상세      ← F-01
├── F-05  태그별 목록  ← F-01, F-04
├── F-11  검색         ← F-01
├── F-39  사이드바     ← F-01, F-04, F-06, F-10, F-17, F-18
├── F-03  카테고리별   ← F-01, F-39
└── F-06  인기 글      ← F-01, F-39

Layer 1 (F-19 기반)
├── F-20  대시보드     ← F-19
├── F-21  글 관리      ← F-19
├── F-22  에디터       ← F-19
├── F-24  카테고리 트리 ← F-19
├── F-26  에셋 업로드  ← F-19
├── F-28  댓글 관리    ← F-19
└── F-29  방명록 관리  ← F-19

Layer 2
├── F-07  댓글 표시    ← F-02
├── F-10  조회수       ← F-02
├── F-16  TOC          ← F-02, F-39
├── F-30  SEO 메타     ← F-01, F-02
├── F-31  JSON-LD      ← F-02
├── F-23  글 메타 폼   ← F-19, F-22
├── F-25  카테고리 CRUD ← F-24
├── F-27  에셋 갤러리  ← F-26
└── F-35c 에러 로깅    ← F-12

Layer 3
└── F-08  댓글 작성    ← F-07
```

### Issue 템플릿

```markdown
## 목표

{1줄 요약}

## SPEC 참조

- `docs/client/specs/{file}.md`

## 서버 API 의존성

| Method | Path | 용도 |
|---|---|---|
| ... | ... | ... |

## 수용 기준

{spec 파일의 "수용 기준" 섹션 전문 인용}

## 접근성 요구사항

{spec 파일에 포함된 접근성 기준 또는 `docs/a11y-checklist.md` 참조}

## 의존성

- Blocked by: {선행 Feature Issue 번호}
- Blocks: {후행 Feature Issue 번호}

## 참고

- FSD 아키텍처 준수 (app → features → entities → shared)
- 데이터 페칭: Public은 Server Component, Admin은 TanStack Query
```

### 라벨

| 라벨 | 용도 |
|---|---|
| `spec` | SPEC 기반 재구현 Issue 공통 |
| `public` | F-01 ~ F-18, F-36, F-39 |
| `admin` | F-19 ~ F-29 |
| `seo` | F-30 ~ F-32 |
| `deploy` | F-33c, F-34c, F-35c |
| `devtool` | F-38 |

### Issue 본문에 포함할 SPEC 내용

각 Issue 본문에 해당 spec 파일의 **수용 기준 + 상세 설계 + API 연동** 섹션을 inline으로 포함한다. AI 에이전트가 Issue만 보고 개발할 수 있어야 하므로, 외부 파일 참조만으로는 부족하다.

- F-01 ~ F-39: 해당 `client/specs/*.md`의 핵심 섹션 (상세 설계, API 연동, 수용 기준)
- F-33c ~ F-35c: 공유 spec 파일에서 client 해당 섹션만 발췌

## Consequences

- `docs/client/specs/`의 모든 spec 파일이 38개 Issue로 빠짐없이 커버된다
- Feature Index(F-01 ~ F-39)와 Issue가 1:1 대응하여 추적이 용이하다
- Layer 0의 15개 Issue는 병렬 개발이 가능하다
- 공유 spec의 client 부분이 server와 독립적으로 관리된다
