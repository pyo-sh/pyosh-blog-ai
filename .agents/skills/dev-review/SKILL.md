---
name: dev-review
description: PR 코드 리뷰 스킬. 코드를 작성한 AI와 다른 세션에서 실행하여 편향 없는 리뷰를 수행. GitHub PR Review(인라인 코멘트 + 요약)로 결과를 남김. 사용자가 "PR 리뷰해줘", "코드 리뷰", "/dev-review" 등을 요청할 때 활성화.
---

# Dev-Review

**코드를 작성한 AI와 다른 세션**에서 PR을 리뷰. 코멘트만 남기고, 코드 수정은 하지 않는다.

## 사전 조건

- 리뷰 대상 PR이 존재해야 함
- **코드 작성 세션과 다른 세션**에서 실행 (컨텍스트 오염 방지)

## Git Remote 규칙

monorepo이며, `server/`와 `client/`는 각각 독립 Git 리포.

| 영역 | 경로 | GitHub 리포 |
|------|------|-------------|
| server | `server/` | `pyo-sh/pyosh-blog-be` |
| client | `client/` | `pyo-sh/pyosh-blog-fe` |

**모든 `gh` 명령은 해당 영역 디렉토리에서 실행**하거나 `--repo` 플래그 사용.

## 리뷰 순서

### 1. PR 확인

```bash
cd {영역}  # server/ 또는 client/
gh pr view {PR번호}
gh pr diff {PR번호}
```

관련 Issue도 확인:
```bash
gh issue view {Issue번호}
```

### 2. 코드 분석

PR diff + 변경된 파일의 주변 컨텍스트를 읽고 아래 체크리스트 기반으로 리뷰.

#### 체크리스트

**보안**
- SQL injection, XSS, command injection 등 OWASP Top 10
- 인증/인가 누락, 민감 데이터 노출

**타입 안전성**
- `any` 타입 사용, 타입 단언 남용
- nullable 처리 누락, 런타임 타입 불일치 가능성

**엣지케이스**
- 빈 배열/null/undefined 처리
- 동시성 문제, 경계값 처리

**에러 핸들링**
- 에러 삼킴(swallowing), 부적절한 에러 메시지
- 예외 미처리 경로

**성능**
- N+1 쿼리, 불필요한 리렌더링
- 메모리 누수, 대용량 데이터 미처리

**컨벤션**
- 네이밍 규칙 (`client/CLAUDE.md`, `server/CLAUDE.md` 참조)
- 코드 스타일, 프로젝트 패턴 준수
- CLAUDE.md 규칙 위반 여부

### 3. 심각도 분류

| 심각도 | 표기 | 의미 | 예시 |
|--------|------|------|------|
| **Critical** | `[CRITICAL]` | 반드시 수정. 버그, 보안 취약점, 데이터 손실 위험 | SQL injection, 인증 우회 |
| **Warning** | `[WARNING]` | 수정 권장. 잠재적 문제, 성능 저하 | N+1 쿼리, 누락된 에러 처리 |
| **Suggestion** | `[SUGGESTION]` | 선택적 개선. 가독성, 컨벤션, 더 나은 패턴 | 네이밍 개선, 중복 코드 |

### 4. PR Review 작성

`gh pr review`로 인라인 코멘트 + 전체 요약을 남긴다.

**반드시 `--body-file` 사용** (마크다운 백틱 셸 충돌 방지):

```bash
# 1. 리뷰 본문 작성
cat > /tmp/pr-{PR번호}-review.md <<'REVIEWEOF'
## Review Summary

| 심각도 | 건수 |
|--------|------|
| [CRITICAL] | 0 |
| [WARNING] | 2 |
| [SUGGESTION] | 3 |

### Critical
(없음)

### Warning
1. `파일:라인` — 설명
2. `파일:라인` — 설명

### Suggestion
1. `파일:라인` — 설명
2. `파일:라인` — 설명
3. `파일:라인` — 설명
REVIEWEOF

# 2. 리뷰 제출
# Critical이 있으면 REQUEST_CHANGES, 없으면 COMMENT
gh pr review {PR번호} \
  --body-file /tmp/pr-{PR번호}-review.md \
  --{comment|request-changes}
```

**판정 기준:**
- Critical이 1건 이상 → `--request-changes`
- Critical이 0건 → `--comment`

### 5. 사용자에게 결과 안내

리뷰 완료 후 사용자에게 요약 보고:
- Critical/Warning/Suggestion 건수
- Critical이 있으면 `dev-review-answer`로 수정 필요하다고 안내
- Critical이 없으면 사용자 승인 후 Merge 가능하다고 안내

## 리뷰 원칙

- **코드 수정 금지** — 코멘트만 남긴다
- **편향 없이** — "왜 이렇게 했는지"를 추측하지 말고, 코드 자체만 평가
- **구체적으로** — "이 부분이 좀 그렇다" 대신 `파일:라인`과 구체적 문제/대안 제시
- **과잉 리뷰 금지** — 사소한 스타일 차이로 Critical/Warning을 남기지 않음
