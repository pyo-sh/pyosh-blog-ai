# 브랜치 명명 규칙

## 형식

```
{type}/issue-{N}-{설명}
```

## Type 목록

| Type | 용도 | 예시 |
|------|------|------|
| `feat` | 새 기능 | `feat/issue-42-post-card` |
| `fix` | 버그 수정 | `fix/issue-55-login-error` |
| `docs` | 문서 수정 | `docs/issue-10-api-docs` |
| `refactor` | 리팩토링 | `refactor/issue-78-auth-cleanup` |

## 규칙

1. **설명**은 kebab-case, 영어, 3단어 이내
2. **Issue 번호** 필수 포함
3. **소문자만** 사용

## 커밋 메시지 형식

```
{type}: {description} (#{N})
```

### 예시
```
feat: add post card component (#42)
fix: resolve login redirect loop (#55)
docs: update API documentation (#10)
refactor: simplify auth middleware (#78)
```

## Conventional Commits Type

| Type | 설명 |
|------|------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 변경 |
| `style` | 코드 포맷팅 (기능 변경 없음) |
| `refactor` | 리팩토링 (기능 변경 없음) |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 설정 변경 |
