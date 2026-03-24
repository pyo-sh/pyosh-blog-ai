# F-08: 댓글 작성/삭제 (게스트 폼, 대댓글, 비밀번호 삭제)

**상태:** DRAFT
**최종 수정:** 2026-03-20

---

## 1. 개요

글 상세 페이지(F-02)의 댓글 섹션(F-07)에서 댓글 작성과 삭제 인터랙션을 처리한다. OAuth/게스트 분기 폼, 대댓글 작성, 비밀글 토글, 삭제 확인 모달, 관리자 hard delete를 포함한다.

## 2. 배경 및 동기

현재 댓글 작성/삭제 기능이 구현되어 있으나 다음 개선이 필요하다:

- 게스트 폼에 이메일 필드가 있으나 표시 용도가 없음 (OAuth만 이메일 사용)
- 비밀글 토글이 체크박스 형태 - 자물쇠 아이콘 토글로 F-07과 일관성 필요
- OAuth 댓글 삭제 시 확인 모달 없이 즉시 삭제
- 관리자 hard delete 기능 없음 (soft delete만)
- Rate limit(429) 에러에 대한 사용자 피드백 불명확
- 글자 수 카운터 없음
- 폼 라벨이 영어/한국어 혼용 ("Comment", "Reply" 등)
- 대댓글 있는 댓글 삭제 시 안내 없음

## 3. 목표

- 게스트 폼에서 이메일 필드를 제거한다
- 비밀글 토글을 자물쇠 아이콘으로 교체한다
- OAuth 삭제에도 확인 모달을 추가한다
- 관리자 hard delete를 추가한다 (cascade 삭제 + 경고)
- Rate limit 에러를 Toast로 표시한다
- 글자 수 카운터를 추가한다
- 폼 라벨을 한국어로 통일한다
- 대댓글 있는 댓글 삭제 시 안내 문구를 추가한다
- 작성 성공 후 게스트 프로필(이름/비밀번호) 유지 동작을 유지한다

## 4. 비목표

- 댓글 수정 기능
- 게스트 프로필 localStorage 저장
- 페이지 이탈 경고
- 마크다운 입력 지원

---

## 5. 상세 설계

### 5.1 댓글 작성 폼

#### 폼 위치

댓글 섹션 상단에 항상 표시. 대댓글 폼은 대상 댓글 아래에 인라인 표시.

#### 게스트 폼 필드

```
변경 전: 이름 / 이메일 / 비밀번호 (3열)
변경 후: 이름 / 비밀번호 (2열)
```

| 필드 | 타입 | 필수 | 검증 | 비고 |
|---|---|---|---|---|
| 이름 | text | O | 1-50자 | placeholder: "홍길동" |
| 비밀번호 | password | O | 4자 이상 | placeholder: "삭제 시 필요합니다" |
| 본문 | textarea | O | 1-2000자 | 글자 수 카운터 표시 |
| 비밀글 | toggle | - | - | 자물쇠 아이콘 토글 |

서버 스키마의 `guestEmail`은 nullable로 유지하되, 클라이언트 폼에서 제거한다.

#### OAuth 폼 필드

| 필드 | 타입 | 필수 | 검증 | 비고 |
|---|---|---|---|---|
| 본문 | textarea | O | 1-2000자 | 글자 수 카운터 표시 |
| 비밀글 | toggle | - | - | 자물쇠 아이콘 토글 |

"로그인된 계정으로 댓글을 작성합니다." 안내 표시.

#### 글자 수 카운터

```
┌─ 본문 ───────────────────────────┐
│                                   │
│ 댓글 내용...                       │
│                                   │
└───────────────────────────────────┘
                          1234/2000   ← 우하단
```

- `text-body-xs`, `text-text-4`
- 1500자 이상: `text-warning-1` (경고색)
- 2000자 도달: `text-negative-1` (에러색)
- `maxLength={2000}`으로 입력 자체 제한

### 5.2 비밀글 토글

체크박스 + 텍스트 형태에서 자물쇠 아이콘 토글로 변경한다.

```
변경 전: [✓] 비밀 댓글로 작성
변경 후: 🔒 비밀 댓글        ← 아이콘 + 텍스트, 클릭 시 토글
```

```tsx
<button
  type="button"
  onClick={() => setIsSecret(!isSecret)}
  className={cn(
    "inline-flex items-center gap-2 text-body-sm transition-colors",
    isSecret ? "text-primary-1" : "text-text-4"
  )}
  aria-pressed={isSecret}
  aria-label={isSecret ? "비밀 댓글 해제" : "비밀 댓글로 작성"}
>
  {isSecret ? <Lock size={16} /> : <Unlock size={16} />}
  비밀 댓글
</button>
```

- 활성: `text-primary-1` + `Lock` 아이콘
- 비활성: `text-text-4` + `Unlock` 아이콘
- `aria-pressed`로 접근성 지원

### 5.3 폼 라벨 한국어 통일

| 변경 전 | 변경 후 |
|---|---|
| eyebrow: "Comment" / "Reply" | "댓글" / "답글" |
| title: 유지 (이미 한국어) | 유지 |
| description: "이름, 이메일, 비밀번호를 입력하면..." | "이름과 비밀번호를 입력하면 게스트 댓글을 작성할 수 있습니다." |

### 5.4 대댓글 작성

F-07에서 대댓글(depth-1)에도 답글 버튼이 추가되었다. 답글 폼 동작:

```
대댓글의 답글 버튼 클릭
  → 해당 대댓글 아래에 인라인 폼 표시
  → parentId: 루트 댓글 ID (depth-0)
  → replyToCommentId: 대상 대댓글 ID
  → 폼 타이틀: "{대상작성자}님에게 답글 남기기"
  → 작성 완료 시 같은 부모 아래 depth-1로 생성, @멘션 설정
```

동시에 하나의 답글 폼만 표시. 다른 댓글의 답글 버튼 클릭 시 이전 폼 닫힘.

### 5.5 작성 후 동작

| 동작 | 처리 |
|---|---|
| 본문 초기화 | `setBody("")` |
| 비밀글 토글 초기화 | `setIsSecret(false)` |
| 게스트 프로필 | 유지 (이름/비밀번호 그대로) |
| 답글 폼 | 닫힘 |
| 스크롤 | 작성된 댓글 위치로 자동 스크롤 (F-07) |
| 게스트 비밀글 | sessionStorage에 `{commentId: body}` 저장 (F-07) |

### 5.6 삭제 - 일반 사용자

#### OAuth 삭제

```
변경 전: 삭제 버튼 클릭 → 즉시 API 호출
변경 후: 삭제 버튼 클릭 → 확인 모달 → API 호출
```

확인 모달:

```
┌─ 댓글 삭제 ────────────────────────┐
│                                     │
│ 로그인된 계정으로 작성한 댓글을       │
│ 삭제합니다.                          │
│                                     │
│ (대댓글이 있는 경우)                  │
│ ⚠ 대댓글이 있는 댓글입니다.           │
│   삭제 후에도 대댓글은 유지됩니다.     │
│                                     │
│ [삭제]  [취소]                       │
└─────────────────────────────────────┘
```

#### 게스트 삭제

기존 비밀번호 입력 모달 유지. 대댓글 안내 추가:

```
┌─ 댓글 삭제 ────────────────────────┐
│                                     │
│ 작성 시 사용한 비밀번호를 입력하면    │
│ 댓글을 삭제할 수 있습니다.           │
│                                     │
│ (대댓글이 있는 경우)                  │
│ ⚠ 대댓글이 있는 댓글입니다.           │
│   삭제 후에도 대댓글은 유지됩니다.     │
│                                     │
│ 비밀번호: [____________]             │
│                                     │
│ [삭제]  [취소]                       │
└─────────────────────────────────────┘
```

- 대댓글 안내: `text-warning-1`, 삼각형 경고 아이콘
- 대댓글이 없으면 안내 미표시

#### Soft delete 동작

기존과 동일: `status="deleted"`, `body=""`, `deletedAt` 설정.

### 5.7 삭제 - 관리자 hard delete

#### API 변경

```
DELETE /api/admin/comments/:id?action=soft_delete
DELETE /api/admin/comments/:id?action=hard_delete
```

| 파라미터 | 동작 |
|---|---|
| `action=soft_delete` | soft delete (status 변경) |
| `action=hard_delete` | DB에서 완전 삭제, 대댓글 cascade 삭제 |

#### 서버 로직

```
1. commentId로 댓글 조회
2. action=hard_delete인 경우:
   a. 해당 댓글을 parentId로 참조하는 대댓글 전부 DELETE
   b. 해당 댓글 DELETE
   c. 트랜잭션으로 묶어 원자적 처리
3. action=soft_delete인 경우: 기존 soft delete
```

#### Admin 클라이언트 경고 모달 (F-28)

```
┌─ 댓글 영구 삭제 ────────────────────┐
│                                      │
│ ⚠ 이 작업은 되돌릴 수 없습니다.       │
│                                      │
│ (대댓글이 있는 경우)                   │
│ 이 댓글에 달린 대댓글 N개도           │
│ 함께 영구 삭제됩니다.                  │
│                                      │
│ [영구 삭제]  [취소]                    │
└──────────────────────────────────────┘
```

- "영구 삭제" 버튼: `bg-negative-1` (빨간색)
- 대댓글 수를 미리 표시하여 관리자가 판단할 수 있도록 함

### 5.8 Rate limit 에러 처리

서버 429 응답 시 Toast 메시지(F-14)로 표시한다.

```
변경 전: 폼 내 인라인 에러 메시지
변경 후: Toast 알림 "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해 주세요."
```

- Toast 타입: `warning`
- 429 외 서버 에러(400, 403, 500 등)는 기존대로 폼 내 인라인 에러 표시

### 5.9 게스트 비밀글 sessionStorage 관리

F-07에서 정의한 구조를 따른다.

```typescript
// features/comment-section/lib/guest-secret-store.ts

const STORAGE_KEY = "guest-secret-comments";
const MAX_ENTRIES = 20;

function save(commentId: number, body: string): void {
  // sessionStorage에서 기존 데이터 로드
  // 새 항목 추가
  // MAX_ENTRIES 초과 시 가장 오래된 항목 제거 (FIFO)
  // sessionStorage에 저장
}

function get(commentId: number): string | null {
  // commentId에 해당하는 원문 반환, 없으면 null
}
```

- 단일 키(`guest-secret-comments`)에 `{ [commentId]: body }` 객체 저장
- 최대 20개 제한, FIFO로 오래된 것부터 제거
- 댓글 작성 성공 후 `isSecret`이면 `save(commentId, body)` 호출

### 5.10 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `features` | `comment-section/ui/comment-form.tsx` | 댓글 작성 폼 (게스트/OAuth 분기, 비밀글 토글, 글자 수) |
| `features` | `comment-section/ui/comment-list.tsx` | 댓글 섹션 컨테이너 (삭제 모달 포함) |
| `features` | `comment-section/lib/guest-secret-store.ts` | sessionStorage 게스트 비밀글 관리 |
| `entities` | `comment/api.ts` | `createComment`, `deleteComment` |
| `entities` | `comment/model.ts` | 타입 정의 |

### 5.11 데이터 흐름

```
댓글 작성:
  CommentForm → handleSubmit
    → createComment(postId, payload) → POST /api/posts/:postId/comments
    → 성공 시:
       → 본문 초기화, 비밀글 토글 초기화
       → 게스트 프로필 유지
       → isSecret이면 sessionStorage 저장
       → 댓글 목록 갱신 (마지막 페이지로 이동)
       → 작성된 댓글 위치로 스크롤
    → 429 에러 시: Toast 표시
    → 기타 에러 시: 폼 내 인라인 에러

댓글 삭제:
  CommentItem 삭제 버튼 → 삭제 모달 표시
    → OAuth: 확인 모달
    → Guest: 비밀번호 입력 모달
    → 대댓글 있으면 안내 문구 추가
    → deleteComment(commentId, payload) → DELETE /api/comments/:id
    → 성공 시: 댓글 목록에서 status="deleted" 처리
    → 에러 시: 모달 내 에러 표시

관리자 Hard delete (F-28):
  AdminCommentItem 영구삭제 버튼 → 경고 모달 표시
    → adminDeleteComment(id, { hard: true }) → DELETE /api/admin/comments/:id?action=hard_delete
    → 성공 시: 댓글 목록에서 제거
```

## 6. API 연동

| 메서드 | 경로 | 용도 | 변경 사항 |
|---|---|---|---|
| POST | `/api/posts/:postId/comments` | 댓글 작성 | `guestEmail` 선택적 처리 |
| DELETE | `/api/comments/:id` | 댓글 삭제 (일반) | 없음 |
| DELETE | `/api/admin/comments/:id?action=hard_delete` | 댓글 삭제 (관리자) | hard delete 파라미터 추가 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| 댓글 작성 스키마 | `guestEmail`을 optional로 변경 |
| 관리자 댓글 삭제 | `hard` 쿼리 파라미터 지원, cascade 삭제 로직 |
| Rate limit 응답 | 429 응답 body에 명확한 메시지 포함 |

## 7. 수용 기준

- [ ] 게스트 폼에서 이메일 필드가 제거되었다
- [ ] 비밀글 토글이 자물쇠 아이콘 형태이다 (Lock/Unlock, `aria-pressed`)
- [ ] 글자 수 카운터가 표시된다 (1500자 경고, 2000자 에러)
- [ ] OAuth 삭제 시 확인 모달이 표시된다
- [ ] 대댓글 있는 댓글 삭제 시 안내 문구가 표시된다
- [ ] 관리자 hard delete가 동작한다 (`?action=hard_delete`)
- [ ] 관리자 hard delete 시 경고 모달에 대댓글 수가 표시된다
- [ ] 대댓글 cascade 삭제가 트랜잭션으로 처리된다
- [ ] Rate limit(429) 에러가 Toast로 표시된다
- [ ] 댓글 작성 성공 후 본문 초기화, 게스트 프로필 유지
- [ ] 게스트 비밀글 작성 시 sessionStorage에 저장된다 (최대 20개, FIFO)
- [ ] 대댓글(depth-1)에서 답글 작성 시 같은 부모 아래 depth-1로 생성된다
- [ ] 폼 라벨이 한국어로 통일되었다
- [ ] `commentStatus: locked/disabled`이면 댓글 작성 폼이 숨겨진다
- [ ] 다크모드 자동 적용
- [ ] 접근성: 비밀글 토글 aria-pressed, 모달 포커스 트랩 (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 빈 본문 제출 | "본문을 입력해 주세요." 인라인 에러 |
| 게스트 이름 미입력 | HTML required 검증 |
| 게스트 비밀번호 4자 미만 | HTML minLength 검증 |
| 본문 2000자 초과 | `maxLength` 속성으로 입력 자체 차단 |
| 429 Rate limit | Toast: "너무 많은 요청을 보냈습니다. 잠시 후 다시 시도해 주세요." |
| 삭제 대상 댓글이 이미 삭제됨 | 서버 404 → 모달 내 에러 표시 |
| 게스트 삭제 비밀번호 불일치 | 서버 403 → 모달 내 에러 표시 |
| Hard delete 중 네트워크 에러 | 모달 내 에러 표시, 재시도 가능 |
| sessionStorage 비활성화 | 게스트 비밀글 저장 실패 (기능 저하, 에러 없음) |
| 동시에 두 개의 답글 폼 | 하나만 표시 (이전 폼 닫힘) |

## 9. 의존성

- F-07 댓글 표시 (댓글 섹션 컨테이너, 페이지네이션)
- F-14 Toast 알림 (Rate limit 에러 표시)
- F-23 글 메타데이터 폼 (commentStatus 필드 정의)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
