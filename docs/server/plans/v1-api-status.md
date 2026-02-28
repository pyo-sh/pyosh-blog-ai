# Server v1 API Status — Client Implementation Ready

**날짜:** 2026-02-28
**상태:** v1 Client Feature Spec에 필요한 모든 API가 구현 완료됨

---

## API 엔드포인트 현황

### Public API — 모두 구현 완료 ✅

| 엔드포인트 | 상태 | Client Phase |
|-----------|------|-------------|
| `GET /api/posts` (pagination, filter, search) | ✅ | Phase 1, 4 |
| `GET /api/posts/:slug` (with prevPost/nextPost) | ✅ | Phase 1 |
| `GET /api/categories` (tree) | ✅ | Phase 1 |
| `GET /api/tags` (with postCount) | ✅ | Phase 3 |
| `GET /api/stats/popular` | ✅ | Phase 3 |
| `POST /api/stats/view` | ✅ | Phase 3 |
| `GET /api/posts/:postId/comments` (hierarchical) | ✅ | Phase 3 |
| `POST /api/posts/:postId/comments` (guest) | ✅ | Phase 3 |
| `DELETE /api/comments/:id` (guest password) | ✅ | Phase 3 |
| `GET /api/guestbook` | ✅ | Phase 3 |
| `POST /api/guestbook` | ✅ | Phase 3 |
| `DELETE /api/guestbook/:id` | ✅ | Phase 3 |
| `/sitemap.xml` | ✅ | Phase 4 |
| `/rss.xml` | ✅ | Phase 4 |

### Admin API — 모두 구현 완료 ✅

| 엔드포인트 | 상태 | Client Phase |
|-----------|------|-------------|
| `POST /api/auth/admin/login` | ✅ | Phase 2 |
| `POST /api/auth/admin/logout` | ✅ | Phase 2 |
| `GET /api/auth/me` | ✅ | Phase 2 |
| `GET /api/auth/csrf-token` | ✅ | Phase 2 |
| `GET /api/admin/stats/dashboard` | ✅ | Phase 2 |
| `GET /api/admin/posts` (all statuses) | ✅ | Phase 2 |
| `GET /api/admin/posts/:id` | ✅ | Phase 2 |
| `POST /api/admin/posts` | ✅ | Phase 2 |
| `PATCH /api/admin/posts/:id` | ✅ | Phase 2 |
| `DELETE /api/admin/posts/:id` (soft) | ✅ | Phase 2 |
| `PUT /api/admin/posts/:id/restore` | ✅ | Phase 2 |
| `DELETE /api/admin/posts/:id/hard` | ✅ | Phase 2 |
| `POST /api/categories` | ✅ | Phase 4 |
| `PATCH /api/categories/:id` | ✅ | Phase 4 |
| `PATCH /api/categories/order` | ✅ | Phase 4 |
| `DELETE /api/categories/:id` | ✅ | Phase 4 |
| `GET /api/assets` | ✅ | Phase 4 |
| `POST /api/assets/upload` (multipart) | ✅ | Phase 4 |
| `DELETE /api/assets/:id` | ✅ | Phase 4 |
| `GET /api/admin/comments` | ✅ | Phase 4 |
| `DELETE /api/admin/comments/:id` | ✅ | Phase 4 |
| `GET /api/admin/guestbook` | ✅ | Phase 4 |
| `DELETE /api/admin/guestbook/:id` | ✅ | Phase 4 |

---

## 핵심 스키마 참조

### Pagination Meta

```json
{ "page": 1, "limit": 10, "total": 100, "totalPages": 10 }
```

> **주의:** 서버는 `total` 필드를 사용. 클라이언트 `PaginatedResponse`의 `totalCount`를 `total`로 수정 필요.

### CSRF 토큰

- `GET /api/auth/csrf-token` → `{ token: string }`
- 모든 POST/PUT/PATCH/DELETE 요청에 `x-csrf-token` 헤더 필수

### Rate Limiting

- Admin login: 5/min
- Comment creation: 10/min
- Guestbook creation: 10/min
- Stats view: 30/min

---

## 서버 미해결 이슈 (v1 비차단)

| Issue | 내용 | 우선순위 |
|-------|------|---------|
| #11 | 테스트 확대 & API 에러 표준화 | priority:3 |
| #9 | 캐싱 전략 & 조회수 중복 제거 개선 | priority:3 |
| #8 | 이미지 최적화 & 에셋 정리 | priority:3 |
| #7 | 초안 자동 저장 | priority:3 |

이들은 모두 priority:3이며 v1 클라이언트 구현을 차단하지 않음.
