# PR 템플릿

## 본문

```markdown
## Summary
Closes #{N}

- 변경 사항 1
- 변경 사항 2

## Changes
- **파일1**: 변경 내용
- **파일2**: 변경 내용

## Test plan
- [ ] 테스트 항목 1
- [ ] 테스트 항목 2

## Screenshots
(UI 변경 시 첨부)
```

## 필수
1. `Closes #{N}` — Issue 자동 종료
2. **Summary** — 1-3 bullet points
3. **Test plan** — 검증 방법

## PR 제목
```
{type}: {description} (#{N})
```

## gh pr create

**`--body-file` 필수** — `--body` 인라인은 마크다운 백틱이 셸 이스케이프와 충돌.

```bash
cat > /tmp/pr-{N}-body.md <<'PREOF'
## Summary
Closes #{N}
- 변경 사항
## Test plan
- [ ] 테스트 항목
PREOF

gh pr create \
  --title "{type}: description (#{N})" \
  --body-file /tmp/pr-{N}-body.md
```
