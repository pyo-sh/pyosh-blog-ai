# Claude Code 공유 설정

pyosh-blog workspace를 위한 공유 Claude Code 설정입니다.
이 디렉터리가 원본이며, bootstrap이 각 repo로 템플릿을 복사합니다.

## 디렉터리 구조

```
tools/claude/
├── bootstrap.sh                  # 동기화 스크립트 (--dry-run / --apply)
├── README.md                     # 영문 가이드
├── README.ko.md                  # 이 파일
└── templates/
    ├── root/                     # workspace root repo
    │   ├── CLAUDE.md
    │   └── .claude/settings.json
    ├── client/                   # Next.js 프론트엔드 repo
    │   ├── CLAUDE.md
    │   └── .claude/
    │       ├── settings.json
    │       └── rules/
    │           ├── frontend-fsd.md
    │           └── tailwind-v4.md
    ├── server/                   # Fastify 백엔드 repo
    │   ├── CLAUDE.md
    │   └── .claude/
    │       ├── settings.json
    │       └── rules/
    │           └── backend-fastify.md
    └── shared/                   # 세 repo 모두에 복사
        └── .claude/
            └── rules/
                ├── bash.md
                ├── docs-context.md
                ├── git-safety.md
                ├── markdown-writing.md
                └── worktree-workflow.md
```

## bootstrap이 하는 일

1. 각 repo의 `CLAUDE.md`와 `.claude/settings.json` 복사
2. `shared/.claude/rules/`를 세 repo 모두에 복사
3. repo별 `.claude/rules/`를 그 위에 덮어쓰기 (client 또는 server 규칙)
4. client/server에 `claudeMdExcludes`가 포함된 `.claude/settings.local.json` 생성 (없을 때만 - 기존 파일은 덮어쓰지 않음)
5. 각 repo의 `.git/info/exclude`에 `settings.local.json`과 `CLAUDE.local.md` 추가
6. 기존 파일은 `.workspace/backups/claude-code/`에 백업

## 빠른 시작

```bash
# 변경 미리보기
bash tools/claude/bootstrap.sh --dry-run

# 변경 적용
bash tools/claude/bootstrap.sh --apply
```

## 적용 후 확인

각 repo에서 Claude Code를 열고 확인합니다:

- `/memory` - 로드된 CLAUDE.md와 규칙
- `/permissions` - allow, ask, deny 목록

## 수정 방법

1. 배포된 사본이 아닌 `tools/claude/templates/`의 템플릿을 수정합니다
2. `bootstrap.sh --apply`로 변경사항을 동기화합니다
3. 이 repo에서 템플릿 변경을 커밋합니다

## 어디에 무엇을 넣는가

| 내용 | 위치 |
|------|------|
| repo 목적, 기술 스택, 워크플로 | `templates/{repo}/CLAUDE.md` |
| 권한, 환경변수 | `templates/{repo}/.claude/settings.json` |
| 공유 팀 규칙 (bash, git, docs) | `templates/shared/.claude/rules/` |
| repo별 코딩 규칙 | `templates/{repo}/.claude/rules/` |
| 개인 선호 | `CLAUDE.local.md` 또는 `.claude/settings.local.json` (여기에 넣지 않음) |

## 참고

- `settings.local.json`은 개인/머신별 파일입니다. bootstrap은 파일이 없을 때만 생성합니다.
- workspace 디렉터리를 옮긴 경우 bootstrap을 다시 실행하여 child repo exclude의 절대 경로를 갱신하세요.
