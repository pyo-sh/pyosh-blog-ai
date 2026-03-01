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

---

## dev-pipeline 스킬 버그 수정 — issue #28

### 작업 내용

**분석 단계**
- dev-pipeline 스킬 전체 코드 리뷰: 15개 잠재 버그/위험 항목 발견
- 인터뷰 형식으로 사용자와 해결 방향 결정 (11개 수정, 2개 현행 유지, 2개 무시)
- GitHub Issue #28 등록 (`refactor`, `priority:1`)

**PR #24에서 이미 수정된 항목 확인**
- `git worktree remove --force`, `pipeline_state_write()`, state 경로 네임스페이스 등 선행 수정 확인

**수정 사항 (`refactor/issue-28-dev-pipeline-fixes`)**

helpers.sh (#6):
- `MONOREPO_ROOT` 감지: `git rev-parse --show-toplevel` → `git worktree list --porcelain` 역추적으로 교체
- 워크트리 내부에서 소싱해도 정확한 루트 반환 확인

helpers.sh (#2, 함수 리네임):
- `pipeline_analyze_review()` 제거 — eval 포맷 출력 삭제
- `pipeline_fetch_review()` 추가 — raw JSON(`{state, body}`)만 반환, AI가 직접 파싱

helpers.sh (#8):
- `pipeline_poll_review()`, `pipeline_poll_commits()` 내 `gh api` 호출에서 `2>/dev/null` 제거 - 오류가 stderr로 출력되도록

SKILL.md (#9):
- Step 0 시작 시 `$TMUX` 미설정 체크 추가 - 명확한 에러 메시지 출력 후 exit

SKILL.md (#4):
- Step 0: 기존 state 파일 발견 시 step/pr 정보 출력 후 "Resume / Start fresh" 사용자 선택 추가

SKILL.md (#3):
- Step 1: PR 생성 후 `lastCommitSha` 캡처 - state JSON에 필드 추가

SKILL.md (#1, #2):
- Step 3: `eval "$(pipeline_analyze_review ...)"` 제거
- `pipeline_fetch_review`로 JSON 가져온 후 AI가 STATE/severity 직접 판단하도록 변경

SKILL.md (#5):
- Step 3 결정 로직: `APPROVED` → Step 5 통일, `PENDING`/`DISMISSED` → 오류 보고 추가

recovery.md (#10):
- resolve step 복구 로직: 날짜 비교(`submitted_at` vs `committer.date`) 제거
- 최신 커밋 SHA vs `lastCommitSha` 비교로 교체 - 명확하고 단순한 완료 판단

dev-review/SKILL.md (#11):
- Constraints에 `## Review Summary` 필수 접두사 규칙 명시 - 폴링 감지 조건과 연동 명시

### 결과

- `refactor/issue-28-dev-pipeline-fixes` 브랜치 PR 생성
- Closes #28
