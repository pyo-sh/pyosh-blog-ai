# Assets API

> 에셋 관리 엔드포인트 5개 구현 (목록, 업로드, 조회, 삭제, 벌크 삭제)

## SPEC 참조

- `docs/server/api-spec.md` > Assets 섹션

## 상세

### 엔드포인트

| Method | Path | Auth | 설명 |
|---|---|---|---|
| GET | `/api/assets` | Admin | 에셋 목록 조회 (페이지네이션) |
| POST | `/api/assets/upload` | Admin | 이미지 업로드 (multipart) |
| GET | `/api/assets/:id` | - | 에셋 정보 조회 |
| DELETE | `/api/assets/:id` | Admin | 에셋 삭제 (DB + 파일) |
| DELETE | `/api/assets/bulk` | Admin | 에셋 벌크 삭제 |

#### GET `/api/assets`

**Query:** `page` (default: 1), `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "data": [{ "id": 1, "url": "/uploads/2026/02/uuid.png", "mimeType": "image/png", "sizeBytes": 12345, "width": 800, "height": 600, "createdAt": "ISO" }],
  "meta": { "page": 1, "limit": 20, "totalCount": 50, "totalPages": 3 }
}
```

#### POST `/api/assets/upload`

**Request:** `multipart/form-data`

허용 MIME 타입:
- `image/jpeg`
- `image/png`
- `image/gif`
- `image/webp`
- `image/svg+xml`

**Response 201:**
```json
{ "assets": [{ "id": 1, "url": "/uploads/2026/02/uuid.png", "mimeType": "image/png", "sizeBytes": 12345, "width": 800, "height": 600 }] }
```

업로드 제한:
- 폼 필드명: `files`
- 최대 파일 크기: 10MB
- 최대 동시 업로드 수: 5개

#### GET `/api/assets/:id`

에셋 정보를 반환한다. Public 엔드포인트.

#### DELETE `/api/assets/:id`

DB 레코드와 물리 파일을 모두 삭제한다.

#### DELETE `/api/assets/bulk`

**Request Body:**
```json
{ "ids": [1, 2, 3] }
```

- 단일 트랜잭션 (DB), 물리 파일 삭제는 best-effort

### 파일 저장소

- 로컬 파일시스템에 저장한다
- URL 형식: `/uploads/{YYYY}/{MM}/{uuid}.{ext}`
- `UPLOAD_DIR` 환경변수로 저장 경로를 설정한다 (기본값: `./uploads`)
- DB에는 경로 string만 저장하여 외부 스토리지 전환이 가능하다

## 수용 기준

- [ ] GET `/api/assets`가 페이지네이션된 에셋 목록을 반환한다
- [ ] POST `/api/assets/upload`가 multipart/form-data로 이미지를 업로드한다
- [ ] 허용되지 않은 MIME 타입은 400 에러를 반환한다
- [ ] 파일 크기가 10MB를 초과하면 413 에러를 반환한다
- [ ] 업로드된 파일이 `/uploads/{YYYY}/{MM}/{uuid}.{ext}` 형식으로 저장된다
- [ ] 이미지의 width, height 정보가 추출되어 저장된다
- [ ] DELETE `/api/assets/:id`가 DB 레코드와 물리 파일을 모두 삭제한다
- [ ] DELETE `/api/assets/bulk`가 단일 트랜잭션으로 DB 삭제를 수행한다
- [ ] 벌크 삭제 시 물리 파일 삭제는 best-effort로 처리된다
- [ ] 모든 관리자 엔드포인트가 `requireAdmin` 훅으로 보호된다

## 의존성

- Blocked by: S-03
- Blocks: 없음

## 참고

- 물리 파일 삭제 실패는 에러를 발생시키지 않는다 (best-effort). DB 레코드 삭제가 우선이다.
- SVG 파일은 width/height 추출이 불가할 수 있으므로 nullable로 처리한다.
- 파일 저장소는 현재 로컬 파일시스템이며, 향후 S3 등으로 전환 가능하도록 추상화한다.
