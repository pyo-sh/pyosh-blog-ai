# Task 02: 게시글 검색 API

> 제목/본문 키워드 기반 게시글 검색 기능 구현

## 선행 조건

- [x] Posts API 구현 완료
- [x] Drizzle ORM 전환 완료

## 작업 항목

### 1. 검색 전략 결정

- [x] **검색 방식 비교 (findings 기록)**
  - MySQL FULLTEXT INDEX vs LIKE vs 외부 엔진(Meilisearch 등)
  - 블로그 규모 고려하여 **MySQL LIKE** 선택 → findings.014

### 2. 검색 API 구현

- [x] **`GET /api/posts` 쿼리 파라미터 확장**
  - `q` 파라미터 추가 (min:1, max:200)
  - 기존 `tagSlug`, `categoryId` 필터와 AND 조합 가능
- [x] **검색 로직 구현**
  - 제목(title) + 본문(contentMd) 대상 LIKE 검색
  - Drizzle `like()` + `or()` 함수로 구현
- [ ] **검색 결과 하이라이트 (선택)**
  - 매칭된 키워드 주변 텍스트 스니펫 반환

### 3. 스키마 & DB

- [x] **Zod 스키마 업데이트**
  - PostListQuerySchema에 `q` 파라미터 추가
- [x] **DB 인덱스 추가 (필요 시)**
  - LIKE 방식 → 추가 인덱스 불필요 (FULLTEXT 미채택)

## 검증

- [x] 키워드 검색 시 관련 게시글 반환
- [x] 빈 검색어 시 전체 목록 반환 (기존 동작 유지)
- [x] 필터 + 검색 조합 동작 확인
- [x] 통합 테스트 추가 (3건 추가, 총 19 tests 통과)
