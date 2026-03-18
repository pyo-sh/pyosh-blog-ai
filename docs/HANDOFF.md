# 기획 문서 작성 핸드오프

## 현재 작업

pyosh-blog v1 프로젝트의 기획 문서를 체계적으로 작성하는 중이다.
워크트리: `/workspace/.workspace/worktrees/docs-architecture-overview` (브랜치: `docs-architecture-overview`)

## 완료된 작업

### 문서 구조 확립

- `docs/architecture.md` - 프로젝트 전체 아키텍처 (7개 섹션, 확정)
- `docs/feature-index.md` - 38개 기능 마스터 목록 + 접근성 체크리스트 1개 (확정)
- 첫 커밋 완료: `docs: add architecture overview and feature index for v1`

### 완료된 기능 스펙

- `docs/client/specs/home-post-list.md` (F-01) - DRAFT 완료
- `docs/client/specs/admin-login.md` (F-19) - DRAFT 완료

## 남은 기능 스펙 작성 순서

사용자가 합의한 우선순위 순서:

| 순서 | ID | 기능 | 상태 |
|---|---|---|---|
| 1 | F-01 | 홈 - 글 목록 | DRAFT 완료 |
| 2 | F-19 | 관리자 로그인 | DRAFT 완료 |
| 3 | F-17 | 다크 모드 | **다음 작성 대상** |
| 4 | F-18 | 반응형 레이아웃 | 미작성 |
| 5 | F-12 | 에러 페이지 | 미작성 |
| 6 | F-13 | 로딩/빈 상태 | 미작성 |
| 7 | F-14 | Toast | 미작성 |
| 8 | F-04 | 태그 목록 | 미작성 |
| 9 | F-09 | 방명록 | 미작성 |
| 10+ | 나머지 | feature-index.md 참조 | 미작성 |

기반 기능(의존성 없음) 이후에는 의존성 트리 순서로 진행.

## 작업 방식 - 인터뷰 기반

**반드시 인터뷰 형식으로 진행한다.** 사용자가 직접 판단하고 피드백하여 스펙을 채운다.

### 각 기능 스펙 작성 프로세스

1. **현재 구현 탐색** - 코드베이스에서 해당 기능의 현재 상태를 Explore 에이전트로 확인
2. **인터뷰 질문** - 기능 범위, UI 구성, 데이터 흐름 등을 질문
3. **대안 제안** - 사용자 답변 후, 추가할 수 있는 대안을 카테고리별로 제시
4. **미해결 사항 확인** - 스펙에 미해결 사항이 있으면 즉시 결정을 요청
5. **스펙 파일 작성** - 확정된 내용으로 마크다운 파일 작성
6. **피드백 반영** - 사용자 수정 요청 반영

### 스펙 템플릿

```markdown
# F-XX: 기능명

**상태:** DRAFT
**최종 수정:** YYYY-MM-DD

---

## 1. 개요
## 2. 배경 및 동기
## 3. 목표
## 4. 비목표
## 5. 상세 설계
  ### 5.1 사용자 흐름
  ### 5.2 UI 구성
  ### 5.3 데이터 흐름
  ### 5.4 컴포넌트 구조 (FSD)
## 6. API 연동
## 7. 수용 기준
## 8. 에지 케이스
## 9. 의존성
## 10. 미해결 사항
```

## 핵심 설계 결정 (이미 확정)

### 전체 아키텍처

- 개인 블로그, 기술 블로그는 일부
- 대상: 관리자 1인 + 비로그인 방문자 (OAuth는 방명록/댓글 전용, post-v1)
- Client(Next.js 14) + Server(Fastify 5) + MySQL, 별도 머신
- 배포: 클라우드 서버 예정 (미확정)

### 데이터 페칭 전략

| 데이터 성격 | 전략 |
|---|---|
| 정적/읽기 전용 | Server Component SSR |
| 가변 (사용자 입력) | SSR initialData + TanStack Query |
| Admin 전용 | TanStack Query only |

### 주요 변경 사항 (기존 구현 대비)

- `/dashboard/*` → `/manage/*` 경로 전체 변경
- 관리자 로그인: 이메일 → username (DB 스키마 변경)
- 관리자 비밀번호 제한 없음 (DB 직접 seed)
- 글 카드: 태그 삭제, 조회수/댓글 수 추가, 리스트형 뷰
- summary 필드: DB 저장 (200자), 발행 시 자동 생성, 관리자 수정 가능
- 고정 글(pinned): is_pinned 컬럼 추가
- 페이지네이션: [<<-5] [<-1] 1 2 3 ... N [+1>] [+5>>], ±3 페이지 표시
- 카테고리 필터: 탭 → 드롭박스
- 댓글/방명록/검색: useState → TanStack Query 전환
- 에러 메시지: Toast 통합 (F-14)
- 목록 API 응답에서 contentMd 제외 (summary만 반환)
- 접근성: 별도 스펙이 아닌 공통 체크리스트(A-01) + 각 기능 수용 기준에 포함
- 스켈레톤: 각 기능 스펙에 포함 (F-13은 로딩 전략 원칙만)
- OAuth: 관리자에는 적용하지 않음. 방명록/댓글 사용자 전용

### 설계 우선순위

1. 보안
2. 재사용성
3. 개발자 편의

## 파일 위치

- 워크트리: `/workspace/.workspace/worktrees/docs-architecture-overview/`
- architecture.md: `docs/architecture.md`
- feature-index.md: `docs/feature-index.md`
- 기능 스펙: `docs/client/specs/`, `docs/server/specs/`, `docs/specs/`
- 접근성 체크리스트: `docs/a11y-checklist.md` (미작성)
- 실제 클라이언트 코드: `/workspace/client/src/`
- 실제 서버 코드: `/workspace/server/src/`

## 주의사항

- 문서 언어: 한국어 (기술 용어는 영어)
- 워크트리 규칙: 파일 편집은 반드시 워크트리에서 진행
- 커밋 후 merge/PR 여부는 사용자에게 확인
- 코드 탐색 시 실제 코드베이스 확인 필수 (추정 금지)
- sentence case for headers, em dash 사용 금지
