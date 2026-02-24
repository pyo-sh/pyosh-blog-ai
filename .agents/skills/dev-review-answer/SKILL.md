---
name: dev-review-answer
description: PR 리뷰 코멘트 대응 스킬. dev-review로 남겨진 리뷰 코멘트를 읽고 코드를 수정한 뒤 재리뷰를 요청. 사용자가 "리뷰 코멘트 수정해줘", "리뷰 반영해줘", "/dev-review-answer" 등을 요청할 때 활성화.
---

# Dev-Review-Answer

## 워크플로

### 1. 리뷰 코멘트 확인

```bash
cd {영역}  # server/ 또는 client/
gh pr view {PR번호} --comments
gh api repos/{owner}/{repo}/pulls/{PR번호}/reviews
```

### 2. 코멘트 분류

| 심각도 | 처리 |
|--------|------|
| **[CRITICAL]** / **[WARNING]** | 필수 수정 |
| **[SUGGESTION]** | 타당하면 수정, 아니면 스킵 (사유 필수) |

### 3. 코드 수정

기존 worktree 또는 브랜치에서 작업.

- **리뷰 코멘트 범위만 수정** — 관련 없는 리팩토링/개선 금지
- **커밋**: `fix: address review comments (#{N})`
- **수정 후 반드시 push**

### 4. PR에 대응 결과 코멘트

**반드시 `--body-file` 사용** (마크다운 백틱 충돌 방지):

```bash
cat > /tmp/pr-{PR번호}-response.md <<'RESPEOF'
## Review Response

### 수정 완료
| # | 심각도 | 파일:라인 | 조치 |
|---|--------|-----------|------|
| 1 | [CRITICAL] | `파일:라인` | 수정 완료 — 설명 |

### 스킵 (Suggestion)
| # | 파일:라인 | 사유 |
|---|-----------|------|
| 1 | `파일:라인` | 스킵 사유 |

> 재리뷰 요청드립니다.
RESPEOF

gh pr comment {PR번호} --body-file /tmp/pr-{PR번호}-response.md
```

### 5. 사용자 안내

- 수정/스킵 항목 수 요약
- **새 세션에서 `/dev-review`** 실행 안내
