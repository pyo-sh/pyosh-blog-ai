# Workspace Progress - 2026-03-04

## Skill 간 중복된 monorepo 로직을 공유 reference + helper로 추출 (#40)

**Issue**: #40
**Branch**: `refactor/issue-40-monorepo-helpers`

### 배경

Root detection 로직이 3가지 방식으로 구현됨 (스크립트 상대경로, `git rev-parse` + 형제 디렉토리 확인, `.agents/` 탐색). area 매핑, workspace 특수 처리가 거의 모든 dev-* skill에 중복.

### 변경 사항

**신규 파일**:
- `.agents/references/monorepo-layout.md` - area 정의, 디렉토리/repo 매핑, worktree 경로 규칙, verify 명령 등 단일 참조 문서
- `.agents/scripts/monorepo-helpers.sh` - `MONOREPO_ROOT` 감지, `monorepo_area_dir()`, `monorepo_area_repo()`, `monorepo_area_from_dir()` 공유 함수

**수정 파일**:
- `pipeline-helpers.sh` - 자체 root detection 제거, monorepo-helpers.sh source
- `orchestrate-helpers.sh` - 자체 root detection 제거, monorepo-helpers.sh source, `monorepo_area_from_dir()` 사용
- `worktree-merge.md` - 자체 root detection 코드 제거, monorepo-helpers.sh 참조
- `dev-build`, `dev-pipeline`, `dev-resolve`, `brainstorming`, `handoff` SKILL.md - monorepo-layout.md 참조 링크 추가

## agent-tracker 토큰 표시 수정 + transcript 읽기 최적화 (#42, PR #43)

**Issue**: #42
**Branch**: `fix/agent-tracker-tokens`

### 문제

agent-tracker 대시보드의 토큰 Nk 값이 Claude Code status bar와 크게 다름 (0k 또는 2k만 표시). 원인은 `on-statusline.sh`가 `context_window.total_input_tokens`를 사용했는데, 이 값이 시스템 프롬프트/도구 정의/메모리를 제외한 불완전한 값이었음. `context-bar.sh`는 이미 transcript JSONL에서 직접 계산하는 방식으로 해결되어 있었음 (claude-code#13652).

### 변경 사항

1. **토큰 소스 변경**: `total_input_tokens` 대신 transcript JSONL의 `usage` 필드에서 계산
2. **이중 읽기 최적화**: `statusline-wrapper.sh`에서 `tail -n 200 | jq -rs` 단일 패스로 토큰 + last_user_msg를 추출, `TRANSCRIPT_TOKENS`/`TRANSCRIPT_LAST_MSG` env var로 하위 스크립트에 전달
3. **context-bar.sh 통합**: 중복된 bar 렌더링 코드를 단일 경로로 통합, env var 우선 사용 + fallback 유지

### 수정 파일

- `tools/agent-tracker/statusline-wrapper.sh` - transcript 1회 읽기 + env var export
- `tools/agent-tracker/hooks/on-statusline.sh` - env var 사용, transcript 직접 읽기 제거
- `scripts/context-bar.sh` - env var 우선 사용, fallback에 tail -n 200 적용, bar 코드 통합
