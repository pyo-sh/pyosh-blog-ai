# Tags API

> 태그 목록 조회 엔드포인트 1개 구현

## SPEC 참조

- `docs/server/api-spec.md` > Tags 섹션

## 상세

### 엔드포인트

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/tags` | - | 태그 목록 (공개+발행 글 기준 postCount 포함) |

#### GET `/api/tags`

**Response 200:**
```json
{
  "tags": [{ "id": 1, "name": "...", "slug": "...", "postCount": 5 }]
}
```

> 공개 발행 게시글에 사용된 태그만 포함됩니다.

### 태그 필터링 규칙

- `status=published`, `visibility=public`, `deletedAt IS NULL`인 게시글에 연결된 태그만 반환한다
- `postCount`는 위 조건을 만족하는 게시글 수이다
- `postCount`가 0인 태그는 반환하지 않는다

## 수용 기준

- [ ] GET `/api/tags`가 태그 목록을 반환한다
- [ ] 공개+발행 게시글에 사용된 태그만 포함된다
- [ ] 각 태그에 postCount가 정확히 계산된다
- [ ] postCount가 0인 태그는 반환되지 않는다
- [ ] 삭제된 게시글의 태그는 카운트에서 제외된다

## 의존성

- Blocked by: S-03
- Blocks: 없음

## 참고

- 태그 CRUD는 별도 Admin 엔드포인트 없이, 게시글 생성/수정 시 `tags` 배열을 통해 관리된다.
- 게시글 하드 삭제 시 고아 태그(다른 게시글에서 사용하지 않는 태그)가 함께 삭제된다 (S-04에서 처리).
