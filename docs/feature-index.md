# Feature Index

> pyosh-blog v1 기능 마스터 목록

**최종 수정:** 2026-03-23

각 기능의 상세 스펙은 `docs/client/specs/`, `docs/server/specs/`, `docs/specs/`에 개별 파일로 관리한다.
접근성 요구사항은 별도 스펙이 아닌 공통 체크리스트(`docs/a11y-checklist.md`)로 관리하며, 각 기능 스펙의 수용 기준에 포함한다.

---

## 상태 정의

| 상태 | 설명 |
|---|---|
| `SPEC` | 스펙 작성 필요 |
| `DRAFT` | 스펙 초안 작성 완료 |
| `APPROVED` | 스펙 검토 완료, 구현 가능 |
| `IN_PROGRESS` | 구현 진행 중 |
| `REVIEW` | 구현 완료, 검토 필요 |
| `DONE` | 검토 완료, 배포 가능 |

---

## Public 기능

| # | 기능 | 스펙 파일 | 상태 | 의존성 |
|---|---|---|---|---|
| F-01 | 홈 - 글 목록 (페이지네이션) | `client/specs/home-post-list.md` | `DRAFT` | - |
| F-02 | 글 상세 (마크다운 렌더링, 코드 하이라이팅) | `client/specs/post-detail.md` | `DRAFT` | F-01 |
| F-03 | 카테고리별 글 목록 | `client/specs/category-post-list.md` | `DRAFT` | F-01, F-39 |
| F-04 | 태그 목록 | `client/specs/tag-list.md` | `DRAFT` | - |
| F-05 | 태그별 글 목록 | `client/specs/tag-post-list.md` | `DRAFT` | F-01, F-04 |
| F-06 | 인기 글 (7일/30일) | `client/specs/popular-posts.md` | `DRAFT` | F-01, F-39 |
| F-07 | 댓글 표시 (계층형 목록, 비밀글 마스킹) | `client/specs/comment-display.md` | `DRAFT` | F-02 |
| F-08 | 댓글 작성/삭제 (게스트 폼, 대댓글, 비밀번호 삭제) | `client/specs/comment-interaction.md` | `DRAFT` | F-07 |
| F-09 | 방명록 | `client/specs/guestbook.md` | `DRAFT` | - |
| F-10 | 조회수 기록 | `client/specs/view-counter.md` | `DRAFT` | F-02 |
| F-11 | 검색 | `client/specs/search.md` | `DRAFT` | F-01 |
| F-12 | 에러 페이지 (404, 글로벌 에러) | `client/specs/error-pages.md` | `DRAFT` | - |
| F-13 | 로딩/빈 상태 | `client/specs/loading-empty-states.md` | `DRAFT` | - |
| F-14 | Toast 알림 | `client/specs/toast.md` | `DRAFT` | - |
| F-15 | 맨 위로 버튼 | `client/specs/scroll-to-top.md` | `DRAFT` | - |
| F-16 | 목차 (TOC) | `client/specs/toc.md` | `DRAFT` | F-02, F-39 |
| F-17 | 다크 모드 | `client/specs/dark-mode.md` | `DRAFT` | - |
| F-18 | 반응형 레이아웃 | `client/specs/responsive.md` | `DRAFT` | - |
| F-39 | Public 사이드바 레이아웃 | `client/specs/public-sidebar.md` | `DRAFT` | F-01, F-04, F-06, F-10, F-17, F-18 |

## Admin 기능

| # | 기능 | 스펙 파일 | 상태 | 의존성 |
|---|---|---|---|---|
| F-19 | 관리자 로그인 | `client/specs/admin-login.md` | `DRAFT` | - |
| F-20 | 대시보드 (통계 요약) | `client/specs/admin-dashboard.md` | `DRAFT` | F-19 |
| F-21 | 글 관리 (목록, 필터, 삭제/복원) | `client/specs/admin-post-list.md` | `DRAFT` | F-19 |
| F-22 | 마크다운 에디터 (편집 + 실시간 프리뷰) | `client/specs/admin-markdown-editor.md` | `DRAFT` | F-19 |
| F-23 | 글 메타데이터 폼 (제목, 카테고리, 태그, 상태, 썸네일) | `client/specs/admin-post-meta-form.md` | `DRAFT` | F-19, F-22 |
| F-24 | 카테고리 트리 표시 | `client/specs/admin-category-tree.md` | `DRAFT` | F-19 |
| F-25 | 카테고리 CRUD (생성/수정/삭제 모달) | `client/specs/admin-category-crud.md` | `DRAFT` | F-24 |
| F-26 | 에셋 업로드 (드래그&드롭, 파일 검증, 업로드 큐) | `client/specs/admin-asset-upload.md` | `DRAFT` | F-19 |
| F-27 | 에셋 갤러리/관리 (그리드, 선택, 삭제, URL 복사) | `client/specs/admin-asset-gallery.md` | `DRAFT` | F-26 |
| F-28 | 댓글 관리 (목록, 비밀글 확인, 강제 삭제) | `client/specs/admin-comment-manager.md` | `DRAFT` | F-19 |
| F-29 | 방명록 관리 (목록, 강제 삭제) | `client/specs/admin-guestbook-manager.md` | `DRAFT` | F-19 |

## SEO / 웹 표준

| # | 기능 | 스펙 파일 | 상태 | 의존성 |
|---|---|---|---|---|
| F-30 | SEO 메타 (메타태그, OG, sitemap, RSS, robots.txt, Canonical URL) | `client/specs/seo-meta.md` | `DRAFT` | F-01, F-02 |
| F-31 | 구조화 데이터 (JSON-LD) | `client/specs/seo-jsonld.md` | `DRAFT` | F-02 |
| F-32 | Favicon / Web Manifest | `client/specs/favicon-manifest.md` | `DRAFT` | F-17 |

## 접근성

| # | 문서 | 스펙 파일 | 상태 | 비고 |
|---|---|---|---|---|
| A-01 | 접근성 공통 체크리스트 | `a11y-checklist.md` | `SPEC` | 키보드 네비게이션, Skip to content, ARIA, 포커스 관리 |

> 접근성은 별도 기능이 아니라 모든 기능의 수용 기준에 포함한다. 체크리스트는 각 기능 스펙에서 참조한다.

## 배포 준비

| # | 기능 | 스펙 파일 | 상태 | 의존성 |
|---|---|---|---|---|
| F-33 | 환경 변수 분리 (dev/production) | `specs/deploy-env.md` | `DRAFT` | - |
| F-34 | 프로덕션 쿠키/CORS 설정 | `specs/deploy-security.md` | `SPEC` | F-33 |
| F-35 | 에러 모니터링 | `specs/deploy-monitoring.md` | `SPEC` | F-33 |
| F-36 | Footer 콘텐츠 | `client/specs/footer.md` | `DRAFT` | - |

## 개발 도구

| # | 기능 | 스펙 파일 | 상태 | 의존성 |
|---|---|---|---|---|
| F-37 | Swagger 세부화 (예시 데이터, 상세 설명) | `server/specs/swagger-docs.md` | `DRAFT` | - |
| F-38 | Storybook 환경 구성 | `client/specs/storybook-setup.md` | `DRAFT` | - |

---

## 의존성 다이어그램

```
기반 (의존성 없음)
├── F-01  홈 - 글 목록
├── F-04  태그 목록
├── F-09  방명록
├── F-12  에러 페이지
├── F-13  로딩/빈 상태
├── F-14  Toast
├── F-15  맨 위로 버튼
├── F-17  다크 모드
├── F-18  반응형
├── F-19  관리자 로그인
├── F-32  Favicon
├── F-33  환경 변수 분리
├── F-36  Footer
├── F-37  Swagger
├── F-38  Storybook
└── A-01  접근성 체크리스트

F-01 홈 기반
├── F-02  글 상세
│   ├── F-07  댓글 표시
│   │   └── F-08  댓글 작성/삭제
│   ├── F-10  조회수
│   ├── F-16  TOC
│   ├── F-30  SEO 메타
│   └── F-31  JSON-LD
├── F-03  카테고리별 목록
├── F-05  태그별 목록 (+ F-04)
├── F-06  인기 글
├── F-11  검색
└── F-39  Public 사이드바 (+ F-04, F-06, F-10, F-17, F-18)

F-19 관리자 로그인 기반
├── F-20  대시보드
├── F-21  글 관리
├── F-22  마크다운 에디터
│   └── F-23  글 메타데이터 폼
├── F-24  카테고리 트리
│   └── F-25  카테고리 CRUD
├── F-26  에셋 업로드
│   └── F-27  에셋 갤러리
├── F-28  댓글 관리
└── F-29  방명록 관리

F-33 환경 변수 기반
├── F-34  쿠키/CORS
└── F-35  에러 모니터링
```
