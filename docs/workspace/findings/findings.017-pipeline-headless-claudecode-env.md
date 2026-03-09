# Findings 017 - pipeline_run_headless_core CLAUDECODE 환경변수 전파 버그

- **날짜**: 2026-03-09
- **태그**: #pipeline #headless #claude-p #claudecode #env-var #nested-session
- **관련 이슈**: #78 (dev-pipeline 세션에서 pipeline_run_review 호출 중 발견)

## 현상

`/dev-pipeline` 스킬이 Claude Code 세션 안에서 실행될 때, `pipeline_run_review` 호출이 exit code 1로 실패한다.

```
Error: Claude Code cannot be launched inside another Claude Code session.
Nested sessions share runtime resources and will crash all active sessions.
To bypass this check, unset the CLAUDECODE environment variable.
```

## 원인 분석

### 환경변수 전파 경로

```
Claude Code 세션 (CLAUDECODE=<session-id> 설정됨)
  └─ /dev-pipeline 스킬 실행
       └─ pipeline_run_review()
            └─ pipeline_run_headless_core()
                 └─ timeout 900 claude -p ... (CLAUDECODE 그대로 상속)
                      └─ Claude Code 시작 시 CLAUDECODE 감지 → 즉시 종료 (rc=1)
```

### 코드 위치

`pipeline-helpers.sh` `pipeline_run_headless_core()`:

```bash
(
  cd -- "$skill_cwd" || exit 3
  PIPELINE_MONOREPO_ROOT="$MONOREPO_ROOT" \
  PIPELINE_AREA="$area" \
  ...
  "${cmd[@]}" > "$log" 2> "$err"   # CLAUDECODE 미해제 상태로 claude -p 실행
)
```

CLAUDECODE를 unset 하는 코드가 없다. 부모 Claude Code 세션의 환경변수가 서브쉘로 그대로 상속된다.

### 오케스트레이터와의 차이

`orch-dispatch-wrapper.sh`는 `setsid + bash`로 새 세션을 만들고 orchestrator가 직접 환경변수를 통제하므로 이 문제가 발생하지 않는다 (finding 014 참고). pipeline-helpers.sh는 Claude Code 스킬 세션 안에서 직접 호출되는 구조라 CLAUDECODE가 항상 설정된 상태다.

## 임시 해결책 (workaround)

pipeline_run_review 호출 전 bash 서브쉘에서 unset:

```bash
(unset CLAUDECODE && source .agents/skills/dev-pipeline/scripts/pipeline-helpers.sh && pipeline_run_review "78" "workspace" "118" "claude-sonnet-4-6")
```

또는 Bash tool 호출 앞에 `unset CLAUDECODE &&` 선행:

```bash
unset CLAUDECODE && source ... && pipeline_run_review ...
```

## 근본 해결책

`pipeline_run_headless_core()` 내부 서브쉘에서 CLAUDECODE를 명시적으로 해제:

```bash
(
  cd -- "$skill_cwd" || exit 3
  unset CLAUDECODE          # ← 추가
  PIPELINE_MONOREPO_ROOT="$MONOREPO_ROOT" \
  ...
  "${cmd[@]}" > "$log" 2> "$err"
)
```

이렇게 하면 caller가 CLAUDECODE 해제를 신경 쓸 필요 없이 항상 안전하게 claude -p를 실행할 수 있다.

## 패턴 일반화

Claude Code 세션 안에서 `claude -p`를 직접 호출하는 모든 코드는 반드시 CLAUDECODE를 unset해야 한다:

| 호출 위치 | CLAUDECODE 처리 | 상태 |
|-----------|-----------------|------|
| `orch-dispatch-wrapper.sh` | setsid 새 세션으로 격리, orchestrator가 통제 | 안전 |
| `pipeline_run_headless_core()` | 미처리 (부모 세션 상속) | **버그** |

## 관련 문서

- [findings.014-headless-dispatch-architecture.md](./findings.014-headless-dispatch-architecture.md) - headless dispatch 전반 설계 및 CLAUDECODE= 원칙
