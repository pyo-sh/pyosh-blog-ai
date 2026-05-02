# F-32: Favicon / Web Manifest

**상태:** DONE
**최종 수정:** 2026-05-02

---

## 1. 개요

사이트 아이덴티티를 위한 favicon 에셋과 PWA Web App Manifest를 관리한다. 기존 PNG/ICO 에셋에 SVG favicon을 추가하고, 색상 불일치를 수정하며, manifest 확장자를 W3C 권장 형식으로 변경한다.

## 2. 배경 및 동기

현재 favicon과 manifest가 동작하고 있으나 다음 문제가 있다:

- theme_color가 manifest(`#8D72E1`), viewport(`#6200EE`), msapplication(`#BB86FC`) 세 곳에서 불일치
- SVG favicon이 없어 다크모드 대응 불가
- `mstile-150x150` 참조가 있으나 실제 파일 없음
- manifest에서 `favicon.ico`의 type이 `image/png`으로 잘못 지정
- manifest 확장자가 `.json`이며, W3C 권장 `.webmanifest`가 아님
- `background_color`가 실제 사이트 배경색과 불일치

## 3. 목표

- Tailwind 디자인 토큰 기준으로 색상을 통일한다
- SVG favicon을 추가하여 다크모드에서 아이콘 색상이 자동 전환되도록 한다
- `theme-color` meta를 다크/라이트 분리하여 브라우저 상단바가 테마에 맞게 변경되도록 한다
- manifest 확장자를 `.webmanifest`로 변경한다
- 불필요한 참조를 정리하고 type 오류를 수정한다

## 4. 비목표

- 아이콘 디자인 변경 (현재 에셋이 최종)
- Service Worker / 오프라인 캐시 (PWA 완전 지원)
- 기존 PNG/ICO 에셋 삭제 (폴백으로 유지)

---

## 5. 상세 설계

### 5.1 favicon 에셋 구성

#### 현재 파일 (유지)

| 파일 | 용도 |
|---|---|
| `favicon.ico` | 레거시 브라우저 폴백 |
| `favicon-16x16.png` | 탭 아이콘 (소형) |
| `favicon-32x32.png` | 탭 아이콘 (표준) |
| `apple-touch-icon.png` | iOS 홈 화면 아이콘 |
| `android-chrome-192x192.png` | Android PWA 아이콘 |
| `android-chrome-512x512.png` | Android PWA 스플래시 아이콘 |

#### 추가 파일

| 파일 | 용도 |
|---|---|
| `favicon.svg` | 모던 브라우저 favicon + 다크모드 대응 |

SVG favicon은 기존 로고 아이콘(`widgets/logo/ui/logo-icon.tsx`)의 패스 데이터를 독립 SVG 파일로 추출한다. `prefers-color-scheme` 미디어 쿼리를 SVG 내부에 포함하여 다크모드 시 fill 색상이 자동 전환된다.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <style>
    path { fill: #232629; }
    @media (prefers-color-scheme: dark) {
      path { fill: #e9eaeb; }
    }
  </style>
  <!-- 로고 아이콘 패스 -->
</svg>
```

- 라이트 모드 fill: `#232629` (text-1 light)
- 다크 모드 fill: `#e9eaeb` (text-1 dark)

#### 브라우저 호환성

| 브라우저 | SVG favicon | 폴백 |
|---|---|---|
| Chrome/Edge | 지원 | - |
| Firefox | 지원 | - |
| Safari macOS 15.6+ | 지원 | - |
| Safari iOS | 탭에서 렌더링, 홈 화면은 PNG | `apple-touch-icon.png` |
| IE/Edge Legacy | 미지원 | `favicon.ico` |

### 5.2 theme-color 다크/라이트 분리

브라우저 상단 주소창/상태바 배경색을 테마에 맞게 변경한다.

- Android Chrome/Edge: 주소창 배경색
- iOS Safari 15+: 상단바 색상
- macOS Safari 15+: 탭바 배경색

#### Next.js Metadata API 설정

```typescript
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#8a6fe0" },
    { media: "(prefers-color-scheme: dark)", color: "#131415" },
  ],
};
```

- 라이트: `#8a6fe0` (primary-1 light)
- 다크: `#131415` (background-1 dark)

### 5.3 manifest 수정

파일명을 `manifest.json` → `manifest.webmanifest`로 변경한다.

```json
{
  "name": "Pyo-sh Blog",
  "short_name": "Pyo-sh Blog",
  "icons": [
    {
      "src": "/favicon.ico",
      "sizes": "64x64",
      "type": "image/x-icon"
    },
    {
      "src": "/favicon-16x16.png",
      "sizes": "16x16",
      "type": "image/png"
    },
    {
      "src": "/favicon-32x32.png",
      "sizes": "32x32",
      "type": "image/png"
    },
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/favicon.svg",
      "sizes": "any",
      "type": "image/svg+xml"
    }
  ],
  "display": "standalone",
  "theme_color": "#8a6fe0",
  "background_color": "#f9f9fa"
}
```

변경 사항:

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| 파일명 | `manifest.json` | `manifest.webmanifest` |
| favicon.ico type | `image/png` | `image/x-icon` |
| theme_color | `#8D72E1` | `#8a6fe0` |
| background_color | `#FFFFFF` | `#f9f9fa` |
| SVG favicon 항목 | 없음 | 추가 |

### 5.4 layout.tsx metadata 수정

```typescript
export const metadata: Metadata = {
  title: "Pyosh Blog",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", type: "image/x-icon" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
    other: [
      {
        rel: "icon",
        url: "/android-chrome-192x192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        rel: "icon",
        url: "/android-chrome-512x512.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  },
  manifest: "/manifest.webmanifest",
};
```

변경 사항:

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| SVG favicon | 없음 | icons 배열 최상단에 추가 |
| manifest 경로 | `/manifest.json` | `/manifest.webmanifest` |
| msapplication-TileColor | `#BB86FC` | 삭제 |
| msapplication-TileImage | `/mstile-150x150` (파일 없음) | 삭제 |
| viewport themeColor | `#6200EE` (단일) | 다크/라이트 분리 (5.2 참조) |

### 5.5 PWA 동작 범위

현재 `display: "standalone"` 설정으로 다음이 가능하다:

- 모바일에서 "홈 화면에 추가" 시 별도 앱 아이콘 생성
- 실행 시 브라우저 주소창/탭바 없이 전체 화면으로 표시
- `theme_color`에 따른 상태바 색상 적용
- `background_color`에 따른 앱 시작 시 스플래시 화면 배경색 표시

Service Worker가 없으므로 오프라인 동작은 불가. 네트워크 연결이 필요하다.

## 6. API 연동

없음. 정적 에셋과 메타데이터 설정만 해당.

## 7. 수용 기준

- [ ] SVG favicon이 `/public/favicon.svg`에 존재한다
- [ ] SVG favicon이 다크모드에서 밝은 색(`#e9eaeb`), 라이트모드에서 어두운 색(`#232629`)으로 표시된다
- [ ] 브라우저 탭에 favicon이 정상 표시된다 (Chrome, Firefox, Safari)
- [ ] iOS "홈 화면에 추가" 시 apple-touch-icon이 표시된다
- [ ] `theme-color`가 라이트(`#8a6fe0`)/다크(`#131415`)로 분리되어 브라우저 상단바에 적용된다
- [ ] manifest 파일이 `manifest.webmanifest`로 제공된다
- [ ] manifest의 `theme_color`가 `#8a6fe0`, `background_color`가 `#f9f9fa`이다
- [ ] `mstile-150x150` 관련 참조가 없다
- [ ] Lighthouse PWA 감사에서 아이콘/manifest 관련 경고 없음

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| SVG 미지원 브라우저 | ICO/PNG 폴백으로 자동 표시 |
| iOS 홈 화면 아이콘 | SVG 무시, apple-touch-icon.png 사용 |
| 시스템 다크모드 미설정 | SVG는 라이트 fill, theme-color는 라이트 값 적용 |
| manifest 캐시 | 파일명 변경이므로 기존 캐시와 충돌 없음 |

## 9. 의존성

- F-17 다크 모드 (theme-color 다크/라이트 분리가 테마 시스템 의존)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
