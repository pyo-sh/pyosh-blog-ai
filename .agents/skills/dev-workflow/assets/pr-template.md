# PR 템플릿

## 기본 형식

```markdown
## Summary
Closes #{N}

- 변경 사항 1
- 변경 사항 2
- 변경 사항 3

## Changes
- **파일1**: 변경 내용
- **파일2**: 변경 내용

## Test plan
- [ ] 테스트 항목 1
- [ ] 테스트 항목 2

## Screenshots
(UI 변경 시 첨부)
```

## PR 제목 형식

```
{type}: {description} (#{N})
```

### 예시
```
feat: add post card component (#42)
fix: resolve login redirect loop (#55)
```

## 필수 포함 사항

1. `Closes #{N}` — Issue 자동 종료
2. **Summary** — 변경 사항 요약 (1-3 bullet points)
3. **Test plan** — 검증 방법

## gh pr create 사용법

**반드시 `--body-file` 사용** — `--body "..."` 인라인은 마크다운 백틱(`` ` ``)이 셸 이스케이프와 충돌하여 금지.

```bash
# 1. 임시 파일에 PR 본문 작성
cat > /tmp/pr-42-body.md <<'PREOF'
## Summary
Closes #42

- PostCard 컴포넌트 생성
- TailwindCSS v4 토큰 적용
- 반응형 레이아웃

## Test plan
- [ ] 데스크톱/모바일 렌더링 확인
- [ ] 다크모드 확인
PREOF

# 2. --body-file로 PR 생성
gh pr create \
  --title "feat: add post card component (#42)" \
  --body-file /tmp/pr-42-body.md
```

## AI 리뷰

PR 생성 후 리뷰는 **별도 세션에서 `/dev-review` 스킬**로 수행.
리뷰 코멘트 형식은 `dev-review` 스킬 참조.
