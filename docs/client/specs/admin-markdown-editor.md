# F-22: 마크다운 에디터 (편집 + 실시간 프리뷰)

**상태:** DRAFT
**최종 수정:** 2026-03-21

---

## 1. 개요

관리자 글 작성/수정 페이지의 마크다운 에디터. 현재 textarea를 CodeMirror 6으로 교체하고, 서식 툴바, 이미지 삽입(드래그 앤 드롭, 클립보드, 버튼), 프리뷰 3가지 모드, 스크롤 동기화를 제공한다.

## 2. 배경 및 동기

현재 구현 상태:

- 단순 `<textarea>` 기반 에디터 (monospace, `min-h-[60vh]`)
- Web Worker + 300ms 디바운스 실시간 프리뷰
- unified.js 파이프라인 (remark-parse → remark-rehype → shiki → rehype-sanitize → rehype-stringify)
- 프리뷰는 XL 이상에서만 2컬럼 표시

개선이 필요한 부분:

- 줄 번호, 마크다운 구문 하이라이팅 없음
- 서식 툴바/키보드 단축키 없음
- 에디터 내 이미지 삽입 불가 (별도 에셋 페이지에서 URL 수동 복사)
- 프리뷰 토글/모달 없음
- 에디터-프리뷰 스크롤 동기화 없음

## 3. 목표

- textarea를 CodeMirror 6으로 교체한다
- 15개 서식 버튼의 마크다운 툴바를 제공한다
- 키보드 단축키 (Ctrl+B, I, K)를 지원한다
- 이미지를 드래그 앤 드롭, 클립보드 붙여넣기, 툴바 버튼으로 삽입한다
- 프리뷰 3가지 모드를 지원한다 (에디터+프리뷰, 에디터만, 프리뷰 모달)
- 에디터-프리뷰 스크롤 동기화를 구현한다

## 4. 비목표

- WYSIWYG 편집 (마크다운 직접 편집 유지)
- 자동 저장 (F-23 저장 플로우에서 관리)
- 협업 편집 / 실시간 공동 작업
- 마크다운 린팅/교정
- 에디터 테마 커스터마이징 (다크모드 자동 적용만)

---

## 5. 상세 설계

### 5.1 CodeMirror 6 설정

#### 패키지

```
@codemirror/state
@codemirror/view
@codemirror/commands
@codemirror/lang-markdown
@codemirror/language-data    (코드블록 내 언어 하이라이팅)
@codemirror/search
```

#### 에디터 설정

```typescript
const extensions = [
  markdown({ base: markdownLanguage, codeLanguages: languages }),
  lineNumbers(),
  highlightActiveLineGutter(),
  highlightActiveLine(),
  bracketMatching(),
  closeBrackets(),
  history(),
  indentOnInput(),
  syntaxHighlighting(defaultHighlightStyle),
  keymap.of([
    ...defaultKeymap,
    ...historyKeymap,
    ...searchKeymap,
    ...markdownKeymap,      // 커스텀 마크다운 단축키
  ]),
  EditorView.lineWrapping,  // 줄 바꿈
  darkModeTheme,            // 다크모드 테마 연동
];
```

#### 다크모드 연동

Tailwind CSS v4 디자인 토큰(`bg-background-1`, `text-text-1` 등)에 맞춰 CM6 테마를 생성한다.

```typescript
const darkModeTheme = EditorView.theme({
  '&': {
    backgroundColor: 'var(--color-background-1)',
    color: 'var(--color-text-1)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--color-background-2)',
    color: 'var(--color-text-4)',
    borderRight: '1px solid var(--color-border-3)',
  },
  '.cm-activeLine': {
    backgroundColor: 'var(--color-background-3)',
  },
  // ...
});
```

### 5.2 마크다운 툴바

#### 버튼 목록

| # | 버튼 | 아이콘 | 마크다운 | 단축키 | 동작 |
|---|---|---|---|---|---|
| 1 | 볼드 | **B** | `**text**` | Ctrl+B | 선택 텍스트 감싸기 |
| 2 | 이탤릭 | *I* | `*text*` | Ctrl+I | 선택 텍스트 감싸기 |
| 3 | 취소선 | ~~S~~ | `~~text~~` | - | 선택 텍스트 감싸기 |
| 4 | H1 | H1 | `# ` | - | 줄 앞에 삽입/토글 |
| 5 | H2 | H2 | `## ` | - | 줄 앞에 삽입/토글 |
| 6 | H3 | H3 | `### ` | - | 줄 앞에 삽입/토글 |
| 7 | 링크 | 🔗 | `[text](url)` | Ctrl+K | 선택 텍스트 → 링크 |
| 8 | 이미지 | 🖼️ | `![alt](url)` | - | 파일 선택 트리거 |
| 9 | 인라인 코드 | `<>` | `` `code` `` | - | 선택 텍스트 감싸기 |
| 10 | 코드블록 | `</>` | ```` ```lang ```` | - | 블록 삽입 |
| 11 | 인용 | `>` | `> ` | - | 줄 앞에 삽입/토글 |
| 12 | 순서 목록 | 1. | `1. ` | - | 줄 앞에 삽입/토글 |
| 13 | 비순서 목록 | - | `- ` | - | 줄 앞에 삽입/토글 |
| 14 | 구분선 | ── | `---` | - | 새 줄에 삽입 |
| 15 | 테이블 | 표 | 템플릿 | - | 기본 테이블 구조 삽입 |

#### 툴바 UI

```
┌─ 툴바 ──────────────────────────────────────────────────────────────────┐
│ [B] [I] [S] │ [H1] [H2] [H3] │ [🔗] [🖼️] │ [<>] [</>] │ [>] [1.] [-] │ [──] [表] │
└─────────────────────────────────────────────────────────────────────────┘
```

- 구분선(`|`)으로 기능 그룹 분리
- 각 버튼에 tooltip (hover 시 기능명 + 단축키 표시)
- 반응형: 모바일에서는 스크롤 또는 접힘 메뉴

#### 서식 명령 구현

```typescript
function wrapSelection(view: EditorView, before: string, after: string) {
  const { from, to } = view.state.selection.main;
  const selected = view.state.sliceDoc(from, to);

  if (selected) {
    // 선택 있음: 감싸기
    view.dispatch({
      changes: { from, to, insert: `${before}${selected}${after}` },
      selection: EditorSelection.range(from + before.length, to + before.length),
    });
  } else {
    // 선택 없음: 빈 마커 삽입 + 커서를 안쪽에 배치
    view.dispatch({
      changes: { from, insert: `${before}${after}` },
      selection: EditorSelection.cursor(from + before.length),
    });
  }
}

function toggleLinePrefix(view: EditorView, prefix: string) {
  const line = view.state.doc.lineAt(view.state.selection.main.from);
  const hasPrefix = line.text.startsWith(prefix);

  if (hasPrefix) {
    // 제거
    view.dispatch({ changes: { from: line.from, to: line.from + prefix.length } });
  } else {
    // 삽입 (기존 다른 헤딩 프리픽스 제거 후)
    const cleaned = line.text.replace(/^#{1,6}\s/, '');
    view.dispatch({ changes: { from: line.from, to: line.to, insert: `${prefix}${cleaned}` } });
  }
}
```

#### 테이블 템플릿

```markdown
| 제목 | 제목 |
|---|---|
| 내용 | 내용 |
```

### 5.3 이미지 삽입

#### 삽입 경로

| 방법 | 트리거 |
|---|---|
| 툴바 이미지 버튼 | 클릭 → 파일 선택 다이얼로그 |
| 드래그 앤 드롭 | 에디터 영역에 이미지 파일 드래그 |
| 클립보드 붙여넣기 | Ctrl+V로 이미지 붙여넣기 |

세 가지 경로 모두 동일한 처리 흐름을 따른다.

#### 파일 검증

- 허용 형식: JPEG, PNG, GIF, WebP, SVG
- 최대 크기: 10MB
- 검증 실패 시 토스트 에러 메시지

#### 플레이스홀더 마커 방식

이미지 삽입 시 raw blob URL 대신 고유 플레이스홀더 마커를 사용하여 치환 오류를 방지한다.

```
삽입: ![이미지](pending-upload:f7a3b2c1-xxxx-xxxx)
```

- `pending-upload:` 프리픽스 + UUID v4로 절대 충돌 없는 고유 식별자
- contentMd 원본에는 플레이스홀더만 존재

#### 이미지 상태 관리

```typescript
interface PendingImage {
  file: File;
  blobUrl: string;       // 프리뷰 표시용
  insertedAt: number;    // 삽입 시점 (디버깅용)
}

// 에디터 레벨 상태
const pendingImages = new Map<string, PendingImage>();  // key: uuid
```

#### 이미지 삽입 흐름

```
1. 사용자가 이미지 삽입 (드래그/붙여넣기/버튼)
2. 파일 검증 (형식, 크기)
3. uuid 생성, blobUrl 생성
4. pendingImages.set(uuid, { file, blobUrl })
5. 에디터 커서 위치에 ![파일명](pending-upload:uuid) 삽입
6. 프리뷰 렌더링 시: pending-upload:uuid → blobUrl 치환 (프리뷰 전용)
7. 사용자에게는 프리뷰에서 이미지가 즉시 보임
```

#### 프리뷰 렌더링 시 마커 해석

```typescript
function resolvePreviewContent(
  contentMd: string,
  pendingImages: Map<string, PendingImage>,
): string {
  return contentMd.replace(
    /!\[([^\]]*)\]\(pending-upload:([a-f0-9-]+)\)/g,
    (match, alt, uuid) => {
      const pending = pendingImages.get(uuid);
      if (!pending) return match;  // 이미 삭제된 경우 마커 유지
      return `![${alt}](${pending.blobUrl})`;
    },
  );
}
```

- 정규식이 마크다운 이미지 문법 `![...](pending-upload:...)` 패턴만 매칭
- 코드블록 내부의 텍스트는 마크다운 이미지 문법이 아니므로 매칭되지 않음

#### 저장 시 일괄 업로드 (F-23에서 호출)

```typescript
async function uploadPendingImages(
  contentMd: string,
  pendingImages: Map<string, PendingImage>,
): Promise<string> {
  // 1. contentMd에 실제로 남아있는 pending-upload만 필터
  const usedUuids = [...contentMd.matchAll(/pending-upload:([a-f0-9-]+)/g)]
    .map(m => m[1]);

  const toUpload = usedUuids
    .filter(uuid => pendingImages.has(uuid))
    .map(uuid => ({ uuid, file: pendingImages.get(uuid)!.file }));

  if (toUpload.length === 0) return contentMd;

  // 2. 일괄 업로드
  const files = toUpload.map(t => t.file);
  const results = await uploadAssets(files);  // 기존 에셋 업로드 API

  // 3. 플레이스홀더 → 실제 URL 치환
  let finalContent = contentMd;
  toUpload.forEach((item, i) => {
    finalContent = finalContent.replace(
      `pending-upload:${item.uuid}`,
      results[i].url,
    );
  });

  // 4. blob URL 해제
  for (const uuid of usedUuids) {
    const pending = pendingImages.get(uuid);
    if (pending) URL.revokeObjectURL(pending.blobUrl);
  }

  return finalContent;
}
```

#### 에러 시나리오 대응

| 시나리오 | 대응 |
|---|---|
| 업로드 전체 실패 | 저장 중단, "이미지 업로드에 실패했습니다" 에러, 재시도 유도 |
| 업로드 일부 실패 | 저장 중단, 실패한 이미지 목록 표시, 해당 이미지 제거 또는 재시도 |
| 이미지 삽입 후 content에서 삭제 | 저장 시 contentMd에 없는 uuid는 업로드 스킵 |
| 코드블록 안에 pending-upload 텍스트 | 마크다운 이미지 문법 `![...](pending-upload:...)` 패턴만 매칭하므로 안전 |
| 페이지 이탈 시 미저장 이미지 | `beforeunload` 경고 (pendingImages.size > 0 또는 dirty 상태) |
| 기존 글 수정 시 기존 이미지 URL | 이미 실제 URL이므로 영향 없음 |

#### 대기 중 이미지 표시

에디터 하단 또는 툴바 근처에 대기 중인 이미지 개수를 표시한다.

```
📎 업로드 대기: 3개
```

- 클릭 시 대기 중인 이미지 목록을 소형 패널로 표시 (파일명, 크기, 미리보기)
- 개별 삭제 가능 (contentMd에서 해당 마커도 함께 제거)

### 5.4 프리뷰 모드

#### 3가지 모드

| 모드 | 레이아웃 | 활성화 |
|---|---|---|
| 에디터 + 프리뷰 | 2컬럼 (좌: 에디터, 우: 프리뷰) | 토글 ON (기본값) |
| 에디터만 | 에디터 전체 너비 | 토글 OFF |
| 프리뷰 모달 | 에디터만 모드에서 모달 오버레이 | 버튼 클릭 |

#### UI

```
┌─ 모드 전환 ─────────────────────────────────────┐
│ [에디터 + 프리뷰 🔘]  [에디터만 ⚪]   [👁 미리보기] │
└─────────────────────────────────────────────────┘
```

- "에디터 + 프리뷰" / "에디터만": 라디오 토글
- "👁 미리보기": 에디터만 모드에서만 활성화, 클릭 시 프리뷰 모달 오픈
- 에디터 + 프리뷰 모드에서도 "👁 미리보기" 클릭 시 모달 오픈 가능

#### 프리뷰 모달

```
┌─ 프리뷰 ───────────────────────────── [X 닫기] ─┐
│                                                   │
│  마크다운 렌더링된 본문                             │
│  (F-02 PostContent 컴포넌트 재활용)                │
│  (typography.css 스타일 적용)                      │
│                                                   │
└───────────────────────────────────────────────────┘
```

- 전체 화면 오버레이 모달
- Esc 키 또는 X 버튼으로 닫기
- 모달 열림 시 body 스크롤 잠금

#### 반응형 동작

| 뷰포트 | 기본 모드 | 동작 |
|---|---|---|
| XL 이상 (1280px+) | 에디터 + 프리뷰 | 2컬럼, 토글 가능 |
| XL 미만 | 에디터만 | 프리뷰는 모달로만 제공 |

### 5.5 스크롤 동기화

에디터와 프리뷰가 나란히 있을 때 (에디터 + 프리뷰 모드), 에디터 스크롤에 프리뷰가 동기화된다.

#### 구현 방식

비율 기반 스크롤 동기화:

```typescript
function syncScroll(editorView: EditorView, previewEl: HTMLElement) {
  const editorScrollInfo = editorView.scrollDOM;
  const scrollRatio = editorScrollInfo.scrollTop /
    (editorScrollInfo.scrollHeight - editorScrollInfo.clientHeight);

  previewEl.scrollTop = scrollRatio *
    (previewEl.scrollHeight - previewEl.clientHeight);
}
```

- 에디터 스크롤 → 프리뷰 동기화 (단방향)
- `requestAnimationFrame`으로 스로틀링
- 프리뷰를 직접 스크롤해도 에디터에 영향 없음 (사용자 자유 탐색)

### 5.6 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `features` | `post-editor/ui/markdown-editor.tsx` | CM6 에디터 (기존 textarea 교체) |
| `features` | `post-editor/ui/markdown-toolbar.tsx` | 서식 툴바 15개 버튼 (신규) |
| `features` | `post-editor/ui/markdown-preview.tsx` | 프리뷰 (기존, 마커 해석 추가) |
| `features` | `post-editor/ui/preview-modal.tsx` | 프리뷰 모달 (신규) |
| `features` | `post-editor/ui/markdown-preview.worker.ts` | 프리뷰 Web Worker (기존) |
| `features` | `post-editor/lib/markdown-commands.ts` | CM6 서식 명령 (신규) |
| `features` | `post-editor/lib/image-handler.ts` | 이미지 삽입/관리 (신규) |
| `features` | `post-editor/lib/scroll-sync.ts` | 스크롤 동기화 (신규) |
| `shared` | `lib/markdown.ts` | unified.js 렌더링 파이프라인 (기존) |

### 5.7 데이터 흐름

```
MarkdownEditor (CM6)
  ├─ onChange → contentMd 상태 업데이트 (부모 PostForm으로 전달)
  ├─ MarkdownToolbar
  │   └─ 버튼 클릭 → CM6 명령 실행 (wrapSelection, toggleLinePrefix 등)
  │   └─ 이미지 버튼 → 파일 선택 → imageHandler.insert()
  │
  ├─ CM6 이벤트
  │   ├─ 드래그 앤 드롭 → imageHandler.insert()
  │   └─ 클립보드 붙여넣기 → imageHandler.insert()
  │
  ├─ imageHandler
  │   ├─ pendingImages: Map<uuid, PendingImage>
  │   ├─ insert(file) → 검증 → uuid/blobUrl 생성 → 마커 삽입
  │   └─ uploadAll(contentMd) → 업로드 → 치환 → finalContent 반환
  │
  ├─ 프리뷰 모드
  │   ├─ 에디터+프리뷰: 2컬럼 + scrollSync
  │   ├─ 에디터만: 단일 컬럼
  │   └─ 프리뷰 모달: PreviewModal
  │
  └─ MarkdownPreview
      └─ resolvePreviewContent(contentMd, pendingImages) → Worker → HTML
```

## 6. API 연동

| 메서드 | 경로 | 용도 | 비고 |
|---|---|---|---|
| POST | `/api/assets/upload` | 이미지 일괄 업로드 | 기존 에셋 업로드 API 활용 |

- 에디터 자체는 API를 직접 호출하지 않음
- `uploadPendingImages()` 함수를 F-23 저장 플로우에 export

## 7. 수용 기준

- [ ] CodeMirror 6으로 에디터가 교체되어 있다
- [ ] 줄 번호가 표시된다
- [ ] 마크다운 구문 하이라이팅이 적용된다
- [ ] 15개 서식 버튼이 툴바에 표시된다
- [ ] 각 서식 버튼이 올바른 마크다운 문법을 삽입/토글한다
- [ ] Ctrl+B(볼드), Ctrl+I(이탤릭), Ctrl+K(링크) 단축키가 동작한다
- [ ] 이미지 파일을 에디터에 드래그 앤 드롭하면 프리뷰에 즉시 표시된다
- [ ] 클립보드에서 이미지를 붙여넣으면 프리뷰에 즉시 표시된다
- [ ] 툴바 이미지 버튼으로 파일을 선택하면 프리뷰에 즉시 표시된다
- [ ] 이미지 삽입 시 `pending-upload:uuid` 플레이스홀더 마커가 사용된다
- [ ] 이미지 파일 검증 (형식: JPEG/PNG/GIF/WebP/SVG, 크기: 10MB) 이 동작한다
- [ ] 대기 중 이미지 개수가 표시된다
- [ ] "에디터 + 프리뷰" 모드에서 2컬럼 레이아웃으로 동작한다
- [ ] "에디터만" 모드에서 에디터가 전체 너비를 사용한다
- [ ] "프리뷰 모달"이 전체 화면 오버레이로 열린다
- [ ] XL 미만에서는 에디터만 모드가 기본이다
- [ ] 에디터+프리뷰 모드에서 스크롤이 동기화된다
- [ ] 실시간 프리뷰가 300ms 디바운스로 동작한다 (Web Worker 유지)
- [ ] 다크모드에서 CM6 에디터 테마가 디자인 토큰에 맞게 적용된다
- [ ] 접근성: 툴바 버튼 aria-label, 키보드 네비게이션 (A-01 참조)

## 8. 에지 케이스

| 케이스 | 처리 |
|---|---|
| 이미지 형식/크기 검증 실패 | 토스트 에러 메시지, 삽입 중단 |
| 매우 큰 마크다운 문서 (10,000줄+) | CM6의 가상 스크롤이 처리, Web Worker 프리뷰 유지 |
| 코드블록 안에 `pending-upload:` 텍스트 입력 | 프리뷰 변환 정규식이 `![...](pending-upload:...)` 패턴만 매칭하므로 안전 |
| 이미지 삽입 후 Undo (Ctrl+Z) | CM6 히스토리가 마커 텍스트 제거, pendingImages에는 남아있으나 저장 시 contentMd에 없으므로 업로드 스킵 |
| 여러 이미지 동시 드래그 앤 드롭 | 각각 별도 uuid, 순차 삽입 |
| 프리뷰 모달 열린 상태에서 Esc | 모달 닫기 (에디터 포커스 복원) |
| CM6 로드 실패 (번들 에러) | textarea 폴백 또는 에러 메시지 |

## 9. 의존성

- F-19 관리자 로그인 (인증)
- F-02 글 상세 (`PostContent` 마크다운 렌더링 - 프리뷰 재활용)

## 10. 미해결 사항

없음. 모든 사항 확정됨.
