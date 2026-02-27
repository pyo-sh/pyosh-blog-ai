# tmux 기반 멀티 AI 에이전트 협업 환경

## 개요

tmux는 터미널 멀티플렉서로, 여러 Claude Code 인스턴스를 독립 pane/session에서 실행하고 프로그래밍 방식으로 제어할 수 있다. 이 문서는 tmux가 AI 에이전트 협업을 위해 제공하는 기능을 정리한다.

---

## 1. 에이전트 격리 및 생성

### 세션 기반 격리

각 에이전트를 독립 tmux 세션으로 실행하여 완전히 격리한다.

```bash
# 에이전트 전용 세션 생성 (detached, 특정 worktree에서 시작)
tmux new-session -d -s "agent-auth" -c "/path/to/worktree" -x 220 -y 50

# 세션 존재 여부 확인 (멱등성)
tmux has-session -t "agent-auth" 2>/dev/null

# 세션 내에서 claude 실행
tmux send-keys -t "agent-auth" "claude" Enter

# 세션 종료
tmux kill-session -t "agent-auth"
```

### Pane 기반 레이아웃

한 윈도우 안에서 여러 에이전트를 시각적으로 배치한다.

```bash
# 수평 분할 (나란히)
tmux split-window -h -t "team" -c "/path/to/worktree"

# 수직 분할 (위아래)
tmux split-window -v -t "team"

# 균등 배치
tmux select-layout -t "team" even-horizontal
```

### 타겟팅 문법

```
session-name              # 세션
session-name:window       # 윈도우 (인덱스 또는 이름)
session-name:window.pane  # 특정 pane
```

---

## 2. 에이전트 간 통신 (IPC)

### 2-1. send-keys — 메시지 전송

한 에이전트가 다른 에이전트의 stdin에 텍스트를 보낸다.

```bash
# coordinator에게 완료 알림
tmux send-keys -t "coordinator" "Agent auth-impl completed task #42" Enter

# JSON 메시지 전송 (-l: 리터럴 모드, 키 이름 해석 안 함)
tmux send-keys -l -t "coordinator" '{"status":"done","task":42}'
```

**용도**: 에이전트 완료 알림, 작업 지시, 상태 보고

### 2-2. capture-pane — 다른 에이전트 출력 읽기

다른 pane의 터미널 출력을 프로그래밍 방식으로 읽는다.

```bash
# stdout으로 캡처
tmux capture-pane -p -t "worker-session"

# 마지막 50줄만
tmux capture-pane -p -S -50 -t "worker-session"

# 이스케이프 시퀀스 포함 (색상 정보)
tmux capture-pane -p -e -t "worker-session"
```

**용도**: 에이전트 상태 폴링, 출력 모니터링, 완료 마커 감지

### 2-3. pipe-pane — 실시간 출력 스트리밍

pane 출력을 파일이나 프로세스로 연속 전달한다.

```bash
# worker 출력을 로그 파일로 스트리밍
tmux pipe-pane -t "worker" "cat >> /tmp/agent-worker.log"

# STATUS: 패턴만 필터링
tmux pipe-pane -t "worker" "grep --line-buffered 'STATUS:' >> /tmp/status.log"

# 스트리밍 중지
tmux pipe-pane -t "worker"
```

**용도**: 실시간 모니터링, 로그 수집, 이벤트 감지 (폴링 없이)

### 2-4. Named Buffers — 공유 메모리

tmux 버퍼를 키-값 저장소처럼 사용한다.

```bash
# 상태 쓰기
tmux set-buffer -b "shared-state" "task=done,pr=142,agent=auth-impl"

# 상태 읽기 (어떤 세션에서든)
tmux show-buffer -b "shared-state"

# 파일을 버퍼로 로드
tmux load-buffer -b "task-queue" /tmp/pending-tasks.json

# 버퍼를 pane에 붙여넣기 (입력 주입)
tmux paste-buffer -b "task-queue" -t "worker-session"

# 전체 버퍼 목록
tmux list-buffers
```

**용도**: 경량 공유 상태, 작업 큐, 파일시스템 I/O 없는 데이터 교환

### 2-5. wait-for — 동기화 배리어

채널 기반 블로킹 동기화를 제공한다.

```bash
# 대기 (블로킹)
tmux wait-for "task-3-complete"

# 시그널 (대기 중인 모든 프로세스 깨움)
tmux wait-for -S "task-3-complete"

# 뮤텍스 잠금/해제 (임계 영역)
tmux wait-for -L "git-lock"     # 잠금 획득
# ... 임계 작업 ...
tmux wait-for -U "git-lock"     # 잠금 해제
```

**용도**: 의존성 동기화, 경쟁 조건 방지, 순차 실행 보장

---

## 3. 프로세스 관찰

### 에이전트 탐색 (macOS)

```bash
# 모든 pane의 PID와 위치 확인
tmux list-panes -s -F '#{window_index}:#{window_name} | pane=#{pane_index} | pid=#{pane_pid} | active=#{pane_active}'

# pane PID의 자식 프로세스에서 claude/codex 찾기 (macOS)
ps -o pid,ppid,command -g $PANE_PID | grep -E '(claude|codex)'

# 에이전트의 작업 디렉토리 확인 (macOS)
lsof -p $AGENT_PID -Fn | grep '^n/' | grep cwd

# pane 내 현재 명령어 (tmux 포맷)
tmux display-message -p -t "session:0.0" "#{pane_current_command}"
tmux display-message -p -t "session:0.0" "#{pane_pid}"
```

### 폴링 패턴 — 완료 마커 감지

```bash
while true; do
  output=$(tmux capture-pane -p -t "worker-agent")
  if echo "$output" | grep -q "TASK_COMPLETE"; then
    break
  fi
  sleep 2
done
```

### Activity/Silence 모니터링

```bash
# 에이전트 활동 감지
tmux set-window-option -t "worker-window" monitor-activity on

# 에이전트 정지 감지 (30초 무응답)
tmux set-window-option -t "worker-window" monitor-silence 30
```

---

## 4. 환경 변수

### tmux 관리 환경변수

```bash
# 세션별 변수 설정 (새 pane에서 상속)
tmux set-environment -t "agent-session" TASK_ID "42"
tmux set-environment -t "agent-session" COORDINATOR_SESSION "team-leader"

# 글로벌 변수 (모든 세션)
tmux set-environment -g SWARM_ID "swarm-2025-02-25"

# 변수 읽기
tmux show-environment -t "agent-session" TASK_ID
```

### 자동 설정 변수

| 변수 | 설명 |
|------|------|
| `$TMUX_PANE` | 현재 pane ID (예: `%3`), 모든 pane에 자동 설정 |
| `$TMUX` | 소켓 경로 + 세션 정보, tmux 내부에서만 설정 |

---

## 5. tmux Hooks — 이벤트 기반 자동화

tmux의 수명주기 이벤트에 셸 명령을 바인딩한다.

| Hook | 트리거 | 에이전트 협업 용도 |
|------|--------|-------------------|
| `pane-exited` | pane 프로세스 종료 | 에이전트 완료/크래시 감지 |
| `pane-died` | `remain-on-exit` 상태에서 종료 | 크래시 후 출력 검사 |
| `alert-activity` | pane에 출력 발생 | 에이전트 작업 시작 감지 |
| `alert-silence` | N초간 출력 없음 | 에이전트 정지/유휴 감지 |
| `session-created` | 새 세션 생성 | 신규 에이전트 자동 구성 |
| `session-closed` | 세션 종료 | worktree/리소스 정리 |
| `window-renamed` | 윈도우 이름 변경 | 에이전트 상태 시그널링 |

```bash
# 에이전트 세션 종료 시 로그 기록
tmux set-hook -g session-closed \
  "run-shell 'echo #{session_name} >> /tmp/completed-agents.log'"

# 에이전트 60초 유휴 감지 → coordinator에 알림
tmux set-window-option -t "worker:0" monitor-silence 60
tmux set-hook -g alert-silence \
  "run-shell 'tmux send-keys -t coordinator AGENT_IDLE Enter'"
```

---

## 6. Claude Code의 tmux 지원

### Agent Teams (실험적)

Claude Code는 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`로 팀 기능을 활성화하면 **내부적으로 tmux를 사용**하여 teammate 세션을 관리한다.

```bash
# 팀 모드 활성화
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# teammate 표시 방식 선택
claude --teammate-mode tmux        # tmux 분할 pane 사용
claude --teammate-mode in-process  # 단일 터미널 내 전환
claude --teammate-mode auto        # tmux 안이면 tmux, 아니면 in-process
```

### Claude Code Hooks + tmux 패턴

Claude Code의 수명주기 Hook에서 tmux 명령을 호출하여 에이전트 간 통신을 구현한다.

```bash
# Stop hook 예시: 에이전트 완료 시 coordinator에 알림
# .claude/settings.json
{
  "hooks": {
    "Stop": [{
      "command": "tmux send-keys -t coordinator 'AGENT_DONE: auth-impl' Enter"
    }]
  }
}
```

관련 Hook:
- `Stop` / `SubagentStop` — 에이전트 종료 시
- `WorktreeCreate` / `WorktreeRemove` — worktree 수명주기

### 세션 관리 CLI

```bash
claude --continue              # 최근 세션 이어서
claude --resume <name-or-id>   # 특정 세션 재개
claude --session-id "uuid"     # 세션 ID 지정
```

---

## 7. 협업 패턴 요약

| 패턴 | tmux 프리미티브 | 설명 |
|------|----------------|------|
| **Coordinator → Worker 지시** | `send-keys -t worker` | 작업 할당 |
| **Worker → Coordinator 보고** | `send-keys -t coordinator` (Stop hook) | 완료 보고 |
| **출력 읽기 (폴링)** | `capture-pane -p -t worker` | 상태 확인 |
| **출력 읽기 (스트리밍)** | `pipe-pane -t worker "cat >> log"` | 실시간 모니터링 |
| **의존성 대기** | `wait-for "channel"` / `wait-for -S "channel"` | 순서 보장 |
| **뮤텍스 (파일 충돌 방지)** | `wait-for -L "lock"` / `wait-for -U "lock"` | 동시 수정 방지 |
| **공유 상태** | `set-buffer -b` / `show-buffer -b` | 경량 데이터 공유 |
| **유휴 감지** | `monitor-silence` + `alert-silence` hook | 에이전트 정지 감지 |
| **크래시 감지** | `pane-exited` hook | 비정상 종료 처리 |
| **에이전트 격리** | `new-session -d -s name -c /worktree` | 독립 실행 환경 |
| **상태 브로드캐스트** | `rename-window` 또는 Named Buffers | 전체 상태 공유 |

---

## 8. macOS 참고사항

Linux의 `/proc` 기반 명령은 macOS에서 사용할 수 없다.

| Linux | macOS 대체 |
|-------|-----------|
| `pstree -p $PID` | `ps -o pid,ppid,command -g $PID` |
| `readlink /proc/$PID/cwd` | `lsof -p $PID -Fn \| grep cwd` |
| `/proc/$PID/environ` | 직접 읽기 불가, `tmux show-environment` 사용 |

---

## 9. Claude Code에서 직접 자식 에이전트 생성 (검증됨)

Claude Code가 tmux 안에서 실행 중일 때, Bash 도구로 tmux 명령을 호출하여 **새 pane을 만들고 다른 Claude Code를 실행**할 수 있다. 2025-02-25 실제 테스트 완료.

### 전제 조건

- 현재 Claude Code가 **tmux 세션 안에서** 실행 중이어야 함
- `$TMUX_PANE` 환경변수로 자신의 pane ID를 알 수 있음
- Bash 도구에서 `tmux` 명령 실행이 허용되어야 함

### 방식 1: 비대화식 (one-shot)

`claude -p` 로 단일 프롬프트를 실행하고 결과를 파일로 받는다.

```bash
# 새 pane에서 claude 실행, 결과를 파일로 저장
tmux split-window -h -d -t "$TMUX_PANE" \
  'claude -p "analyze this code" --output-format text > /tmp/result.txt 2>&1'

# -h: 수평 분할 (옆에 생성)
# -d: 포커스를 빼앗지 않음 (부모 pane 유지)

# 결과 대기 후 읽기
while [ ! -f /tmp/result.txt ] || ! grep -q "EXIT" /tmp/result.txt; do
  sleep 2
done
cat /tmp/result.txt
```

**장점**: 간단, 결과를 확실히 받을 수 있음
**단점**: 단발성, 대화 불가

### 방식 2: 대화식 (interactive)

새 pane에서 claude를 대화 모드로 실행하고, `send-keys`로 명령을 주입한다.

```bash
# 1. pane 생성 + claude 실행
tmux split-window -h -d -t "$TMUX_PANE"
tmux send-keys -t "{last}" "claude" Enter

# 2. 초기화 대기 후 프롬프트 전송
sleep 5
tmux send-keys -t "{last}" "Review PR #42 and leave comments" Enter

# 3. 출력 관찰
tmux capture-pane -p -t "{last}"
```

**장점**: 연속 대화 가능, 사용자가 화면에서 진행 과정을 볼 수 있음
**단점**: 타이밍 제어가 어려움, 완료 감지 필요

### 방식 3: worktree 격리 + 비대화식

독립 worktree에서 작업하는 자식 에이전트를 생성한다.

```bash
# 1. worktree 생성
git worktree add .claude/worktrees/agent-task-42 -b feat/issue-42-auth

# 2. 해당 worktree에서 claude 실행
tmux split-window -h -d -t "$TMUX_PANE" \
  -c ".claude/worktrees/agent-task-42" \
  'claude -p "Implement auth feature per issue #42" --output-format text > /tmp/task-42.txt 2>&1'
```

### 결과 수집 패턴

```bash
# 폴링으로 완료 대기
RESULT_FILE="/tmp/child-agent-result.txt"
for i in $(seq 1 30); do
  if [ -f "$RESULT_FILE" ] && grep -q "EXIT_CODE" "$RESULT_FILE"; then
    cat "$RESULT_FILE"
    break
  fi
  sleep 2
done

# 또는 wait-for 채널로 동기화
# 자식: ... && tmux wait-for -S "task-42-done"
# 부모: tmux wait-for "task-42-done"
```

### 주의사항

| 항목 | 설명 |
|------|------|
| **API 비용** | 자식 Claude도 동일하게 API 토큰을 소비함 |
| **권한** | Bash 도구에서 `tmux` 명령이 허용되어야 함 |
| **파일 충돌** | 부모-자식이 같은 파일을 수정하면 충돌 → worktree 격리 필수 |
| **컨텍스트 격리** | 자식 Claude는 부모의 대화 컨텍스트를 모름 → 프롬프트에 충분한 정보 포함 필요 |
| **정리** | 자식 pane과 worktree는 작업 완료 후 수동 정리 필요 |
