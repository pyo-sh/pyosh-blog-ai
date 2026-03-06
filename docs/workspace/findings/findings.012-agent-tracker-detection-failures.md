# Findings 012: agent-tracker 동적 pane 감지 실패 원인 분석

> **Date**: 2026-03-06
> **Tags**: #agent-tracker #sidecar #pane-id #cache #staleness
> **Issue**: #47 / PR #50

## 문제

다른 pane에서 Claude Code를 동적으로 시작하면 agent-tracker 대시보드에서 tokens=0, status=idle, activity="" 고정.

## 원인 분석

### 1. AGENT_TYPE_CACHE negative cache return code 불일치 (Critical)

`detect_agent_type`의 캐시 로직에서 negative cache hit 시 `return 0`을 반환:

```bash
# 캐시 hit
if [[ -n "${AGENT_TYPE_CACHE[$root_pid]+x}" ]]; then
  [[ -n "${AGENT_TYPE_CACHE[$root_pid]}" ]] && printf '%s' "${AGENT_TYPE_CACHE[$root_pid]}"
  return 0  # negative cache도 return 0 - 호출자는 성공으로 판단
fi
```

- positive cache: 값 출력 + return 0 (정상)
- negative cache: 출력 없음 + return 0 (버그 - 호출자가 `|| continue` 하지 않아 빈 etype으로 진행)
- 실제 탐색 실패: return 1 (정상)

캐시 무효화도 없어 에이전트 시작 전에 탐색 실패가 캐시되면 영구적으로 감지 불가.

### 2. on-statusline.sh pane ID 불안정 (Medium)

`on-statusline.sh`는 `statusline-wrapper.sh`의 자식으로 실행됨. PPID 체인:

```
Claude Code (PID 100) → statusline-wrapper.sh (PID 200) → on-statusline.sh (PID 300)
```

- `on-status.sh`의 `$PPID` = 100 (Claude Code) - 안정
- `on-statusline.sh`의 `$PPID` = 200 (wrapper) - 불안정 (매 ~300ms 새 wrapper)

결과: non-tmux 환경에서 `pid-200.json`, `pid-201.json` 등 sidecar가 파편화.

**해결**: wrapper가 `AGENT_TRACKER_PANE="${TMUX_PANE:-pid-$PPID}"`를 export, on-statusline.sh가 수신.

### 3. TRANSCRIPT_LAST_MSG 제거 시 성능 회귀

초기 분석에서 "미사용 연산"으로 판단하고 제거했으나, `context-bar.sh:164`에서 소비 중이었음.

제거 시: wrapper가 tokens만 계산 → context-bar.sh가 자체적으로 `tail -n 200 | jq -rs` 실행 → 매 ~300ms마다 transcript 이중 읽기.

**교훈**: env var export 제거 전 반드시 소비처를 grep으로 확인해야 함.

## 수정 사항

| 항목 | 파일 | 수정 |
|------|------|------|
| 캐시 제거 | agent-tracker.sh | `AGENT_TYPE_CACHE` 전체 삭제, 매 사이클 재감지 |
| needs-input 복구 | on-status.sh | PostToolUse에서 needs-input → working 전이 |
| pane ID 안정화 | statusline-wrapper.sh, on-statusline.sh | `AGENT_TRACKER_PANE` env var 전달 |
| staleness 감지 | agent-tracker.sh | `updated_at` 30초 초과 시 idle 전환 |
| 디렉토리 권한 | 3개 파일 | `chmod 700 "$SIDECAR_DIR"` 일관 적용 |
| 변수 누수 | agent-tracker.sh | `make_line`/`token_bar`에 `local i` |
| TRANSCRIPT_LAST_MSG | statusline-wrapper.sh | 제거 취소 - single-pass 유지 |

## 주요 원칙

- **캐시 제거가 캐시 무효화보다 낫다**: 매 사이클 ~50 /proc reads 비용은 무시 가능. 캐시 무효화 로직의 복잡성/버그 위험이 더 큼.
- **다단계 프로세스 체인에서 PPID는 불안정**: wrapper 경유 시 자식의 PPID는 wrapper PID. env var로 안정 식별자 전달.
- **env var 삭제 전 소비처 확인 필수**: `grep -r VAR_NAME` 후 제거.
- **비대칭 flock은 의도적 설계**: 중요한 쓰기(status hook)는 blocking, 주기적 쓰기(statusline)는 non-blocking skip.
