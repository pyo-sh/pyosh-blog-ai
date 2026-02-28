# Claude Code vs Codex CLI — Hook 기능 비교 분석

## Metadata
- **Date**: 2026-02-28
- **Related Issue**: N/A (기술 조사)

## Problem

AI 코딩 에이전트 CLI 도구들의 Hook 기능 설계가 어떻게 다른지 비교 분석이 필요했다. Claude Code(Anthropic)와 Codex CLI(OpenAI) 두 도구의 Hook 아키텍처를 조사했다.

## Research

### Claude Code — 양방향 제어 Hook 시스템

**설정**: `~/.claude/settings.json` (JSON), 5단계 스코프 (User / Project / Local / Plugin / Managed)

**아키텍처**: 이벤트 기반 완전한 Hook 시스템

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "bash ./validate.sh" }
        ]
      }
    ]
  }
}
```

**14+ 이벤트 지원**:

| 이벤트 | 설명 | 차단 가능 |
|--------|------|----------|
| `SessionStart` | 세션 시작/재개 | No |
| `UserPromptSubmit` | 사용자 프롬프트 제출 | Yes |
| `PreToolUse` | 도구 실행 전 | Yes |
| `PostToolUse` | 도구 실행 후 | No |
| `PostToolUseFailure` | 도구 실행 실패 후 | No |
| `PermissionRequest` | 권한 요청 시 | Yes |
| `Stop` | 응답 완료 시 | Yes |
| `Notification` | 알림 발생 시 | No |
| `SubagentStart/Stop` | 서브에이전트 시작/종료 | No |
| `PreCompact` | 컨텍스트 압축 전 | No |
| `ConfigChange` | 설정 변경 시 | Yes |
| `SessionEnd` | 세션 종료 시 | No |
| `WorktreeCreate/Remove` | 워크트리 생성/삭제 | Yes/No |
| `TaskCompleted` | 태스크 완료 시 | Yes |

**4가지 핸들러 타입**:

| 타입 | 설명 |
|------|------|
| `command` | Shell 커맨드 실행 (stdin JSON, exit code로 제어) |
| `http` | HTTP POST 웹훅 호출 |
| `prompt` | AI 모델(Haiku) 단일 프롬프트로 판단 |
| `agent` | 서브에이전트 스폰, 도구 접근 가능 |

**핵심 기능**:
- **Matcher (정규식)** 으로 세밀한 이벤트 필터링
- **차단(blocking)**: exit code 2로 에이전트 액션 차단
- **컨텍스트 주입**: `additionalContext`로 Claude에 정보 전달
- **권한 제어**: `permissionDecision: allow|deny|ask`
- **피드백**: stderr가 Claude 컨텍스트에 주입됨

**입출력 예시**:
```json
// stdin 입력
{
  "session_id": "abc123",
  "tool_name": "Bash",
  "tool_input": { "command": "rm -rf /" },
  "cwd": "/project"
}
// stdout JSON 출력 (차단)
{ "decision": "block", "reason": "위험한 명령" }
```

### Codex CLI — 단방향 알림 시스템

**설정**: `~/.codex/config.toml` (TOML), 2단계 스코프 (User / Project)

**아키텍처**: 단순 알림 커맨드

```toml
notify = ["python3", "/path/to/notify.py"]
```

**이벤트**: `agent-turn-complete`, `approval-requested` 정도만 공식 지원

**JSON payload** (알림 스크립트에 전달):
```json
{
  "type": "agent-turn-complete",
  "thread-id": "...",
  "last-assistant-message": "...",
  "client": "codex-tui"
}
```

**TUI 알림 필터링**:
```toml
[tui]
notifications = true  # 또는 ["agent-turn-complete", "approval-requested"]
notification_method = "auto"  # auto | osc9 | bel
```

**한계**:
- 에이전트 동작 차단 불가 (단방향 알림 전용)
- 정규식 매칭 없음
- AI 기반 Hook 없음
- 커뮤니티에서 Claude Code 수준의 Hook 시스템 적극 요청 중 (Discussion #2150, 79+ 참여)

## Decision

| 관점 | Claude Code | Codex CLI |
|------|------------|-----------|
| **설계 철학** | 양방향 제어 (Gate) | 단방향 알림 (Notify) |
| **이벤트 수** | 14+ | 2~3 |
| **핸들러 타입** | 4가지 (command, http, prompt, agent) | 1가지 (외부 명령) |
| **차단 기능** | exit code 2 / JSON decision | 없음 |
| **AI 연동** | prompt, agent 핸들러 | 없음 |
| **필터링** | 정규식 matcher | 없음 |
| **설정 스코프** | 5단계 | 2단계 |
| **성숙도** | 완성된 시스템 | 최소 구현 (확장 요청 중) |

Claude Code의 Hook은 에이전트 행동을 **사전 검증·차단·수정**할 수 있는 "Gate" 역할을 하고, Codex CLI의 Hook은 작업 완료 후 **외부 알림**을 보내는 수준에 머물러 있다.

## References
- [Claude Code Hooks 공식 문서](https://code.claude.com/docs/en/hooks.md)
- [Codex Advanced Configuration](https://developers.openai.com/codex/config-advanced/)
- [Codex Configuration Reference](https://developers.openai.com/codex/config-reference/)
- [Codex Hook 기능 요청 Discussion #2150](https://github.com/openai/codex/discussions/2150)
