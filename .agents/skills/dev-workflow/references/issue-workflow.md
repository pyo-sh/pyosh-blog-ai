# Issue 생명주기

## 상태 흐름

```
Open → In Progress → PR Created → Review → Merged/Closed
```

## 상세 단계

### 1. Open (생성)
- 사용자 또는 AI가 Issue 생성
- 라벨 부여: `client`, `server`, `feat`, `fix`, `docs`, `refactor`
- 필요 시 마일스톤 연결

### 2. In Progress (작업 중)
- 에이전트가 Issue를 self-assign
- worktree 생성 후 코딩 시작

### 3. PR Created
- 코딩 완료 후 PR 생성
- PR 본문에 `Closes #{N}` 포함

### 4. Review
- AI가 코드 리뷰 수행
- 사용자 최종 승인

### 5. Merged/Closed
- Squash merge 후 자동 Close
- worktree 정리

## Issue 생성 규칙

### 제목 형식
```
[{area}] {description}
```

### 예시
```
[client] 블로그 포스트 카드 컴포넌트 개발
[server] 포스트 목록 조회 API 구현
[docs] API 문서 업데이트
```

### 본문 포함 사항
- **배경**: 왜 이 작업이 필요한가
- **요구사항**: 구체적인 작업 항목
- **완료 기준**: 무엇이 완료되면 이 Issue를 닫을 수 있는가

## 라벨 체계

| 라벨 | 설명 |
|------|------|
| `client` | 프론트엔드 작업 |
| `server` | 백엔드 작업 |
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 |
| `refactor` | 리팩토링 |
| `priority:high` | 긴급 |
| `priority:low` | 나중에 |

## gh CLI 명령어

```bash
# Issue 목록
gh issue list
gh issue list --assignee @me
gh issue list --label "client"

# Issue 상세
gh issue view {N}

# Issue 생성
gh issue create --title "[client] 포스트 카드 개발" --body "..." --label "client,feat"

# Issue 할당
gh issue edit {N} --add-assignee @me

# Issue 종료 (보통 PR merge로 자동 종료)
gh issue close {N}
```
