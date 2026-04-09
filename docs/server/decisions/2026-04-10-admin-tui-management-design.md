# Decision 001: Admin 계정 로컬 TUI 관리 스크립트 설계

**날짜**: 2026-04-10
**상태**: accepted
**태그**: #admin #tui #operations #scripts

## 배경

현재 [`hash-password.ts`](/workspace/server/scripts/hash-password.ts)는 Argon2id 해시만 출력하며, 실제 admin 계정 생성/수정/삭제는 운영자가 DB에 직접 SQL을 실행해야 한다. 이 방식은 다음 문제가 있다.

- 현재 등록된 admin 계정을 한 번에 확인하기 어렵다.
- 계정 생성, username 변경, 비밀번호 변경, 삭제가 모두 수작업 SQL에 의존한다.
- 운영 절차가 코드로 표준화되어 있지 않아 실수 가능성이 높다.

동시에 이 기능은 배포된 온라인 Admin UI에서는 제공하면 안 된다. admin 계정 관리까지 원격에서 가능해지면 권한 경계가 과도하게 넓어지기 때문이다.

## 결정

admin 계정 관리는 서버 API나 온라인 Admin 페이지가 아니라, `server/scripts` 아래의 로컬 실행 전용 TUI 스크립트로 제공한다.

기본 실행 방식은 다음과 같다.

```bash
pnpm tsx scripts/admin-manager.ts
```

이 스크립트는 `.env`의 DB 접속 정보를 사용해 직접 MySQL에 연결하고, 등록된 admin 목록 조회와 생성, 수정, 비밀번호 변경, 삭제를 수행한다.

## 목표

- 현재 존재하는 admin 계정을 즉시 조회할 수 있어야 한다.
- admin 생성, username 변경, 비밀번호 변경, 삭제를 한 흐름에서 처리할 수 있어야 한다.
- 온라인 노출 없이 로컬 운영 절차만 개선해야 한다.
- 위험 작업에는 재확인 단계를 두어 오조작을 줄여야 한다.

## 비목표

- 배포된 Admin 웹 페이지에서 admin 계정 관리 기능 제공
- 공개/내부 HTTP API 추가
- RBAC, 역할 분리, 다중 권한 체계 도입
- 외부 IAM 또는 시크릿 매니저 연동

## 실행 환경 정책

- 기본 실행 환경은 `development`다.
- 사용자가 필요하면 `NODE_ENV=production` 같은 방식으로 명시적으로 override 할 수 있다.
- DB 접속 정보는 기존 [`db-env.ts`](/workspace/server/scripts/db-env.ts) 헬퍼를 재사용한다.
- 이 스크립트는 서버 프로세스를 띄우지 않고 DB에 직접 연결한다.

예시:

```bash
pnpm tsx scripts/admin-manager.ts
NODE_ENV=production pnpm tsx scripts/admin-manager.ts
```

## 권한 및 보안 경계

- 스크립트 실행 권한을 가진 운영자는 DB 접근이 가능한 신뢰 주체로 간주한다.
- 별도의 추가 로그인이나 마스터 패스프레이즈는 두지 않는다.
- 대신 위험 작업에만 재확인을 둔다.

위험 작업 정책:

- 비밀번호 변경: 대상 username 재입력 + 새 비밀번호 2회 입력
- 삭제: 대상 username 재입력 + 최종 확인

추가 보안 원칙:

- 비밀번호 입력은 항상 마스킹한다.
- 평문 비밀번호는 로그나 화면에 출력하지 않는다.
- 해시는 기존 password helper와 동일한 Argon2id 옵션을 사용한다.

## UX 설계

첫 실행 시 TUI는 현재 admin 목록을 보여주고, 다음 작업으로 이동할 수 있어야 한다.

- 목록 조회
- 상세 보기
- 생성
- username 변경
- 비밀번호 변경
- 삭제
- 종료

목록 컬럼:

- `id`
- `username`
- `createdAt`
- `updatedAt`
- `lastLoginAt`

상세 보기에서는 위 필드를 더 읽기 쉽게 보여준다.

특수 상태:

- admin이 0명이어도 정상 상태로 취급한다.
- 이 경우 빈 목록 메시지를 보여주고 `생성`을 주요 액션으로 제시한다.
- 마지막 admin 삭제도 허용한다.

## 아키텍처

도메인 로직과 UI 로직을 분리한다.

예상 파일 구조:

- `scripts/admin-manager.ts`: 엔트리포인트
- `scripts/admin-manager/db.ts`: env 로드 및 Drizzle 연결
- `scripts/admin-manager/service.ts`: admin CRUD와 비밀번호 변경
- `scripts/admin-manager/tui.ts`: 메뉴, 입력, 출력, 확인 프롬프트
- `scripts/admin-manager/validators.ts`: username/password 입력 검증

핵심 원칙:

- DB 연결 로직은 UI에서 직접 다루지 않는다.
- CRUD 로직은 service 계층에 모은다.
- TUI는 service 호출과 사용자 입력 흐름만 담당한다.

이 구조를 택하면 이후 필요 시 비대화형 서브커맨드 CLI를 같은 service 위에 추가하기 쉽다.

## 데이터 작업 정의

지원 기능은 다음으로 제한한다.

### 1. 목록 조회

- 전체 admin를 username 오름차순 또는 id 오름차순으로 조회
- `passwordHash`는 절대 반환하거나 출력하지 않음

### 2. 생성

- `username` 중복 검사
- 새 비밀번호 2회 입력 확인
- Argon2id 해시 생성 후 저장

### 3. username 변경

- 대상 admin 선택
- 새 username 중복 검사
- 변경 후 즉시 목록/상세 반영

### 4. 비밀번호 변경

- 대상 admin 선택
- 대상 username 재입력으로 확인
- 새 비밀번호 2회 입력
- 성공 시 비밀번호 변경 완료 메시지 출력

### 5. 삭제

- 대상 admin 선택
- 대상 username 재입력으로 확인
- 마지막 admin도 삭제 가능

## 오류 처리

다음 오류를 명시적으로 처리한다.

- DB env 누락
- DB 연결 실패
- 대상 admin 없음
- username 중복
- 비밀번호 확인 불일치
- 사용자의 취소 입력
- 예상치 못한 DB 예외

TUI에서는 에러를 즉시 보여주고 프로세스를 종료하기보다 메뉴로 복귀시키는 것을 기본값으로 한다. 단, 초기 env 로드 실패나 DB 연결 실패처럼 시작 자체가 불가능한 오류는 종료한다.

## 대안 검토

### 대안 1. 온라인 Admin 페이지에 기능 추가

장점:

- 사용성이 좋고 접근이 쉽다.

단점:

- 배포된 환경에서 admin 계정 관리가 가능해져 공격면이 넓어진다.
- 현재 요구사항과 명시적으로 충돌한다.

채택하지 않음.

### 대안 2. 개별 단일 목적 스크립트 여러 개

예시:

- `create-admin.ts`
- `update-admin.ts`
- `delete-admin.ts`

장점:

- 구현은 단순하다.

단점:

- 사용 흐름이 분산된다.
- 목록 확인 후 후속 작업으로 이어지는 UX가 약하다.
- 공통 검증/출력이 중복되기 쉽다.

채택하지 않음.

### 대안 3. 로컬 전용 TUI 스크립트

장점:

- 온라인 노출이 없다.
- 운영 절차를 한 곳에 모을 수 있다.
- 현재 요구사항과 가장 직접적으로 맞는다.

채택.

## 테스트 전략

테스트는 UI 전체 E2E보다 service 계층 중심으로 둔다.

우선 검증 대상:

- 목록 조회 성공
- 생성 성공
- 생성 시 username 중복 실패
- username 변경 성공
- username 변경 시 중복 실패
- 비밀번호 변경 성공
- 삭제 성공
- 마지막 admin 삭제 허용

TUI 계층은 가능한 범위에서 입력 검증 및 확인 유틸을 분리해 단위 테스트한다.

## 결과

이 결정으로 admin 계정 관리는 온라인 기능과 분리된 로컬 운영 스크립트로 수렴한다. 운영자는 env 기반 DB 연결만으로 현재 admin 상태를 확인하고 안전한 재확인 절차를 거쳐 생성, 수정, 비밀번호 변경, 삭제를 수행할 수 있다.
