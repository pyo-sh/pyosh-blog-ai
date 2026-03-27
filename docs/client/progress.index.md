# Client Progress Index

> Client(Next.js) 진행 상황 요약

## 📅 타임라인

| 날짜       | 주요 작업                            | 상태 |
| ---------- | ------------------------------------ | ---- |
| 2026-03-28 | #196 댓글 표시 개선 (F-27/F-28b) - paginated comment fetch/meta, locked/disabled 상태, guest secret 복원, delete fallback/hydration fix, PR #242 머지 | ✅   |
| 2026-03-28 | #200 글 메타데이터 편집 (F-20) - PostForm 메타 필드 확장(summary/description/comment status/thumbnail/tag/category), 공개 post card/detail 반영, JSON-LD/TOC 충돌 정리, PR #245 머지 | ✅   |
| 2026-03-28 | #199 구조화 데이터 (JSON-LD) - `WebSite`/`SearchAction`/`BlogPosting`/`BreadcrumbList` 삽입, 리뷰 수정 2라운드, PR #246 머지 | ✅   |
| 2026-03-28 | #197 목차 (TOC) (F-16) - 글 상세 사이드바 TOC, markdown heading anchor slug, Storybook story PR #244 머지 | ✅   |
| 2026-03-28 | #198 조회수 기록 PR #241 머지 | ✅   |
| 2026-03-28 | #194 인기 글 (7일/30일) (F-06) - 사이드바 인기글 7일/30일 토글, top 5 SSR 프리패치, `/popular` 호환 리다이렉트, Storybook story PR #243 머지 | ✅   |
| 2026-03-28 | #195 카테고리별 글 목록 (F-03) - CategoryNav 제거, breadcrumb 헤더, category entity 유틸 추출, Storybook story PR #240 머지 | ✅   |
| 2026-03-28 | #189 CodeMirror 기반 마크다운 에디터 안정화 - controlled sync/undo/history 회귀, toolbar multi-line/inline formatting, label wiring, language bundle 축소 PR #237 머지 | ✅   |
| 2026-03-27 | #193 댓글 관리 테이블 + 필터 + 상세 모달 (F-28a) - Admin 댓글 테이블/필터/상세 모달/스레드 뷰, 단건 삭제 복구, thread API 계약 정합화 PR #238 머지 | ✅   |
| 2026-03-27 | #190 카테고리 트리 표시 (F-24a) - 재귀 렌더링, 접기/펼치기, 숨김 필터, 글 개수 표시 PR #236 머지 | ✅   |
| 2026-03-27 | #191 에셋 업로드 (F-26) - XHR 진행률, 드래그 피드백, magic bytes 검증, Cache-Control PR #235 머지 | ✅   |
| 2026-03-27 | #186 글 관리 테이블 + 필터 + 정렬 (F-21a) - PostTable/PostFilters/BulkActions 위젯, ConfirmDialog/ToggleSwitch 공유 컴포넌트, optimistic 토글, 3단계 정렬 PR #234 머지 | ✅   |
| 2026-03-27 | #183 포스트 상세 마크다운 렌더링 개선 (F-06) - GFM, 코드 블록 복사/언어 헤더(CodeBlockEnhancer), 관련 글 섹션, SSR 코드 블록 시각 폴백 PR #229 머지 | ✅   |
| 2026-03-27 | #187 관리자 대시보드 리팩터링 - dashboard-home 분리(StatsSection/PostStatusSection/RecentCommentsSection), formatNumber 공유 유틸, deleteError onMutate 클리어, totalPosts 활용 PR #233 머지 | ✅   |
| 2026-03-27 | #185 Public 사이드바 레이아웃 (F-39) - 2컬럼 레이아웃, SlideInPanel, StickySidebarWrapper, 햄버거 포커스 반환(WCAG 2.4.3), SSR 페치 graceful degradation PR #232 머지 | ✅   |
| 2026-03-27 | #188 클라이언트 에러 수집 (F-35c) - ErrorBoundary + 라우트 자동 리셋, API 에러 구조화 로깅(4xx warn/5xx error), unhandledrejection 핸들러 PR #230 머지 | ✅   |
| 2026-03-27 | #181 검색 (F-11) - 6개 필터 드롭다운, highlightText 유틸, SearchResultItem (하이라이팅+댓글발췌), 헤더 SearchBar UX 개선, SEARCH_FILTERS const PR #231 머지 | ✅   |
| 2026-03-27 | #182 태그별 글 목록 (F-05) - PostListItem 통일(tags+categories), Pagination 조건 제거(F-01·F-03·F-05), Storybook story PR #228 머지 | ✅   |
| 2026-03-27 | #184 Favicon / Web Manifest (F-32) - SVG favicon 추가(다크/라이트), manifest.webmanifest 전환, theme-color 분리, msapplication 제거 PR #227 머지 | ✅   |
| 2026-03-27 | #174 CSP 미들웨어 (F-34c) - nonce 기반 CSP-Report-Only 헤더, strict-dynamic, object-src none, matcher 확장 PR #225 머지 | ✅   |
| 2026-03-27 | #180 Storybook 환경 구성 (F-38) - Storybook 10 + MSW 2, QueryClient useState factory, tsconfig.storybook.json, 스토리 22개 PR #226 머지 | ✅   |
| 2026-03-27 | #179 Footer 콘텐츠 - 저작권 문구 추가, GitHub 프로필 URL 수정, (public) route group으로 Admin 페이지 숨김 PR #224 머지 | ✅   |
| 2026-03-27 | #178 Client 환경 변수 설정 - serverFetch/clientFetch API URL 분리 (INTERNAL_API_URL/PUBLIC_API_URL), .env.local.example 주석 추가 PR #223 머지 | ✅   |
| 2026-03-27 | #221 Design token 동기화 - theme.css/typography.css figma_tokens.json 동기화 (tertiary→info, quaternary 삭제, warning/overlay/special 추가, 색상 값 8개 수정, text-ui-* 추가) PR #222 머지 | ✅   |
| 2026-03-27 | #176 반응형 레이아웃 (F-18) - Tailwind v4 브레이크포인트, 모바일 사이드바 오버레이(focus trap), 반응형 페이지네이션, max-width 정규화 PR #220 머지 | ✅   |
| 2026-03-27 | #175 관리자 로그인 (F-19) - /manage 경로 이전, username 인증, 사이드바 로그아웃 버튼 PR #219 머지 | ✅   |
| 2026-03-27 | #169 로딩/빈 상태 (F-13) - Skeleton/Spinner/EmptyState 공유 컴포넌트, 로컬 스켈레톤 7개 제거, 버튼 Spinner 피드백 PR #217 머지 | ✅   |
| 2026-03-27 | #171 Toast 알림 (F-14) - sonner 도입, getErrorMessage 공유 유틸 추출, 7개 파일 Toast 마이그레이션 PR #216 머지 | ✅   |
| 2026-03-27 | #177 다크 모드 (F-17) - transition-theme 완성, aria-label, cookie Secure/MaxAge PR #218 머지 | ✅   |
| 2026-03-27 | #173 에러 페이지 (F-12) - ErrorContent 공통 컴포넌트, Public/Admin 에러 경계, 403 인터셉터 PR #215 머지 | ✅   |
| 2026-03-27 | #172 맨 위로 버튼 (F-15) - ScrollToTop 컴포넌트, 5개 페이지 적용 PR #214 머지 | ✅   |
| 2026-03-27 | #170 방명록 페이지 (F-09) - 상대 시간, flat 구조, 스크롤, 비밀글 PR #213 머지 | ✅   |
| 2026-03-27 | #168 태그 목록 - PostListItem 배지 + TagCloud feature PR #212 머지 | ✅   |
| 2026-03-27 | #167 홈 글 목록 (리스트형 + 고정 글 + 페이지네이션) PR #211 머지 | ✅   |
| 2026-03-15 | #63 SEO 메타데이터 + Open Graph PR #166 머지 | ✅   |
| 2026-03-15 | #69 조회수 기록 hook + ViewCounter PR #164 머지 | ✅   |
| 2026-03-14 | #48 공개 방명록 페이지 PR #165 머지 | ✅   |
| 2026-03-14 | #37 카테고리별 글 목록 페이지 PR #163 머지 | ✅   |
| 2026-03-14 | #70 Admin 댓글 관리 페이지 PR #162 머지 | ✅   |
| 2026-03-14 | #53 Admin 글 작성/수정 페이지 PR #161 머지 | ✅   |
| 2026-03-14 | #61 인기 글 페이지 기간 필터 PR #160 머지 | ✅   |
| 2026-03-14 | #64 헤더 검색바 PR #157 머지 | ✅   |
| 2026-03-14 | #60 에셋 라이브러리 feature + 페이지 PR #159 머지 | ✅   |
| 2026-03-14 | #68 Admin 방명록 관리 페이지 PR #158 머지 | ✅   |
| 2026-03-14 | #55 댓글 섹션 feature PR #155 머지 | ✅   |
| 2026-03-14 | #57 카테고리 관리 feature + 페이지 PR #156 머지 | ✅   |
| 2026-03-14 | #59 태그 목록/태그별 글 목록 페이지 PR #154 머지 | ✅   |
| 2026-03-14 | #67 헤더 네비게이션 업데이트 PR #152 머지 | ✅   |
| 2026-03-14 | #36 홈 페이지 SSR PR #153 머지, #66 검색 결과 페이지 SSR PR #151 머지, #65 Admin 댓글/방명록 API functions PR #150 머지, #62 Category Admin API functions PR #148 머지, #58 Asset entity types + API PR #149 머지, #54 마크다운 에디터 + 프리뷰 feature PR #147 머지, #56 PopularPost API PR #146 머지, #52 Comment entity types + API PR #145 머지, #40 Dashboard 인증 미들웨어 PR #144 머지, #51 Guestbook entity types + API PR #142 머지, #49 Tag entity types + API PR #143 머지, #41 Admin 로그인 페이지 PR #141 머지, #35 마크다운 타이포그래피 스타일링 PR #140 머지, #39 글 상세 페이지 SSR PR #139 머지, #33 PostCard PR #138 머지, #43 Admin 대시보드 페이지 PR #136 머지, #45 Admin 글 목록 페이지 PR #137 머지, #44 Admin Post API functions PR #135 머지, #28 CategoryNav 위젯 PR #134 머지, #27 글로벌 loading/error/not-found 페이지 PR #133 머지, #26 Public Post API functions PR #131 머지, #32 Pagination 공통 컴포넌트 PR #128 머지, #30 PostContent + PostNavigation PR #132 머지 | ✅   |
| 2026-03-09 | #24 PR #127 리뷰 코멘트 대응 (processor 모듈화, sanitizeSchema 코멘트), #29 Category entity PR #129 머지 | ✅   |
| 2026-03-08 | #24 마크다운 렌더링 유틸리티 (shiki), #29 Category entity 타입 + API, #30 PostContent + PostNavigation 컴포넌트 | ✅   |
| 2026-03-07 | #25 Post entity - PostNavigation 타입 추가 | ✅   |
| 2026-03-06 | #46 Admin 레이아웃 (사이드바), #50 Post CRUD API, #42 Stat entity, #31 마크다운 렌더링 의존성 설치, #23 PaginatedResponse meta.total 수정 | ✅   |
| 2026-03-04 | #34 CSRF 토큰 유틸리티 + mutation helper, #38 Auth entity types + API | ✅   |
| 2026-02-23 | #4 API 클라이언트 설정 (fetch wrapper + TanStack Query) | ✅   |
| 2026-02-06 | 기술 스택 분석 & Phase 0 (보안 패치) | ✅   |
| 2026-02-07 | ESLint 9 & Phase A (TailwindCSS v4)  | ✅   |
| 2026-02-08 | Phase D, E (Component 경계 & 테마)   | ✅   |
| 2026-02-09 | FSD 마이그레이션 & Emotion 제거 완성 | ✅   |

## 🔗 상세 문서

- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #196 댓글 표시 개선 PR #242 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #200 글 메타데이터 편집 PR #245 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #199 구조화 데이터 (JSON-LD) PR #246 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #197 목차 (TOC) PR #244 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #198 조회수 기록 PR #241 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #194 인기 글 (7일/30일) PR #243 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #195 카테고리별 글 목록 PR #240 머지
- [progress.2026-03-28.md](./progress/progress.2026-03-28.md) - #189 CodeMirror 기반 마크다운 에디터 안정화 PR #237 머지
- [progress.2026-03-27.md](./progress/progress.2026-03-27.md) - #193 댓글 관리 테이블 + 필터 + 상세 모달 PR #238 머지
- [progress.2026-03-27.md](./progress/progress.2026-03-27.md) - #186 글 관리 테이블+필터+정렬 PR #234 머지, #185 Public 사이드바 레이아웃 PR #232 머지, #188 클라이언트 에러 수집 PR #230 머지, #182 태그별 글 목록 PR #228 머지, #174 CSP 미들웨어 PR #225 머지, #179 Footer 콘텐츠 PR #224 머지, #178 Client 환경 변수 설정 PR #223 머지, #221 Design token 동기화 PR #222 머지, #175 관리자 로그인 /manage 경로 이전 PR #219 머지, #169 로딩/빈 상태 Skeleton/Spinner/EmptyState PR #217 머지, #168 태그 목록 PostListItem 배지 + TagCloud feature PR #212 머지
- [progress.2026-03-15.md](./progress/progress.2026-03-15.md) - #63 SEO 메타데이터 + Open Graph PR #166 머지
- [progress.2026-03-15.md](./progress/progress.2026-03-15.md) - #69 조회수 기록 hook + ViewCounter PR #164 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #48 공개 방명록 페이지 PR #165 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #37 카테고리별 글 목록 페이지 PR #163 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #70 Admin 댓글 관리 페이지 PR #162 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #53 Admin 글 작성/수정 페이지 PR #161 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #61 인기 글 페이지 기간 필터 PR #160 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #64 헤더 검색바 PR #157 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #60 에셋 라이브러리 feature + 페이지 PR #159 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #68 Admin 방명록 관리 페이지 PR #158 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #55 댓글 섹션 feature PR #155 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #57 카테고리 관리 feature + 페이지 PR #156 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #59 태그 목록/태그별 글 목록 페이지 PR #154 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #67 헤더 네비게이션 업데이트 PR #152 머지
- [progress.2026-03-14.md](./progress/progress.2026-03-14.md) - #36 홈 페이지 SSR PR #153 머지, #66 검색 결과 페이지 SSR PR #151 머지, #65 Admin 댓글/방명록 API functions PR #150 머지, #62 Category Admin API functions PR #148 머지, #58 Asset entity types + API PR #149 머지, #54 마크다운 에디터 + 프리뷰 feature PR #147 머지, #56 PopularPost API PR #146 머지, #52 Comment entity types + API PR #145 머지, #40 Dashboard 인증 미들웨어 PR #144 머지, #51 Guestbook entity types + API PR #142 머지, #49 Tag entity types + API PR #143 머지, #41 Admin 로그인 페이지 PR #141 머지, #35 마크다운 타이포그래피 스타일링 PR #140 머지, #39 글 상세 페이지 SSR PR #139 머지, #33 PostCard PR #138 머지, #43 Admin 대시보드 페이지 PR #136 머지, #45 Admin 글 목록 페이지 PR #137 머지, #44 Admin Post API functions PR #135 머지, #28 CategoryNav 위젯 PR #134 머지, #27 글로벌 loading/error/not-found 페이지 PR #133 머지, #26 Public Post API functions PR #131 머지, #32 Pagination 공통 컴포넌트 PR #128 머지, #30 PostContent + PostNavigation PR #132 머지
- [progress.2026-03-09.md](./progress/progress.2026-03-09.md) - #24 PR #127 리뷰 코멘트 대응, #29 Category entity PR #129 머지
- [progress.2026-03-08.md](./progress/progress.2026-03-08.md) - #24 마크다운 렌더링 유틸리티 (shiki), #29 Category entity 타입 + API, #30 PostContent + PostNavigation 컴포넌트
- [progress.2026-03-07.md](./progress/progress.2026-03-07.md) - #25 Post entity - PostNavigation 타입 추가
- [progress.2026-03-06.md](./progress/progress.2026-03-06.md) - #46 Admin 레이아웃 (사이드바), #50 Post CRUD API, #42 Stat entity, #31 마크다운 렌더링 의존성 설치, #23 PaginatedResponse meta.total 수정
- [progress.2026-03-04.md](./progress/progress.2026-03-04.md) - #34 CSRF 토큰 유틸리티 + mutation helper, #38 Auth entity types + API
- [progress.2026-02-23.md](./progress/progress.2026-02-23.md) - #4 API 클라이언트 설정
- [progress.2026-02-06.md](./progress/progress.2026-02-06.md) - 기술 스택 분석 & Phase 0
- [progress.2026-02-07.md](./progress/progress.2026-02-07.md) - ESLint 9 & Phase A
- [progress.2026-02-08.md](./progress/progress.2026-02-08.md) - Phase D & E
- [progress.2026-02-09.md](./progress/progress.2026-02-09.md) - FSD 완성

## 📊 최종 성과

### 기술 스택 전환

- **Pages Router → App Router** 완료
- **Emotion → TailwindCSS v4** 완료
- **ESLint 8 → ESLint 9 Flat Config** 완료
- **TypeScript 4.9 → 5.9** 완료

### 보안 & 품질

- **취약점**: 20개 → 2개 (90% 감소)
- **"use client"**: 20+개 → 8개 (최소화)
- **타입 오류**: 4개 → 0개

### 구조 개선

- **FSD 구조** 전환 완료
- **레거시 제거**: pages/, styles/, components/ 삭제
- **CSS 통합**: theme.css 중심 구조
