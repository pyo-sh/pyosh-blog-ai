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
- [x] Review resolve 2라운드 - dead code 제거(~100줄), schema cross-reference, `import subprocess` module-level, unused import 제거, INFO severity count table 추가
- [x] dev-review 스킬 최적화 - SKILL.md 109줄→42줄(-61%), 구 `review-template.md` 삭제, 토큰 절감 ~72%

## Discoveries
- `gh pr edit --body-file` 실패: GitHub Projects Classic deprecation 에러 발생 시 GraphQL `updatePullRequest` mutation으로 우회

## Notes
- 두 이슈(#142, #144)를 동일 branch/PR에서 작업하여 단일 PR #143으로 통합
