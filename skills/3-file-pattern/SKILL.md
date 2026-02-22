---
name: 3-file-pattern
description: pyosh-blog 모노레포에서 tasks/, findings.index.md, progress.index.md를 중심으로 작업 계획·기술 조사·진행 상황을 추적하는 문서 관리 전략. 작업 시작, 진행 상황 기록, 기술 결정 문서화가 필요할 때 자동 활성화.
disable-model-invocation: false
user-invocable: true
---

# 3-File Pattern for pyosh-blog

## 개요

pyosh-blog 모노레포에서 **client/server 영역별**로 3개 폴더/파일(tasks/, findings.index.md, progress.index.md)을 중심으로 작업을 관리합니다. 작업은 `tasks/` 폴더에 개별 파일로 관리하고, 인덱스 파일은 요약과 경로만 유지하며, 실제 내용은 하위 파일에 저장하여 토큰을 절약합니다.

**핵심 전략**: tasks/ 폴더 스캔 → 인덱스 → 선택적 하위 파일 읽기 → 업데이트 → 헬스체크

## 필수 규칙

1. **작업 시작 전**: 해당 영역의 `tasks/` 폴더 목록 확인 → 해당 task 파일 읽기 + `progress.index.md` 읽기
2. **폴더/파일 없으면**: 즉시 생성 ([templates.md](assets/templates.md) 참고)
3. **새 작업 추가**: `tasks/task-NN-topic.md` 파일 생성
4. **기술 조사**: `findings/findings.NNN-topic.md` 생성 + `findings.index.md`에 항목 추가
5. **작업 완료**: `progress/progress.YYYY-MM-DD.md` 생성 + `progress.index.md`에 요약 추가
6. **체크박스 갱신**: 하위 작업 완료 시 해당 `tasks/task-NN-topic.md` 파일 업데이트
7. **선택적 읽기**: tasks/ 폴더 목록에서 관련 task 파일만 읽기, 인덱스에서 관련 항목만 찾아 하위 파일 읽기 (전체 읽기 금지)
8. **응답 종료 시**: 업데이트한 파일 명시 + 헬스체크 로그 작성

## 디렉토리 구조

```
pyosh-blog/
├── docs/
│   ├── client/
│   │   ├── tasks/
│   │   │   ├── task-01-component-library.md
│   │   │   ├── task-02-page-routing.md
│   │   │   └── ...
│   │   ├── findings.index.md
│   │   ├── progress.index.md
│   │   ├── findings/
│   │   │   └── findings.NNN-topic.md
│   │   └── progress/
│   │       └── progress.YYYY-MM-DD.md
│   └── server/
│       └── (동일 구조)
├── client/
└── server/
```

## 작업 워크플로

### 1. 영역 판단
- **client**: UI, 컴포넌트, 페이지, 스타일링, 라우팅
- **server**: API, DB 스키마, 인증, 비즈니스 로직

### 2. 작업 시작 체크리스트

```
- [ ] 해당 영역의 tasks/ 폴더 목록 확인 (ls 또는 Glob)
- [ ] 관련 task 파일 읽기 (예: tasks/task-05-test-taxonomy.md)
- [ ] progress.index.md 읽어 최근 작업 확인
- [ ] findings.index.md에서 관련 키워드 검색
- [ ] 필요 시 관련 findings/progress 하위 파일만 선택적 읽기
- [ ] client/CLAUDE.md 또는 server/CLAUDE.md에서 코딩 규칙 확인
```

### 3. 실행 중
- 기술 조사/결정 발생 → `findings/findings.NNN-topic.md` 작성 + `findings.index.md` 갱신
- 하위 작업 완료 → 해당 `tasks/task-NN-topic.md` 체크박스 갱신

### 4. 작업 완료
- `progress/progress.YYYY-MM-DD.md`에 상세 로그 작성
- `progress.index.md`에 한줄 요약 추가
- 업데이트한 파일 목록 명시
- 헬스체크 로그 작성

## 파일 네이밍 규칙

| 파일 유형 | 형식 | 예시 |
|-----------|------|------|
| Task | `task-NN-topic.md` | `task-01-stats-service.md` |
| Findings | `findings.NNN-topic.md` | `findings.001-nextjs-app-router.md` |
| Progress | `progress.YYYY-MM-DD.md` | `progress.2026-02-15.md` |

- **NN**: 2자리 순번 (01부터 시작)
- **NNN**: 3자리 순번 (001부터 시작)
- **topic**: kebab-case
- **날짜**: ISO 8601 형식

## 컨텍스트 전략 모드

기본적으로 **balanced** 모드로 작동합니다. 특정 상황에서는 명시적으로 다른 모드를 요청할 수 있습니다:

| 모드 | 언제 사용 | 읽는 파일 |
|------|-----------|-----------|
| **minimal** | 단순 수정, 빠른 작업 | 해당 task 파일만 |
| **balanced** (기본) | 일반적인 작업 | task 파일 + 인덱스 + 관련 항목 1-2개 |
| **deep** | 복잡한 아키텍처 결정 | tasks/ 목록 + 인덱스 + 최근 항목 5개 |

**사용 예**: "minimal 모드로 버튼 색상만 바꿔줘"

## 도구 결과 처리 규칙

### 웹 검색/DB 조회 후
1. 원본 결과를 그대로 출력하지 말 것
2. 현재 작업 목표와의 관련성 기준으로 3줄 이내 요약
3. 재사용 가능한 지식 → findings에 기록
4. 일회성 정보 → progress에 기록

### 코드 실행 결과
- **에러**: 원인과 해결책만 기록
- **성공**: 다음 단계에 영향 주는 사실만 기록

### 파일 읽기
- 읽은 내용을 반복하지 말 것
- "이 파일에서 발견한 작업 관련 사실" 1-2줄만 언급

### Before/After 예시

✗ **나쁨**: "검색 결과: [전체 텍스트 붙여넣기]"  
✓ **좋음**: "Next.js App Router 선택 근거 3가지 확인 → findings.015에 기록"

✗ **나쁨**: "파일 내용: [200줄 코드 반복]"  
✓ **좋음**: "auth.hook.ts에서 session 검증 로직 확인"

## 헬스체크 로그

매 턴 종료 시 다음 형식으로 작성:

```text
--- healthcheck ---
area: client | server
mode: minimal | balanced | deep
read: [tasks/task-03-test-infra.md, findings.index.md, findings.002]
updated: [progress.2026-02-15.md, progress.index.md]
notes: (선택) 특이사항
--- end ---
```

## Client/Server 작업 분기

### Client 작업
**참조 순서**: `@docs/client/tasks/` 목록 확인 → 해당 task 파일 → `@docs/client/progress.index.md` → `@docs/client/findings.index.md` → `@client/CLAUDE.md`

**주요 작업**: UI 컴포넌트(`src/shared/ui/`), 페이지(`src/app/`), Feature(`src/features/`), 스타일링

**코딩 규칙**: kebab-case 파일명, PascalCase 컴포넌트, `"use client"` 필요 시 추가, `cn()` 함수로 클래스 병합

### Server 작업
**참조 순서**: `@docs/server/tasks/` 목록 확인 → 해당 task 파일 → `@docs/server/progress.index.md` → `@docs/server/findings.index.md` → `@server/CLAUDE.md`

**주요 작업**: API 라우트(`src/routes/`), DB 스키마(`src/db/schema/`), 비즈니스 로직(`src/services/`)

**코딩 규칙**: kebab-case 파일명, `HttpError` static 메서드, Zod 스키마 수동 검증, Drizzle query builder

## 상세 문서

- [파일 템플릿](assets/templates.md) - task, findings, progress 파일 포맷
- [인덱싱 전략](references/indexing-strategy.md) - 인덱스 파일 관리 방법
- [작업 예시](references/examples.md) - 시나리오별 워크플로

## 응답 포맷

1. 이번 턴의 결론/결과 한두 문장 요약
2. 구체적 설명·코드·리스트 (필요 시)
3. 업데이트한 파일 목록 명시
4. 헬스체크 로그 블록
