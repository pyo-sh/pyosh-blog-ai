# F-38: Storybook 환경 구성

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

프론트엔드 컴포넌트의 디자인 검토와 테스트를 위한 Storybook 환경을 구성한다. DB/서버 없이 MSW로 API를 모킹하여 Admin 페이지를 포함한 모든 화면을 Storybook에서 확인할 수 있도록 한다. Wireframe 문서화와 대응하는 페이지/화면 단위 Story를 작성하여 체계적인 개발-검토 흐름을 만든다.

## 2. 배경 및 동기

- AI가 개발한 프론트엔드 결과물을 최종 승인자가 검토할 환경이 부족하다
- Admin 페이지 확인을 위해 DB + 서버를 매번 구동해야 하는 비효율
- 디자인만 검토하고 싶을 때 전체 스택이 필요한 것은 과도하다
- Wireframe과 Storybook의 문서 구조를 맞추면 설계-구현-검토가 일관된 흐름으로 연결된다
- 모든 클라이언트 기능 개발 시 Storybook story 작성을 표준으로 포함해야 한다

## 3. 목표

- Storybook 8 + Next.js + Tailwind CSS v4 통합 환경을 구성한다
- MSW로 API를 모킹하여 서버 의존성 없이 모든 화면을 표시한다
- 다크/라이트 모드 전환을 Storybook 툴바에서 지원한다
- 반응형 뷰포트 전환(1080px 브레이크포인트)을 지원한다
- 접근성 자동 검사(addon-a11y)를 통합한다
- Wireframe 문서화와 대응하는 페이지/화면 단위 Story 구조를 정의한다
- 이후 모든 클라이언트 기능 스펙에 "Storybook story 작성" 수용 기준을 포함한다

## 4. 비목표

- Storybook 정적 빌드/배포 (`build-storybook`)
- 프로덕션 환경 포함 (로컬 개발 전용)
- 시각적 회귀 테스트 자동화 (Chromatic 등)
- 개별 기본 UI 컴포넌트(버튼, 아이콘) 단위 Story

---

## 5. 상세 설계

### 5.1 패키지 구성

#### 핵심 패키지

| 패키지 | 용도 |
|---|---|
| `@storybook/nextjs` | Next.js App Router 프레임워크 지원 |
| `@storybook/react` | React 렌더러 |
| `@storybook/addon-essentials` | 기본 애드온 번들 (Controls, Actions, Viewport 등) |
| `@storybook/addon-themes` | 다크/라이트 모드 툴바 전환 |
| `@storybook/addon-a11y` | axe-core 기반 접근성 자동 검사 |
| `msw` | API 모킹 (Mock Service Worker) |
| `msw-storybook-addon` | Storybook + MSW 통합 |

#### package.json 스크립트

```json
{
  "scripts": {
    "storybook": "storybook dev -p 6006"
  }
}
```

로컬 개발 전용. `build-storybook`은 추가하지 않는다.

### 5.2 Storybook 설정

#### `.storybook/main.ts`

```typescript
import type { StorybookConfig } from "@storybook/nextjs";

const config: StorybookConfig = {
  stories: ["../stories/**/*.stories.@(ts|tsx)"],
  addons: [
    "@storybook/addon-essentials",
    "@storybook/addon-themes",
    "@storybook/addon-a11y",
  ],
  framework: {
    name: "@storybook/nextjs",
    options: {},
  },
  staticDirs: ["../public"],
};

export default config;
```

#### `.storybook/preview.tsx`

```typescript
import type { Preview } from "@storybook/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import { initialize, mswLoader } from "msw-storybook-addon";
import "../src/app-layer/style/index.css"; // Tailwind + 테마 토큰

// MSW 초기화
initialize();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: Infinity },
  },
});

const preview: Preview = {
  decorators: [
    // TanStack Query Provider
    (Story) => (
      <QueryClientProvider client={queryClient}>
        <Story />
      </QueryClientProvider>
    ),
    // 다크/라이트 모드 전환
    withThemeByDataAttribute({
      themes: {
        light: "light",
        dark: "dark",
      },
      defaultTheme: "light",
      parentSelector: "body",
      attributeName: "data-theme",
    }),
  ],
  loaders: [mswLoader],
  parameters: {
    viewport: {
      viewports: {
        mobile: { name: "Mobile", styles: { width: "375px", height: "812px" } },
        desktop: { name: "Desktop", styles: { width: "1280px", height: "800px" } },
      },
    },
  },
};

export default preview;
```

### 5.3 MSW 모킹 전략

#### 디렉토리 구조

```
stories/
├── mocks/
│   ├── handlers.ts          # 공통 API handler 모음
│   ├── data/
│   │   ├── posts.ts         # 게시글 임시 데이터
│   │   ├── categories.ts    # 카테고리 임시 데이터
│   │   ├── comments.ts      # 댓글 임시 데이터
│   │   ├── guestbook.ts     # 방명록 임시 데이터
│   │   ├── assets.ts        # 에셋 임시 데이터
│   │   └── stats.ts         # 통계 임시 데이터
│   └── browser.ts           # MSW browser worker 설정
```

#### 공통 handler vs Story 오버라이드

```typescript
// stories/mocks/handlers.ts - 공통 API 응답
export const handlers = [
  http.get("/api/posts", () => {
    return HttpResponse.json({ data: mockPosts, meta: mockMeta });
  }),
  http.get("/api/auth/me", () => {
    return HttpResponse.json({ id: 1, name: "Admin" });
  }),
  // ...
];

// stories/widgets/admin-dashboard.stories.tsx - 특수 케이스 오버라이드
export const EmptyDashboard: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/stats/summary", () => {
          return HttpResponse.json({ views: 0, posts: 0, comments: 0 });
        }),
      ],
    },
  },
};
```

공통 API 응답은 `stories/mocks/`에 중앙 관리하고, 빈 상태/에러 상태 등 특수 케이스만 개별 Story에서 오버라이드한다.

### 5.4 Story 디렉토리 구조

`stories/` 디렉토리를 별도로 두고, FSD 계층 구조를 반영한다. Story 단위는 **페이지/화면 단위**로 Wireframe 문서와 대응한다.

```
stories/
├── mocks/                           # MSW 모킹 데이터
├── app/                             # 페이지 레벨 Story
│   ├── home.stories.tsx             # F-01: 홈 - 글 목록
│   ├── post-detail.stories.tsx      # F-02: 글 상세
│   ├── category-posts.stories.tsx   # F-03: 카테고리별 글 목록
│   ├── tags.stories.tsx             # F-04: 태그 목록
│   ├── search.stories.tsx           # F-11: 검색
│   ├── guestbook.stories.tsx        # F-09: 방명록
│   └── error.stories.tsx            # F-12: 에러 페이지
├── widgets/                         # 위젯 레벨 Story
│   ├── header.stories.tsx           # 헤더
│   ├── footer.stories.tsx           # F-36: Footer
│   ├── sidebar.stories.tsx          # F-39: 사이드바
│   └── admin/
│       ├── dashboard.stories.tsx    # F-20: 대시보드
│       ├── post-editor.stories.tsx  # F-22 + F-23: 에디터 + 메타데이터
│       ├── post-list.stories.tsx    # F-21: 글 관리
│       ├── category-tree.stories.tsx # F-24 + F-25: 카테고리
│       ├── asset-gallery.stories.tsx # F-26 + F-27: 에셋
│       ├── comment-manager.stories.tsx # F-28: 댓글 관리
│       └── guestbook-manager.stories.tsx # F-29: 방명록 관리
└── shared/                          # 공통 UI 조합 Story (필요 시)
    ├── toast.stories.tsx            # F-14: Toast
    ├── loading-states.stories.tsx   # F-13: 로딩/빈 상태
    └── scroll-to-top.stories.tsx    # F-15: 맨 위로 버튼
```

#### Wireframe 대응 규칙

| Wireframe 문서 | Story 파일 | 관계 |
|---|---|---|
| 페이지 Wireframe | `stories/app/*.stories.tsx` | 1:1 대응 |
| 위젯 Wireframe | `stories/widgets/*.stories.tsx` | 1:1 대응 |
| 상태 변형 (빈 상태, 에러 등) | 같은 Story 파일 내 variant | Story 내 분기 |

### 5.5 Story 작성 컨벤션

#### 기본 구조

```typescript
import type { Meta, StoryObj } from "@storybook/react";
import { http, HttpResponse } from "msw";
import { PostDetailPage } from "@app/posts/[slug]/page";

const meta: Meta<typeof PostDetailPage> = {
  title: "App/PostDetail",     // Storybook 사이드바 경로
  component: PostDetailPage,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof PostDetailPage>;

// 기본 상태
export const Default: Story = {};

// 다크모드 (툴바 전환으로도 가능하지만 고정 variant 제공)
export const DarkMode: Story = {
  parameters: {
    themes: { themeOverride: "dark" },
  },
};

// 모바일 뷰포트
export const Mobile: Story = {
  parameters: {
    viewport: { defaultViewport: "mobile" },
  },
};

// 에러 상태
export const NotFound: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/posts/:slug", () => {
          return new HttpResponse(null, { status: 404 });
        }),
      ],
    },
  },
};
```

#### 네이밍 컨벤션

| Story 이름 | 용도 |
|---|---|
| `Default` | 기본 상태 (데이터 있음) |
| `Empty` | 빈 상태 |
| `Loading` | 로딩 상태 |
| `Error` | 에러 상태 |
| `Mobile` | 모바일 뷰포트 |
| `DarkMode` | 다크모드 고정 |

### 5.6 접근성 검사 (addon-a11y)

axe-core 기반으로 Story 렌더링 시 자동 실행된다.

**검사 항목:**
- 색상 대비 비율 (WCAG AA 기준)
- `alt` 텍스트 누락
- `aria-label` 누락
- 키보드 포커스 순서
- 색맹 시뮬레이션

A-01 접근성 체크리스트의 항목 중 자동 검출 가능한 약 57%를 커버한다. Storybook의 Accessibility 패널에서 Violations/Passes/Incomplete 탭으로 결과를 확인한다.

### 5.7 다른 기능 스펙과의 관계

F-38은 모든 클라이언트 기능의 선행 조건이다. 이후 클라이언트 기능 스펙의 수용 기준에 다음을 포함해야 한다:

```markdown
- [ ] Storybook story가 작성되어 `stories/` 에 배치되었다
- [ ] 기본 상태, 빈 상태, 에러 상태 variant가 포함된다
- [ ] addon-a11y 위반 사항이 없다
```

## 6. API 연동

없음. MSW로 모든 API를 모킹한다.

## 7. 수용 기준

- [ ] `pnpm storybook`으로 Storybook이 정상 실행된다
- [ ] Tailwind CSS v4 디자인 토큰이 Story에 올바르게 적용된다
- [ ] 툴바에서 다크/라이트 모드 전환이 동작한다
- [ ] 뷰포트 전환(모바일 375px, 데스크톱 1280px)이 동작한다
- [ ] MSW로 모킹된 API 응답으로 컴포넌트가 정상 렌더링된다
- [ ] TanStack Query 의존 컴포넌트가 서버 없이 동작한다
- [ ] addon-a11y 패널에서 접근성 검사 결과가 표시된다
- [ ] `stories/` 디렉토리가 FSD 계층 구조로 구성되었다
- [ ] 프로덕션 빌드에 Storybook 관련 코드가 포함되지 않는다

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| Next.js Server Component를 Story로 작성 | Client Component wrapper로 감싸거나, Storybook에서는 Client Component 버전 사용 |
| `next/image` 최적화 | Storybook의 Next.js 프레임워크가 자동 처리 (`@storybook/nextjs`) |
| `next/navigation` 사용 컴포넌트 | `@storybook/nextjs`가 자동 모킹 제공 |
| 파일 업로드 Story | MSW로 업로드 응답 모킹, 실제 파일 저장 없음 |
| 인증 필요 화면 | MSW에서 `/api/auth/me` 성공 응답 반환으로 인증 상태 시뮬레이션 |

## 9. 의존성

- 없음 (기반 기능, 다른 클라이언트 기능의 선행 조건)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
