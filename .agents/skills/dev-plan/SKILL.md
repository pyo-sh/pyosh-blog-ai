---
name: dev-plan
description: decisions/ 디렉토리의 decision 파일을 GitHub Issue로 변환하는 스킬. decision 파일 기반 태스크 수립 후 Issue 등록, 파일 정리까지 자동 수행. /dev-workflow 전 단계로 사용. 사용자가 "/dev-plan", "이슈 등록해줘", "decision을 issue로 변환해줘" 등을 요청할 때 활성화.
---

# Dev-Plan for pyosh-blog

decisions/ 디렉토리의 decision 파일을 GitHub Issue로 변환하고 정리하는 스킬. `/dev-workflow` 전 단계.

## Git Remote 규칙

| 영역 | 경로 | GitHub 리포 |
|------|------|-------------|
| server | `server/` | `pyo-sh/pyosh-blog-be` |
| client | `client/` | `pyo-sh/pyosh-blog-fe` |

## 워크플로

### 1. 대상 영역 감지

인자가 있으면 해당 영역 사용. 없으면:
- 현재 대화 맥락에서 영역 유추
- 양쪽 `decisions/` 스캔하여 변환 대상 파일이 있는 영역 자동 감지
- 판단 불가 시 사용자에게 질문

### 2. Decision 파일 스캔 및 분류

`docs/{area}/decisions/` 디렉토리의 모든 `.md` 파일을 읽고, 각 파일의 **상태(status)**에 따라 분류:

| 상태 | 동작 |
|------|------|
| `accepted`, `rejected` | 파일 삭제 + index에서 제거 (이미 완료된 결정) |
| `pending`, `deferred` | 건드리지 않음 (진행 중/보류) |
| `draft`, 상태 없음 | **GitHub Issue로 변환** |

상태는 파일 내 메타데이터에서 추출 (예: `> **상태**: draft`).

### 3. 우선순위 결정

1. 해당 리포의 기존 open Issue 목록 조회: `gh issue list --state open --repo {repo} --json number,title,labels`
2. 해당 리포의 `{area}/.github/labels.json`에서 priority 라벨 확인
3. 각 decision의 Phase, 의존성, 내용을 기존 Issue와 비교하여 우선순위를 AI가 판단
4. 우선순위 배분 결과를 **사용자에게 제시하고 승인** 받은 후 진행

참고: [priority-guide.md](references/priority-guide.md) 참조

### 4. Issue 생성

- 관련 decision 파일을 **묶어서** 하나의 Issue로 만들 수 있음 (AI 판단)
- 각 Issue 생성 시:
  - `--repo` 플래그로 대상 리포 명시
  - `--label` 로 타입 라벨 + priority 라벨 부여
  - `--body` 에 decision 파일 내용 기반으로 작성 (목표, 범위, 구현 작업 포함)

Issue body 형식:
```
## 개요
{decision 파일의 목표/배경}

## 범위
{decision 파일의 범위}

## 작업 항목
- [ ] 항목 1
- [ ] 항목 2

## 참조
- decision 파일명, Phase 정보, 의존성 등
```

### 5. 파일 정리

Issue 생성 완료 후:
1. 변환된 decision 파일 삭제
2. `accepted`/`rejected` 상태 파일 삭제
3. `decisions.index.md`에서 삭제된 파일의 참조 제거
4. 삭제 결과를 사용자에게 보고

### 6. 결과 보고

생성된 Issue 목록 (번호 + URL + 우선순위)과 정리된 파일 목록을 요약 출력.

## 주의사항

- `pending`, `deferred` 상태 파일은 절대 수정/삭제하지 않음
- Issue 생성 전 반드시 우선순위 승인을 받을 것
- 루트 디렉토리에서 gh 명령 실행 금지 — 반드시 `--repo` 플래그 사용
