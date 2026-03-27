# Client Progress - 2026-03-28

## 완료된 작업

### #189 CodeMirror 기반 마크다운 에디터 안정화 (PR #237 머지)

관리자 글 작성/수정용 CodeMirror 마크다운 에디터를 머지했다. 자동 리뷰에서 드러난 제어형 입력 동기화, 접근성, 툴바 명령, 번들 크기 회귀를 여러 라운드에 걸쳐 정리한 뒤 병합했다.

**주요 변경 사항:**

- `src/features/post-editor/ui/markdown-editor.tsx`
  - CodeMirror 에디터를 제어형 `value`와 안전하게 동기화하고, 외부 sync transaction은 `onChange`와 undo history에서 제외
  - `id`, `labelId`, placeholder 관련 속성을 재구성 가능하도록 정리
  - 실제 editor surface에 `id`를 유지하고 `spellcheck="false"`를 적용
  - hidden `textarea`는 form serialization 용도로만 유지
- `src/features/post-editor/lib/markdown-commands.ts`
  - heading/quote/list 툴바 동작이 multi-line selection 전체에 적용되도록 수정
  - code block / horizontal rule / table 삽입 시 줄바꿈 정규화
  - bold/italic/bold+italic 조합에서 inline emphasis toggle이 기존 마커를 파괴하지 않도록 보완
- `src/features/post-editor/ui/post-form.tsx`
  - 본문 라벨과 editor naming/focus 연결을 CodeMirror 구조에 맞게 조정
- `package.json`, `pnpm-lock.yaml`
  - `@codemirror/language-data` 제거로 불필요한 fenced-code language bundle 축소

**리뷰 수정 사항:**

- controlled sync가 dirty 상태를 다시 켜는 문제, undo가 hydration/reset 이전 내용을 되살리는 문제 수정
- exported `MarkdownEditor` prop 계약(`id`, `name`, `placeholder`)과 label wiring 회귀 보완
- toolbar의 block prefix, code block, horizontal rule, table, nested emphasis edge case 수정
- `@codemirror/language-data` 제거로 editor route 번들 부담 완화

**검증:**

- `pnpm compile:types`
- `pnpm lint`
- `pnpm build`

**메모:**

- 전체 `pnpm lint`는 저장소 기존 warning인 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 항목 1건이 남아 있었지만, 이번 이슈 수정 범위 밖으로 두고 병합했다.
