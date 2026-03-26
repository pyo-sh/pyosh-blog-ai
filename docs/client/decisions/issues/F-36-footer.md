# [F-36] Footer 콘텐츠

> 모든 Public 페이지 하단에 표시되는 Footer. GitHub 프로필 링크, 이메일 링크, 저작권 문구를 포함한다. Admin 페이지에서는 숨긴다.

## SPEC 참조

- `docs/client/specs/footer.md`

## 상세 설계

### 콘텐츠 구성

위에서 아래 순서:

1. **소셜 링크**
   - GitHub: 아이콘 + "pyo-sh" 텍스트, `https://github.com/pyo-sh` 링크
   - 이메일: 아이콘 + 이메일 주소 텍스트, `mailto:` 링크
2. **저작권 문구** - `(c) {연도} pyo-sh`

### UI 구성

#### 레이아웃

```
┌──────────────────────────────────┐
│                                  │
│       GitHub pyo-sh              │
│       Mail   pygosky@gmail.com   │
│                                  │
│        (c) 2026 pyo-sh           │
│                                  │
└──────────────────────────────────┘
```

- 전체: 수직 중앙 정렬, 수평 중앙 정렬
- 상단 border: `border-t border-border-3`
- 배경: `bg-background-1`

#### 간격

| 요소 간 | 간격 |
|---|---|
| 소셜 링크 항목 간 | `8px` (0.5rem) |
| 소셜 링크 ~ 저작권 | `16px` (1rem) |
| Footer 상하 패딩 | `32px` (2rem) |

#### 저작권 문구 스타일

- 폰트: `body-xs`
- 색상: `text-text-4` (보조 텍스트)
- 연도: JavaScript `new Date().getFullYear()`로 동적 생성

#### 소셜 링크 스타일

- 아이콘: `1.5rem x 1.5rem`
- 텍스트: `body-xs`
- 기본 색상: `text-text-4`
- 호버: `text-text-1` + `transition-colors`
- 아이콘-텍스트 간격: `10px` (0.625rem)

### 표시 범위

| 페이지 | Footer |
|---|---|
| Public 전체 (홈, 글 상세, 태그 등) | 표시 |
| Admin 대시보드 (`/manage/*`) | 숨김 |
| Admin 로그인 (`/manage/login`) | 숨김 |

Admin에서 숨기는 방법: Admin 레이아웃(`app/manage/layout.tsx`)은 별도의 Provider를 사용하거나, Providers 컴포넌트에 Footer 표시 여부를 제어하는 prop을 전달한다.

### URL 변경

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| `URLS.github` | `https://github.com/pyo-sh/pyosh_blog` | `https://github.com/pyo-sh` |
| GitHub 표시 텍스트 | `https://github.com/pyo-sh/pyosh_blog` (전체 URL) | `pyo-sh` |

`URLS.githubProfile`은 이미 `https://github.com/pyo-sh`로 정의되어 있으므로, `URLS.github`를 프로필 URL로 통일하거나 Footer에서 `URLS.githubProfile`을 사용한다.

### 반응형

모바일과 데스크톱 모두 동일한 세로 중앙 정렬 레이아웃을 사용한다. 브레이크포인트별 차이 없음.

### 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `widgets` | `footer/index.tsx` | Footer 컴포넌트 (기존 파일 수정) |
| `shared` | `constant/url.ts` | GitHub URL 값 변경 |
| `shared` | `ui/icons/github-icon.tsx` | 기존 아이콘 재사용 |
| `shared` | `ui/icons/mail-icon.tsx` | 기존 아이콘 재사용 |

### 다크모드

시맨틱 토큰 기반으로 자동 대응. 추가 작업 없음.

- `bg-background-1`: 라이트 `#f9f9fa` / 다크 `#131415`
- `border-border-3`: 라이트 `#dbdde0` / 다크 `#54595d`
- `text-text-4`: 라이트 `#babfc4` / 다크 `#656b70`

## API 연동

없음. 순수 정적 UI.

## 수용 기준

- [ ] Footer에 GitHub 링크, 이메일 링크, 저작권 문구가 표시된다
- [ ] 저작권 문구가 `(c) {현재연도} pyo-sh` 형식으로 표시된다
- [ ] GitHub 링크가 `https://github.com/pyo-sh`로 이동하며 "pyo-sh"로 표시된다
- [ ] Public 페이지에서 Footer가 표시된다
- [ ] Admin 페이지(`/manage/*`)에서 Footer가 숨겨진다
- [ ] 모바일/데스크톱 모두 중앙 정렬이 유지된다
- [ ] 다크모드 자동 적용
- [ ] 접근성: 링크에 적절한 텍스트, nav 랜드마크 (A-01 참조)

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| 연도가 바뀌는 시점 | `new Date().getFullYear()` 실시간 반영 |
| 이메일 링크 클릭 시 메일 앱 없음 | 브라우저 기본 동작 (OS 메일 앱 선택 또는 무반응) |
| 매우 좁은 뷰포트 | 텍스트 줄바꿈 허용, 최소 너비 제한 없음 |

## 의존성

- Blocked by: 없음
- Blocks: 없음
