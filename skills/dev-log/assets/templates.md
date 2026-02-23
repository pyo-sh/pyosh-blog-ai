# 파일 템플릿

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
- **관련 Issue**: #N

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

## 완료 작업
- [x] 작업 1: 상세 설명 (#Issue번호)
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

## decisions.index.md

```markdown
# Decisions Index

## 001 - 인증 전략 선택
- **파일**: `decisions/decision-001-auth-strategy.md`
- **날짜**: 2026-02-20
- **상태**: accepted
- **요약**: OAuth2 + Session 기반 인증 선택
- **키워드**: auth, OAuth, session
```

## decisions/decision-NNN-topic.md

```markdown
# Decision NNN: [제목]

## 메타데이터
- **날짜**: YYYY-MM-DD
- **상태**: draft | accepted | rejected
- **관련 Issue**: #N

## 배경
왜 이 결정이 필요한가

## 옵션 비교

### 옵션 A: [이름]
- **장점**: ...
- **단점**: ...
- **비용/복잡도**: 낮음/중간/높음

### 옵션 B: [이름]
- **장점**: ...
- **단점**: ...
- **비용/복잡도**: 낮음/중간/높음

## AI 제안
> AI가 분석한 추천 옵션과 근거

## 최종 결정
> 사용자가 확인/수정한 최종 결정 (draft 상태에서는 비워둠)

## 후속 조치
- [ ] 구현 항목 1
- [ ] 구현 항목 2
```

### 순번 규칙 (공통)
1. 해당 디렉토리의 기존 파일 확인
2. 파일명에서 순번 추출
3. 최대 순번 + 1로 새 파일 생성
