# SEO endpoints

> sitemap.xml과 rss.xml 엔드포인트 2개 구현

## SPEC 참조

- `docs/server/api-spec.md` > SEO 섹션
- `docs/specs/deploy-env.md` > 5.2 (BASE_URL, BLOG_TITLE, BLOG_DESCRIPTION)

## 상세

### 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/sitemap.xml` | XML 사이트맵 (Cache: 3600s) |
| GET | `/rss.xml` | RSS 2.0 피드 - 최신 20개 공개 글 (Cache: 3600s) |

#### GET `/sitemap.xml`

XML 사이트맵을 반환한다.

- Content-Type: `application/xml`
- Cache: 3600s (1시간)
- 발행된 공개 글(`status=published`, `visibility=public`, `deletedAt IS NULL`)의 URL 포함
- `GET /api/posts/slugs`와 동일한 데이터 소스를 사용할 수 있다
- 각 URL에 `lastmod` (updatedAt)를 포함한다

#### GET `/rss.xml`

RSS 2.0 피드를 반환한다.

- Content-Type: `application/rss+xml` 또는 `application/xml`
- Cache: 3600s (1시간)
- 최신 20개 공개+발행 글을 포함한다
- RSS 채널 정보:
  - `title`: `BLOG_TITLE` 환경변수 (기본값: `pyosh blog`)
  - `description`: `BLOG_DESCRIPTION` 환경변수 (기본값: `Pyosh 개발 블로그의 최신 글을 제공합니다.`)
  - `link`: `BASE_URL` 환경변수 (미지정 시 `CLIENT_URL` 파생)

### 환경 변수 (RSS 관련)

| 변수 | 타입 | 필수 | 기본값 | 용도 |
|---|---|---|---|---|
| `BASE_URL` | url | 선택 | `CLIENT_URL` 파생 | RSS 피드 기본 URL |
| `BLOG_TITLE` | string | 선택 | `pyosh blog` | RSS 채널 제목 |
| `BLOG_DESCRIPTION` | string | 선택 | `Pyosh 개발 블로그의 최신 글을 제공합니다.` | RSS 채널 설명 |

## 수용 기준

- [ ] GET `/sitemap.xml`이 XML 사이트맵을 반환한다
- [ ] 사이트맵에 발행된 공개 글의 URL이 포함된다
- [ ] 사이트맵 응답에 3600초 캐시가 적용된다
- [ ] GET `/rss.xml`이 RSS 2.0 형식의 피드를 반환한다
- [ ] RSS 피드에 최신 20개 공개+발행 글이 포함된다
- [ ] RSS 채널 정보에 BLOG_TITLE, BLOG_DESCRIPTION, BASE_URL이 반영된다
- [ ] RSS 응답에 3600초 캐시가 적용된다
- [ ] Content-Type이 올바르게 설정된다 (application/xml)

## 의존성

- Blocked by: S-04, S-08
- Blocks: 없음

## 참고

- sitemap.xml과 rss.xml은 루트 경로(`/`)에 위치한다 (`/api` 프리픽스 없음).
- 캐시는 서버 사이드에서 처리한다 (응답 헤더 `Cache-Control: public, max-age=3600`).
- RSS 피드의 각 항목에는 title, link, description(summary), pubDate(publishedAt)를 포함한다.
