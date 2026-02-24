---
name: dev-review
description: PR 코드 리뷰 스킬. 코드를 작성한 AI와 다른 세션에서 실행하여 편향 없는 리뷰를 수행. GitHub PR Review(인라인 코멘트 + 요약)로 결과를 남김. 사용자가 "PR 리뷰해줘", "코드 리뷰", "/dev-review" 등을 요청할 때 활성화.
---

# Dev-Review

코드 작성자와 **다른 세션**에서 PR을 리뷰. 코멘트만 남기고 코드 수정은 하지 않는다.

## 리뷰 순서

### 1. PR 확인

해당 영역(`server/` 또는 `client/`) 디렉토리에서 실행:

```bash
gh pr view {PR번호}
gh pr diff {PR번호}
gh issue view {Issue번호}  # 관련 Issue 확인
```

### 2. 코드 분석

PR diff + 변경된 파일의 주변 컨텍스트를 읽고 리뷰. `client/CLAUDE.md`, `server/CLAUDE.md` 규칙 준수 여부도 확인.

**중점 확인 영역**: 보안(OWASP Top 10), 타입 안전성(`any` 남용, nullable 누락), 엣지케이스, 에러 핸들링, 성능(N+1 쿼리 등), 프로젝트 컨벤션

### 3. 심각도 분류

| 표기 | 의미 |
|------|------|
| `[CRITICAL]` | 필수 수정 — 버그, 보안 취약점, 데이터 손실 위험 |
| `[WARNING]` | 수정 권장 — 잠재적 문제, 성능 저하 |
| `[SUGGESTION]` | 선택적 개선 — 가독성, 컨벤션, 더 나은 패턴 |

### 4. PR Review 작성

`gh pr review`로 인라인 코멘트 + 전체 요약. **반드시 `--body-file` 사용** (마크다운 백틱 셸 충돌 방지):

```bash
cat > /tmp/pr-{PR번호}-review.md <<'REVIEWEOF'
## Review Summary

| 심각도 | 건수 |
|--------|------|
| [CRITICAL] | N |
| [WARNING] | N |
| [SUGGESTION] | N |

### Critical
1. `파일:라인` — 설명

### Warning
1. `파일:라인` — 설명

### Suggestion
1. `파일:라인` — 설명
REVIEWEOF

gh pr review {PR번호} \
  --body-file /tmp/pr-{PR번호}-review.md \
  --{comment|request-changes}
```

- Critical 1건 이상 → `--request-changes`
- Critical 0건 → `--comment`

### 5. 사용자에게 결과 안내

- Critical/Warning/Suggestion 건수 요약
- Critical 있으면 → `/dev-review-answer`로 수정 필요 안내
- Critical 없으면 → 사용자 승인 후 Merge 가능 안내

## 리뷰 원칙

- **코드 수정 금지** — 코멘트만 남긴다
- **편향 배제** — 의도를 추측하지 말고 코드 자체만 평가
- **구체적으로** — `파일:라인`과 문제/대안을 명시
- **과잉 리뷰 금지** — 사소한 스타일 차이에 Critical/Warning 사용 금지
