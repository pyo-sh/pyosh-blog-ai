# Progress 2026-03-13

## dev-pipeline: log → merge 순서 변경 (#164, PR #165)

- **문제**: dev-pipeline 상태 머신이 `merge → log → done` 순서로 실행되어, dev-log가 standalone 모드의 `lock_merge`로 local main에 커밋하지만 push하지 않음. 다음 PR squash merge 시 origin/main과 발산하여 `ff-only` 실패 100% 재현
- **해결**: 상태 머신 순서를 `log → merge → done`으로 변경
  - dev-log가 issue worktree에서 실행되어 `inRootWorktree: true` 경로를 타고 PR branch에 push
  - `lock_merge`(Phase 5)를 완전히 우회하여 local-only 커밋 원천 차단
- **변경**: SKILL.md state machine, `steps.py` 전이 변경(`step_log_setup` 추가, `step_merge` cleanup 통합), `cli.py` dispatch table
- **리뷰 피드백**: `push_safely` 반환값 미검사 경고 수정, `log_transition` audit trail 추가
- 2라운드 리뷰, PR #165 squash merge 완료

## dev-log detect-context area 검증 (#164, PR #166)

- **문제**: `detect-context`가 `.workspace/worktrees/` 하위 경로만으로 `inRootWorktree: true` 판단하여 client/server worktree에서 false positive 발생. dev-log가 client/server PR branch에 docs를 혼입할 위험
- **해결**: worktree의 `.git` 파일에서 `gitdir:` 경로를 읽어 root repo에 속하는지 검증
  - `_find_worktree_root()`: nested path에서 `.git` 파일이 있는 worktree root 탐색
  - `_is_root_repo_worktree()`: gitdir 경로가 `{root_repo}/.git/` 하위인지 확인
- **테스트**: client/server false positive, no `.git` file 케이스 등 7개 테스트, 전체 25개 pass
