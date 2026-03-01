# Progress: 2026-03-02

## dev-pipeline merge 단계 버그 수정 및 스킬 개선 — PR #24

### 작업 내용

**분석 및 이슈 등록**
- dev-pipeline merge 단계(Step 6) 버그 12개 분석 (핸드오프 이어받기)
- Critical 5개, Major 4개, Design 3개 분류
- GitHub Issues #21, #22, #23 등록 (3개 그룹으로 묶음)

**수정 사항 (fix/pipeline-merge-robustness, PR #24)**

merge 안정성 (#21):
- `gh pr merge` 종료 코드 체크 — 실패 시 cleanup 중단
- `gh pr view --json state` 로 MERGED 상태 검증
- pane kill을 merge **전으로** 이동 (실패 시 orphaned pane 방지)
- `git fetch --prune` + `git worktree remove --force` + `git worktree prune`

cleanup 정확성 (#22):
- `git branch -D {branch}` 추가 — worktree 제거 후 실행 (squash merge 후 `-D` 필요)

state 파일 namespace 충돌 (#23):
- `pipeline_state_path(issue, area)` — `.workspace/pipeline/{area}/issue-{N}.state.json`
- 모든 호출처 업데이트: `pipeline_init`, `pipeline_state_exists/read/delete`, `pipeline_cleanup`, `pipeline_list`
- `orch_check_completion` 네임스페이스된 경로 사용, 중복 collision guard 제거

**Check plan + DoD 체크 개편**
- PR "Test plan" → "Check plan" 명칭 변경
- PR body에서 체크박스 제거 — 평문 리스트로 변경
- dev-build Step 2.5 추가: feat 이슈 처리 시 Issue의 DoD 체크박스 완료 항목 체크
- dev-review: Check plan 항목은 informational context만 확인
- dev-resolve: checkbox update 단계 제거
- dev-pipeline Step 5: 미체크 항목 카운트 제거, Check plan 표시로 교체
- 기존 closed PR/Issue 체크박스 일괄 업데이트 (Issues 8개, PRs 6개)

**skill-creator 최적화**
- dev-review: 90 → 42 lines, `references/review-template.md` 분리
- dev-resolve: 88 → 51 lines, `references/response-template.md` 분리
- dev-pipeline: 189 → 166 lines, `references/pane-lifecycle.md` 분리
- dev-build: 중복 PR body 예시 제거 (pr-template.md 참조)

**Codex 리뷰 대응 (2차, 3차)**

1차 리뷰 (Warning 3개) 수정:
- `dev-orchestrator/SKILL.md`, `recovery.md`, `state-detection.md`, `dependency-resolution.md` 구 경로 → `{area}/issue-{N}` 네임스페이스 적용

2차 리뷰 (Warning 2개) 수정:
- `pipeline_cleanup()`: `git worktree remove --force` + `git worktree prune` + `git branch -D`
- `pipeline_state_write()` 헬퍼 추가
- SKILL.md Step 6: merge 실패 시 `exit 1` 전 `merge-failed` state 저장
- Step 5 Check plan `grep || true` (섹션 없는 구 PR body 안전 처리)

3차 리뷰: CRITICAL 0, WARNING 0, SUGGESTION 3 (런타임 검증 항목만 남음)

### 결과

- PR #24 머지: `fix/pipeline-merge-robustness` → main
- Closes #21, #22, #23
