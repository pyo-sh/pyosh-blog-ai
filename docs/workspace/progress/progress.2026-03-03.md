# Workspace Progress - 2026-03-03

## PR #33 머지 완료 - agent-tracker 버그 수정, 성능 최적화, lifecycle 개선 (#30 #31 #32)

**Issues**: #30 (성능 최적화), #31 (버그 수정), #32 (UI/lifecycle 개선)
**PR**: [#33](https://github.com/pyo-sh/pyosh-blog-ai/pull/33)
**Branch**: `fix/agent-tracker-improvements`
**Review rounds**: 4 (Codex), Resolve rounds: 3 (Claude Sonnet)

### 변경 파일

- `tools/agent-tracker/agent-tracker.sh`
- `tools/agent-tracker/hooks/on-status.sh`
- `tools/agent-tracker/setup.sh`
- `tools/docker/Dockerfile`
- `tools/tmux/session.docker.yml`

### 구현 내용

**버그 수정 (#31)**
- Spinner false positive 수정: sidecar status가 idle일 때만 pane scraping으로 override - non-idle 상태에서 코드/출력에 스피너 문자가 포함되어도 상태 유지
- W_TASK off-by-one: `-10` → `-9` (실제 overhead: left_pad(2) + 5 separators + trailing(2) = 9)
- tput TERM 미설정 에러: startup `smcup`/`civis` 호출에 `2>/dev/null` 추가

**성능 최적화 (#30)**
- `display_width` ASCII fast path: `[[ "$s" != *[^[:ascii:]]* ]]` 체크 후 `${#s}` 사용 - subshell ~80% 감소
- Border/header 캐싱: `_PREV_COLS` 비교로 terminal width 변경 시에만 재생성 (W_TOKENS, h_task/h_activity 제외 - data-dependent)
- Codex jq 통합: 5회 별도 호출 → `jq -rs` 단일 패스 (리뷰에서 `last_ne` null 반환 수정)
- `detect_agent_type` 캐싱: `AGENT_TYPE_CACHE` associative array로 pane_pid별 결과 재사용
- Pipeline jq 통합: 파일당 2회 → 1회

**Lifecycle & UI 개선 (#32)**
- Activity 컬럼 동적 크기: `W_ACTIVITY=18` 하드코딩 제거 → 실제 content 최대 width로 계산, `W_ACTIVITY_MAX` 캡으로 W_TASK 최소 15 보장
- 고아 sidecar 파일 정리: startup 시 현재 세션의 활성 pane에 속하지 않는 파일만 선택적 삭제
- SessionEnd hook: 세션 종료 시 해당 pane의 sidecar 파일 삭제 - `setup.sh`에 등록 추가
- `/clear` 초기화: UserPromptSubmit에서 prompt가 `/clear`면 sidecar를 idle 상태로 리셋
- Task 완료 표시: Stop hook에서 task 앞에 `(Done) ` 접두사 추가
- `session.docker.yml` 경로: `bash scripts/agent-tracker.sh` → `bash tools/agent-tracker/agent-tracker.sh`
- `Dockerfile`: 빌드 시 `setup.sh --yes` 자동 실행

### 리뷰 이슈 및 해결

| 라운드 | 이슈 | 해결 |
| ------ | ---- | ---- |
| 1 | Codex jq `last_ne` → `""` 반환으로 `//` fallback 깨짐 | `last` (null 반환)으로 수정, join 시 `// ""` 적용 |
| 2 | `W_ACTIVITY` 무제한 확장으로 border 정렬 깨질 수 있음 | `W_ACTIVITY_MAX` 계산으로 캡 |
| 3 | `_CACHE_h_tokens`/`_CACHE_d_tokens` COLS 캐시에 포함 - W_TOKENS는 data-dependent | h_tokens/d_tokens를 캐시 블록 밖으로 이동 |
| 4 | `AGENT_TYPE_CACHE` 무효화 없음, multi-session sidecar 삭제 위험 | 두 항목 모두 edge case로 merge as-is 결정 |
