---
name: dev-log
description: pyosh-blog 모노레포에서 progress/, findings/, decisions/ 폴더를 중심으로 진행 상황·기술 조사·아키텍처 결정을 기록하는 문서 관리 스킬. 기록 전용 — 작업 관리는 GitHub Issues에서 수행.
---

# Dev-Log for pyosh-blog

기록 전용 스킬. 작업 관리는 GitHub Issues, 전역 규칙은 `CLAUDE.md` 참조.

**핵심 전략**: 인덱스 스캔 → 선택적 하위 파일 읽기 → 기록 업데이트

## 디렉토리 구조

```
docs/{client|server}/
├── progress.index.md
├── findings.index.md
├── decisions.index.md
├── progress/
│   └── progress.YYYY-MM-DD.md
├── findings/
│   └── findings.NNN-topic.md
└── decisions/
    └── decision-NNN-topic.md
```

## 파일 네이밍

| 유형 | 형식 | NNN/날짜 |
|------|------|----------|
| Progress | `progress.YYYY-MM-DD.md` | ISO 8601 |
| Findings | `findings.NNN-topic.md` | 3자리 순번, kebab-case |
| Decision | `decision-NNN-topic.md` | 3자리 순번, kebab-case |

## 워크플로

### 1. 기록 전 컨텍스트 확인
- 해당 영역의 `progress.index.md` + `findings.index.md` + `decisions.index.md` 읽기
- 관련 항목만 선택적으로 하위 파일 읽기 (전체 읽기 금지)

### 2. 기록 작성
- **기술 조사 시**: `findings/findings.NNN-topic.md` 생성 + `findings.index.md` 갱신
- **아키텍처 결정 시**: `decisions/decision-NNN-topic.md` 작성 (draft) + `decisions.index.md` 갱신
- **작업 완료 시**: `progress/progress.YYYY-MM-DD.md` 생성/업데이트 + `progress.index.md` 갱신
- 폴더/파일 없으면 즉시 생성 ([templates.md](assets/templates.md) 참고)
- 관련 GitHub Issue 번호 포함 (예: `#123`)

### 3. 인덱스 갱신 규칙
- NNN 순번: 해당 디렉토리 스캔 → 최대 순번 + 1
- progress.index.md: **최상단**에 추가
- 상세: [indexing-strategy.md](references/indexing-strategy.md)

## 참조

- [파일 템플릿](assets/templates.md) — findings, progress, decision 파일 포맷
- [인덱싱 전략](references/indexing-strategy.md) — 인덱스 갱신 규칙, 순번 충돌 방지
- [작업 예시](references/examples.md) — 시나리오별 워크플로
