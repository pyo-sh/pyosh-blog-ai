# DB schema + migrations

> Drizzle ORM 기반 13개 테이블 스키마 정의 및 마이그레이션 설정

## SPEC 참조

- `docs/server/api-spec.md` > DB 스키마 요약, 각 엔드포인트 응답 스키마
- `docs/architecture.md` > 기술 스택 (Drizzle ORM + MySQL)

## 상세

### 테이블 목록 (13개)

| 테이블 | 용도 |
|---|---|
| `admin_tb` | 관리자 계정 (username + argon2) |
| `user_tb` | OAuth 사용자 (레거시) |
| `oauth_account_tb` | OAuth 계정 (provider별 관리) |
| `session_tb` | 세션 저장소 |
| `image_tb` | 이미지 (레거시) |
| `asset_tb` | 에셋 (현재 이미지 업로드 시스템) |
| `category_tb` | 카테고리 (트리 구조, self-FK) |
| `tag_tb` | 태그 |
| `post_tb` | 게시글 (소프트 삭제 지원) |
| `post_tag_tb` | 게시글-태그 M:N |
| `comment_tb` | 댓글 (계층형, 비밀글) |
| `guestbook_entry_tb` | 방명록 (계층형, 비밀글) |
| `stats_daily_tb` | 일별 조회 통계 (postId NULL = 사이트 전체) |

### 테이블 스키마 상세

API 응답 스키마에서 추론한 컬럼 정의.

#### admin_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| username | varchar | unique, not null | |
| password | varchar | not null | argon2 해시 |
| createdAt | datetime | not null, default now | |
| updatedAt | datetime | not null, on update | |
| lastLoginAt | datetime | nullable | 마지막 로그인 시각 |

#### user_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| provider | varchar | not null | github, google |
| email | varchar | nullable | |
| displayName | varchar | not null | 1-100자 |
| avatarUrl | varchar(500) | nullable | |
| createdAt | datetime | not null, default now | |
| updatedAt | datetime | not null, on update | |
| deletedAt | datetime | nullable | 소프트 삭제 |

#### oauth_account_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| userId | int | FK -> user_tb.id, not null | |
| provider | varchar | not null | google, github |
| providerAccountId | varchar | not null | 외부 계정 ID |
| createdAt | datetime | not null, default now | |

- UNIQUE(provider, providerAccountId)

#### session_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | varchar | PK | 세션 ID |
| data | text/json | not null | 세션 데이터 |
| expiresAt | datetime | not null | 만료 시각 |

#### image_tb (레거시)

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| url | varchar | not null | 이미지 경로 |
| createdAt | datetime | not null, default now | |

#### asset_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| url | varchar | not null | `/uploads/2026/02/uuid.png` 형식 |
| mimeType | varchar | not null | image/jpeg, image/png 등 |
| sizeBytes | int | not null | 파일 크기 |
| width | int | nullable | 이미지 너비 |
| height | int | nullable | 이미지 높이 |
| createdAt | datetime | not null, default now | |

#### category_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| parentId | int | FK -> category_tb.id, nullable | self-FK (트리 구조) |
| name | varchar(50) | not null | 1-50자 |
| slug | varchar | unique, not null | URL 슬러그 |
| sortOrder | int | not null, default 0 | 정렬 순서 |
| isVisible | boolean | not null, default true | 숨김 여부 |
| createdAt | datetime | not null, default now | |
| updatedAt | datetime | not null, on update | |

#### tag_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| name | varchar(30) | unique, not null | |
| slug | varchar | unique, not null | |

#### post_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| categoryId | int | FK -> category_tb.id, not null | |
| title | varchar(200) | not null | 1-200자 |
| slug | varchar | unique, not null | URL 슬러그 |
| contentMd | text | not null | 마크다운 본문 |
| summary | varchar(200) | nullable | 요약 (최대 200자) |
| description | varchar(300) | nullable | 설명 (최대 300자) |
| thumbnailUrl | varchar | nullable | 썸네일 URL |
| visibility | enum('public','private') | not null, default 'public' | |
| status | enum('draft','published','archived') | not null, default 'draft' | |
| commentStatus | enum('open','locked','disabled') | not null, default 'open' | |
| isPinned | boolean | not null, default false | |
| publishedAt | datetime | nullable | 발행일 |
| contentModifiedAt | datetime | nullable | 본문 수정일 |
| createdAt | datetime | not null, default now | |
| updatedAt | datetime | not null, on update | |
| deletedAt | datetime | nullable | 소프트 삭제 |

#### post_tag_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| postId | int | FK -> post_tb.id, not null | |
| tagId | int | FK -> tag_tb.id, not null | |

- PK(postId, tagId) 또는 UNIQUE(postId, tagId)

#### comment_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| postId | int | FK -> post_tb.id, not null | |
| parentId | int | FK -> comment_tb.id, nullable | 부모 댓글 (depth=0) |
| replyToCommentId | int | FK -> comment_tb.id, nullable | 대상 댓글 추적 |
| depth | int | not null, default 0 | 최대 1 |
| body | text | not null | 1-2000자 |
| isSecret | boolean | not null, default false | 비밀글 |
| status | enum('active','deleted','hidden') | not null, default 'active' | |
| authorType | enum('oauth','guest') | not null | |
| userId | int | FK -> user_tb.id, nullable | OAuth 사용자 |
| guestName | varchar(50) | nullable | 게스트 이름 |
| guestEmail | varchar | nullable | 게스트 이메일 |
| guestPassword | varchar | nullable | 게스트 비밀번호 (해시) |
| createdAt | datetime | not null, default now | |
| updatedAt | datetime | not null, on update | |
| deletedAt | datetime | nullable | 소프트 삭제 시각 |

- 대댓글은 최대 depth 1. `parentId`는 depth=0 댓글을 가리키고, `replyToCommentId`는 같은 parent 내 대상 댓글을 추적한다.

#### guestbook_entry_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| parentId | int | FK -> guestbook_entry_tb.id, nullable | 계층형 |
| body | text | not null | 1-2000자 |
| isSecret | boolean | not null, default false | 비밀글 |
| status | enum('active','deleted','hidden') | not null, default 'active' | |
| authorType | enum('oauth','guest') | not null | |
| userId | int | FK -> user_tb.id, nullable | |
| guestName | varchar(50) | nullable | |
| guestEmail | varchar | nullable | |
| guestPassword | varchar | nullable | 해시 |
| createdAt | datetime | not null, default now | |
| updatedAt | datetime | not null, on update | |
| deletedAt | datetime | nullable | |

#### stats_daily_tb

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | int | PK, auto increment | |
| postId | int | FK -> post_tb.id, nullable | NULL = 사이트 전체 조회수 |
| date | date | not null | KST 기준 날짜 |
| pageviews | int | not null, default 0 | 페이지뷰 |
| uniques | int | not null, default 0 | 유니크 방문자 |

- UNIQUE(postId, date) - 같은 글 같은 날짜 중복 방지

### 테이블 관계 (FK)

```
admin_tb (독립)
user_tb (독립)
  └─ oauth_account_tb.userId -> user_tb.id
session_tb (독립)
image_tb (독립, 레거시)
asset_tb (독립)
category_tb.parentId -> category_tb.id (self-FK)
tag_tb (독립)
post_tb.categoryId -> category_tb.id
  └─ post_tag_tb.postId -> post_tb.id
  └─ post_tag_tb.tagId -> tag_tb.id
  └─ comment_tb.postId -> post_tb.id
  └─ stats_daily_tb.postId -> post_tb.id
comment_tb.parentId -> comment_tb.id (self-FK)
comment_tb.userId -> user_tb.id
guestbook_entry_tb.parentId -> guestbook_entry_tb.id (self-FK)
guestbook_entry_tb.userId -> user_tb.id
```

### Drizzle Kit 마이그레이션

- `drizzle.config.ts` 설정 파일
- `drizzle/` 디렉토리에 마이그레이션 파일 관리
- `npx drizzle-kit generate` 로 마이그레이션 생성
- `npx drizzle-kit migrate` 로 마이그레이션 실행

## 수용 기준

- [ ] 13개 테이블의 Drizzle ORM 스키마가 정의된다
- [ ] 모든 FK 관계가 올바르게 설정된다
- [ ] category_tb의 self-FK (parentId)가 설정된다
- [ ] comment_tb, guestbook_entry_tb의 self-FK (parentId)가 설정된다
- [ ] post_tb의 소프트 삭제 (deletedAt nullable) 지원
- [ ] comment_tb, guestbook_entry_tb의 status enum이 정의된다
- [ ] post_tag_tb의 복합 unique 제약이 설정된다
- [ ] stats_daily_tb의 (postId, date) unique 제약이 설정된다
- [ ] Drizzle Kit 설정 파일이 존재하고 마이그레이션이 실행 가능하다
- [ ] 마이그레이션으로 테이블 생성/변경이 정상 동작한다

## 의존성

- Blocked by: 없음
- Blocks: S-03, S-04~S-12

## 참고

- `image_tb`는 레거시 테이블이다. 현재 이미지 업로드는 `asset_tb`를 사용한다.
- `user_tb`는 OAuth 사용자 전용이다. v1에서 OAuth는 서버 구현만 유지하고 클라이언트는 미지원한다.
- 게스트 비밀번호(guestPassword)는 반드시 해시하여 저장한다.
- DB는 MySQL을 사용하며, mysql2 드라이버로 연결한다.
