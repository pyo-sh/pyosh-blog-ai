# Claude Code 가이드

이 저장소는 팀 일관성을 위한 공유 Claude Code 설정을 사용합니다.

## 공유 대상

아래 파일들은 버전 관리되며 팀 정책으로 취급합니다:

- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/rules/*.md`
- `.claude/hooks/*`
- `.claude/README.md`

## 개인 설정

개인 선호와 머신별 오버라이드는 아래에 넣으세요:

- `CLAUDE.local.md`
- `.claude/settings.local.json`
- `~/.claude/CLAUDE.md`
- `~/.claude/settings.json`

공유 `CLAUDE.md`에 개인 설정을 넣지 마세요.

## 왜 나뉘어 있는가

- `CLAUDE.md`는 짧고 안정적으로 유지합니다.
- `.claude/rules/`는 모듈식 규칙을 담고, path-scoped 규칙은 관련 파일을 다룰 때만 로드됩니다.
- `.claude/settings.json`은 권한, 훅, 공유 환경변수, 추가 디렉터리를 담습니다.
- `.claude/settings.local.json`은 로컬 제외 및 개인 오버라이드용입니다.

## 일상 워크플로

1. 변경하려는 저장소에서 Claude Code를 시작합니다.
2. 파일 편집이 필요하면 먼저 worktree를 생성하거나 전환합니다.
3. 아키텍처나 동작을 변경하기 전에 관련 docs index 파일을 읽습니다.
4. 셸 명령은 읽기 쉽게 유지합니다. 여러 단계나 위험한 작업은 짧은 스크립트를 사용합니다.
5. worktree에서 커밋한 뒤, 멈추고 로컬 머지할지 PR을 열지 결정합니다.

## Bash 및 환경변수 정책

- 간단한 일회성 명령에는 인라인 환경변수 1 - 2개까지 허용합니다.
- 환경변수가 3개 이상이거나 quoting이 복잡하면 스크립트를 사용합니다.
- 공유 또는 지속적인 환경변수는 `.claude/settings.json`이나 `CLAUDE_ENV_FILE`에 쓰는 `SessionStart` 훅에 넣습니다.
- bash 명령 안에서 커스텀 JSON 문법을 만들지 마세요.
- 다른 저장소의 `gh`, `pnpm`, 또는 repo-local 스크립트는 `(cd "$repo" && ...)`로 하나의 명령이나 짧은 스크립트 안에서 실행합니다.

## child repo 제외

`client/`나 `server/` 안에서 Claude를 실행하면 상위 workspace 설정도 같이 로드됩니다. bootstrap 스크립트가 child repo에 절대 경로 `claudeMdExcludes`가 포함된 `.claude/settings.local.json`을 생성하여, 각 child repo가 root 규칙을 중복 로드하지 않고 자체 설정만 사용하도록 합니다.

## 공유 설정 업데이트

원본은 workspace root의 `tools/claude/templates/`입니다.

변경 미리보기:

```bash
bash tools/claude/bootstrap.sh --dry-run
```

변경 적용:

```bash
bash tools/claude/bootstrap.sh --apply
```

## 검증

배포 후 각 저장소에서 Claude를 열고 확인합니다:

- `/memory` - 어떤 `CLAUDE.md`와 규칙이 로드되었는지
- `/permissions` - 유효한 allow, ask, deny 규칙
- `/hooks` - 설치된 훅 동작
