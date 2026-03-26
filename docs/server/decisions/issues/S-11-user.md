# User API

> OAuth 사용자 프로필 관리 엔드포인트 3개 구현

## SPEC 참조

- `docs/server/api-spec.md` > User 섹션

## 상세

### 엔드포인트

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/user/me` | requireAuth | 현재 OAuth 사용자 프로필 |
| PUT | `/api/user/me` | requireAuth | 사용자 프로필 수정 |
| DELETE | `/api/user/me` | requireAuth | 사용자 소프트 삭제 (세션 파기) |

#### GET `/api/user/me`

**Response 200:**
```json
{
  "id": 1, "provider": "github", "email": "...",
  "displayName": "...", "avatarUrl": "...",
  "createdAt": "ISO", "updatedAt": "ISO"
}
```

#### PUT `/api/user/me`

**Request Body:**
```json
{ "displayName": "string (1-100)", "avatarUrl": "string (URL, max 500) | null" }
```

모든 필드 optional.

**Response 200:** GET `/api/user/me`와 동일한 형식.

#### DELETE `/api/user/me`

- 소프트 삭제: `deletedAt`을 현재 시각으로 설정
- 세션을 파기한다
- 삭제된 사용자의 댓글/방명록은 유지되며, 작성자 정보가 "탈퇴한 사용자"로 표시된다

## 수용 기준

- [ ] GET `/api/user/me`가 현재 OAuth 사용자 프로필을 반환한다
- [ ] 미인증 시 401을 반환한다
- [ ] PUT `/api/user/me`가 displayName, avatarUrl을 부분 업데이트한다
- [ ] avatarUrl에 null을 전달하면 아바타가 제거된다
- [ ] DELETE `/api/user/me`가 사용자를 소프트 삭제한다
- [ ] 삭제 시 세션이 파기된다
- [ ] 모든 엔드포인트가 `requireAuth` 훅으로 보호된다

## 의존성

- Blocked by: S-03
- Blocks: 없음

## 참고

- User API는 OAuth 사용자 전용이다. Admin은 별도의 Auth 시스템을 사용한다.
- v1에서 OAuth는 서버 구현만 유지하고 클라이언트는 미지원하므로, 이 API도 서버 구현만 완료한다.
- 소프트 삭제된 사용자의 데이터(댓글, 방명록)는 유지되며, 향후 복구 가능성을 위해 보존한다.
