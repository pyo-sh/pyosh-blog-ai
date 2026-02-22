# Findings 011: Stats Service 설계 (Task 01)

**날짜**: 2026-02-16
**태그**: #stats #drizzle #fastify #anti-abuse

## 요약

Task 01 구현을 위해 페이지뷰 집계 서비스를 설계했다. 핵심은 5분 IP 중복 차단, `stats_daily_tb`의 Upsert 집계, 최근 N일 인기글/대시보드 조회 쿼리다.

## 결정 사항

1. **중복 방지 전략**
- 저장소: 서비스 인스턴스 내부 `Map<{postId}:{ip}, timestamp>`
- 윈도우: 5분
- 동작: 5분 이내 중복 요청은 DB 갱신 없이 차단

2. **일별 집계 전략**
- 테이블: `stats_daily_tb`
- 키: `(post_id, date)` unique index (`post_date_idx`)
- 쓰기: `INSERT ... ON DUPLICATE KEY UPDATE`
- 갱신: `pageviews + 1`, `uniques + 1`

3. **인기글 집계 범위**
- 조건: 최근 N일 (`gte(date, fromDate)`)
- 대상: `published + public + deleted_at IS NULL` 게시글
- 정렬: `SUM(pageviews)` 내림차순

4. **대시보드 지표 범위**
- 조회수: 오늘/최근 7일/최근 30일
- 개수: 삭제되지 않은 게시글 수, active 상태 댓글 수

## 트레이드오프

- 인메모리 dedupe는 단일 프로세스 기준으로만 완전 동작한다.
- 다중 인스턴스 환경에서는 Redis 같은 중앙 캐시가 필요하다.
- 현재 프로젝트 단계에서는 단순성과 구현 속도를 우선해 인메모리를 채택했다.

## 관련 파일

- `server/src/services/stats.service.ts`
- `server/src/routes/stats/stats.schema.ts`
- `server/src/routes/stats/stats.route.ts`
