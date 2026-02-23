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

```bash
gh pr create \
  --title "feat: add post card component (#42)" \
  --body "$(cat <<'EOF'
## Summary
Closes #42

- PostCard 컴포넌트 생성
- TailwindCSS v4 토큰 적용
- 반응형 레이아웃

## Test plan
- [ ] 데스크톱/모바일 렌더링 확인
- [ ] 다크모드 확인
EOF
)"
```
