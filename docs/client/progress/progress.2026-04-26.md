# Client Progress - 2026-04-26

## 완료된 작업

### #337 public 비밀글 안내 문구 한글화 (PR #339 머지)

public 댓글 비밀글이 영어 문구 `This comment is secret.` 으로 노출되던 문제를 client 이슈 `#337` 기준으로 정리했다. 클라이언트 코드 검색 결과 비밀글 마스크 판별은 `src/features/comment-section/ui/comment-list.tsx` 한 곳에서만 이뤄지고 있었고, 여기서는 한국어 sentinel `비공개 메시지입니다` 만 비밀글 마스크로 취급하고 있었다. 이번 수정으로 legacy 영어/한국어 마스크 문자열은 모두 비밀글로 인식하되, 실제 사용자 표시 문구는 항상 `비공개입니다.` 로 통일했다.

자동 리뷰 1차에서는 새 표시 문구 자체를 sentinel alias에 포함하면 실제 댓글 본문과 충돌할 수 있다는 suggestion이 나왔다. 이에 따라 판별 alias는 기존에 알려진 영어/이전 한국어 마스크만 유지하고, 렌더링 시에만 새 문구 `비공개입니다.` 를 사용하도록 보정했다. 재리뷰 후 clean 판정으로 PR `#339`를 머지했다.

**주요 변경 사항:**

- `src/features/comment-section/ui/comment-list.tsx`
  - 비밀글 표시 문구를 `비공개입니다.` 로 통일
  - legacy 영어 마스크 `This comment is secret.` 지원 추가
  - 이전 한국어 마스크 `비공개 메시지입니다` 도 계속 지원
  - 표시 문구와 비밀글 판별 sentinel을 분리해 실제 댓글 본문과의 충돌 가능성 축소

**검증:**

- `pnpm install --frozen-lockfile`
- `pnpm lint` *(저장소 기존 warning 2건 유지)*
- `pnpm build`
- `pnpm compile:types`

**메모:**

- client 코드 기준 동일 런타임 판별 지점은 `comment-list.tsx` 한 곳뿐이었다.
- `pnpm lint`는 저장소 기존 warning인 `src/features/post-editor/ui/image-gallery-modal.tsx`의 `<img>` 사용 1건과 `src/shared/ui/error-boundary.tsx`의 `_error` 미사용 1건만 남았다.
