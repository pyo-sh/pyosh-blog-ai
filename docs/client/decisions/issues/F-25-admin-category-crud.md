# [F-25] 카테고리 CRUD (생성/수정/삭제 모달)

> 관리자 카테고리 관리 페이지의 생성/수정/삭제 모달. 이름, 부모 카테고리, 공개여부를 폼으로 관리하고, 삭제 시 해당 카테고리에 속한 글을 다른 카테고리로 이동하거나 휴지통으로 이동하는 선택지를 제공한다.

## SPEC 참조

- `docs/client/specs/admin-category-crud.md`

## 와이어프레임

- `docs/client/designs/admin/admin-category.html` - 카테고리 관리 페이지 (생성/수정/삭제 모달)
- Admin 공통 셸: `docs/client/designs/admin/_admin-shell.html`
- 공통 디자인 시스템: `docs/client/designs/DESIGN_SYSTEM.md`

## 상세 설계

### 생성 모달

#### UI

```
┌─ 카테고리 추가 ──────────────────────────┐
│                                            │
│  이름:     [_______________]               │
│                                            │
│  부모:     [최상위 카테고리        ▼]      │
│                                            │
│  공개:     [v]                             │
│                                            │
│                        [취소] [추가]       │
└────────────────────────────────────────────┘
```

#### 필드

| 필드 | 타입 | 필수 | 검증 |
|---|---|---|---|
| 이름 | 텍스트 입력 | O | 1-50자, trim 적용 |
| 부모 카테고리 | 드롭다운 | X | 기본값: 최상위 (null) |
| 공개 | 체크박스 | - | 기본값: true |

#### 부모 드롭다운

- "최상위 카테고리" 옵션 (parentId = null)
- 전체 카테고리 트리를 인덴트로 표시 (F-23 동일 표기)
- `include_hidden=true`로 숨김 카테고리도 포함

#### slug 자동 생성

- 서버에서 이름 기반 자동 생성 (`generateSlug()`)
- 중복 시 접미사 추가 (`my-category-2`, `my-category-3`)
- 한글은 제거됨. 결과가 빈 문자열이면 `category-{id}`로 fallback
- 생성 후 변경 불가 (이름 변경 시에도 slug 유지)

#### sortOrder 자동 관리

- 서버에서 같은 부모 아래 최대 sortOrder + 1 자동 할당
- 생성 위치는 항상 해당 부모의 마지막

### 수정 모달

#### UI

생성 모달과 동일한 폼. 모드에 따라 제목과 버튼 라벨 변경.

```
┌─ 카테고리 수정 ──────────────────────────┐
│                                            │
│  이름:     [Frontend_______]               │
│                                            │
│  부모:     [개발                    ▼]     │
│                                            │
│  공개:     [v]                             │
│                                            │
│                        [취소] [저장]       │
└────────────────────────────────────────────┘
```

#### 부모 드롭다운 - 순환참조 방지

수정 시 부모 드롭다운에서 다음을 제외:
- 자기 자신
- 자신의 모든 자손 (재귀 수집)

```typescript
function getParentOptions(
  categories: Category[],
  editingCategory: Category,
): CategoryOption[] {
  const excludedIds = new Set([
    editingCategory.id,
    ...collectDescendantIds(editingCategory),
  ]);

  return flattenCategories(categories)
    .filter(cat => !excludedIds.has(cat.id));
}
```

#### slug 유지 정책

이름 변경 시 slug은 갱신하지 않는다. URL (`/categories/{slug}`) 안정성을 위해 최초 생성 시점의 slug을 유지한다.

### 삭제 모달

#### 하위 카테고리 존재 시

```
┌─ 삭제 불가 ──────────────────────────────┐
│                                            │
│  하위 카테고리가 있는 항목은               │
│  삭제할 수 없습니다.                       │
│                                            │
│  하위 카테고리를 먼저 삭제하거나            │
│  이동해 주세요.                            │
│                                            │
│                              [확인]        │
└────────────────────────────────────────────┘
```

- 클라이언트에서 사전 차단 (children.length > 0)
- 서버에서도 이중 검증 (409 Conflict)

#### 글이 없는 카테고리

```
┌─ 카테고리 삭제 ──────────────────────────┐
│                                            │
│  "DevOps" 카테고리를 삭제하시겠습니까?     │
│                                            │
│                      [취소] [삭제]         │
└────────────────────────────────────────────┘
```

#### 글이 있는 카테고리

```
┌─ 카테고리 삭제 ──────────────────────────────────┐
│                                                    │
│  "Backend" 카테고리에 5개의 글이 있습니다.         │
│                                                    │
│  (o) 다른 카테고리로 이동  [Frontend          ▼]   │
│  ( ) 글을 휴지통으로 이동                           │
│                                                    │
│                            [취소] [삭제]           │
└────────────────────────────────────────────────────┘
```

라디오 버튼으로 두 가지 선택지 제공:

**A. 다른 카테고리로 이동**
- 카테고리 드롭다운 표시 (삭제 대상 제외)
- 기본값: 빈 상태 (미선택)
- 대상 카테고리 미선택 시 [삭제] 버튼 비활성화
- 서버: 글의 categoryId 일괄 변경 + 카테고리 삭제 (트랜잭션)

**B. 글을 휴지통으로 이동**
- 글을 soft delete (deletedAt 설정) 후 카테고리 삭제
- 서버: 글 soft delete + 카테고리 삭제 (트랜잭션)

#### 삭제 후 네비게이션

해당 카테고리의 글 목록 페이지 (`/categories/{slug}`)에 있었다면, 삭제 후 상위 카테고리로 이동한다. 상위 카테고리가 없으면 (루트) 카테고리 관리 페이지로 이동.

### 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `features` | `category-manager/ui/category-form-modal.tsx` | 생성/수정 모달 (기존 리팩토링) |
| `features` | `category-manager/ui/category-delete-modal.tsx` | 삭제 모달 (신규 - 글 처리 옵션 포함) |
| `features` | `category-manager/ui/category-manager.tsx` | 매니저 오케스트레이션 (기존 리팩토링) |
| `entities` | `category/api.ts` | 카테고리 API (삭제 파라미터 확장) |

### 데이터 흐름

```
CategoryManager
  ├─ [추가] 버튼 → CategoryFormModal (mode="create")
  │   └─ onSubmit → POST /api/categories → 캐시 무효화
  │
  ├─ CategoryTree (F-24)
  │   ├─ 행 [수정] → CategoryFormModal (mode="edit")
  │   │   └─ onSubmit → PATCH /api/categories/:id → 캐시 무효화
  │   │
  │   └─ 행 [삭제] → 사전 검증
  │       ├─ 하위 카테고리 존재 → 차단 모달
  │       └─ 하위 없음 → CategoryDeleteModal
  │           ├─ 글 없음 → 단순 확인
  │           └─ 글 있음 → 이동/휴지통 선택
  │               └─ DELETE /api/categories/:id?action=...
  │
  └─ 에러 처리
      ├─ 폼 에러: 모달 내 표시
      └─ API 에러: 토스트
```

## API 연동

| 메서드 | 경로 | 용도 | 비고 |
|---|---|---|---|
| POST | `/api/categories` | 카테고리 생성 | 기존 |
| PATCH | `/api/categories/:id` | 카테고리 수정 | 기존 |
| DELETE | `/api/categories/:id` | 카테고리 삭제 | 쿼리 파라미터 확장 |

### 삭제 API 확장

```
# 글 없는 카테고리 삭제 (기존 동작 유지)
DELETE /api/categories/:id

# 글을 다른 카테고리로 이동 후 삭제
DELETE /api/categories/:id?action=move&moveTo=3

# 글을 휴지통으로 이동 후 삭제
DELETE /api/categories/:id?action=trash
```

#### 서버 처리 (단일 트랜잭션)

```typescript
async deleteCategory(id: number, action?: string, moveTo?: number) {
  await db.transaction(async (tx) => {
    // 1. 하위 카테고리 존재 → 409
    // 2. 글 존재 확인
    const postCount = await countPostsByCategory(tx, id);

    if (postCount > 0 && !action) {
      // 기존 동작: 409 Conflict
      throw HttpError.conflict('...');
    }

    if (action === 'move') {
      // 3a. 글을 moveTo 카테고리로 이동
      await tx.update(postTable)
        .set({ categoryId: moveTo })
        .where(eq(postTable.categoryId, id));
    } else if (action === 'trash') {
      // 3b. 글을 soft delete
      await tx.update(postTable)
        .set({ deletedAt: new Date() })
        .where(eq(postTable.categoryId, id));
    }

    // 4. 카테고리 삭제
    await tx.delete(categoryTable).where(eq(categoryTable.id, id));
  });
}
```

#### 응답

| 시나리오 | HTTP | 응답 |
|---|---|---|
| 성공 | 204 | No Content |
| 하위 카테고리 존재 | 409 | `{ error: "has_children" }` |
| 글 존재 + action 없음 | 409 | `{ error: "has_posts", postCount: N }` |
| moveTo 카테고리 미존재 | 404 | `{ error: "target_not_found" }` |
| moveTo가 자기 자신 | 400 | `{ error: "invalid_target" }` |

### 벌크 카테고리 변경 (F-21 연동)

F-21의 글 목록에서 벌크 카테고리 변경이 가능하다. `PATCH /api/admin/posts/bulk` 엔드포인트를 사용하며, 상세는 F-21 스펙 참조.

## 수용 기준

- [ ] 생성 모달에서 이름, 부모 카테고리, 공개여부를 입력할 수 있다
- [ ] 이름이 비어있으면 저장이 비활성화된다
- [ ] 생성 시 slug이 이름에서 자동 생성된다
- [ ] 생성 시 sortOrder가 해당 부모의 마지막에 자동 할당된다
- [ ] 수정 모달에서 이름, 부모, 공개여부를 변경할 수 있다
- [ ] 수정 시 부모 드롭다운에서 자기 자신과 자손이 제외된다
- [ ] 이름 변경 시 slug이 유지된다
- [ ] 하위 카테고리가 있는 카테고리는 삭제가 차단된다
- [ ] 글이 없는 카테고리는 확인 후 바로 삭제된다
- [ ] 글이 있는 카테고리 삭제 시 "다른 카테고리로 이동" / "휴지통으로 이동" 선택지가 표시된다
- [ ] "다른 카테고리로 이동" 선택 시 대상 카테고리 드롭다운이 표시된다
- [ ] 대상 카테고리 미선택 시 [삭제] 버튼이 비활성화된다
- [ ] 글 이동 + 카테고리 삭제가 단일 트랜잭션으로 처리된다
- [ ] 글 휴지통 이동 + 카테고리 삭제가 단일 트랜잭션으로 처리된다
- [ ] 삭제 후 해당 카테고리 글 목록에 있었다면 상위 카테고리로 이동한다
- [ ] API 에러 시 모달 내 에러 메시지 또는 토스트가 표시된다
- [ ] 접근성: 모달 focus trap, Esc 닫기, 폼 필드 aria-label (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| 같은 이름의 카테고리 생성 | slug에 접미사 추가 (-2, -3)로 중복 방지. 이름 자체는 중복 허용 |
| 한글만으로 이름 생성 | slug이 빈 문자열 → `category-{id}`로 fallback |
| 삭제 대상 카테고리가 이미 삭제됨 | 서버 404 → 에러 토스트 + 목록 갱신 |
| moveTo 대상 카테고리가 삭제됨 (동시 접근) | 서버 404 → 에러 토스트 |
| 수정 중 다른 사용자가 같은 카테고리 삭제 | PATCH 404 → 에러 토스트 + 목록 갱신 |
| 부모 변경으로 깊은 트리 생성 | 제한 없음 (F-24에서 인덴트로 표현) |
| 생성 직후 목록에 반영 | React Query 캐시 무효화로 즉시 반영 |

## 의존성

- Blocked by: F-24
- Blocks: 없음
