# [F-26] 에셋 업로드 (드래그&드롭, 파일 검증, 업로드 큐)

> 관리자 에셋 관리 페이지의 이미지 업로드 기능. 드래그 앤 드롭, 파일 선택 버튼, 업로드 큐(미리보기 + 개별 제거), 파일 검증, 전체 진행률 표시를 제공한다. 업로드 시 서버에서 이미지 width/height를 자동 추출하여 DB에 저장한다.

## SPEC 참조

- `docs/client/specs/admin-asset-upload.md`

## 와이어프레임

- `docs/client/designs/admin/admin-asset.html` - 에셋 관리 페이지 (업로드 영역)
- Admin 공통 셸: `docs/client/designs/admin/_admin-shell.html`
- 공통 디자인 시스템: `docs/client/designs/DESIGN_SYSTEM.md`

## 상세 설계

### 업로드 영역 (기존 구현 문서화)

#### UI

```
┌─ 업로드 ─────────────────────────────────────────────┐
│                                                        │
│     파일을 드래그하거나 클릭하여 선택하세요             │
│                                                        │
│  ┌─ 큐 ───────────────────────────────────────────┐   │
│  │ [미리보기1 x] [미리보기2 x] [미리보기3 x]      │   │
│  │                             [전체 삭제]         │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  [===========================-----] 75%                │
│                                                        │
│                                        [업로드]        │
└────────────────────────────────────────────────────────┘
```

#### 업로드 경로

| 방법 | 트리거 |
|---|---|
| 드래그 앤 드롭 | 업로드 영역에 파일 드래그 |
| 파일 선택 | 영역 클릭 또는 버튼 클릭 → 파일 다이얼로그 |

#### 드래그 앤 드롭 시각 피드백

파일을 업로드 영역 위로 드래그하면 시각 피드백을 제공한다.

| 상태 | 피드백 |
|---|---|
| 기본 | 점선 테두리 (`border-dashed border-border-3`) |
| 파일 드래그 중 (영역 위) | 테두리 하이라이트 (`border-primary-1`) + 배경 (`bg-primary-2/10`) + "놓으면 추가됩니다" 메시지 |
| 드래그 영역 이탈 | 기본 상태 복귀 |

`dragenter`/`dragleave`/`dragover`/`drop` 이벤트로 상태 관리.

### 파일 검증

#### 클라이언트 검증 (큐 추가 시)

| 항목 | 제한 | 에러 메시지 |
|---|---|---|
| 허용 형식 | JPEG, PNG, GIF, WebP, SVG | "지원하지 않는 파일 형식입니다" |
| 최대 크기 | 10MB | "파일 크기가 10MB를 초과합니다" |
| 최대 큐 개수 | 5개 | "최대 5개까지 업로드할 수 있습니다" |
| 중복 파일 | 파일명 + 크기 + 수정일 기준 | "이미 추가된 파일입니다" |

- 검증 실패 시 토스트 에러
- 유효한 파일만 큐에 추가

#### 서버 검증 (업로드 시)

| 항목 | 제한 |
|---|---|
| MIME 타입 | image/jpeg, image/png, image/gif, image/webp, image/svg+xml |
| Magic bytes | 파일 헤더 바이트 검증 (아래 참조) |
| 파일 크기 | 10MB (`@fastify/multipart` 설정) |
| 동시 파일 수 | 5개 (`@fastify/multipart` 설정) |

- 검증 실패 시 400 Bad Request

#### Magic bytes 검증

MIME 타입만으로는 확장자를 속인 파일을 걸러낼 수 없다. 파일 버퍼의 첫 바이트를 확인하여 실제 이미지인지 검증한다.

```typescript
const MAGIC_BYTES: Record<string, number[]> = {
  'image/jpeg': [0xFF, 0xD8, 0xFF],
  'image/png':  [0x89, 0x50, 0x4E, 0x47],
  'image/gif':  [0x47, 0x49, 0x46, 0x38],
  'image/webp': [0x52, 0x49, 0x46, 0x46],  // RIFF header
};

function validateMagicBytes(buffer: Buffer, mimeType: string): boolean {
  const expected = MAGIC_BYTES[mimeType];
  if (!expected) return true;  // SVG는 텍스트 기반이므로 스킵
  return expected.every((byte, i) => buffer[i] === byte);
}
```

- SVG는 텍스트 기반이므로 magic bytes 검증 대상 외
- 검증 실패 시 400 Bad Request: "파일 형식이 올바르지 않습니다"

### 업로드 큐

#### 큐 아이템

각 파일은 blob URL로 미리보기와 파일 크기를 표시한다.

```typescript
interface QueueItem {
  file: File;
  previewUrl: string;  // URL.createObjectURL(file)
}
```

#### 큐 아이템 표시

```
┌──────────┐
│  미리보기 │
│          │
│  2.4 MB  │  <- 파일 크기 (formatFileSize 유틸)
│        x │  <- 제거 버튼
└──────────┘
```

파일 크기 포맷: `< 1KB` → "1 KB", `< 1MB` → "N KB", `>= 1MB` → "N.N MB"

#### 큐 동작

- 파일 추가: 검증 통과 → 큐에 추가 + blob 미리보기 생성
- 개별 제거: x 버튼 → 큐에서 제거 + blob URL 해제
- 전체 삭제: 모든 아이템 제거 + blob URL 일괄 해제
- 업로드 완료 시: 큐 자동 비움

### 업로드 진행률

모든 파일을 하나의 FormData 요청으로 전송하며, 전체 바이트 기준 진행률을 표시한다.

#### 구현

```typescript
function uploadWithProgress(
  formData: FormData,
  onProgress: (percent: number) => void,
): Promise<UploadAssetsResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => { /* resolve */ };
    xhr.onerror = () => { /* reject */ };
    xhr.open('POST', '/api/assets/upload');
    // CSRF 토큰 헤더 설정
    xhr.send(formData);
  });
}
```

- 기존 `fetch` 기반 API를 `XMLHttpRequest`로 교체 (fetch는 upload progress 미지원)
- 진행률 표시 형태는 디자인에 위임

#### 상태

| 상태 | UI |
|---|---|
| 큐 비어있음 | [업로드] 비활성 |
| 큐에 파일 있음 | [업로드] 활성 |
| 업로드 중 | 진행률 표시, [업로드] 비활성, 큐 조작 비활성 |
| 업로드 완료 | 큐 비움, 성공 토스트, 갤러리 갱신 |
| 업로드 실패 | 에러 토스트, 큐 유지 (재시도 가능) |

### width/height 자동 추출 (서버)

`image-size` 라이브러리로 업로드 시 이미지 크기를 자동 추출하여 DB에 저장한다.

#### 패키지

```
image-size
```

- 순수 JavaScript, native 빌드 불필요
- 파일 헤더만 읽으므로 빠름 (전체 디코딩 없음)
- JPEG, PNG, GIF, WebP, SVG 모두 지원

#### 구현

```typescript
import sizeOf from 'image-size';

// FileStorageService.saveFile() 내부
async saveFile(file: MultipartFile): Promise<SaveFileResult> {
  // 기존: 검증, 버퍼 읽기, UUID 생성, 파일 저장
  const buffer = await file.toBuffer();

  // 신규: 이미지 크기 추출
  let width: number | null = null;
  let height: number | null = null;
  try {
    const dimensions = sizeOf(buffer);
    width = dimensions.width ?? null;
    height = dimensions.height ?? null;
  } catch {
    // SVG 등 일부 형식에서 실패할 수 있음 - nullable 유지
  }

  // ... 파일 저장 로직

  return { storageKey, mimeType, sizeBytes, width, height };
}
```

#### SVG 처리

SVG는 벡터 형식이라 고정 크기가 없을 수 있음. `image-size`가 viewBox에서 크기를 추출하지만, viewBox가 없는 SVG는 null 유지.

### Cache-Control (서버)

`@fastify/static` 설정에 Cache-Control 헤더를 추가한다.

```typescript
// plugins/static.ts
fastify.register(fastifyStatic, {
  root: uploadDir,
  prefix: '/uploads/',
  maxAge: 30 * 24 * 60 * 60 * 1000,  // 30일 (밀리초)
  immutable: true,
});
```

- `Cache-Control: public, max-age=2592000, immutable`
- UUID 파일명이므로 같은 URL에 다른 파일이 올라갈 수 없음 → 캐시 오염 없음
- 30일 후 브라우저가 재검증 요청

### 파일 저장 구조 (기존 구현 문서화)

```
uploads/
  2026/
    03/
      f7a3b2c1-xxxx-xxxx-xxxx-xxxxxxxxxxxx.jpg
      a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx.png
    04/
      ...
```

- 연/월 디렉토리 자동 생성
- UUID v4 + 원본 확장자
- URL: `/uploads/2026/03/f7a3b2c1-xxxx.jpg`

### 데이터 모델

#### DB 스키마 (기존)

```typescript
assetTable {
  id: int (PK, autoincrement)
  storageProvider: varchar(20) = "local"
  storageKey: varchar(500)     // "2026/03/f7a3b2c1-xxxx.jpg"
  mimeType: varchar(100)
  sizeBytes: int
  width: int (nullable)        // image-size로 자동 추출
  height: int (nullable)       // image-size로 자동 추출
  createdAt: timestamp
}
```

#### 클라이언트 모델 (기존)

```typescript
interface UploadedAsset {
  id: number;
  url: string;          // "/uploads/2026/03/f7a3b2c1-xxxx.jpg"
  mimeType: string;
  sizeBytes: number;
  width?: number;
  height?: number;
}
```

### 컴포넌트 구조 (FSD)

| 계층 | 파일 | 역할 |
|---|---|---|
| `app` | `manage/assets/page.tsx` | 에셋 관리 라우트 (기존) |
| `features` | `asset-uploader/ui/asset-uploader.tsx` | 업로드 + 갤러리 오케스트레이션 (기존) |
| `features` | `asset-uploader/ui/upload-zone.tsx` | 드래그 앤 드롭 + 큐 (기존, 진행률 추가) |
| `features` | `asset-uploader/ui/asset-grid.tsx` | 갤러리 그리드 (기존, F-27 스펙) |
| `entities` | `asset/api.ts` | 업로드 API (기존, XHR 진행률 추가) |
| `entities` | `asset/model.ts` | Asset 타입 (기존) |

### 데이터 흐름

```
UploadZone
  ├─ 파일 추가 (드래그/선택)
  │   └─ 검증 → 큐에 추가 → blob 미리보기
  │
  ├─ [업로드] 클릭
  │   ├─ FormData 구성 (큐의 모든 파일)
  │   ├─ uploadWithProgress() → XHR + onprogress
  │   ├─ 진행률 UI 업데이트
  │   └─ 완료
  │       ├─ 성공 → 큐 비움 + 토스트 + 갤러리 React Query 무효화
  │       └─ 실패 → 에러 토스트 + 큐 유지
  │
  └─ 서버 처리
      ├─ @fastify/multipart 파싱
      ├─ 파일 검증 (MIME, 크기)
      ├─ image-size로 width/height 추출
      ├─ 파일 저장 (uploads/YYYY/MM/uuid.ext)
      └─ DB 레코드 생성 (storageKey, mimeType, sizeBytes, width, height)
```

## API 연동

| 메서드 | 경로 | 용도 | 비고 |
|---|---|---|---|
| POST | `/api/assets/upload` | 파일 업로드 (최대 5개) | 기존 - width/height 응답 추가 |
| GET | `/api/assets` | 에셋 목록 (페이지네이션) | 기존 |
| GET | `/api/assets/:id` | 에셋 메타데이터 | 기존 |
| DELETE | `/api/assets/:id` | 에셋 삭제 | 기존 |

### 서버 변경 필요사항

| 항목 | 설명 |
|---|---|
| `image-size` 패키지 추가 | width/height 자동 추출 |
| `FileStorageService.saveFile()` | 반환값에 width, height 추가 |
| `AssetService.uploadAsset()` | width, height를 DB에 저장 |
| `@fastify/static` 설정 | `maxAge: 2592000000`, `immutable: true` 추가 |

## 수용 기준

- [ ] 드래그 앤 드롭으로 파일을 업로드 영역에 추가할 수 있다
- [ ] 파일 선택 버튼으로 파일을 추가할 수 있다
- [ ] 큐에 추가된 파일의 미리보기가 표시된다
- [ ] 큐에서 개별 파일을 제거할 수 있다
- [ ] 전체 삭제 버튼으로 큐를 비울 수 있다
- [ ] 허용되지 않는 형식의 파일 추가 시 토스트 에러가 표시된다
- [ ] 10MB 초과 파일 추가 시 토스트 에러가 표시된다
- [ ] 6개 이상 파일 추가 시 토스트 에러가 표시된다
- [ ] 중복 파일 추가 시 토스트 에러가 표시된다
- [ ] 업로드 중 전체 진행률이 표시된다
- [ ] 업로드 중 큐 조작과 업로드 버튼이 비활성화된다
- [ ] 업로드 완료 시 큐가 비워지고 성공 토스트가 표시된다
- [ ] 업로드 실패 시 에러 토스트가 표시되고 큐가 유지된다
- [ ] 업로드된 이미지의 width/height가 DB에 자동 저장된다
- [ ] 업로드 응답에 width/height가 포함된다
- [ ] 정적 파일 응답에 `Cache-Control: public, max-age=2592000, immutable` 헤더가 포함된다
- [ ] 파일 드래그 시 업로드 영역에 시각 피드백 (테두리 하이라이트 + 메시지)이 표시된다
- [ ] 큐 미리보기에 파일 크기가 표시된다
- [ ] 서버에서 magic bytes 검증이 수행된다 (MIME 위조 차단)
- [ ] 접근성: 드래그 앤 드롭 영역에 키보드 포커스 가능, 파일 선택 aria-label (A-01 참조)
- [ ] Storybook story 작성 (F-38 참조)

## 에지 케이스

| 케이스 | 처리 |
|---|---|
| SVG에 viewBox 없음 | width/height null 유지 |
| image-size 파싱 실패 | width/height null, 업로드 자체는 성공 |
| 5개 초과 파일을 한번에 드래그 | 처음 5개만 추가, 나머지 무시 + 토스트 |
| 업로드 중 네트워크 끊김 | XHR onerror → 에러 토스트, 큐 유지 |
| 동일 파일을 수정 후 재업로드 | lastModified가 다르므로 중복 감지 통과 |
| 파일명에 특수문자 | UUID로 저장되므로 영향 없음 |
| 디스크 공간 부족 | 서버 500 → 에러 토스트 |
| 매우 큰 이미지 (50MP+) | image-size는 헤더만 읽으므로 문제 없음 |
| MIME 타입은 image/jpeg이지만 실제 PNG 파일 | magic bytes 검증 실패 → 400 에러 |
| 확장자를 .jpg로 바꾼 실행 파일 | magic bytes 불일치 → 400 에러 |

## 의존성

- Blocked by: F-19
- Blocks: F-27
