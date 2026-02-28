# tmux OSC 52 드래그 복사 설정 문제

## Metadata
- **Date**: 2026-02-28
- **Related Issue**: #1

## Problem

Host tmux → Docker tmux 이중 환경에서 마우스 드래그 시 시스템 클립보드로 복사가 동작하지 않음. 클립보드 체인: inner tmux → OSC 52 → outer tmux → OSC 52 재전송 → 터미널 에뮬레이터 → 시스템 클립보드.

## Research

### OSC 52 클립보드 체인

```
[Docker tmux] MouseDrag → copy-pipe-and-cancel → tmux buffer → OSC 52
    → [Host tmux] set-clipboard on → OSC 52 재전송
    → [터미널 에뮬레이터] OSC 52 수신 → 시스템 클립보드
```

주의: OSC 52는 **터미널 에뮬레이터** 기능이며 셸(zsh/bash)과 무관함.

### 발견된 문제 3가지

**1. `set-clipboard` 옵션 scope 오류**

tmux 3.2+에서 `set-clipboard`은 server option으로 변경됨. `set -g` (global session)로는 적용되지 않을 수 있음.

```bash
# 잘못된 설정
set -g set-clipboard on

# 올바른 설정
set -s set-clipboard on
```

**2. `Ms` 캡빌리티 포맷 오류**

`%p1%s` (clipboard target 파라미터)를 생략하고 `c`를 하드코딩. terminfo 포맷 문자열에서 `%p1`을 사용하지 않으면 파라미터 스택 처리가 비정상일 수 있음.

```bash
# 잘못된 포맷 — clipboard target 'c' 하드코딩, %p1 누락
set -ga terminal-overrides ",*:Ms=\\E]52;c;%p2%s\\7"

# 올바른 포맷 — %p1%s로 clipboard target 동적 전달
set -ga terminal-overrides ",*:Ms=\\E]52;%p1%s;%p2%s\\7"
```

**3. `mode-keys` 미설정**

`mode-keys` 미설정 시 기본값 `emacs`가 적용되어 `copy-mode` 테이블만 활성. `copy-mode-vi` 바인딩이 사용되려면 명시적으로 `set -g mode-keys vi` 필요.

## Decision

세 가지 모두 수정. `host.tmux.conf`와 `docker.tmux.conf` 양쪽 동일하게 적용:

1. `set -g set-clipboard on` → `set -s set-clipboard on`
2. `Ms=\\E]52;c;%p2%s\\7` → `Ms=\\E]52;%p1%s;%p2%s\\7`
3. `set -g mode-keys vi` 추가

## Implementation Guide

적용 후 반영: `tmux source-file ~/.tmux.conf` 또는 tmux 세션 재시작.

터미널 에뮬레이터별 OSC 52 지원 확인 필수:

| 터미널 | OSC 52 | 비고 |
|--------|--------|------|
| iTerm2 | O | Prefs → General → Selection → clipboard 접근 허용 필요 |
| Alacritty | O | 기본 활성화 |
| WezTerm | O | 기본 활성화 |
| kitty | O | 기본 활성화 |
| VS Code Terminal | O | 기본 활성화 |
| macOS Terminal.app | X | 미지원 |

## References

- tmux man page: `set-clipboard`, `terminal-overrides`, `Ms` capability
- tmux 3.2 changelog: `set-clipboard` server option 변경
