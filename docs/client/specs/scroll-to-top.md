# F-15: 맨 위로 버튼

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

긴 콘텐츠 페이지에서 우하단에 고정된 "맨 위로" 버튼을 표시한다. 1 viewport 이상 스크롤 시 나타나며, 클릭 시 smooth scroll로 페이지 상단으로 이동한다. 모바일에서는 미표시.

## 2. 배경 및 동기

글 상세, 태그 목록 등 긴 콘텐츠 페이지에서 상단으로 빠르게 복귀할 수단이 필요하다.

## 3. 목표

- 1 viewport 이상 스크롤 시 맨 위로 버튼을 표시한다
- 클릭 시 smooth scroll로 상단 이동한다
- 긴 콘텐츠 페이지에서만 표시한다
- 데스크톱 전용 (모바일 미표시)

## 4. 비목표

- 스크롤 진행률 표시
- 모바일 표시
- 모든 페이지에서 표시

---

## 5. 상세 설계

### 5.1 사용자 흐름

1. 긴 콘텐츠 페이지 접속
2. 1 viewport 높이 이상 스크롤
3. 우하단에 맨 위로 버튼 페이드인
4. 버튼 클릭 → smooth scroll로 상단 이동
5. 상단 도달 시 버튼 페이드아웃

### 5.2 UI 구성

#### 버튼

- 위치: 우하단 고정 (`fixed bottom-6 right-6`)
- 형태: 원형 버튼 + 업 화살표(↑) SVG 아이콘
- Z-index: `z-40` (헤더 `z-[1000]`, 모달 `z-50` 보다 낮음)
- 애니메이션: opacity 페이드인/아웃 transition

#### 표시 조건

| 조건 | 버튼 |
|---|---|
| 스크롤 < 1 viewport 높이 | 숨김 |
| 스크롤 >= 1 viewport 높이 | 표시 |
| 뷰포트 < 1080px (모바일) | 숨김 |

#### 표시 대상 페이지

긴 콘텐츠가 예상되는 페이지에서만 렌더링:

- 글 상세 (`/posts/[slug]`)
- 태그 목록 (`/tags`)
- 태그별 글 목록 (`/tags/[slug]`)
- 검색 결과 (`/search`)
- 방명록 (`/guestbook`)

홈(`/`), Admin 페이지 등 짧은 페이지에서는 미표시.

### 5.3 데이터 흐름

```
ScrollToTop 컴포넌트:
  useEffect
    └─ window.addEventListener("scroll", throttledHandler)
    └─ handler: window.scrollY >= window.innerHeight → setVisible(true)

  클릭:
    └─ window.scrollTo({ top: 0, behavior: "smooth" })
```

- 기존 `throttle` 유틸 재활용 (100ms 주기)
- `window.innerHeight`로 1 viewport 높이 기준 계산

### 5.4 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `shared` | `ui/scroll-to-top.tsx` | ScrollToTop 컴포넌트 |
| `shared` | `ui/icons/arrow-up-icon.tsx` | 업 화살표 SVG 아이콘 |
| `shared` | `lib/throttle.ts` | 기존 throttle 유틸 재활용 |

- 표시 대상 페이지의 레이아웃 또는 페이지 컴포넌트에서 `<ScrollToTop />` 배치
- 모바일 숨김은 CSS `hidden md:block` 또는 Tailwind 반응형 클래스로 처리

## 6. API 연동

없음. 순수 클라이언트 UI.

## 7. 수용 기준

- [ ] 1 viewport 높이 이상 스크롤 시 우하단에 버튼이 페이드인된다
- [ ] 버튼 클릭 시 smooth scroll로 페이지 상단으로 이동한다
- [ ] 상단 복귀 후 버튼이 페이드아웃된다
- [ ] 긴 콘텐츠 페이지에서만 표시된다
- [ ] 모바일(1080px 미만)에서 미표시
- [ ] 헤더, 모달보다 낮은 z-index
- [ ] 다크모드 자동 적용
- [ ] 접근성: `aria-label="맨 위로"`, 키보드 포커스 가능 (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 페이지 콘텐츠가 1 viewport 미만 | 버튼 미표시 (스크롤 불가하므로 조건 충족 안 됨) |
| 브라우저 리사이즈로 viewport 높이 변경 | 실시간 반영 (window.innerHeight 재계산) |
| smooth scroll 중 사용자가 추가 스크롤 | 브라우저 기본 동작 (scroll 중단) |
| 모달 열린 상태에서 버튼 표시 | 모달 z-index가 높으므로 자연스럽게 가려짐 |

## 9. 의존성

- 없음 (기반 기능)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
