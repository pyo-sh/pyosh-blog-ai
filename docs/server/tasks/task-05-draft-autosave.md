# Task 05: 초안 자동 저장

> 게시글 작성 중 자동 저장 엔드포인트 구현

## 선행 조건

- [x] Posts API 구현 완료
- [ ] 클라이언트 에디터 자동 저장 UI 결정

## 작업 항목

### 1. 초안 저장 전략 결정

- [ ] **저장 방식 비교 (findings 기록)**
  - 별도 draft_tb vs post_tb에 status 컬럼 추가 (draft/published)
  - 버전 관리 필요 여부

### 2. DB 스키마 변경

- [ ] **post_tb 또는 draft_tb 스키마 수정**
  - status 컬럼 추가 또는 별도 테이블 생성
- [ ] **Drizzle 마이그레이션 작성**

### 3. API 구현

- [ ] **`PUT /api/admin/posts/:id/draft` 구현**
  - 부분 저장 지원 (title, content 등 일부 필드만)
  - 마지막 저장 시간 반환
- [ ] **`GET /api/admin/posts/drafts` 구현**
  - 초안 목록 조회
- [ ] **기존 게시글 발행 API 연동**
  - draft → published 상태 전환

## 검증

- [ ] 초안 저장 및 불러오기 동작
- [ ] 부분 필드만 저장 가능 확인
- [ ] 초안 → 발행 전환 동작
- [ ] 기존 게시글 CRUD 영향 없음 확인
- [ ] 통합 테스트 추가
