# Task 04: 게시글 시리즈/연재

> 연관 게시글을 그룹핑하여 시리즈로 관리하는 기능

## 선행 조건

- [x] Posts API 구현 완료
- [x] Drizzle ORM 전환 완료

## 작업 항목

### 1. 스키마 설계

- [ ] **series_tb 테이블 설계**
  - id, title, slug, description, createdAt, updatedAt
- [ ] **post_tb에 시리즈 연결 컬럼 추가**
  - seriesId (FK → series_tb.id, nullable)
  - seriesOrder (시리즈 내 순서, nullable)
- [ ] **Drizzle 마이그레이션 작성**

### 2. 시리즈 CRUD API

- [ ] **`GET /api/series`** — 시리즈 목록
- [ ] **`GET /api/series/:slug`** — 시리즈 상세 (소속 게시글 목록 포함)
- [ ] **`POST /api/admin/series`** — 시리즈 생성 (관리자)
- [ ] **`PATCH /api/admin/series/:id`** — 시리즈 수정 (관리자)
- [ ] **`DELETE /api/admin/series/:id`** — 시리즈 삭제 (관리자)

### 3. 게시글-시리즈 연결

- [ ] **`POST/PATCH /api/admin/posts`에 seriesId, seriesOrder 필드 추가**
- [ ] **`GET /api/posts` 응답에 시리즈 정보 포함**
- [ ] **게시글 상세에서 이전/다음 시리즈 게시글 정보 반환**

## 검증

- [ ] 시리즈 CRUD 동작 확인
- [ ] 게시글에 시리즈 연결/해제 동작
- [ ] 시리즈 내 게시글 순서 정렬 확인
- [ ] 시리즈 삭제 시 게시글 seriesId null 처리
- [ ] 통합 테스트 추가
