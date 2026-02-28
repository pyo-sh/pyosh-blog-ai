# tmux Pane 수명 관리와 Pipeline 안정성

## Metadata
- **Date**: 2026-02-28
- **Related Issue**: Pipeline Issue #10

## Problem

dev-pipeline 오케스트레이터가 tmux side pane을 생성한 뒤, 해당 pane이 즉시 소멸해도 감지하지 못하고 GitHub API polling만 계속하는 문제.

근본 원인: `cd '$workdir' && $cmd` 패턴에서 `cd` 실패 시 `&&` 이후 명령이 실행되지 않고 shell이 종료 → tmux pane 자동 소멸.

## Research

### tmux pane 생존 확인

- `tmux list-panes` — 기본값은 **현재 window만** 검색. 다른 window/session의 pane을 찾으려면 `-a` 플래그 필수.
- `grep -q "%1"` — `%10`, `%100`에도 매칭됨. `grep -qx` (exact line match)로 앵커링 필요.

```bash
# 올바른 pane 생존 확인
tmux list-panes -a -F '#{pane_id}' | grep -qx "$pane_id"
```

### tmux window별 pane 독립성

- 각 window는 pane 레이아웃을 독립적으로 관리
- 비활성 window에서 `split-window` 실행해도 해당 window로 전환 시 정상 표시
- "다른 window에 split되어 안 보임" 가설은 **기각** — pane이 보이지 않는 건 pane 자체가 소멸했기 때문

### polling 중 health check 순서

**API 먼저 → health check 나중** 순서가 올바름:
- Review/resolve pane이 작업 완료 후 정상 종료하면 pane은 사라지지만 결과(리뷰/커밋)는 이미 GitHub에 존재
- health check를 먼저 하면 정상 종료를 PANE_DEAD로 오판 (false positive)

## Decision

**Pane Lifecycle Tracking 패턴** 도입:

1. **Startup verification** — pane 열기 → 3초 대기 → `pipeline_pane_alive()` 확인
2. **Path re-resolution** — 실패 시 `pipeline_resolve_worktree_path()`로 현재/레거시 경로 재탐색 후 1회 재시도
3. **Health-monitored polling** — polling 루프마다 API 결과 확인 → 없으면 pane 생존 확인 → 사망 시 최종 API 1회 재확인 후 PANE_DEAD 반환

### Return code 규약

| Code | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 타임아웃 |
| 2 | Pane 사망 (PANE_DEAD) |
| 3 | 경로 무효 (PATH_INVALID) |
| 4 | 재시도 소진 (RETRY_FAILED) |

## References
- [pipeline-helpers.sh](../../.agents/skills/dev-pipeline/scripts/pipeline-helpers.sh)
- [dev-pipeline skill.md](../../.agents/skills/dev-pipeline/skill.md)
