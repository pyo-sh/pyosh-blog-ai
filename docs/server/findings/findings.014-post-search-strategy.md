# Findings 014: 게시글 검색 전략 (MySQL LIKE)

**날짜**: 2026-02-22
**태그**: #search #mysql #like #drizzle

## 📝 요약

개인 블로그 규모에서 MySQL LIKE로 제목+본문 키워드 검색을 구현하는 것이 최적이라고 판단.

## 🎯 목표

GET /api/posts?q=keyword 파라미터로 게시글 제목과 본문을 동시에 검색하는 기능 구현.

## 🔧 기술 선택

### MySQL LIKE 선택 이유

| 방식 | 장점 | 단점 | 적합한 규모 |
|------|------|------|------------|
| **LIKE** | 추가 설정 없음, 즉시 동작 | 인덱스 미활용, Full scan | 수천 건 이하 |
| FULLTEXT INDEX | 인덱스 활용, 빠름 | 마이그레이션 필요, 한국어 형태소 분석기 별도 설정 | 수만 건 이상 |
| Meilisearch | 고성능, 풍부한 기능 | 외부 서비스 운영, 동기화 필요 | 수십만 건 이상 |

**선택**: MySQL LIKE

- 블로그 규모(수백~수천 개): LIKE로 충분
- 외부 서비스 의존성 증가 없음
- FULLTEXT 전환은 추후 필요 시 마이그레이션으로 가능

## 🏗️ 구현 패턴

```typescript
// post.service.ts - getPostList()
if (query.q) {
  const term = `%${query.q}%`;
  conditions.push(
    or(like(postTable.title, term), like(postTable.contentMd, term))!,
  );
}
```

- Drizzle의 `like()` + `or()` 함수 사용
- 제목(title) OR 본문(contentMd) 양쪽 검색
- 기존 categoryId, tagSlug, status, visibility 필터와 AND로 조합 가능

### 스키마 변경 (post.schema.ts)

```typescript
PostListQuerySchema에 추가:
  q: z.string().min(1).max(200).optional(),
```

- min(1): 빈 문자열 허용 안 함 (빈 q는 undefined와 동일하게 전체 반환)
- max(200): 지나치게 긴 검색어 방지

## 🐛 이슈 & 해결

- `or()` 함수의 반환 타입이 `SQL | undefined`라 `!` non-null assertion 필요
- Drizzle import에 `like`, `or` 추가 필요

## 🎓 교훈

- 규모에 맞는 기술 선택이 중요. 과도한 설계는 운영 복잡도만 증가
- FULLTEXT 전환이 필요해지면 DB 마이그레이션 + `match()` 함수로 교체 가능

## 📚 참고 자료

- Drizzle ORM 공식 문서: like, or 함수
