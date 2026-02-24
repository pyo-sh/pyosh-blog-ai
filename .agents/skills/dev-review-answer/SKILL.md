---
name: dev-review-answer
description: PR 리뷰 코멘트 대응 스킬. dev-review로 남겨진 리뷰 코멘트를 읽고 코드를 수정한 뒤 재리뷰를 요청. 사용자가 "리뷰 코멘트 수정해줘", "리뷰 반영해줘", "/dev-review-answer" 등을 요청할 때 활성화.
---

# Dev-Review-Answer

PR의 리뷰 코멘트를 읽고, 코드를 수정하고, 재리뷰를 요청하는 스킬.

## 사전 조건

- 리뷰 코멘트가 달린 PR이 존재해야 함
- 해당 PR의 worktree가 존재해야 함 (또는 브랜치 체크아웃 가능)

## Git Remote 규칙

monorepo이며, `server/`와 `client/`는 각각 독립 Git 리포.

| 영역 | 경로 | GitHub 리포 |
|------|------|-------------|
| server | `server/` | `pyo-sh/pyosh-blog-be` |
| client | `client/` | `pyo-sh/pyosh-blog-fe` |

**모든 `gh` 명령은 해당 영역 디렉토리에서 실행**하거나 `--repo` 플래그 사용.

## 수정 순서

### 1. 리뷰 코멘트 확인

```bash
cd {영역}  # server/ 또는 client/
gh pr view {PR번호}
gh pr view {PR번호} --comments
gh api repos/{owner}/{repo}/pulls/{PR번호}/reviews
```

### 2. 코멘트 분류 및 처리 계획

리뷰 코멘트를 심각도별로 분류:

| 심각도 | 처리 | 설명 |
|--------|------|------|
| **[CRITICAL]** | **필수 수정** | 반드시 수정. 건너뛰기 불가 |
| **[WARNING]** | **필수 수정** | 반드시 수정. 건너뛰기 불가 |
| **[SUGGESTION]** | **판단 후 처리** | 타당하면 수정, 아니면 스킵 가능 |

Suggestion 스킵 시, 스킵 사유를 PR 코멘트에 남긴다.

### 3. 코드 수정

worktree 또는 브랜치에서 작업:
```bash
cd {영역}/.claude/worktrees/issue-{N}  # 기존 worktree
# 또는 브랜치 체크아웃
```

수정 원칙:
- **리뷰 코멘트 범위만 수정** — 관련 없는 리팩토링/개선 금지
- **커밋 형식**: `fix: address review comments (#{N})`
- **코멘트당 하나씩** 해결하며 진행

### 4. 수정 결과 보고

모든 수정 완료 후, PR에 코멘트로 대응 결과를 남긴다.

**반드시 `--body-file` 사용**:

```bash
cat > /tmp/pr-{PR번호}-response.md <<'RESPEOF'
## Review Response

### 수정 완료
| # | 심각도 | 파일:라인 | 조치 |
|---|--------|-----------|------|
| 1 | [CRITICAL] | `파일:라인` | 수정 완료 — 설명 |
| 2 | [WARNING] | `파일:라인` | 수정 완료 — 설명 |

### 스킵 (Suggestion)
| # | 파일:라인 | 사유 |
|---|-----------|------|
| 1 | `파일:라인` | 스킵 사유 |

> 재리뷰 요청드립니다.
RESPEOF

gh pr comment {PR번호} --body-file /tmp/pr-{PR번호}-response.md
```

### 5. Push & 재리뷰 요청

```bash
git push
```

사용자에게 재리뷰 필요하다고 안내:
- 수정한 항목 수 / 스킵한 항목 수 요약
- **새 세션에서 `/dev-review`** 실행을 안내

## 수정 원칙

- **리뷰 범위만 수정** — 추가 리팩토링/개선 금지
- **Suggestion 스킵은 합리적 사유 필수** — "귀찮아서"는 불가
- **수정 후 반드시 push** — 로컬에만 남기지 않음
