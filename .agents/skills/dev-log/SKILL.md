---
name: dev-log
description: pyosh-blog 모노레포에서 progress/, findings/, decisions/ 폴더를 중심으로 진행 상황·기술 조사·아키텍처 결정을 기록하는 문서 관리 스킬. 기록 전용 — 작업 관리는 GitHub Issues에서 수행.
disable-model-invocation: false
user-invocable: true
---

# Dev-Log for pyosh-blog

## 개요

pyosh-blog 모노레포에서 **client/server 영역별**로 3개 폴더(progress/, findings/, decisions/)와 인덱스 파일을 중심으로 작업 기록을 관리합니다. **작업 관리(할 일, 할당)는 GitHub Issues**에서 수행하고, 이 스킬은 **기록 전용**입니다.

**핵심 전략**: 인덱스 스캔 → 선택적 하위 파일 읽기 → 기록 업데이트

## 필수 규칙

1. **작업 시작 전**: `progress.index.md` + `findings.index.md` + `decisions.index.md` 읽기 (최근 컨텍스트 파악)
2. **폴더/파일 없으면**: 즉시 생성 ([templates.md](assets/templates.md) 참고)
3. **기술 조사**: `findings/findings.NNN-topic.md` 생성 + `findings.index.md`에 항목 추가
4. **작업 완료**: `progress/progress.YYYY-MM-DD.md` 생성/업데이트 + `progress.index.md`에 요약 추가
5. **아키텍처 결정**: `decisions/decision-NNN-topic.md` 작성 (draft) + `decisions.index.md`에 항목 추가
6. **선택적 읽기**: 인덱스에서 관련 항목만 찾아 하위 파일 읽기 (전체 읽기 금지)
7. **Issue 참조**: 기록에 관련 GitHub Issue 번호를 포함 (예: `#123`)

## 디렉토리 구조

```
pyosh-blog/
├── docs/
│   ├── client/
│   │   ├── findings.index.md
│   │   ├── progress.index.md
│   │   ├── decisions.index.md
│   │   ├── findings/
│   │   │   └── findings.NNN-topic.md
│   │   ├── progress/
│   │   │   └── progress.YYYY-MM-DD.md
│   │   └── decisions/
│   │       └── decision-NNN-topic.md
│   └── server/
│       └── (동일 구조)
├── client/
└── server/
```

## 작업 워크플로

### 1. 영역 판단
- **client**: UI, 컴포넌트, 페이지, 스타일링, 라우팅
- **server**: API, DB 스키마, 인증, 비즈니스 로직

### 2. 기록 시작 체크리스트

```
- [ ] progress.index.md 읽어 최근 작업 확인
- [ ] findings.index.md에서 관련 키워드 검색
- [ ] decisions.index.md에서 관련 결정 확인
- [ ] 필요 시 관련 하위 파일만 선택적 읽기
```

### 3. 실행 중
- 기술 조사/결정 발생 → `findings/findings.NNN-topic.md` 작성 + `findings.index.md` 갱신
- 아키텍처/기술 선택 필요 → `decisions/decision-NNN-topic.md` 작성 (draft 상태)

### 4. 작업 완료
- `progress/progress.YYYY-MM-DD.md`에 상세 로그 작성
- `progress.index.md`에 한줄 요약 추가
- 업데이트한 파일 목록 명시

## 파일 네이밍 규칙

| 파일 유형 | 형식 | 예시 |
|-----------|------|------|
| Findings | `findings.NNN-topic.md` | `findings.001-nextjs-app-router.md` |
| Progress | `progress.YYYY-MM-DD.md` | `progress.2026-02-15.md` |
| Decision | `decision-NNN-topic.md` | `decision-001-auth-strategy.md` |

- **NNN**: 3자리 순번 (001부터 시작)
- **topic**: kebab-case
- **날짜**: ISO 8601 형식

## 컨텍스트 전략 모드

기본적으로 **balanced** 모드로 작동합니다:

| 모드 | 언제 사용 | 읽는 파일 |
|------|-----------|-----------|
| **minimal** | 단순 수정, 빠른 작업 | progress 생략 가능 |
| **balanced** (기본) | 일반적인 작업 | 인덱스 + 관련 항목 1-2개 |
| **deep** | 복잡한 아키텍처 결정 | 인덱스 + 최근 항목 5개 |

## 도구 결과 처리 규칙

### 웹 검색/DB 조회 후
1. 원본 결과를 그대로 출력하지 말 것
2. 현재 작업 목표와의 관련성 기준으로 3줄 이내 요약
3. 재사용 가능한 지식 → findings에 기록
4. 일회성 정보 → progress에 기록

### Before/After 예시

✗ **나쁨**: "검색 결과: [전체 텍스트 붙여넣기]"
✓ **좋음**: "Next.js App Router 선택 근거 3가지 확인 → findings.015에 기록"

## Client/Server 작업 분기

### Client 작업
**참조 순서**: `@docs/client/progress.index.md` → `@docs/client/findings.index.md` → `@docs/client/decisions.index.md` → `@client/CLAUDE.md`

### Server 작업
**참조 순서**: `@docs/server/progress.index.md` → `@docs/server/findings.index.md` → `@docs/server/decisions.index.md` → `@server/CLAUDE.md`

## 상세 문서

- [파일 템플릿](assets/templates.md) - findings, progress, decision 파일 포맷
- [인덱싱 전략](references/indexing-strategy.md) - 인덱스 파일 관리 방법
- [작업 예시](references/examples.md) - 시나리오별 워크플로

## 응답 포맷

1. 이번 턴의 결론/결과 한두 문장 요약
2. 구체적 설명·코드·리스트 (필요 시)
3. 업데이트한 파일 목록 명시
