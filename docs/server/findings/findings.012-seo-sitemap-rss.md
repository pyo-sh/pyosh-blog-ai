# Findings 012: SEO XML Route 설계 (Sitemap + RSS)

## 배경

Task 02에서 `/sitemap.xml`, `/rss.xml`을 Fastify 라우트로 직접 생성해야 했고, 추가 패키지 없이 문자열 기반 XML 생성을 요구했다.

## 결정 사항

1. `src/routes/seo/seo.route.ts` 단일 라우트 파일로 구현
2. DB 조회 조건을 `status='published' AND visibility='public' AND deleted_at IS NULL`로 통일
3. `BASE_URL`은 `env.BASE_URL` 우선, 없으면 `CLIENT_URL` fallback
4. RSS 메타는 `BLOG_TITLE`, `BLOG_DESCRIPTION` 환경변수 기본값 제공
5. XML 특수문자 이스케이프 유틸을 라우트 내부에 포함

## 이유

- 기존 코드베이스가 라우트 중심 구조이며 SEO용 별도 서비스 계층 이점이 작았다.
- 공개 컨텐츠만 인덱싱해야 SEO/보안 요구를 동시에 충족한다.
- 배포 환경별 도메인 차이를 흡수하려면 `BASE_URL` 주입이 필요하다.
- 외부 라이브러리 없이도 RSS 2.0/사이트맵 요구를 충족할 수 있다.

## 적용 결과

- `GET /sitemap.xml`: 정적 페이지 + 카테고리 페이지 + 공개 게시글 URL 생성
- `GET /rss.xml`: 최신 20개 공개 게시글 RSS 2.0 피드 생성
- 두 엔드포인트 모두 `Cache-Control: public, max-age=3600` 적용
