# figma-remote MCP - HTML capture workflow

HTML 와이어프레임을 Playwright로 렌더링한 뒤 figma-remote의 `generate_figma_design`으로 Figma 파일에 캡처하는 워크플로우.

## Architecture

```
HTML file (.workspace/captures/wireframe-*.html)
    ↓ python3 -m http.server (localhost)
Playwright MCP (Chromium)
    ↓ capture.js injection
figma-remote generate_figma_design
    ↓ Figma REST API
Figma file (new page or existing node)
```

## Prerequisites

- `.mcp.json`에 `figma-remote` 설정:
  ```json
  {
    "figma-remote": {
      "type": "http",
      "url": "https://mcp.figma.com/mcp"
    }
  }
  ```
- Playwright MCP (browser automation)
- Figma Personal Access Token (figma-remote API 인증)

## Workflow

### Step 1. HTML wireframe 작성

`.workspace/captures/` 아래에 HTML 파일을 생성한다.

```
.workspace/captures/wireframe-home.html
.workspace/captures/wireframe-post.html
```

필수 요소:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>wireframe title</title>
<!-- Figma capture script - 반드시 포함 -->
<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script>
</head>
```

규칙:
- **capture.js 필수**: 이 스크립트가 DOM을 직렬화하여 Figma로 전송한다. 없으면 캡처가 동작하지 않는다.
- **CSS 인라인**: 외부 스타일시트 대신 `<style>` 블록 사용. 외부 CSS는 캡처 시 누락될 수 있다.
- **Google Fonts OK**: `<link>` 태그로 Google Fonts를 불러오면 Figma가 해당 폰트를 인식한다.
- **프레임 분리**: Desktop(1280px)과 Mobile(375px) 프레임을 별도 `<div>`로 나누면 Figma에서 각각 독립 프레임으로 캡처된다.

### Step 2. Local server 실행

```bash
cd .workspace/captures && python3 -m http.server 8888
```

또는 Playwright MCP가 직접 `file://` 경로를 열 수 있으면 서버 없이도 가능하다.

### Step 3. Playwright로 페이지 열기

Playwright MCP의 `browser_navigate`로 해당 URL을 연다:

```
browser_navigate({ url: "http://localhost:8888/wireframe-home.html" })
```

페이지가 완전히 렌더링될 때까지 대기한 뒤, `browser_take_screenshot`으로 렌더 상태를 확인할 수 있다.

### Step 4. Figma capture 시작

`generate_figma_design`을 `outputMode` 없이 호출하여 캡처 옵션을 받는다:

```
generate_figma_design({})
```

응답에서 `outputMode` 선택지를 확인한 뒤, 원하는 모드로 다시 호출한다.

#### 기존 파일에 추가하는 경우

```
generate_figma_design({
  outputMode: "existingFile",
  fileKey: "<figma-file-key>",
  nodeId: "<target-node-id>"    // 생략하면 새 페이지 생성
})
```

#### 새 파일로 생성하는 경우

```
generate_figma_design({
  outputMode: "newFile",
  fileName: "wireframe-home"
})
```

### Step 5. Capture polling

초기 호출이 `captureId`를 반환한다. 이후 완료될 때까지 polling:

```
generate_figma_design({ captureId: "<returned-capture-id>" })
```

5초 간격, 최대 10회 polling. 완료되면 Figma 파일 URL이 반환된다.

## File structure

```
.workspace/
  captures/
    wireframe-home.html      # 홈 와이어프레임
    wireframe-post.html      # 포스트 상세 와이어프레임
    wireframe-*.html          # 추가 와이어프레임
```

`.workspace/`는 `.gitignore` 처리되어 있으므로 HTML 임시 파일이 git에 포함되지 않는다.

## HTML wireframe template

최소 템플릿:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>wireframe</title>
<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script>
<link href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:            #f1f2f3;
    --surface:       #f9f9fa;
    --surface-2:     #f1f2f3;
    --surface-3:     #e6e8e9;
    --border:        #dbdde0;
    --border-strong: #a6adb3;
    --text:          #232629;
    --text-2:        #4b5158;
    --text-3:        #838c95;
    --text-4:        #babfc4;
    --primary:       #8a6fe0;
    --primary-2:     #b09ee9;
    --yellow:        #ffbe3d;
  }

  body {
    font-family: 'Gothic A1', ui-sans-serif, system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
  }
</style>
</head>
<body>

<!-- Desktop frame -->
<div style="width: 1280px; padding: 40px; margin: 0 auto;">
  <!-- content here -->
</div>

<!-- Mobile frame -->
<div style="width: 375px; padding: 20px; margin: 40px auto 0;">
  <!-- content here -->
</div>

</body>
</html>
```

## Troubleshooting

### Capture 후 빈 프레임

- `capture.js` 스크립트가 포함되어 있는지 확인.
- Playwright 브라우저에서 페이지가 완전히 렌더링되었는지 screenshot으로 확인.

### 폰트가 적용되지 않음

- Google Fonts `<link>` 태그가 `<head>`에 있는지 확인.
- Figma에서 해당 폰트가 설치되어 있거나 Google Fonts에서 지원하는 폰트인지 확인.

### Localhost 접근 불가

- Docker 컨테이너에서 `python3 -m http.server`를 실행하면 컨테이너 내부의 localhost.
- `network_mode: host`이면 macOS에서도 접근 가능.
- Playwright MCP가 같은 컨테이너에서 실행 중이면 localhost로 접근 가능.

### captureId polling timeout

- 10회 polling 후에도 완료되지 않으면 Figma 서버 측 문제. 잠시 후 재시도.
- 각 `captureId`는 1회만 사용 가능. 새 캡처를 시작하려면 새로운 `generate_figma_design` 호출 필요.
