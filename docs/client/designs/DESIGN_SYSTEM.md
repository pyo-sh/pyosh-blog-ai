# pyosh blog - Design System Reference

> 이 문서를 새 페이지 디자인 요청 시 프롬프트에 첨부하면, 홈 페이지와 동일한 스타일로 출력된다.
> 레퍼런스 파일: `.workspace/design/home-page.html`

---

## 1. 기반 설정

### 출력 형식
- Standalone HTML, 브라우저에서 바로 열리는 단일 파일
- `<!DOCTYPE html>` ~ `</html>` 완전한 파일, 생략 금지

### CDN
```html
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@300;400;500;600;700;800;900&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap">
<script src="https://code.iconify.design/iconify-icon/2.3.0/iconify-icon.min.js"></script>
```

### 폰트
- **본문:** Gothic A1 (한국어 기본)
- **영문 디스플레이:** Outfit (헤딩, 로고 등)
- **font-family:** `'Gothic A1', ui-sans-serif, system-ui, sans-serif`
- **금지:** Inter, Noto Sans KR, Roboto, Arial, Open Sans, Pretendard

---

## 2. 컬러 시스템

### 토큰 구조
의미 기반 4단계 시스템. 모든 색상은 CSS 변수로 참조한다.

| 토큰 | 용도 | Light | Dark |
|---|---|---|---|
| `--background1` | 페이지 배경 | `#f9f9fa` | `#131415` |
| `--background2` | 카드/섹션 배경, footer | `#f1f2f3` | `#1d1e20` |
| `--background3` | hover 배경, 썸네일 placeholder | `#e6e8e9` | `#26282a` |
| `--background4` | 강조 배경 | `#dbdde0` | `#303335` |
| `--text1` | 제목, 강조 텍스트 | `#232629` | `#e9eaeb` |
| `--text2` | 본문 | `#4b5158` | `#c4c6c9` |
| `--text3` | 보조 텍스트, 부제 | `#838c95` | `#999ea2` |
| `--text4` | 날짜, 메타 정보, 비활성 | `#babfc4` | `#656b70` |
| `--border3` | 구분선, 얇은 테두리 | `#dbdde0` | `#54595d` |
| `--border4` | footer 상단선 등 미세 테두리 | `#f1f2f3` | `#35383a` |
| `--primary1` | 액센트 (배지, 활성 버튼, 링크) | `#8a6fe0` | `#a591e8` |
| `--primary2` | 액센트 hover/light | `#b09ee9` | `#c7bbf0` |

### 색상 사용 규칙
- **액센트:** Primary Purple 1개만 사용. 페이지당 추가 액센트 색상 없음
- **배지 배경:** `color-mix(in srgb, var(--primary1) 12%, transparent)` + `color: var(--primary1)`
- **순수 검정 (#000000) 금지.** 가장 어두운 색은 `--background1` Dark (#131415)
- **네온 글로우, AI 그라디언트 금지**
- Light/Dark 양쪽 모두 지원. `data-theme` 속성으로 전환

---

## 3. 레이아웃

### 컨테이너
```
max-w-4xl mx-auto px-4 sm:px-6 lg:px-8
```
- 컨텐츠 폭: `max-w-4xl` (896px)
- 좌우 패딩: 모바일 16px, sm 24px, lg 32px
- `max-w-7xl` 아님. 블로그 컨텐츠 특성상 좁은 컨테이너 사용

### 네비게이션
- 상단 고정 (`fixed top-0 z-40`)
- Glass 효과: `backdrop-filter: blur(16px) saturate(1.4)` + `color-mix` 반투명 배경
- 높이: `h-14` (56px)
- 좌: 로고 (아이콘 + 텍스트), 우: 아이콘 버튼들 (검색, 테마 토글)
- 아래 `h-14` spacer로 본문 밀어냄

### 섹션 간격
- 페이지 상단 패딩: `pt-8`
- 페이지 하단 패딩: `pb-16`
- 섹션 간 간격: `mb-8` (헤더 → 리스트), `mb-2` (고정글 → 구분선 → 일반글)
- 리스트 아이템 내부 패딩: `px-4 py-5 sm:px-5`

### 높이
- `min-h-[100dvh]` 사용. `h-screen` 금지 (iOS Safari 문제)

---

## 4. 타이포그래피

### 계층 구조
| 요소 | 클래스 | 용도 |
|---|---|---|
| 페이지 제목 | `text-2xl md:text-3xl font-bold tracking-tight` | 섹션 헤딩 |
| 부제 | `text-sm` + `color: var(--text3)` | 페이지 설명 |
| 아이템 제목 | `text-base sm:text-lg font-bold leading-snug` | 리스트 아이템 |
| 본문/요약 | `text-sm leading-relaxed` + `color: var(--text3)` | 요약, 설명 |
| 메타 정보 | `text-xs` + `color: var(--text4)` | 날짜, 조회수, 댓글수 |
| 배지 | `text-xs font-medium` | 카테고리 태그 |

### 한국어 규칙
- `word-break: keep-all` (`.break-keep`) - 한국어 텍스트 블록에 필수
- `leading-snug` ~ `leading-relaxed` 사용. `leading-none` 금지 (한국어 가독성)
- 모든 콘텐츠는 자연스러운 한국어. 번역체 금지
- 존댓말(합니다/하세요) 일관 유지

### 텍스트 생략
- 제목: `line-clamp-2`
- 요약: `line-clamp-2` (sm 이상에서만 표시, `hidden sm:block`)

---

## 5. 컴포넌트 패턴

### 리스트 아이템
```
article.post-item > a(absolute overlay) + div.flex
  ├── div.thumb-wrap (hidden md:block, w-32 h-24, rounded-lg, overflow-hidden)
  └── div.flex-1.min-w-0
       ├── div (배지 + 날짜)
       ├── h2 (제목, line-clamp-2)
       ├── p (요약, line-clamp-2, hidden sm:block)
       └── div (메타: 조회수, 댓글수)
```
- `rounded-xl` 컨테이너
- 호버: `hover:bg-bg-2` + `translateX(4px)`
- 전체 영역 클릭: absolute positioned `<a>` 오버레이

### 배지
```html
<span style="background: color-mix(in srgb, var(--primary1) 12%, transparent); color: var(--primary1);"
      class="px-2 py-0.5 rounded-md text-xs font-medium">카테고리</span>
```
- 호버 시 shimmer 효과 (::after pseudo-element)

### 페이지네이션
- `w-9 h-9 rounded-lg` 버튼
- 활성: `background: var(--primary1); color: #fff; font-bold`
- 비활성: `disabled:opacity-30 disabled:cursor-not-allowed`
- 호버: `scale(1.08)`, 클릭: `scale(0.95)`
- 구성: `[<<] [<] 1 2 3 4 ... 18 19 20 [>] [>>]`

### 아이콘
- Iconify Solar 세트 전용
- 사용 예: `<iconify-icon icon="solar:eye-linear" width="14"></iconify-icon>`
- 자주 쓰는 아이콘:
  - 검색: `solar:magnifer-linear`
  - 테마: `solar:sun-2-linear` / `solar:moon-linear`
  - 조회수: `solar:eye-linear`
  - 댓글: `solar:chat-round-dots-linear`
  - 고정: `solar:pin-bold`
  - 화살표: `solar:alt-arrow-left-linear` / `solar:alt-arrow-right-linear`
  - 링크: `solar:link-minimalistic-2-linear`
- 이모지 사용 금지. 모든 아이콘은 Iconify Solar로 대체

### Footer
- `border-top: 1px solid var(--border4)` + `background: var(--background2)`
- 로고 + 저작권 (좌), 링크 (우)
- 미니멀. 4컬럼 링크 팜 금지

---

## 6. 모션 / 인터랙션

### 이징 함수
모든 인터랙션의 기본 easing: `cubic-bezier(0.16, 1, 0.3, 1)` (decelerate)

### 진입 애니메이션
- `IntersectionObserver`로 뷰포트 진입 감지 (threshold: 0.08)
- `@keyframes fadeInUp`: `opacity: 0; translateY(1.5rem)` -> `opacity: 1; translateY(0)`
- 지속 시간: 0.5~0.6s
- 아이템 간 stagger: `80ms` 간격
- `window.addEventListener('scroll')` 사용 금지

### 호버 효과
| 요소 | 효과 |
|---|---|
| 리스트 아이템 | `translateX(4px)` + `bg-bg-2` |
| 썸네일 이미지 | `scale(1.05)` (0.5s) |
| 페이지네이션 버튼 | `scale(1.08)` hover, `scale(0.95)` active |
| 테마 토글 | `rotate(30deg) scale(1.1)` |
| 배지 | shimmer sweep (::after translateX) |

### 상시 애니메이션
- 고정(pin) 아이콘: `float` 효과 (2.5s ease-in-out infinite, translateY -3px)

### 텍스처
- body::after에 노이즈 텍스처 오버레이 (opacity: 0.025, z-60, pointer-events: none)
- SVG feTurbulence 기반, fixed position

---

## 7. 이미지

- Placeholder: `https://picsum.photos/seed/{설명적_이름}/{width}/{height}`
- Avatar: `https://i.pravatar.cc/150?u={고유_이름}`
- Unsplash URL 사용 금지
- 모든 이미지: `loading="lazy"` + `decoding="async"` + `alt` 텍스트
- 썸네일 컨테이너: `overflow-hidden rounded-lg` + background fallback

---

## 8. 반응형

### 브레이크포인트 전략
| 요소 | 모바일 | sm (640px+) | md (768px+) | lg (1024px+) |
|---|---|---|---|---|
| 컨테이너 패딩 | px-4 | px-6 | - | px-8 |
| 썸네일 | hidden | - | block | - |
| 요약 텍스트 | hidden | block | - | - |
| 제목 크기 | text-base | text-lg | - | - |
| 페이지 헤딩 | text-2xl | - | text-3xl | - |

---

## 9. 접근성

- 네비게이션 버튼: `aria-label`
- 페이지네이션: `aria-label="페이지 탐색"`, 각 버튼에 `aria-label="N 페이지"`
- 현재 페이지: `aria-current="page"`
- 리스트 아이템: absolute `<a>`에 전체 제목을 `aria-label`로
- 섹션: `aria-label` 로 용도 명시

---

## 10. 금지 패턴 (체크리스트)

- [ ] Inter, Noto Sans KR, Roboto, Arial 폰트 없음
- [ ] 이모지 없음, 모든 아이콘은 Iconify Solar
- [ ] 순수 검정(#000) 없음
- [ ] `h-screen` 없음 (`min-h-[100dvh]` 사용)
- [ ] 네온/외곽 글로우 없음
- [ ] Purple/Blue AI 그라디언트 없음
- [ ] Unsplash URL 없음
- [ ] Lorem ipsum 또는 영문 placeholder 없음
- [ ] "김철수", "Acme Corp" 같은 AI 클리셰 이름 없음
- [ ] 둥근 숫자 (50,000+) 없음 - 유기적 숫자 사용 (47,200+)
- [ ] `<!-- 나머지 동일 -->` 같은 생략 패턴 없음
- [ ] `window.addEventListener('scroll')` 없음
