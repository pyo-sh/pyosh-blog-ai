# F-07: 댓글 표시 (계층형 목록, 비밀글 마스킹)

**상태:** DRAFT
**최종 수정:** 2026-03-20

---

## 1. 개요

글 상세 페이지(F-02) 하단에 댓글 섹션을 표시한다. 2단계 계층 구조(루트 + 대댓글)로 표시하며, 비밀글 마스킹, 페이지네이션, 대댓글 접기/펼치기, @멘션 하이라이팅을 지원한다.

## 2. 배경 및 동기

현재 댓글 표시 기능이 구현되어 있으나 다음 개선이 필요하다:

- 페이지네이션 없이 전체 댓글을 한 번에 로드
- 댓글 수 표시가 루트 댓글만 카운트 (대댓글 미포함)
- 비밀글 마스킹 텍스트가 영어 (`"This comment is secret."`)
- "Secret" 텍스트 뱃지를 아이콘으로 교체 필요
- 대댓글에 답글 버튼 없음 (depth-0만 답글 가능)
- @멘션(`replyToName`) 하이라이팅 부족
- 댓글 섹션 헤더가 영어/한국어 혼용 ("Comments" + "댓글")
- 삭제된 루트 댓글의 대댓글이 함께 사라지는 문제

## 3. 목표

- 루트 댓글 기준 페이지네이션을 도입한다 (역순 페이지, 10개/페이지)
- 대댓글 접기/펼치기를 지원한다 (3개 이상이면 기본 접힘)
- 댓글 수를 대댓글 포함 전체 카운트로 표시한다
- 비밀글 마스킹 텍스트를 한국어로 통일한다
- 비밀글 뱃지를 자물쇠 아이콘으로 교체한다
- 대댓글에서도 답글 작성을 가능하게 한다 (@멘션 대댓글)
- @멘션을 시각적으로 하이라이팅한다
- 게스트 비밀글 작성 직후 본인 열람을 지원한다
- 삭제된 댓글의 대댓글 표시 정책을 개선한다
- 댓글 작성 후 자동 스크롤한다

## 4. 비목표

- 3단계 이상 댓글 중첩 (DB 스키마 변경)
- 댓글 수정 기능
- 댓글 좋아요/추천
- 실시간 댓글 업데이트 (WebSocket)

---

## 5. 상세 설계

### 5.1 페이지 구조

```
┌─ 글 상세 (F-02) ──────────────────────────────┐
│ ...글 본문...                                    │
│                                                  │
├─ 댓글 섹션 ──────────────────────────────────────┤
│                                                  │
│  댓글 (12)                    ← 타이틀 + 전체 수  │
│                                                  │
│  [댓글 작성 폼]                                   │
│                                                  │
│  ┌─ 루트 댓글 ────────────────────────────────┐  │
│  │ 작성자 · 2026.03.15 · 🔒                   │  │
│  │ 비공개 메시지입니다                          │  │
│  │ [답글]                                      │  │
│  │                                             │  │
│  │ 답글 5개 ▼              ← 접힌 상태 (3개+)   │  │
│  └─────────────────────────────────────────────┘  │
│                                                  │
│  ┌─ 루트 댓글 ────────────────────────────────┐  │
│  │ 작성자 · 2026.03.18                         │  │
│  │ 댓글 본문 내용...                            │  │
│  │ [답글] [삭제]                                │  │
│  │                                             │  │
│  │  ┌─ 대댓글 ─────────────────────────────┐   │  │
│  │  │ 대댓글 작성자 · 2026.03.19            │   │  │
│  │  │ @원댓글작성자 대댓글 내용...            │   │  │
│  │  │ [답글] [삭제]                          │   │  │
│  │  └───────────────────────────────────────┘   │  │
│  │  ┌─ 대댓글 ─────────────────────────────┐   │  │
│  │  │ 다른작성자 · 2026.03.19               │   │  │
│  │  │ @대댓글작성자 또 다른 대댓글...         │   │  │
│  │  │ [답글] [삭제]                          │   │  │
│  │  └───────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────┘  │
│                                                  │
│  ┌─ Pagination ──────────────────────────────┐   │
│  │ « 1 2 3 [4] »            ← 4가 마지막(최신) │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

### 5.2 페이지네이션

#### 역순 페이지 구조

| 항목 | 설명 |
|---|---|
| 페이지 크기 | 루트 댓글 10개 |
| 페이지 1 | 가장 오래된 루트 댓글 10개 |
| 마지막 페이지 | 가장 최신 루트 댓글 |
| 기본 페이지 | 마지막 페이지 (최신 댓글 우선 표시) |
| 페이지 내 정렬 | 최신이 위, 오래된 것이 아래 (DESC) |

#### 서버 API 변경

```
GET /api/posts/:postId/comments?page={n}&limit=10
```

응답:

```typescript
interface CommentListResponse {
  data: CommentDetail[];     // 계층 구조 (루트 + replies)
  meta: {
    page: number;
    limit: number;
    totalCount: number;      // 전체 댓글 수 (대댓글 포함)
    totalRootComments: number; // 루트 댓글 수 (페이지네이션 기준)
    totalPages: number;      // ceil(totalRootComments / limit)
  };
}
```

- `page` 미지정 시 기본값: 마지막 페이지 (`totalPages`)
- 루트 댓글 기준 페이지네이션 후, 해당 루트 댓글의 대댓글은 전부 포함하여 반환
- `totalCount`는 댓글 섹션 헤더의 `댓글 (N)` 표시에 사용
- `totalRootComments`는 Pagination 컴포넌트의 `totalPages` 계산에 사용

#### 클라이언트 동작

- 초기 로드: SSR로 마지막 페이지 프리페치
- 페이지 전환: 클라이언트에서 API 호출하여 갱신
- URL 변경 없음 (댓글 페이지는 쿼리 파라미터로 관리하지 않고 컴포넌트 내부 상태)
- 페이지 전환 시 댓글 섹션 상단으로 스크롤

### 5.3 대댓글 접기/펼치기

| 조건 | 기본 상태 | UI |
|---|---|---|
| 대댓글 2개 이하 | 펼침 (기본 표시) | 대댓글 바로 표시 |
| 대댓글 3개 이상 | 접힘 | `답글 5개 ▼` 버튼 표시 |

```
답글 5개 ▼     ← 접힌 상태 (클릭하면 펼침)
답글 5개 ▲     ← 펼친 상태 (클릭하면 접음)
```

- 토글 버튼: `text-body-sm`, `text-text-3`, `hover:text-text-1`
- 삼각형 아이콘: Lucide `ChevronDown` / `ChevronUp`
- 펼침/접힘 상태는 컴포넌트 로컬 state

### 5.4 댓글 헤더

```
댓글 (12)
```

- `댓글`: `text-h2`, `text-text-1`
- `(12)`: `text-h2`, `text-text-3` — 대댓글 포함 전체 카운트
- API 응답 `meta.totalCount` 사용
- 댓글 0개일 때: `댓글 (0)`

기존의 영어 라벨 ("Comments"), 부연 설명 ("현재 N개의 루트 댓글이 등록되어 있습니다.") 삭제.

### 5.5 비밀글 마스킹

#### 마스킹 텍스트

```
변경 전: "This comment is secret." (영어)
변경 후: "비공개 메시지입니다" (한국어)
```

서버 `maskSecretContent()` 함수의 마스킹 텍스트를 변경한다.

#### 비밀글 아이콘

"Secret" 텍스트 뱃지를 Lucide `Lock` 아이콘으로 교체한다.

```tsx
{comment.isSecret && (
  <Lock
    size={14}
    className="text-text-4"
    aria-label="비밀글"
  />
)}
```

- 아이콘만 표시, 텍스트 없음
- `aria-label="비밀글"`로 접근성 보장
- 작성자/관리자가 볼 때도 아이콘은 표시 (비밀글임을 인지)

#### 마스킹 권한

| 조회자 | 볼 수 있는가 |
|---|---|
| 관리자 | 원문 표시 |
| OAuth 작성자 본인 | 원문 표시 |
| 게스트 작성자 (작성 직후) | 원문 표시 (sessionStorage) |
| 그 외 | "비공개 메시지입니다" |

### 5.6 게스트 비밀글 본인 열람

서버 변경 없이 클라이언트에서 처리한다.

```
1. 게스트가 비밀 댓글 작성
2. 서버 응답에 전체 내용 포함 (createComment 응답)
3. sessionStorage에 저장: { [commentId]: body }
4. 댓글 목록 렌더링 시:
   - isSecret && body === "비공개 메시지입니다" && sessionStorage에 ID 존재
   → 저장된 원문으로 대체 표시
5. 브라우저 탭 닫으면 자동 소멸
```

- 보안 위험 없음: sessionStorage는 동일 탭에서만 접근 가능
- 서버는 여전히 마스킹된 데이터만 반환 (GET 요청 시)
- 페이지 새로고침 시에도 유지 (같은 탭이면 sessionStorage 유지)

### 5.7 @멘션 하이라이팅

대댓글(depth-1)이 다른 대댓글에 답할 때 `replyToName` 필드가 설정된다. UI에서 이를 하이라이팅한다.

```tsx
{comment.replyToName && (
  <span className="font-medium text-primary-1">
    @{comment.replyToName}
  </span>
)}
```

**표시 위치**: 댓글 본문 맨 앞에 인라인으로 표시. 본문 텍스트와 같은 줄에서 자연스럽게 이어진다.

```
대댓글작성자 · 2026.03.19
@원댓글작성자 대댓글 본문 내용...
```

- `@{name}`: `text-primary-1`, `font-bold`, 나머지 font 속성은 본문과 동일
- 현재 구현에서는 `rounded-full bg-background-2 px-3 py-1` pill 스타일 → 인라인 텍스트로 변경

### 5.8 대댓글 답글 버튼

현재 `canReply`가 `depth === 0`일 때만 true. depth-1 대댓글에도 답글 버튼을 추가한다.

```
대댓글의 답글 → 같은 부모(depth-0) 아래에 depth-1로 생성
             → replyToCommentId = 대상 대댓글 ID
             → replyToName = 대상 대댓글 작성자명
```

DB 스키마 변경 없음. `replyToCommentId`와 `replyToName` 필드가 이미 이를 지원한다. 서버의 depth 제한 (`parent.depth >= 1` 시 거부)은 유지하되, `parentId`는 항상 루트 댓글 ID를 전달한다.

### 5.9 삭제된 댓글 표시 정책

#### 서버 변경

현재 서버는 `status="active"` 댓글만 조회한다. 대댓글이 있는 삭제된 루트 댓글을 표시하려면 조회 로직을 변경해야 한다.

```
변경 전: WHERE status = 'active' AND deleted_at IS NULL
변경 후: 삭제된 댓글도 조회하되, 대댓글이 있는 경우에만 포함
```

| 상황 | 표시 |
|---|---|
| 삭제된 루트 댓글 + 대댓글 있음 | "삭제된 댓글입니다." + 대댓글 표시 |
| 삭제된 루트 댓글 + 대댓글 없음 | 표시하지 않음 |
| 삭제된 대댓글 + 하위 대댓글 있음 | "삭제된 댓글입니다." + 하위 대댓글 표시 |
| 삭제된 대댓글 + 하위 대댓글 없음 | 표시하지 않음 |

여기서 "하위 대댓글"은 같은 부모 아래에서 `replyToCommentId`로 해당 댓글을 참조하는 댓글을 의미한다. DB depth는 동일하게 1이지만, `replyToCommentId` 체인으로 논리적 참조 관계를 판별한다.

#### 삭제된 댓글 UI

```
┌─ 삭제된 루트 댓글 ──────────────────┐
│ (회색) 삭제된 댓글입니다.             │  ← 작성자, 날짜 미표시
│                                     │
│  ┌─ 대댓글 (활성) ───────────────┐  │
│  │ 작성자 · 날짜                  │  │
│  │ 대댓글 내용...                 │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

- 삭제된 댓글: `text-text-4`, `italic`, 작성자/날짜/버튼 미표시
- 답글/삭제 버튼 미표시
- 서버에서 `status: "deleted"` 기반으로 마스킹 (body 데이터는 DB에 보존되나 공개 API에서는 "삭제된 댓글입니다"로 대체)

### 5.10 댓글 작성 후 자동 스크롤

- 루트 댓글 작성 후: 작성된 댓글이 마지막 페이지에 추가되므로, 마지막 페이지로 이동 + 해당 댓글 위치로 스크롤
- 대댓글 작성 후: 해당 대댓글 위치로 스크롤
- `scrollIntoView({ behavior: 'smooth', block: 'center' })` 사용
- 접힌 대댓글에 답글 작성 시 자동으로 펼침 + 스크롤

### 5.11 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `features` | `comment-section/ui/comment-list.tsx` | 댓글 섹션 컨테이너 (페이지네이션, 상태 관리) |
| `features` | `comment-section/ui/comment-item.tsx` | 개별 댓글 (비밀글 아이콘, @멘션, 접기/펼치기) |
| `features` | `comment-section/lib/guest-secret-store.ts` | sessionStorage 게스트 비밀글 저장/조회 |
| `entities` | `comment/api.ts` | `fetchComments(postId, page?, limit?)` |
| `entities` | `comment/model.ts` | `Comment`, `CommentListResponse` 타입 |
| `shared` | `ui/libs/pagination.tsx` | 페이지네이션 (F-01 공유) |

### 5.12 데이터 흐름

```
PostDetailPage (Server Component)
  └─ fetchComments(postId) → 마지막 페이지 프리페치
  └─ initialComments, initialMeta → CommentList에 전달

CommentList (Client Component)
  ├─ 페이지 전환 → clientFetch → GET /api/posts/:postId/comments?page=N&limit=10
  ├─ 댓글 작성 → createComment → 마지막 페이지로 이동 + 스크롤
  ├─ 대댓글 작성 → createComment → 대댓글 펼침 + 스크롤
  ├─ 게스트 비밀글 작성 → sessionStorage 저장
  └─ 렌더링 시 sessionStorage 확인 → 마스킹 해제
```

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| GET | `/api/posts/:postId/comments?page={n}&limit=10` | 댓글 목록 (계층) | 페이지네이션 파라미터 추가, 응답에 meta 포함 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `CommentService.getCommentsByPostId()` | `page`/`limit` 파라미터 지원, 루트 댓글 기준 페이지네이션 |
| `CommentService.getCommentsByPostId()` | 삭제된 댓글도 조회 (대댓글 존재 시) |
| `CommentService.getCommentsByPostId()` | 응답에 `meta` 포함 (`total`, `totalRootComments`, `totalPages`) |
| `maskSecretContent()` | 마스킹 텍스트 `"비공개 메시지입니다"` 로 변경 |
| 댓글 조회 정렬 | 페이지 내 DESC 정렬 (최신이 위) |

### 응답 데이터

```typescript
interface CommentDetail {
  id: number;
  postId: number;
  parentId: number | null;
  depth: number;
  body: string;
  isSecret: boolean;
  status: "active" | "deleted";
  author: CommentAuthor;
  replyToName: string | null;
  replies: CommentDetail[];
  createdAt: string;
  updatedAt: string;
}

interface CommentAuthor {
  type: "oauth" | "guest";
  id?: number;
  name: string;
  email?: string;
  avatarUrl?: string;
}

interface CommentListResponse {
  data: CommentDetail[];
  meta: {
    page: number;
    limit: number;
    totalCount: number;
    totalRootComments: number;
    totalPages: number;
  };
}
```

## 7. 수용 기준

- [ ] 루트 댓글 기준 10개 단위 페이지네이션이 동작한다
- [ ] 기본 페이지가 마지막 페이지(최신 댓글)이다
- [ ] 페이지 내 정렬이 최신순(DESC)이다
- [ ] 대댓글 3개 이상일 때 기본 접힌 상태이고, "답글 N개" 토글로 펼칠 수 있다
- [ ] 대댓글 2개 이하일 때 기본 펼침 상태이다
- [ ] 댓글 헤더에 "댓글 (N)" 형태로 대댓글 포함 전체 수가 표시된다
- [ ] 비밀글이 "비공개 메시지입니다"로 마스킹된다
- [ ] 비밀글에 자물쇠 아이콘이 표시된다 (`aria-label="비밀글"`)
- [ ] 게스트 비밀글 작성 직후 본인이 원문을 볼 수 있다 (같은 탭)
- [ ] @멘션이 본문 맨 앞에 `text-primary-1 font-bold`로 하이라이팅된다
- [ ] 대댓글에서도 답글 버튼이 표시되고, 같은 부모 아래 depth-1로 생성된다
- [ ] 삭제된 댓글은 대댓글이 있을 때만 "삭제된 댓글입니다." 표시된다
- [ ] 삭제된 댓글에 대댓글이 없으면 표시되지 않는다
- [ ] 댓글/대댓글 작성 후 해당 위치로 자동 스크롤된다
- [ ] `commentStatus: open`이면 댓글 영역이 정상 표시된다
- [ ] `commentStatus: locked`이면 기존 댓글만 표시되고, 헤더에 "댓글이 잠겼습니다" 안내가 표시된다
- [ ] `commentStatus: disabled`이면 댓글 영역 전체가 숨겨진다
- [ ] 다크모드 자동 적용
- [ ] 접근성: 시맨틱 마크업, 자물쇠 아이콘 aria-label (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 댓글 0개 | "첫 댓글을 남겨 보세요." 메시지, 헤더 "댓글 (0)" |
| 페이지 번호 초과 | 마지막 페이지로 폴백 |
| 댓글 작성 중 페이지 전환 | 작성 폼 상태 유지 (컴포넌트 내부 state) |
| 대댓글만 있고 루트 댓글 삭제 | "삭제된 댓글입니다." + 대댓글 표시 |
| 루트 댓글 + 대댓글 모두 삭제 | 표시하지 않음 |
| 매우 긴 댓글 본문 | `whitespace-pre-wrap`으로 줄바꿈, 최대 길이 2000자 (서버 검증) |
| sessionStorage 비활성화 | 게스트 비밀글 본인 열람 불가 (기능 저하, 에러 없음) |
| 페이지네이션 중 새 댓글 추가 | 마지막 페이지로 이동 + 새 댓글 반영 |

## 9. 의존성

- F-02 글 상세 (배치 위치)
- F-08 댓글 작성/삭제 (작성/삭제 인터랙션)
- F-23 글 메타데이터 폼 (commentStatus 필드 정의)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
