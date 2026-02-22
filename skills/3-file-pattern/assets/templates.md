# 파일 템플릿

## tasks/task-NN-topic.md

개별 작업 파일은 `tasks/` 폴더에 저장합니다. 파일명: `task-NN-topic.md` (NN: 2자리 순번, topic: kebab-case)

```markdown
# Task NN: [작업명]

> 한줄 설명

## 선행 조건

- [x] 선행 작업 완료 여부
- [ ] 필요한 환경 설정

## 작업 항목

### 1. [영역명]

- [ ] **세부 작업명**
  - 상세 설명

- [ ] **세부 작업명**
  - 상세 설명

### 2. [영역명]

- [ ] **세부 작업명**
  - 상세 설명

## 검증

- [ ] 검증 항목 1
- [ ] 검증 항목 2
```

### 순번 규칙
1. `tasks/` 디렉토리의 기존 파일 확인
2. 파일명에서 순번 추출 (예: `task-05-test-taxonomy.md` → 05)
3. 최대 순번 + 1로 새 파일 생성

## findings.index.md

```markdown
# Findings Index

## 001 - Next.js App Router 선택 근거
- **파일**: `findings/findings.001-nextjs-app-router.md`
- **날짜**: 2026-02-01
- **요약**: Pages Router 대신 App Router 선택. RSC, Streaming, Layouts 장점.
- **키워드**: Next.js, App Router, RSC

## 002 - TailwindCSS v4 토큰 네이밍
- **파일**: `findings/findings.002-tailwind-v4-tokens.md`
- **날짜**: 2026-02-05
- **요약**: kebab-case 토큰 네이밍 규칙과 @theme 블록 사용법.
- **키워드**: TailwindCSS, v4, 토큰
```

## findings/findings.NNN-topic.md

```markdown
# [주제]

## 메타데이터
- **날짜**: YYYY-MM-DD
- **관련 작업**: task.md 항목 참조

## 문제
해결하려는 문제나 선택이 필요했던 상황

## 조사 결과

### 옵션 A
- 장점: ...
- 단점: ...

### 옵션 B
- 장점: ...
- 단점: ...

## 결정
최종 선택과 이유

## 구현 가이드
(선택) 실제 적용 시 주의사항

## 참고 자료
- [링크 1](URL)
```

## progress.index.md

```markdown
# Progress Index

## 2026-02-15
- **파일**: `progress/progress.2026-02-15.md`
- **요약**: 포스트 카드 컴포넌트 개발 완료. TailwindCSS 토큰 적용.
- **태그**: #component #ui #tailwind

## 2026-02-10
- **파일**: `progress/progress.2026-02-10.md`
- **요약**: Drizzle ORM 스키마 13개 테이블 설계 완료.
- **태그**: #database #schema #drizzle
```

## progress/progress.YYYY-MM-DD.md

```markdown
# Progress: YYYY-MM-DD

## 작업 시간
- 시작: HH:MM
- 종료: HH:MM

## 완료 작업
- [x] 작업 1: 상세 설명
- [x] 작업 2: 상세 설명

## 발견 사항
- 기술적 인사이트나 예상치 못한 이슈

## 이슈 및 해결
- **이슈**: 문제 설명
- **해결**: 해결 방법

## 다음 단계
- [ ] 즉시 다음 작업
- [ ] 이후 작업

## 참고
- 관련 findings: `findings/findings.NNN-topic.md`
```
