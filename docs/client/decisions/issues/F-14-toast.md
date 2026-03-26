# [F-14] Toast 알림

> 전역 Toast 알림 시스템. 서버 요청 결과, 클립보드 복사, 권한 에러 등 사용자 액션에 대한 피드백을 상단 우측 Toast로 표시한다.

## SPEC 참조

- `docs/client/specs/toast.md`

## 와이어프레임

와이어프레임 없음. `docs/client/designs/DESIGN_SYSTEM.md`의 컬러/타이포그래피 규칙을 따른다.

## 상세 설계

### Toast 유형

| 유형 | 색상 토큰 | 용도 |
|---|---|---|
| `success` | `positive-1` | 저장, 삭제, 업로드 성공 |
| `error` | `negative-1` | 서버 요청 실패, 네트워크 에러 |
| `info` | `primary-1` | 클립보드 복사, 안내 메시지 |

### 동작

| 항목 | 값 |
|---|---|
| 위치 | 상단 우측 |
| 자동 사라짐 | 3초 |
| 동시 표시 | 스택 (최대 3개, 이후 오래된 것부터 제거) |
| 클릭 액션 | 액션이 있으면 해당 위치로 이동, 없으면 Toast 닫기 |
| 수동 닫기 | 닫기 버튼 (X) |

### 사용 예시

```tsx
import { toast } from "sonner";

// 성공
toast.success("글이 저장되었습니다.");

// 에러
toast.error("글 저장에 실패했습니다.");

// 액션 포함 (클릭 시 이동)
toast.error("댓글 작성에 실패했습니다.", {
  action: {
    label: "다시 시도",
    onClick: () => retrySubmit(),
  },
});

// 403 에러 (F-12에서 정의)
toast.error("접근 권한이 없습니다.");
// → /manage/login 리다이렉트는 API 인터셉터에서 처리
```

### 마이그레이션 대상

#### 인라인 에러 → Toast 전환

서버 요청 결과 피드백만 Toast로 전환한다. 폼 검증 에러는 인라인 유지.

| 파일 | 현재 | 변경 |
|---|---|---|
| `features/post-editor/ui/post-form.tsx` | `setSubmitError(msg)` (onError) | `toast.error(msg)` |
| `features/asset-uploader/ui/asset-uploader.tsx` | `setFeedbackMessage(msg)` + 3초 timeout | `toast.success(msg)` |
| `features/comment-section/ui/comment-form.tsx` | `setSubmitError(msg)` (onError) | `toast.error(msg)` |
| `features/category-manager/ui/category-manager.tsx` | `setError(msg)` (onError) | `toast.error(msg)` |
| `features/admin-login/ui/login-form.tsx` | `setError(msg)` (onError) | `toast.error(msg)` |
| `app/manage/posts/page.tsx` | `setError(msg)` (onError) | `toast.error(msg)` |
| `features/guestbook-manager/ui/guestbook-manager.tsx` | `setError(msg)` (onError) | `toast.error(msg)` |

#### 인라인 유지 (변경 없음)

- 폼 검증 에러: "카테고리를 선택하세요", "제목을 입력하세요" 등
- 로그인 폼 검증: "아이디를 입력하세요" 등

### `getErrorMessage()` 추출

현재 7개 파일에서 동일하게 정의된 유틸을 `@shared/lib`로 추출한다.

```tsx
// @shared/lib/get-error-message.ts
export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiResponseError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}
```

**교체 대상 (7개 파일):**

- `features/post-editor/ui/post-form.tsx`
- `features/asset-uploader/ui/asset-uploader.tsx`
- `features/comment-section/ui/comment-form.tsx`
- `features/category-manager/ui/category-manager.tsx`
- `features/admin-login/ui/login-form.tsx`
- `app/manage/posts/page.tsx`
- `features/guestbook-manager/ui/guestbook-manager.tsx`

### 데이터 흐름

```
Toaster 설정:
  app-layer/provider/ → <Toaster position="top-right" duration={3000} visibleToasts={3} />

성공 흐름:
  useMutation onSuccess → toast.success("메시지")

에러 흐름:
  useMutation onError → toast.error(getErrorMessage(error, "기본 메시지"))

403 흐름 (F-12):
  API 인터셉터 → toast.error("접근 권한이 없습니다") → /manage/login 리다이렉트

복사 흐름:
  clipboard API → toast.info("URL을 복사했습니다")
```

### 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app-layer` | `provider/toast-provider.tsx` | `<Toaster />` 전역 설정 |
| `shared` | `lib/get-error-message.ts` | 에러 메시지 추출 유틸 |

- `sonner`의 `toast()` 함수를 직접 import하여 사용 (별도 wrapper 불필요)
- `<Toaster />` 컴포넌트를 루트 레이아웃 provider에 추가

### sonner 테마 연동

- `theme` prop으로 다크모드 연동: `<Toaster theme={resolvedTheme} />`
- 커스텀 색상은 CSS 변수(`--positive-1`, `--negative-1`, `--primary-1`)로 적용

## API 연동

없음. 순수 클라이언트 UI.

403 응답 처리는 API 클라이언트 공통 인터셉터에서 `toast.error()` 호출 (F-12에서 정의된 흐름).

## 수용 기준

- [ ] `sonner` 설치 및 `<Toaster />` 전역 설정 완료
- [ ] Toast 위치: 상단 우측
- [ ] 자동 사라짐: 3초
- [ ] 동시 표시: 스택 (최대 3개)
- [ ] Toast 클릭 시 액션 실행 또는 닫기
- [ ] 닫기 버튼(X) 표시
- [ ] `success`, `error`, `info` 유형별 색상 적용
- [ ] 7개 파일의 서버 요청 에러가 Toast로 전환된다
- [ ] AssetUploader `feedbackMessage` → `toast.success`로 전환, setTimeout 제거
- [ ] 폼 검증 에러는 인라인 유지 (Toast 아님)
- [ ] `getErrorMessage()` 유틸이 `@shared/lib`로 추출되고 7개 파일에서 import된다
- [ ] 다크모드 자동 적용 (`theme` prop 연동)
- [ ] 접근성: Toast에 `role="status"`, 스크린리더 안내 (A-01 참조)

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| 3개 초과 Toast 동시 발생 | 오래된 것부터 자동 제거 |
| Toast 표시 중 페이지 이동 | Toast 유지 (전역 provider) |
| 네트워크 끊김 상태에서 에러 Toast | "네트워크 연결을 확인해 주세요" 메시지 (getErrorMessage fallback) |
| Toast 액션 클릭 시 해당 페이지 이미 이동 | 액션 무시 (중복 이동 방지) |

## 의존성

- Blocked by: 없음
- Blocks: 없음
