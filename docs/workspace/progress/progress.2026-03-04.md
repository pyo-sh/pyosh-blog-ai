# Workspace Progress - 2026-03-04

## Skill 간 중복된 monorepo 로직을 공유 reference + helper로 추출 (#40)

**Issue**: #40
**Branch**: `refactor/issue-40-monorepo-helpers`

### 배경

Root detection 로직이 3가지 방식으로 구현됨 (스크립트 상대경로, `git rev-parse` + 형제 디렉토리 확인, `.agents/` 탐색). area 매핑, workspace 특수 처리가 거의 모든 dev-* skill에 중복.

### 변경 사항

**신규 파일**:
- `.agents/references/monorepo-layout.md` - area 정의, 디렉토리/repo 매핑, worktree 경로 규칙, verify 명령 등 단일 참조 문서
- `.agents/scripts/monorepo-helpers.sh` - `MONOREPO_ROOT` 감지, `monorepo_area_dir()`, `monorepo_area_repo()`, `monorepo_area_from_dir()` 공유 함수

**수정 파일**:
- `pipeline-helpers.sh` - 자체 root detection 제거, monorepo-helpers.sh source
- `orchestrate-helpers.sh` - 자체 root detection 제거, monorepo-helpers.sh source, `monorepo_area_from_dir()` 사용
- `worktree-merge.md` - 자체 root detection 코드 제거, monorepo-helpers.sh 참조
- `dev-build`, `dev-pipeline`, `dev-resolve`, `brainstorming`, `handoff` SKILL.md - monorepo-layout.md 참조 링크 추가
