# Task 03: 관리자 댓글/방명록 관리 API

> 관리자가 전체 댓글과 방명록을 조회/관리할 수 있는 어드민 API

## 선행 조건

- [x] Comments API 구현 완료
- [x] Guestbook API 구현 완료
- [x] Admin 인증 구현 완료

## 작업 항목

### 1. 관리자 댓글 목록 API

- [x] **`GET /api/admin/comments` 구현**
  - 전체 댓글 목록 (flat, 비밀글 마스킹 없음)
  - 페이지네이션 지원
  - 필터: 게시글 ID, authorType, startDate, endDate
- [x] **`DELETE /api/admin/comments/:id` 구현**
  - 관리자 권한으로 댓글 삭제

### 2. 관리자 방명록 목록 API

- [x] **`GET /api/admin/guestbook` 구현**
  - 전체 방명록 목록 (flat, 비밀글 마스킹 없음)
  - 페이지네이션 지원
  - 필터: authorType, startDate, endDate
- [x] **`DELETE /api/admin/guestbook/:id` 구현**
  - 관리자 권한으로 방명록 삭제

### 3. 공통

- [x] **Zod 스키마 정의**
  - AdminCommentListQuerySchema
  - AdminGuestbookListQuerySchema
- [x] **라우트 등록**
  - requireAdmin 가드 적용

## 검증

- [x] 관리자 인증 없이 접근 시 403
- [x] 페이지네이션 동작 확인
- [x] 필터 조합 동작 확인 (postId, authorType)
- [x] 삭제 후 목록 반영 확인
- [x] 통합 테스트 추가 (댓글 4건 + 방명록 4건)
