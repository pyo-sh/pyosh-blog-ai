# F-23: 글 메타데이터 폼 (제목, 카테고리, 태그, 상태, 썸네일)

**상태:** DRAFT
**최종 수정:** 2026-03-23

---

## 1. 개요

관리자 글 작성/수정 페이지의 메타데이터 폼. 상단 탭으로 전체/정보/글 뷰를 전환하고, 제목, 카테고리(트리 드롭다운), 태그(Chip/Badge + 자동완성), 상태/공개여부, 썸네일(다중 업로드 방식), summary, description을 관리한다. 저장/발행/보관 버튼을 분리하고, F-22 에디터의 pending 이미지 업로드를 저장 시 일괄 처리한다.

## 2. 배경 및 동기

현재 구현 상태:

- 메타데이터 6개 필드가 에디터 위에 그리드 배치 (md:2cols, xl:3cols)
- 카테고리: flat `<select>` (계층 미표시)
- 태그: 쉼표 구분 텍스트 입력 (자동완성 없음)
- 상태/공개여부: 각각 별도 `<select>`
- 썸네일: URL 직접 입력 (미리보기 없음, 에셋 연동 없음)
- 저장 버튼 1개 (저장/발행 구분 없음)
- summary, description 필드 없음

개선이 필요한 부분:

- F-22 CodeMirror 업그레이드 시 화면이 밀집되므로 탭 분리 필요
- 카테고리 계층 구조가 폼에서 보이지 않음
- 태그 입력이 직관적이지 않고 기존 태그를 참조할 수 없음
- 썸네일 업로드 경로가 불편 (에셋 페이지 → URL 복사 → 입력)
- 발행 전 확인 절차 없음
- 글 목록 미리보기 불가

## 3. 목표

- 상단 탭 (전체/정보/글)으로 편집 뷰를 분리한다
- 카테고리 드롭다운에 트리 계층을 인덴트로 표현한다
- 태그를 Chip/Badge 방식으로 입력하고, 기존 태그 자동완성을 제공한다
- 썸네일을 에셋 갤러리 선택, URL 입력, 드래그 앤 드롭, 클립보드 버튼으로 업로드한다
- 저장(초안)과 발행 버튼을 분리하고, 발행 시 확인 모달을 표시한다
- 정보 탭에서 글 목록 아이템 미리보기를 제공한다
- summary (F-01)와 description (F-30) 편집 필드를 추가한다

## 4. 비목표

- 자동 저장 (수동 저장만 지원)
- 이미지 크롭/리사이즈 (v1 범위 밖)
- 태그 추천/인기 태그 표시
- 탭 상태 기억 (localStorage, URL 등)
- 글 공동 편집

---

## 5. 상세 설계

### 5.1 탭 구조

상단에 3개 탭을 배치한다. 탭 전환은 동일 폼 내 뷰 전환이며 데이터 손실 없음.

| 탭 | 내용 | 용도 |
|---|---|---|
| 전체 | 메타데이터 필드 + CodeMirror + 프리뷰 | 기본 작업 (기존 레이아웃과 유사) |
| 정보 | 메타데이터 필드 + 글 목록 미리보기 | 메타데이터 집중 편집 |
| 글 | CodeMirror + 프리뷰 (F-22 모드 전환 포함) | 본문 집중 편집 |

#### 레이아웃

```
┌─ [전체] [정보] [글] ───────────────────────────────────────────────┐
│                                                                     │
│  (탭에 따라 내용 전환)                                              │
│                                                                     │
├─ 하단 버튼 바 ────────────────────────────────────────────────────┤
│  [보관]                                    [저장 (초안)] [발행]    │
└─────────────────────────────────────────────────────────────────────┘
```

- 하단 버튼 바는 모든 탭에서 고정 표시
- 페이지 이탈 시 dirty 상태면 `beforeunload` 경고 (탭 전환은 해당 없음)

### 5.2 메타데이터 필드

#### 필드 목록

| 필드 | 타입 | 필수 | 검증 |
|---|---|---|---|
| 제목 | 텍스트 입력 | O | 1-200자 |
| 카테고리 | 트리 드롭다운 | O | 유효한 categoryId |
| 태그 | Chip/Badge + 자동완성 | X | 개별 태그 최대 30자, 개수 제한 없음 |
| 상태 | 버튼으로 관리 (5.6 참조) | - | draft/published/archived |
| 공개여부 | 드롭다운 | O | public/private |
| 댓글 상태 | 드롭다운 | O | open/locked/disabled |
| 썸네일 | 다중 업로드 (5.5 참조) | X | 이미지 파일 또는 URL |
| Summary | 텍스트 입력 | X | 최대 200자 |
| Description | 텍스트 입력 | X | 최대 300자 |

#### 댓글 상태 (commentStatus)

| 값 | 라벨 | 동작 |
|---|---|---|
| `open` | 열림 (기본) | 댓글 작성과 표시 모두 가능 |
| `locked` | 잠김 | 기존 댓글 표시, 새 댓글 작성 불가 |
| `disabled` | 비활성 | 댓글 영역 전체 숨김 |

- DB: `posts` 테이블에 `comment_status` 컬럼 추가 (ENUM, default "open")
- F-07 댓글 표시: `disabled` → 댓글 영역 미렌더링, `locked` → 댓글 목록만 표시
- F-08 댓글 작성: `locked`/`disabled` → 댓글 폼 미표시, "댓글이 잠겨있습니다" 메시지
- F-21 벌크 작업에서도 변경 가능

### 5.3 카테고리 트리 드롭다운

`<select>`에 계층을 인덴트로 표현한다. 모든 레벨 선택 가능 (서버에 리프 노드 제한 없음).

#### 깊이 표기 규칙 (글 작성 폼 전용)

| 깊이 | 표기 | 예시 |
|---|---|---|
| 0 (루트) | 이름 그대로 | `개발` |
| 1 | 들여쓰기 | `　Frontend` |
| 2+ | 들여쓰기 + (깊이) | `　(2) Node.js` |

#### 예시

```html
<select>
  <option disabled>카테고리 선택</option>
  <option value="1">개발</option>
  <option value="2">　Frontend</option>
  <option value="3">　Backend</option>
  <option value="4">　(2) Node.js</option>
  <option value="5">　(2) Database</option>
  <option value="6">　(3) MySQL</option>
  <option value="7">일상</option>
</select>
```

#### 구현

```typescript
interface CategoryOption {
  id: number;
  name: string;
  depth: number;
}

function flattenCategoryTree(
  categories: Category[],
  depth: number = 0,
): CategoryOption[] {
  return categories.flatMap(cat => [
    { id: cat.id, name: cat.name, depth },
    ...(cat.children ? flattenCategoryTree(cat.children, depth + 1) : []),
  ]);
}

function formatCategoryLabel(option: CategoryOption): string {
  if (option.depth === 0) return option.name;
  if (option.depth === 1) return `\u3000${option.name}`;
  return `\u3000(${option.depth}) ${option.name}`;
}
```

- `\u3000` (전각 공백)으로 시각적 들여쓰기
- `include_hidden=true`로 Admin용 카테고리 포함

### 5.4 태그 Chip/Badge 입력

#### UI

```
┌─ 태그 ────────────────────────────────────┐
│ [React ×] [Next.js ×] [블로그 ×]  [입력…] │
│  ┌─ 자동완성 ──────────┐                  │
│  │ TypeScript           │                  │
│  │ TailwindCSS          │                  │
│  │ + "Tai" (새 태그)    │                  │
│  └─────────────────────┘                  │
└───────────────────────────────────────────┘
```

#### 동작

1. 텍스트 입력 시 기존 태그 목록에서 필터링하여 드롭다운 표시
2. Enter 또는 드롭다운 항목 클릭 시 Chip 추가
3. 각 Chip의 x 버튼 또는 Backspace로 삭제
4. 중복 태그 입력 시 무시

#### 자동완성 드롭다운

- `GET /api/tags`로 전체 태그 목록을 초기 로드 (태그 수가 적으므로 전체 fetch)
- 입력값으로 클라이언트 필터링 (case-insensitive 부분 매칭)
- **기존 태그**: 기본 스타일 (예: `bg-background-3 text-text-2`)
- **새 태그**: 강조 스타일 (예: `bg-primary-2/20 text-primary-1`) + "새 태그" 라벨
- 이미 추가된 태그는 드롭다운에서 제외

#### Chip 색상 구분

| 종류 | 스타일 | 설명 |
|---|---|---|
| 기존 태그 | `bg-background-3 text-text-2` | 서버에 이미 존재하는 태그 |
| 새 태그 | `bg-primary-2/20 text-primary-1` | 서버에 없는 태그 (저장 시 자동 생성) |

### 5.5 썸네일 업로드

4가지 업로드 경로를 제공한다.

#### 썸네일 UI

```
┌─ 썸네일 ────────────────────────────────────────┐
│  ┌────────────────┐                              │
│  │   미리보기      │  [에셋 갤러리] [URL 입력]   │
│  │   (이미지)      │  [클립보드]                  │
│  │                 │                              │
│  │  드래그 앤 드롭 │  [삭제]                      │
│  └────────────────┘                              │
└──────────────────────────────────────────────────┘
```

#### 업로드 경로

| 방법 | 트리거 | 설명 |
|---|---|---|
| 에셋 갤러리 | 버튼 클릭 → 갤러리 모달 | 기존 에셋에서 선택 (F-27 구현 후) |
| URL 입력 | 버튼 클릭 → 입력 필드 | 외부 이미지 URL 직접 입력 |
| 드래그 앤 드롭 | 미리보기 영역에 파일 드래그 | 파일 업로드 후 URL 설정 |
| 클립보드 | 버튼 클릭 → 대기 상태 진입 | 아래 플로우 참조 |

#### 클립보드 업로드 플로우

```
1. [클립보드] 버튼 클릭
2. 대기 상태 진입 (버튼 스타일 변경, "붙여넣기 대기 중..." 표시)
3. 사용자가 Ctrl+V (이미지 붙여넣기)
   → blob 미리보기 표시
   → [업로드] [취소] 버튼 표시
   → [업로드] 클릭 시 에셋 API로 업로드, thumbnailUrl 설정
4. 취소 조건: Esc 키, 미리보기 영역 외부 클릭, [취소] 버튼
   → 대기 상태 해제, blob 해제
```

#### 파일 검증

- 허용 형식: JPEG, PNG, GIF, WebP, SVG
- 최대 크기: 10MB
- 검증 실패 시 토스트 에러

#### 미리보기

- 썸네일이 설정되면 미리보기 영역에 이미지 표시
- 드래그 앤 드롭 / 클립보드 업로드 시 blob URL로 즉시 미리보기 → 업로드 완료 후 실제 URL로 교체
- [삭제] 버튼으로 썸네일 제거

### 5.6 저장/발행/보관 버튼

하단 버튼 바에 3개 버튼 배치.

```
┌─ 하단 버튼 바 ──────────────────────────────────────────────┐
│ [보관]                                   [저장 (초안)] [발행] │
└─────────────────────────────────────────────────────────────┘
```

#### 버튼 동작

| 버튼 | 동작 | 상태 변경 |
|---|---|---|
| 저장 (초안) | 즉시 저장, 현재 상태 유지 (신규면 draft) | status 변경 없음 |
| 발행 | 확인 모달 → 저장 + status: published | draft/archived → published |
| 보관 | 저장 + status: archived | draft/published → archived |

#### 발행 확인 모달

```
┌─ 글 발행 ─────────────────────────────┐
│                                         │
│  이 글을 발행하시겠습니까?              │
│  발행하면 공개 설정에 따라              │
│  방문자에게 노출됩니다.                 │
│                                         │
│              [취소]  [발행]              │
└─────────────────────────────────────────┘
```

#### 상태 전환 규칙

서버에 상태 전환 제한 없음. 모든 방향 허용:

```
draft ↔ published ↔ archived
draft ↔ archived
```

- published → draft: `publishedAt` 유지 (이전 발행 시각 보존)
- draft → published: `publishedAt`이 null이면 서버가 자동으로 `now()` 설정
- 이미 발행된 글 수정 시: 저장 (초안) 버튼이 "저장"으로 변경, 발행 상태 유지

#### 버튼 조건부 표시

| 현재 상태 | 저장 (초안) | 발행 | 보관 |
|---|---|---|---|
| draft | 저장 (초안) | 발행 | 보관 |
| published | 저장 | 발행 취소 (→ draft) | 보관 |
| archived | 초안으로 복원 | 발행 | - |

### 5.7 summary / description 필드

#### summary (F-01 정의)

- DB: `posts.summary` VARCHAR(200), nullable
- 용도: 글 목록 카드에 표시되는 요약
- 관리자가 수동으로 작성 가능 (선택)
- API payload: 관리자가 직접 작성한 값만 전송. 자동 추출 값은 전송하지 않음
- 서버: 발행 시 summary가 비어있으면 `contentMd`에서 plain text 200자 자동 생성 (F-01 스펙)

#### description (F-30 정의)

- DB: `posts.description` VARCHAR(300), nullable
- 용도: SEO meta description, OG description
- 관리자가 수동으로 입력 (선택)
- 서버: 자동 생성 없음. 비어있으면 클라이언트에서 contentMd 160자 폴백 (F-30 스펙)

#### 미리보기용 summary 자동 추출

summary 입력 필드가 비어있을 때, 정보 탭의 PostListItem 미리보기에 표시할 **임시 summary**를 클라이언트에서 자동 추출한다. 이 값은 미리보기 전용이며 API에 전송하지 않는다.

추출 타이밍: **CodeMirror blur 시점**

```typescript
// 미리보기 전용 상태 (폼 값과 분리)
const [previewSummary, setPreviewSummary] = useState('');

function handleEditorBlur(contentMd: string, userSummary: string) {
  if (userSummary.trim() !== '') return;  // 사용자가 직접 작성함
  const extracted = extractPlainText(contentMd, 200);
  setPreviewSummary(extracted);
}
```

- `previewSummary`는 PostListItem 미리보기에서만 사용
- 폼의 summary 입력 필드에는 반영하지 않음 (비어있는 상태 유지)
- 사용자가 summary를 직접 작성하면 해당 값이 미리보기에 표시됨
- `extractPlainText`: 마크다운 스트립 → plain text → N자 제한 (F-01, F-30 공용 유틸)

### 5.8 정보 탭 - 글 목록 미리보기

정보 탭 하단에 PostListItem와 동일한 형태의 미리보기를 표시한다.

```
┌─ 정보 탭 ─────────────────────────────────────────┐
│                                                     │
│  [메타데이터 필드들...]                             │
│                                                     │
│  ── 글 목록 미리보기 ──────────────────────────    │
│  ┌─ PostListItem 미리보기 ──────────────────────────┐  │
│  │ [썸네일]  카테고리 | 2026-03-23               │  │
│  │           제목                                 │  │
│  │           summary 텍스트 (line-clamp)          │  │
│  │           #태그1 #태그2                        │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

- 현재 폼 값을 실시간 반영 (제목, 카테고리명, 태그, 썸네일)
- summary 표시 우선순위: 사용자 입력 summary > previewSummary (에디터 blur 시 자동 추출) > "본문에서 자동 생성됩니다" placeholder
- `PostListItem` 컴포넌트를 재사용하되, 링크 동작은 비활성화 (미리보기 전용)

### 5.9 저장 플로우

```
1. 사용자가 저장/발행/보관 버튼 클릭
2. 발행인 경우: 확인 모달 표시 → 확인
3. 폼 검증 (필수 필드: 제목, 카테고리, 본문)
4. F-22 pending 이미지 일괄 업로드 (uploadPendingImages)
   → 플레이스홀더 마커를 실제 URL로 치환
5. 폼 데이터 구성 (buildPayload)
6. POST (신규) 또는 PATCH (수정) API 호출
7. 성공 시: 토스트 알림 + 글 목록 (`/dashboard/posts`)으로 이동
8. 실패 시: 에러 메시지 표시, 페이지 유지
```

#### payload 구성

```typescript
interface PostPayload {
  title: string;
  categoryId: number;
  contentMd: string;          // pending 마커 치환 완료된 본문
  tags?: string[];            // Chip에서 추출
  status?: 'draft' | 'published' | 'archived';
  visibility?: 'public' | 'private';
  commentStatus?: 'open' | 'locked' | 'disabled';
  thumbnailUrl?: string | null;
  summary?: string | null;    // 사용자 직접 입력값만. 자동 추출은 전송하지 않음
  description?: string | null;
}
```

### 5.10 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `dashboard/posts/new/page.tsx` | 글 작성 라우트 (기존) |
| `app` | `dashboard/posts/[id]/edit/page.tsx` | 글 수정 라우트 (기존) |
| `features` | `post-editor/ui/post-form.tsx` | 탭 레이아웃 + 폼 상태 관리 (리팩토링) |
| `features` | `post-editor/ui/post-meta-fields.tsx` | 메타데이터 필드 모음 (신규) |
| `features` | `post-editor/ui/category-tree-select.tsx` | 카테고리 트리 드롭다운 (신규) |
| `features` | `post-editor/ui/tag-chip-input.tsx` | 태그 Chip/Badge + 자동완성 (신규) |
| `features` | `post-editor/ui/thumbnail-uploader.tsx` | 썸네일 다중 업로드 (신규) |
| `features` | `post-editor/ui/post-card-preview.tsx` | 글 목록 미리보기 (신규) |
| `features` | `post-editor/ui/publish-confirm-modal.tsx` | 발행 확인 모달 (신규) |
| `features` | `post-editor/lib/extract-plain-text.ts` | 마크다운 → plain text 유틸 (공용) |
| `entities` | `tag/api.ts` | 태그 목록 API (기존) |
| `entities` | `asset/api.ts` | 에셋 업로드 API (기존) |

### 5.11 데이터 흐름

```
PostForm (탭 레이아웃 + 폼 상태)
  ├─ 탭: 전체
  │   ├─ PostMetaFields (제목, 카테고리, 태그, 공개여부, 썸네일, summary, description)
  │   └─ MarkdownEditor (F-22) + Preview
  │
  ├─ 탭: 정보
  │   ├─ PostMetaFields
  │   └─ PostListItemPreview (폼 값 실시간 반영)
  │
  ├─ 탭: 글
  │   └─ MarkdownEditor (F-22) + Preview (탭/모드 전환 포함)
  │
  ├─ 하단 버튼 바 (모든 탭 공통)
  │   ├─ 보관 → status: archived
  │   ├─ 저장 → 현재 status 유지
  │   └─ 발행 → PublishConfirmModal → status: published
  │
  └─ 저장 플로우
      ├─ uploadPendingImages() (F-22)
      ├─ buildPayload()
      └─ POST/PATCH API
```

---

## 6. API 연동

| 메서드 | 경로 | 용도 | 비고 |
|---|---|---|---|
| POST | `/api/admin/posts` | 글 생성 | payload에 summary, description 추가 |
| PATCH | `/api/admin/posts/:id` | 글 수정 | payload에 summary, description 추가 |
| GET | `/api/admin/posts/:id` | 글 조회 (수정 모드) | summary, description 포함 |
| GET | `/api/categories?include_hidden=true` | 카테고리 트리 | 기존 |
| GET | `/api/tags` | 태그 전체 목록 | 자동완성용 |
| POST | `/api/assets/upload` | 썸네일/이미지 업로드 | 기존 에셋 API |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| DB 스키마 | `posts` 테이블에 `summary` 컬럼 추가 (VARCHAR 200, nullable) - F-01에서 정의 |
| DB 스키마 | `posts` 테이블에 `description` 컬럼 추가 (VARCHAR 300, nullable) - F-30에서 정의 |
| POST/PATCH 스키마 | `summary`, `description` 필드를 CreatePostBodySchema, UpdatePostBodySchema에 추가 |
| GET 응답 | admin 단건 응답에 `summary`, `description` 포함 |

## 7. 수용 기준

- [ ] 상단 탭 (전체/정보/글) 전환이 동작한다
- [ ] 탭 전환 시 폼 데이터가 유지된다
- [ ] 카테고리 드롭다운에 트리 계층이 인덴트로 표현된다
- [ ] depth 0은 이름, depth 1은 들여쓰기, depth 2+는 들여쓰기 + (깊이)로 표시된다
- [ ] 모든 레벨의 카테고리를 선택할 수 있다
- [ ] 태그 입력 시 기존 태그 자동완성 드롭다운이 표시된다
- [ ] Enter 또는 드롭다운 항목 클릭으로 태그 Chip이 추가된다
- [ ] Chip의 x 버튼 또는 Backspace로 태그가 삭제된다
- [ ] 기존 태그와 새 태그가 색상으로 구분된다
- [ ] 중복 태그 입력이 무시된다
- [ ] 썸네일을 에셋 갤러리에서 선택할 수 있다 (F-27 구현 후)
- [ ] 썸네일을 URL 입력으로 설정할 수 있다
- [ ] 썸네일을 드래그 앤 드롭으로 업로드할 수 있다
- [ ] 썸네일 클립보드 버튼: 대기 → 붙여넣기 → 미리보기 → 업로드 플로우가 동작한다
- [ ] 클립보드 대기 중 Esc/외부 클릭 시 취소된다
- [ ] 썸네일 미리보기가 표시된다
- [ ] 저장 (초안) 버튼으로 status 변경 없이 저장된다
- [ ] 발행 버튼 클릭 시 확인 모달이 표시된다
- [ ] 발행 확인 후 status: published로 저장된다
- [ ] 보관 버튼으로 status: archived로 저장된다
- [ ] 발행된 글에서 "발행 취소" 버튼으로 draft로 되돌릴 수 있다
- [ ] summary 필드가 200자 제한으로 편집 가능하다
- [ ] description 필드가 300자 제한으로 편집 가능하다
- [ ] summary가 비어있을 때 CodeMirror blur 시 contentMd에서 자동 생성된다
- [ ] 정보 탭에서 글 목록 미리보기 (PostListItem)가 폼 값을 실시간 반영한다
- [ ] 저장 시 F-22 pending 이미지가 일괄 업로드된다
- [ ] 페이지 이탈 시 미저장 변경이 있으면 beforeunload 경고가 표시된다
- [ ] 접근성: 탭 키보드 네비게이션, 폼 필드 aria-label (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 카테고리 목록 로딩 중 | "불러오는 중..." placeholder, 저장 버튼 비활성 |
| 카테고리가 0개 | "카테고리를 먼저 생성하세요" 안내, 저장 버튼 비활성 |
| 태그 이름에 쉼표 포함 | 쉼표는 구분자가 아니므로 그대로 허용 (Chip 방식) |
| 태그 30자 초과 입력 | 입력 필드에서 30자 제한, 초과 시 토스트 경고 |
| 썸네일 클립보드에 이미지 아닌 텍스트 | "이미지를 복사해 주세요" 토스트, 대기 상태 유지 |
| 썸네일 업로드 실패 | 에러 토스트, 이전 썸네일 값 유지 |
| 에셋 갤러리 미구현 (F-27 전) | 에셋 갤러리 버튼 비활성 + "준비 중" tooltip |
| 발행 시 필수 필드 누락 | 검증 에러 메시지, 누락 필드 하이라이트 |
| 이미 발행된 글의 저장 | status 변경 없이 내용만 업데이트 |
| summary 자동 생성 시 contentMd가 비어있음 | summary도 빈 문자열, placeholder 유지 |
| 네트워크 오류로 저장 실패 | 에러 메시지, 폼 데이터 유지 |
| pending 이미지 업로드 실패 | 저장 중단, 실패 이미지 안내 (F-22 에러 처리) |

## 9. 의존성

- F-19 관리자 로그인 (인증)
- F-22 마크다운 에디터 (CodeMirror, pendingImages, uploadPendingImages)
- F-01 summary 필드 (DB 스키마)
- F-30 description 필드 (DB 스키마)
- F-27 에셋 갤러리 (썸네일 갤러리 선택 - 구현 전까지 버튼 비활성)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
