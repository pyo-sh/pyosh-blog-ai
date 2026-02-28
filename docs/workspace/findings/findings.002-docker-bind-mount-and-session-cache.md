# Findings 002: Docker 단일 파일 bind mount 깨짐 & Claude Code 세션 캐싱

**날짜**: 2026-02-28
**태그**: #docker #bind-mount #inode #claude-code #cache #session

## 요약

Host tmux → Docker(Ubuntu) → tmux 이중 환경에서 설정 파일 수정 시 두 가지 독립적인 문제가 발생:
1. **Docker 단일 파일 bind mount**: 에디터의 파일 교체로 inode가 변경되면 마운트가 깨짐
2. **Claude Code 세션 캐싱**: CLAUDE.md, Skills, Hooks 등이 세션 시작 시 1회만 로드되어 런타임 변경 미반영

## 문제 1: Docker 단일 파일 bind mount 깨짐

### 증상

```bash
# Host에서 docker.tmux.conf 수정 후 Docker 내부에서 확인
dev@docker-desktop:/workspace$ ls -al /home/dev/.tmux.conf
ls: cannot access '/home/dev/.tmux.conf': No such file or directory
-????????? ? ?    ?       ?            ? .tmux.conf
```

`tmux source-file /home/dev/.tmux.conf` 실행 시 파일을 찾지 못함.

### 원인

대부분의 에디터(vim, VSCode, IntelliJ 등)는 파일을 **in-place 수정하지 않고**:

1. 임시 파일에 새 내용 작성
2. 원본 파일 삭제
3. 임시 파일을 원본 이름으로 rename

이 과정에서 **inode가 변경**됨. Docker의 단일 파일 bind mount는 파일 경로가 아닌 **원본 inode**에 바인딩되므로, 에디터가 파일을 교체하면 컨테이너 안의 마운트가 깨짐.

### 해결

단일 파일 bind mount 대신 **디렉토리 마운트를 경유하는 심링크**로 변경.

**docker-compose.yaml** — 단일 파일 마운트 제거:
```yaml
volumes:
  - ../../:/workspace
  - dev-auth:/home/dev/.auth
  # 단일 파일 bind mount는 에디터가 inode를 교체하면 깨지므로 사용하지 않음
```

**entrypoint.sh** — /workspace 디렉토리 마운트 경유 심링크:
```bash
ln -sfn /workspace/tools/tmux/docker.tmux.conf /home/dev/.tmux.conf
ln -sfn /workspace/tools/docker/.bash_aliases /home/dev/.bash_aliases
```

디렉토리 마운트(`../../:/workspace`)는 inode 변경에 영향받지 않으므로 항상 최신 파일을 참조.

### 원칙

> Docker에서 단일 파일 bind mount는 사용하지 않는다. 디렉토리 마운트 + 심링크 패턴을 사용한다.

---

## 문제 2: Claude Code 세션 캐싱

### 캐싱 범위

Claude Code는 다음 항목들을 **세션 시작 시 1회** 로드하고 캐싱:

| 항목 | 캐싱 여부 | 런타임 변경 반영 |
|------|----------|----------------|
| CLAUDE.md | 세션 시작 시 로드 | X — 재시작 필요 |
| Skills (SKILL.md) | 세션 시작 시 스캔 | X — 재시작 필요 |
| Custom commands (.claude/commands/) | 세션 시작 시 로드 | X — 재시작 필요 |
| Hooks (.claude/settings.json) | 세션 시작 시 로드 | X — 재시작 필요 |
| Plugins (.claude/plugins/) | 세션 시작 시 캐시 검사 | X — 재시작 필요 |

### `/clear` vs 재시작

| 동작 | `/clear` | 프로세스 재시작 (exit → 재실행) |
|------|----------|------|
| 대화 히스토리 초기화 | O | O |
| CLAUDE.md 재로드 | **X** | O |
| Skills 재스캔 | **X** | O |
| Custom commands 재로드 | **X** | O |
| Hooks 재로드 | **X** | O |
| 내부 캐시 초기화 | **X** | O |

**`/clear`는 대화만 초기화할 뿐, 파일 캐시를 무효화하지 않는다.**

### 관련 GitHub Issues

- [#2538](https://github.com/anthropics/claude-code/issues/2538) — `/clear` 후에도 삭제된 파일 참조, 이전 git 브랜치 기억 (closed, not planned)
- [#20507](https://github.com/anthropics/claude-code/issues/20507) — `/reload-skills` 명령어 요청 (closed, duplicate of #18193)
- [#15803](https://github.com/anthropics/claude-code/issues/15803) — `.claude/commands/*.md` 변경 감지 요청
- [#22679](https://github.com/anthropics/claude-code/issues/22679) — Hook 설정 캐싱, 변경 미반영
- [#17361](https://github.com/anthropics/claude-code/issues/17361) — Plugin 캐시 미갱신
- [#21925](https://github.com/anthropics/claude-code/issues/21925) — Context compaction 시 CLAUDE.md 재로드 안 됨

### 해결: Claude Code 프로세스 재시작

유일하게 확실한 방법은 **Claude Code 프로세스 자체를 재시작**하는 것.

tmux 전체 pane에 일괄 재시작하는 함수 (.bash_aliases에 추가 가능):

```bash
dev-skill-refresh() {
  local session="${1:-lab}"
  local cmd="${2:-cc}"
  local count=0
  for pane in $(tmux list-panes -s -t "$session" -F '#{pane_id}'); do
    tmux send-keys -t "$pane" C-c
    tmux send-keys -t "$pane" "$cmd" Enter
    ((count++))
  done
  echo "=== Restarted $cmd in $count panes (session: $session) ==="
}
```

**주의**: 진행 중인 대화 컨텍스트가 모두 소실됨. 작업 중인 에이전트가 없을 때만 사용.

---

## 교훈

1. **Docker 단일 파일 bind mount는 신뢰할 수 없다** — 에디터의 파일 교체 패턴과 충돌
2. **Claude Code의 `/clear`는 파일 재로드가 아니다** — 대화 초기화만 수행
3. **설정 변경 = 프로세스 재시작** — 현재 Claude Code에서 hot-reload 미지원 (관련 Feature Request 다수 존재)
4. **디렉토리 마운트 + 심링크 패턴**이 Docker 환경에서 가장 안정적

## 참고 자료

- [ClaudeLog - Restarting Claude Code](https://claudelog.com/faqs/restarting-claude-code/)
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Building a /reload Command for Claude Code](https://www.panozzaj.com/blog/2026/02/07/building-a-reload-command-for-claude-code/)
