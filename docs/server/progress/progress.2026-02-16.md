# Server Progress - 2026-02-16

## 완료: Task 01 - Stats Service & Routes 구현

### 구현 파일

- `server/src/services/stats.service.ts`
  - `incrementPageView(postId, ip)`
  - `getPostStats(postId)`
  - `getPopularPosts(limit, days)`
  - `getDashboardStats()`
- `server/src/routes/stats/stats.schema.ts`
- `server/src/routes/stats/stats.route.ts`
- `server/src/app.ts` (stats 라우트 등록)

### API 추가

- `POST /api/stats/view`
- `GET /api/stats/popular`
- `GET /api/admin/stats/dashboard`

### 문서 반영

- `docs/server/tasks/task-01-stats-service.md` 체크박스 갱신
- `docs/server/findings/findings.011-stats-service-design.md` 추가

### 검증

- `pnpm compile:types` ✅ 통과
- `pnpm lint` ✅ 통과 (기존 경고 18건 유지, 신규 에러 없음)

### 미완료 항목

- Stats API 수동 테스트 (`task-08`에서 통합 테스트 예정)

---

## 완료: Task 02 - SEO Sitemap & RSS 구현

### 구현 파일

- `server/src/routes/seo/seo.route.ts`
  - `GET /sitemap.xml`
  - `GET /rss.xml`
  - XML escape/markdown 요약 유틸 포함
- `server/src/shared/env.ts`
  - `BASE_URL` (optional)
  - `BLOG_TITLE`, `BLOG_DESCRIPTION` 기본값
- `server/src/app.ts`
  - SEO 라우트 root level 등록

### API 추가

- `GET /sitemap.xml`
- `GET /rss.xml`

### 문서 반영

- `docs/server/tasks/task-02-seo-sitemap-rss.md` 체크박스 갱신
- `docs/server/findings/findings.012-seo-sitemap-rss.md` 추가

### 검증

- `pnpm compile:types` ✅ 통과

### 미완료 항목

- `/sitemap.xml`, `/rss.xml` 실제 응답 XML 수동 검증 필요
