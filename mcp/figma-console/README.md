# figma-console MCP setup guide

figma-console-mcp를 Claude Code (Docker container)에서 Figma Desktop과 연결하는 설정 가이드.

## Architecture

```
Claude Code (Docker container, network_mode: host)
    ↓ stdio (subprocess)
figma-console-mcp (npx, WebSocket 0.0.0.0:9223-9232)
    ↓ WebSocket (macOS localhost)
Figma Desktop Bridge Plugin (macOS)
    ↓ Figma Plugin API
Figma file (node CRUD, Variables, Typography, Components)
```

### Docker Desktop for Mac network

```
macOS
  ├── Figma Desktop (ws://localhost:9223)
  ├── Docker Desktop
  │     └── Linux VM (network_mode: host)
  │           └── container (figma-console-mcp 0.0.0.0:9223)
  └── "Enable host networking" → VM ports exposed to macOS localhost
```

### MCP role split

| MCP | Role |
|---|---|
| `figma-remote` | Read designs + HTML capture (`generate_figma_design`) |
| `figma-console` | 63+ tools: node CRUD, Variables, Typography, Components |
| `playwright` (plugin) | Browser automation for HTML capture |

## Prerequisites

- Docker Desktop 4.34+ with `network_mode: host`
- Figma Desktop (macOS)
- Figma Personal Access Token (`figd_` prefix)

## Setup steps

### 1. Docker Desktop network settings

Docker container에서 바인딩한 포트가 macOS localhost에 노출되어야 한다.

1. Docker Desktop > **Settings** > **Resources** > **Network**
2. **Enable host networking** 활성화
3. IPv4/IPv6 dual stack 설정 (선택)
4. **Apply & restart**

이 설정이 없으면 `network_mode: host`로 컨테이너가 Linux VM의 네트워크를 공유하더라도 macOS에서 접근할 수 없다.

### 2. Figma Personal Access Token

1. Figma > Settings > **Personal access tokens**
2. 토큰 생성 (`figd_`로 시작)
3. `/workspace/.env`에 추가:

```
FIGMA_ACCESS_TOKEN=figd_...
```

`.env`는 `.gitignore` 처리되어 있다.

### 3. `.mcp.json` configuration

```json
{
  "mcpServers": {
    "figma-remote": {
      "type": "http",
      "url": "https://mcp.figma.com/mcp"
    },
    "figma-console": {
      "command": "npx",
      "args": ["-y", "figma-console-mcp@latest"],
      "env": {
        "FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}",
        "ENABLE_MCP_APPS": "true",
        "FIGMA_WS_HOST": "0.0.0.0"
      }
    }
  }
}
```

Key env vars:

| Variable | Value | Why |
|---|---|---|
| `FIGMA_ACCESS_TOKEN` | `${FIGMA_ACCESS_TOKEN}` | `.env`에서 주입 |
| `ENABLE_MCP_APPS` | `true` | Token Browser 등 앱 기능 활성화 |
| `FIGMA_WS_HOST` | `0.0.0.0` | Linux에서 `localhost`는 IPv6 `::1`에만 바인딩됨. IPv4로 오버라이드 필요 |

### 4. Bridge Plugin installation

Bridge Plugin은 Figma Desktop에서 실행되어 MCP WebSocket 서버와 연결하는 역할을 한다.

1. **호스트(macOS) 터미널**에서 manifest 생성:
   ```bash
   npx figma-console-mcp@latest
   ```
   `~/.figma-console-mcp/plugin/manifest.json` 자동 생성 후 Ctrl+C.

2. Figma Desktop > **Plugins** > **Development** > **Import plugin from manifest**
3. `~/.figma-console-mcp/plugin/manifest.json` 선택
4. Plugin 실행 시 "MCP ready" 표시 확인

### 5. Connection test

1. Claude Code에서 `/mcp` 로 figma-console 연결
2. Figma Desktop에서 Bridge Plugin 실행
3. `figma_get_status` 호출하여 확인:

```json
{
  "transport": {
    "active": "websocket",
    "websocket": {
      "available": true,
      "port": "9223"
    }
  },
  "setup": {
    "valid": true,
    "message": "✅ Connected to Figma Desktop via WebSocket Bridge"
  }
}
```

## Troubleshooting

### Orphan processes (port occupied)

npx의 `npm → sh → node` 프로세스 체인에서 `/mcp` reconnect 시 node가 고아(ppid=1)로 남아 포트를 점유한다.

```bash
# 고아 프로세스 확인
ps aux | grep figma-console | grep -v grep

# 정리
kill <PID>
```

정리 후 `/mcp`로 재연결하면 선호 포트(9223)를 다시 잡는다.

참고: [southleft/figma-console-mcp#40](https://github.com/southleft/figma-console-mcp/issues/40)

### Port fallback (9224+)

서버가 9224 이상의 폴백 포트에서 실행 중이면 이전 세션의 고아 프로세스가 9223을 점유하고 있을 가능성이 높다. 위의 고아 프로세스 정리 절차를 따른다.

Plugin이 9223만 스캔하는 구버전이면 연결 실패할 수 있다. 이 경우 manifest를 재생성하고 Plugin을 re-import한다.

### WebSocket unreachable from macOS

macOS 터미널에서 확인:

```bash
curl http://localhost:9223
```

응답이 없으면:
1. Docker Desktop "Enable host networking" 설정 확인
2. 컨테이너 내부에서 `FIGMA_WS_HOST=0.0.0.0` 설정 확인
3. Docker Desktop restart

### Plugin shows "MCP ready" but not connected

- Plugin 캐시 문제일 수 있다. Plugin을 닫고 다시 실행.
- 참고: [southleft/figma-console-mcp#26](https://github.com/southleft/figma-console-mcp/issues/26)

## Key capabilities

### Design tokens and variables

`figma_setup_design_tokens`으로 collection + modes + variables를 한 번에 생성:

```
figma_setup_design_tokens({
  collectionName: "Theme",
  modes: ["Light"],
  tokens: [
    { name: "color/primary", resolvedType: "COLOR", values: { "Light": "#8a6fe0" } },
    ...
  ]
})
```

### Typography styles

`figma_execute`로 Figma Plugin API를 직접 호출하여 Text Styles 생성:

```javascript
await figma.loadFontAsync({ family: 'Gothic A1', style: 'Bold' });
const ts = figma.createTextStyle();
ts.name = 'Heading/H1';
ts.fontName = { family: 'Gothic A1', style: 'Bold' };
ts.fontSize = 30;
ts.lineHeight = { value: 39, unit: 'PIXELS' };
```

### Node operations

| Tool | Purpose |
|---|---|
| `figma_create_child` | Create frame, rectangle, text, etc. |
| `figma_set_fills` | Set fill colors |
| `figma_set_text` | Set text content |
| `figma_resize_node` | Resize nodes |
| `figma_move_node` | Move nodes |
| `figma_delete_node` | Delete nodes |
| `figma_clone_node` | Clone nodes |
| `figma_execute` | Arbitrary Figma Plugin API calls |

### Screenshots

`figma_take_screenshot` or `figma_capture_screenshot` for visual validation after modifications.
