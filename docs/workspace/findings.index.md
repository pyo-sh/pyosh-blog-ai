# Workspace Findings Index

> 루트 레포 및 워크스페이스 환경 (Docker, tmux, skills, 워크플로) 관련 기술 조사, 문제 해결, 인사이트 모음

## 목차

| ID  | 제목                                                      | 날짜       | 태그                                        |
| --- | --------------------------------------------------------- | ---------- | ------------------------------------------- |
| 001 | tmux 기반 멀티 AI 에이전트 협업 환경                      | 2026-02-25 | #tmux #multi-agent #claude-code #ipc        |
| 002 | Docker 단일 파일 bind mount 깨짐 & Claude Code 세션 캐싱 | 2026-02-28 | #docker #bind-mount #claude-code #cache     |
| 003 | tmux Pane 수명 관리와 Pipeline 안정성                     | 2026-02-28 | #tmux #pane #pipeline #health-check         |
| 004 | Claude Code vs Codex CLI Hook 비교                        | 2026-02-28 | #claude-code #codex #hooks #comparison      |

## 상세 문서

- [findings.001-tmux-multi-agent.md](./findings/findings.001-tmux-multi-agent.md) - tmux 멀티 에이전트 협업 패턴
- [findings.002-docker-bind-mount-and-session-cache.md](./findings/findings.002-docker-bind-mount-and-session-cache.md) - Docker bind mount inode 문제 & Claude Code 캐싱 한계
- [findings.003-tmux-pane-lifecycle.md](./findings/findings.003-tmux-pane-lifecycle.md) - tmux Pane 수명 관리, health check 패턴, return code 규약
- [findings.004-claude-code-vs-codex-hooks.md](./findings/findings.004-claude-code-vs-codex-hooks.md) - Claude Code vs Codex CLI Hook 아키텍처 비교

## 주요 원칙

- **Docker 단일 파일 bind mount 금지** → 디렉토리 마운트 + 심링크 패턴 사용
- **Claude Code 설정 변경 = 프로세스 재시작 필수** → `/clear`로는 불충분
- **Pane health check 순서: API 먼저 → health 나중** → 정상 종료 후 결과 누락 방지
- **Claude Code Hook = 양방향 Gate** → Codex CLI는 단방향 Notify만 지원
