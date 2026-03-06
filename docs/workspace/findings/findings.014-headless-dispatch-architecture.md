# Headless dispatch architecture - tmux pane에서 claude -p 백그라운드 프로세스로

## Metadata
- **Date**: 2026-03-07
- **Related Issue**: #55, #57

## Problem

tmux pane 기반 AI 프로세스 dispatch가 반복적 버그의 근원:
- Pane death 감지 실패 (remain-on-exit 상호작용, pane ID 재사용)
- Orphan pane 증식 (startup crash 시 remain-on-exit pane 미정리)
- Pane release 누락 (interactive mode 잔류, Ctrl+C fallback 불안정)
- Docker 환경에서 tmux 의존성

~230줄의 방어 코드가 pipeline-helpers.sh의 46%를 차지.

## Architecture

### Pipeline (synchronous)

```
pipeline_run_headless(workdir, prompt, issue, area, stage)
  -> timeout $SEC claude -p ... "$prompt" > $LOG 2>$ERR
  -> blocks until exit
  -> returns exit code: 0=success, 124=timeout, other=error
  -> ALWAYS check API after exit (result may exist even on non-zero)
```

- Review/resolve를 동기 서브프로세스로 실행
- Poll loop 불필요 - blocking 후 API 확인만

### Orchestrator (asynchronous)

```
orch_dispatch(issue, area_dir, agent)
  -> CLAUDECODE= timeout 3600 claude -p ... "$prompt" > $LOG 2>$ERR &
  -> pid=$!
  -> sleep 1 + kill -0 $pid (early crash detection)
  -> returns PID
```

- 각 Issue별 백그라운드 프로세스 실행
- PID 기반 lifecycle 관리 (`kill -0`)
- 30초 폴링으로 완료/실패/정체 감지

### Nested headless

```
User Session
  └── Orchestrator (interactive claude)
        ├── claude -p & (pipeline #1, PID 12345)
        │     ├── claude -p (review, synchronous)
        │     └── claude -p (resolve, synchronous)
        ├── claude -p & (pipeline #2, PID 12346)
        └── claude -p & (pipeline #5, PID 12347)
```

오케스트레이터 → 파이프라인은 background, 파이프라인 → review/resolve는 synchronous.

## Key findings

1. **`CLAUDECODE=` env unset 필수** - 부모 claude 프로세스의 환경변수가 자식에게 상속되면 충돌 발생
2. **`--no-session-persistence`** - 헤드리스 프로세스의 세션 파일 생성 방지
3. **`$$` vs `$BASHPID`** - 서브셸/백그라운드에서 `$$`는 top-level shell PID. `$BASHPID`가 현재 프로세스 PID
4. **`--max-turns` 설정 필수** - 무한 루프 방지 (pipeline: 80, review: 15, resolve: 25)
5. **Merge queue** - 병렬 파이프라인 동시 merge 시 rebase 충돌. `mkdir` atomic lock으로 직렬화
6. **pipelineStarted flag** - state file 부재가 "아직 미생성"인지 "완료 후 삭제"인지 구분하기 위해 최초 관찰 시점 기록

## References

- findings.011 - pane orphan 증식 (이번 전환으로 해결)
- findings.013 - pane release 누락 (이번 전환으로 해결)
