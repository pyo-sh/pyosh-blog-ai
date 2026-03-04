# Findings 009 - Pipeline review/resolve pane workdir

**날짜**: 2026-03-04
**태그**: #pipeline #claude-code #skills #workdir #monorepo

## 문제

`/dev-pipeline`에서 review/resolve pane을 `cd /workspace/client`로 열면 해당 pane의 Claude Code가 skills(`/dev-review`, `/dev-resolve`)를 찾지 못함.

## 원인

`/workspace/client`는 독립 Git repo (`pyo-sh/pyosh-blog-fe`). Claude Code는 project root(= git root)를 기준으로 `.claude/skills/`를 탐색. `/workspace/client`를 project root로 인식하면 `/workspace/.claude/skills/`에 접근하지 못함.

```
/workspace/               ← pyosh-blog-ai git root → .claude/skills/ 존재
└── client/               ← pyosh-blog-fe git root → .claude/skills/ 없음
    └── (no .claude/)
```

## 해결책

review/resolve pane의 workdir를 `/workspace`(모노레포 루트)로 설정.

```bash
# 기존 (잘못됨)
pipeline_open_pane "/workspace/client" "Run /dev-review ..." "claude" "%5"

# 수정 (올바름)
pipeline_open_pane "/workspace" "Run /dev-review ..." "claude" "%5"
```

pane 내부에서 area-specific 명령은 `cd client && ...` 형태로 프롬프트에 명시하거나, skill 자체가 area 인자로 처리.

## 영향 범위

`dev-pipeline` skill의 Step 2 (review pane open) 및 Step 4a (resolve pane open). `pipeline_open_pane_verified` 호출 시 workdir 인자를 `/workspace`로 고정해야 함.
