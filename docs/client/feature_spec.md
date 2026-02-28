# Client Feature Spec — 초기 버전 (v1)

> Next.js 14 App Router + TailwindCSS v4 | Server: Fastify 5 (Base URL: `http://localhost:5500`)

---

## 1. 페이지 구조 & 라우팅

### Public (블로그)

| 경로 | 페이지 | 데이터 소스 |
|---|---|---|
| `/` | 홈 — 최신 글 목록 (페이지네이션) | `GET /api/posts` |
| `/posts/[slug]` | 글 상세 (MD 렌더링 + 댓글) | `GET /api/posts/:slug` |
| `/categories/[slug]` | 카테고리별 글 목록 | `GET /api/posts?categoryId=N` |
| `/tags` | 태그 목록 | `GET /api/tags` |
| `/tags/[slug]` | 태그별 글 목록 | `GET /api/posts?tagSlug=xxx` |
| `/popular` | 인기 글 | `GET /api/stats/popular` |
| `/guestbook` | 방명록 | `GET /api/guestbook` |
| `/search?q=keyword` | 검색 결과 | `GET /api/posts?q=keyword` |

### Admin (관리자) — prefix: `/dashboard`

| 경로 | 페이지 | 데이터 소스 |
|---|---|---|
| `/dashboard/login` | 관리자 로그인 | `POST /api/auth/admin/login` |
| `/dashboard` | 대시보드 (통계 요약) | `GET /api/admin/stats/dashboard` |
| `/dashboard/posts` | 글 목록 (전체 상태) | `GET /api/admin/posts` |
| `/dashboard/posts/new` | 글 작성 | `POST /api/admin/posts` |
| `/dashboard/posts/[id]/edit` | 글 수정 | `PATCH /api/admin/posts/:id` |
| `/dashboard/categories` | 카테고리 관리 | `GET /api/categories` |
| `/dashboard/assets` | 에셋 라이브러리 | `GET /api/assets`, `POST /api/assets/upload` |
| `/dashboard/comments` | 댓글 관리 | `GET /api/admin/comments` |
| `/dashboard/guestbook` | 방명록 관리 | `GET /api/admin/guestbook` |

---

## 2. 레이아웃 구조

### 공통

```
┌─────────────────────────────────┐
│           Header                │  ← 로고, 네비게이션, 검색, 테마 토글
├─────────────────────────────────┤
│                                 │
│         Main Content            │  ← 사이드바 없음, 단일 컬럼
│                                 │
├─────────────────────────────────┤
│           Footer                │  ← 저작권, 링크
└─────────────────────────────────┘
```

- **사이드바 없음** — 헤더 네비게이션으로 충분
- **반응형** — 모바일/태블릿/데스크톱 초기부터 대응
- **다크 모드** — 기존 테마 시스템 (`useToggleTheme`) 활용

### Admin 레이아웃

```
┌─────────────────────────────────┐
│       Admin Header / Nav        │  ← 관리자 전용 네비게이션
├──────────┬──────────────────────┤
│ Sidebar  │                      │
│ - 글     │    Main Content      │
│ - 카테고리│                      │
│ - 댓글   │                      │
│ - 방명록 │                      │
│ - 에셋   │                      │
├──────────┴──────────────────────┤
│           Footer                │
└─────────────────────────────────┘
```

---

## 3. 기능 상세

### 3.1 홈 — 글 목록 (`/`)

- **레이아웃**: 리스트형 (세로 목록)
- **항목 표시**: 썸네일(선택, `next/image`) + 제목 + 요약(contentMd 앞부분) + 카테고리 + 태그 + 작성일
- **페이지네이션**: 번호 기반 (`?page=N`)
- **정렬**: 최신순 (published_at desc) 기본

### 3.2 글 상세 (`/posts/[slug]`)

- **마크다운 렌더링**: 서버 사이드 (Server Component에서 HTML로 변환)
  - 코드 하이라이팅: `shiki`
  - 이미지, 테이블, 인용문 등 기본 MD 문법
- **이전/다음 글 네비게이션**: API의 `prevPost`/`nextPost` 활용
- **메타 정보**: 카테고리, 태그, 작성일, 수정일
- **댓글 영역**: 하단에 댓글 목록 + 작성 폼

### 3.3 카테고리별 목록 (`/categories/[slug]`)

- 홈과 동일한 리스트 레이아웃
- 상단에 카테고리 이름 표시
- 카테고리 트리 네비게이션 (헤더 또는 페이지 상단)

### 3.4 태그 (`/tags`, `/tags/[slug]`)

- `/tags`: 전체 태그 클라우드/목록 (`GET /api/tags` — post count 포함)
- `/tags/[slug]`: 해당 태그의 글 목록 (홈과 동일 레이아웃)

### 3.5 인기 글 (`/popular`)

- `GET /api/stats/popular` 기반
- 기간 선택 가능 (7일/30일)
- 조회수/방문자수 표시

### 3.6 댓글 시스템

- **게스트 전용** (OAuth는 후속 버전)
- 작성 시: 이름, 이메일, 비밀번호, 본문 입력
- 삭제 시: 비밀번호 확인
- **계층형**: depth 1까지 대댓글 지원
- **비밀 댓글**: `isSecret` 플래그 — 공개 화면에서 "비밀 댓글입니다" 마스킹. 관리자 대시보드에서만 내용 확인 가능

### 3.7 방명록 (`/guestbook`)

- 댓글과 유사한 UX (게스트 작성)
- 페이지네이션 (`?page=N`)
- 작성/삭제 기능

### 3.8 조회수 기록

- 글 상세 페이지 마운트 시 클라이언트 `useEffect`에서 `POST /api/stats/view` 호출
- `sessionStorage`로 이미 조회한 글 추적 → 같은 세션 내 재방문 시 API 호출 생략
- 추가 중복 제거는 서버 담당

### 3.9 검색 (`/search`)

- 헤더 네비게이션에 검색 아이콘/바 추가
- `/search?q=keyword` 페이지에서 결과 표시
- `GET /api/posts?q=keyword` 활용 (서버 사이드 검색)
- 결과 레이아웃은 홈 글 목록과 동일
- 페이지네이션 지원

---

## 4. Admin 기능 상세

### 4.1 로그인 (`/dashboard/login`)

- 이메일 + 비밀번호 폼
- 세션 쿠키 기반 인증
- 미인증 시 `/dashboard/*` 접근 → `/dashboard/login` 리다이렉트

### 4.2 대시보드 (`/dashboard`)

- 오늘/주간/월간 조회수
- 총 게시글 수, 총 댓글 수
- 최근 글 목록 (quick access)

### 4.3 글 관리 (`/dashboard/posts`)

- **목록**: 전체 상태(draft/published/archived), 가시성(public/private), 삭제된 글 포함
- **필터**: 상태, 가시성, 카테고리별
- **작업**: 생성, 수정, 소프트 삭제, 복원, 하드 삭제

### 4.4 글 에디터 (`/dashboard/posts/new`, `/dashboard/posts/[id]/edit`)

- **순수 textarea + 실시간 프리뷰** (좌: 마크다운 입력, 우: 렌더링 미리보기)
- **입력 필드**:
  - 제목 (max 200)
  - 본문 (마크다운)
  - 카테고리 선택 (드롭다운)
  - 태그 입력 (자동완성 또는 자유 입력)
  - 썸네일 (업로드 또는 URL)
  - 상태 (draft / published / archived)
  - 가시성 (public / private)
  - 발행일 (선택)
- **이미지 업로드**: 에디터 인라인 (드래그&드롭 또는 버튼) → `POST /api/assets/upload` → 마크다운에 `![](url)` 자동 삽입

### 4.5 카테고리 관리 (`/dashboard/categories`)

- 카테고리 트리 시각화
- 생성: 이름, 부모 카테고리, 표시 여부
- 수정: 이름, 표시 여부
- 순서 변경: 드래그&드롭 또는 순서 입력
- 삭제: 자식/글이 있으면 경고

### 4.6 에셋 라이브러리 (`/dashboard/assets`)

- 업로드된 이미지 갤러리 (그리드)
- 업로드: 드래그&드롭, 멀티 파일 (max 5개, 10MB/개)
- 허용 MIME: jpeg, png, gif, webp, svg
- URL 복사 기능 (마크다운/일반)
- 삭제 기능

### 4.7 댓글 관리 (`/dashboard/comments`)

- 전체 댓글 목록 (페이지네이션)
- 비밀 댓글 내용 확인 가능
- 강제 삭제 기능
- 필터: 게시글별, 비밀 여부

### 4.8 방명록 관리 (`/dashboard/guestbook`)

- 전체 방명록 목록 (페이지네이션)
- 강제 삭제 기능

---

## 5. 기술 결정

### 5.1 데이터 페칭

| 영역 | 전략 |
|---|---|
| **Public 페이지** | Server Components에서 초기 fetch (SSR) |
| **Admin 페이지** | TanStack Query로 클라이언트 캐시/리패치 |
| **뮤테이션** | TanStack Query `useMutation` + 캐시 무효화 |

### 5.2 마크다운 렌더링

- **서버 사이드**: Server Component에서 MD → HTML 변환
- 라이브러리: `unified` + `remark` + `rehype` 파이프라인
- 코드 하이라이팅: `shiki`
- HTML sanitize 적용

### 5.3 SEO

- Next.js `metadata` API 활용
- Open Graph 태그 (제목, 설명, 썸네일)
- 서버의 `/sitemap.xml`, `/rss.xml` 연동 (프록시 또는 링크)

### 5.4 인증 (Admin)

- 세션 쿠키 기반 (`POST /api/auth/admin/login`)
- Next.js middleware로 `/dashboard/*` 보호
- `GET /api/auth/me`로 세션 유효성 확인

### 5.5 이미지 처리

- 썸네일: `next/image` 컴포넌트 (자동 최적화, lazy loading)
- 마크다운 본문 내 이미지: 일반 `<img>` (rehype에서 렌더링)
- `next.config`에 API 서버 도메인을 `remotePatterns`에 등록

### 5.6 에러/로딩 상태

- 글로벌 `loading.tsx` — 스켈레톤 또는 스피너
- 글로벌 `error.tsx` — 에러 메시지 + 재시도 버튼
- 글로벌 `not-found.tsx` — 404 페이지
- 페이지별 전용 UI는 필요 시 추가

---

## 6. 디렉토리 구조 (예상)

```
client/src/
├── app/
│   ├── layout.tsx                    # 루트 레이아웃
│   ├── page.tsx                      # 홈 (글 목록)
│   ├── loading.tsx                   # 글로벌 로딩
│   ├── error.tsx                     # 글로벌 에러
│   ├── not-found.tsx                 # 404
│   ├── posts/
│   │   └── [slug]/page.tsx           # 글 상세
│   ├── categories/
│   │   └── [slug]/page.tsx           # 카테고리별 목록
│   ├── tags/
│   │   ├── page.tsx                  # 태그 목록
│   │   └── [slug]/page.tsx           # 태그별 목록
│   ├── popular/
│   │   └── page.tsx                  # 인기 글
│   ├── guestbook/
│   │   └── page.tsx                  # 방명록
│   ├── search/
│   │   └── page.tsx                  # 검색 결과
│   └── dashboard/
│       ├── login/page.tsx            # 관리자 로그인
│       ├── layout.tsx                # Admin 레이아웃 (사이드바)
│       ├── page.tsx                  # 대시보드
│       ├── posts/
│       │   ├── page.tsx              # 글 목록
│       │   ├── new/page.tsx          # 글 작성
│       │   └── [id]/edit/page.tsx    # 글 수정
│       ├── categories/
│       │   └── page.tsx              # 카테고리 관리
│       ├── assets/
│       │   └── page.tsx              # 에셋 라이브러리
│       ├── comments/
│       │   └── page.tsx              # 댓글 관리
│       └── guestbook/
│           └── page.tsx              # 방명록 관리
├── entities/
│   ├── post/                         # Post 타입, API 함수
│   ├── category/                     # Category 타입, API 함수
│   ├── tag/                          # Tag 타입, API 함수
│   ├── comment/                      # Comment 타입, API 함수
│   ├── guestbook/                    # Guestbook 타입, API 함수
│   ├── asset/                        # Asset 타입, API 함수
│   └── auth/                         # Auth 타입, API 함수
├── features/
│   ├── post-list/                    # 글 목록 (필터, 페이지네이션)
│   ├── post-detail/                  # 글 상세 (MD 렌더링)
│   ├── comment-section/              # 댓글 작성/목록
│   ├── guestbook-form/               # 방명록 작성
│   ├── search/                       # 검색 기능
│   ├── admin-login/                  # 로그인 폼
│   ├── post-editor/                  # 마크다운 에디터 + 프리뷰
│   ├── category-manager/             # 카테고리 CRUD
│   ├── asset-uploader/               # 이미지 업로드
│   └── admin-comment-manager/        # Admin 댓글/방명록 관리
├── widgets/
│   ├── header/                       # (기존) 공개 헤더
│   ├── footer/                       # (기존) 푸터
│   ├── logo/                         # (기존) 로고
│   ├── admin-sidebar/                # Admin 사이드바 네비게이션
│   └── admin-header/                 # Admin 헤더
├── shared/
│   ├── ui/                           # (기존) Button, Modal, Text 등
│   ├── lib/                          # (기존) 유틸리티
│   ├── hooks/                        # (기존) 공통 훅
│   ├── constant/                     # (기존) 상수
│   └── api/                          # API 클라이언트 (fetch wrapper)
└── app-layer/
    ├── provider/                     # (기존) 프로바이더
    ├── theme/                        # (기존) 테마
    └── style/                        # (기존) CSS
```

---

## 7. 구현 우선순위

### Phase 1: 핵심 골격
1. ~~API 클라이언트 설정 (`shared/api/`)~~ ✅ 완료
2. 홈 — 글 목록 페이지
3. 글 상세 페이지 (MD 서버 렌더링, shiki 코드 하이라이팅)
4. 카테고리 네비게이션 (헤더 통합)

### Phase 2: Admin 기본
5. 관리자 로그인 + 인증 미들웨어
6. 대시보드 (통계)
7. 글 목록 (Admin)
8. 글 에디터 (순수 textarea + 프리뷰)

### Phase 3: 공개 부가 기능
9. 댓글 시스템 (게스트, 비밀댓글 마스킹)
10. 방명록
11. 태그 목록/필터 (`GET /api/tags`)
12. 인기 글
13. 조회수 기록 (useEffect + sessionStorage 중복 방지)

### Phase 4: 부가 기능
14. 카테고리 관리
15. 에셋 라이브러리
16. SEO 최적화 (meta, OG, sitemap/RSS 연동)
17. 검색 기능 (헤더 검색바 + 결과 페이지)
18. Admin 댓글/방명록 관리

---

## 8. 제외 항목 (후속 버전)

- OAuth 로그인 (Google/GitHub) — 댓글/방명록에서 사용
- 글 시리즈/연재
- 뉴스레터/구독
- 관리자 사용자 관리
- i18n (다국어)
