# Progress: 2026-03-12

## Completed
- [x] dispatch_codex structured output + env isolation + fail-closed (#142, PR #143)
  - `codex exec --output-schema` / `-o` 전환, `_validate_codex_payload` + `_render_codex_review` 인라인 검증/렌더, `CODEX_HOME` temp dir env 격리, `normalize_codex_output` line-start rfind 수정, `failed_parse` 상태 보존
- [x] Contract-driven review publisher + JSON-first dev-review flow (#144, PR #143)
  - `review_publish.py` CLI: schema 검증 + contamination 검사 + markdown 렌더링 + gh publish
  - `review_schema.json`: canonical review JSON schema (P0-P3/info, suggested_fix)
  - SKILL.md JSON-first flow 전면 개편, `gh pr review` 직접 호출 금지
  - codex 경로: inline render+post 제거 → publisher CLI 위임
  - 36 regression tests
- [x] PR identity metadata + doctor command (#84, PR #145)
  - `orch_branch_name()`: deterministic branch naming `orch/{area}/issue-{N}/{attemptId}`
  - `_orch_pr_list()` 재작성: branch-based (primary) > label-based > body search (fallback)
  - `orch_label_pr()` + `_orch_ensure_labels()`: PR identity labels (`orch`, `area:{area}`, `issue:{N}`, `attempt:{attemptId}`)
  - `orch_doctor()`: state file integrity, status consistency, process health, stale lock, worktree state, PR/issue mismatch
  - `issueMetadata` in batch state: branch/pr/attemptId durable across dispatch cleanup
  - `orch_dispatch()` prompt에 branch name 전달, `orch_poll_cycle()` completion handler에 PR labeling 추가
  - `orch_print_summary()` cached PR from issueMetadata 우선 사용
- [x] Review resolve 2라운드 - dead code 제거(~100줄), schema cross-reference, `import subprocess` module-level, unused import 제거, INFO severity count table 추가
- [x] dev-review 스킬 최적화 - SKILL.md 109줄→42줄(-61%), 구 `review-template.md` 삭제, 토큰 절감 ~72%

- [x] dev-review 자동 게시 + dev-log standalone squash merge 충돌 수정 (#148, PR #149)
  - `dev-review/SKILL.md`: `${REVIEW_MODE:-dry-run}` → `${REVIEW_MODE:-publish}` 기본값 변경
  - `review_publish.py`: `_is_pr_author(repo, pr)` 추가 - gh API로 reviewer=PR작성자 감지 시 verdict를 `comment`로 자동 하강; `argparse` 기본값도 `publish`로 통일
  - `dev-log/SKILL.md`: Phase 0에 worktree 컨텍스트 감지 지시 추가 - 선행 `/dev-build` 컨텍스트에 worktree 경로가 있으면 이동 후 Phase 0 실행 → `IN_ROOT_WORKTREE=true` → Phase 4.5 → squash merge 충돌 방지
  - codex 0.114.0 `--output-schema` 플래그 제거로 codex review 실패 → claude 폴백으로 자동 전환 확인

- [x] dev-review + dev-issue SKILL.md 표준화 (#152, PR #156)
  - 6개 dev-* 스킬의 SKILL.md 섹션 구조 통일 - 첫 2개 스킬(dev-review, dev-issue) 적용
  - 표준 섹션 순서: Invariants → Environment → Workflow → Constraints
  - `dev-review`: `## Prohibited` → `## Invariants`로 이동, `## Steps` → `## Workflow` 이름 변경, `## Verdict rules` → `## Constraints` 하위로 이동
  - `dev-issue`: `## Constraints` 3줄 → `## Invariants`로 승격, Title rules/Labels → `## Constraints` 하위로 이동, 섹션 순서 재배치


## Discoveries
- `gh pr edit --body-file` 실패: GitHub Projects Classic deprecation 에러 발생 시 GraphQL `updatePullRequest` mutation으로 우회

## Notes
- 두 이슈(#142, #144)를 동일 branch/PR에서 작업하여 단일 PR #143으로 통합
