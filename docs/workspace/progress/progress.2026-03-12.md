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

- [x] dev-pipeline Python CLI step subcommand + bug fixes (#150, PR #157)
  - `steps.py`: 9개 step 함수 (`step_build_setup/finalize`, `step_review_dispatch/wait/process`, `step_resolve_setup/finalize`, `step_merge`, `step_log_finalize`) + `StepResult` 데이터클래스(action/data/message)
  - `cli.py`: `step` 서브커맨드 파서(7 step names, `--phase setup/finalize`, `--review-id`, `--tool`), `cmd_step` 핸들러(stdout `action:`/`data:` 라우팅)
  - Bug fix #1: codex `--output-schema` → `--output-last-message` (v0.114.0 호환)
  - Bug fix #2: `step_review_wait`에서 모든 `failed_*` 상태(6종) codex→claude 폴백 (기존: `failed_parse`만)
  - Bug fix #3: `init --issue N`이 초기 상태 파일 생성 (기존: 디렉토리만 생성)
  - 37 new tests (`test_steps.py`), 258 total passing, 0 regressions

- [x] dev-pipeline SKILL.md thin contract 재작성 + 참조 파일 정리 (#151, PR #158)
  - `SKILL.md` 409줄 → 125줄(-69%), bash 코드 블록 26개 → 0개, `step` 서브커맨드 + action 테이블로 대체
  - #152 표준 섹션 구조 적용: Invariants → State machine → Workflow → Constraints → References
  - `suggestion_only` 규칙 우선순위 명확화 ("first matching rule wins"), headless `round_limit` 동작 문서화
  - `references/process-lifecycle.md`: Step subcommands 섹션 추가 (호출 패턴, 출력 계약, two-phase 패턴)
  - `references/recovery.md`: v3 recovery strategy로 간소화 (step 함수 내부 검증 + recovery action 매핑)
  - `references/python-migration-spec.md`: `steps.py`, `test_steps.py`, `test_review_postcondition.py` 패키지 레이아웃 추가
  - `references/pipeline-audit.md` 삭제 (모든 항목 해결 완료)


- [x] dev-log Python CLI + SKILL.md thin contract (#153, PR #159)
  - Self-contained `dev_log` Python CLI package (8 modules: cli, command_runner, context, git_ops, indexing, merge, worktree)
  - SKILL.md 108줄 → 71줄(-34%), 참조 파일 3개 삭제(worktree-merge.md, indexing-strategy.md, examples.md), templates.md 유지
  - AI 컨텍스트 로딩: 537줄 → 211줄(-61% 토큰 감소)
  - 주요 CLI 서브커맨드: detect-context, create-worktree, next-seq, check-progress, commit, push, lock-merge, cleanup
  - lock_merge main branch guard, `Path.is_relative_to` 정확한 경로 포함 검사, `\d{3,}` 시퀀스 >= 1000 지원
  - 22 tests (context 4, indexing 7, merge 6, worktree 2, git_ops 3), 4라운드 리뷰 통과

## Discoveries
- `gh pr edit --body-file` 실패: GitHub Projects Classic deprecation 에러 발생 시 GraphQL `updatePullRequest` mutation으로 우회

## Notes
- 두 이슈(#142, #144)를 동일 branch/PR에서 작업하여 단일 PR #143으로 통합
