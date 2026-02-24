# Progress: 2026-02-24

## 완료 작업
- [x] Issue #12 요구사항 분석 및 server 워크트리(`feat/issue-12-deploy-infra`) 생성 (#12)
- [x] Health Check 확장: `/api/health`, `/api/health/live`, `/api/health/ready` 추가 및 DB/uptime/memory/version 응답 반영 (#12)
- [x] DB 마이그레이션 자동화 스크립트 추가: `scripts/db-migrate.ts`, `scripts/db-migration-status.ts` + `package.json` 스크립트 등록 (#12)
- [x] GitHub Actions 워크플로 추가: `.github/workflows/db-migrate.yml` (main push/workflow_dispatch 시 마이그레이션 상태 확인 및 적용) (#12)
- [x] 환경 변수 샘플 파일 추가: `server/.env.example` (#12)
- [x] Health 엔드포인트 테스트 추가: `test/routes/health.test.ts` (#12)
- [x] PR #19 3차 리뷰 반영: env 로더 중복 제거(`src/shared/env-loader.ts` 추출), `tsconfig.json`에 `scripts` 포함, migration pending=0 시 Apply step skip 조건 추가 (#12)
- [x] PR #19 제안 반영: `/api/health`·`/api/health/ready` 공통 상태 계산 로직을 `health.service.ts`로 통합 (`getHealthStatus`) (#12)
- [x] PR #19 최종 리뷰 반영: `main` 머지 충돌(`src/app.ts`) 해결 + `/api/health`에 메모리 사용량 응답 복원 + 관련 테스트 기대값 정렬 (#12)

## 발견 사항
- 워크트리 환경에서 외부 네트워크(DNS) 제한으로 npm registry 접근이 불가해 `pnpm install`, `vitest`, `compile:types` 재검증을 완료하지 못함.
- 기존 `compile:types`는 현재 환경의 TypeScript/의존성 상태에서도 Fastify 타입 파싱 에러가 재현되어, 이번 변경과 무관한 기존 환경 이슈 가능성이 높음.
- `pnpm db:migrate:status -- --pending-only` 형태로 pending 건수를 숫자 단일 출력으로 받아 GitHub Actions 조건 분기에 안전하게 사용 가능함.
- `main`과 PR 브랜치가 `src/app.ts`에서 충돌했으며, tags 라우트 추가 변경과 health-check 변경을 함께 반영하는 방식으로 충돌 해소 가능함.

## 이슈 및 해결
- **이슈**: `gh issue view` 초기 호출 실패 (api.github.com 연결 불가)
- **해결**: 권한 상승 실행으로 `--repo pyo-sh/pyosh-blog-be` 직접 조회해 Issue #12 요구사항 확보

- **이슈**: 워크트리에서 `pnpm install --frozen-lockfile` 실패 (`ENOTFOUND registry.npmjs.org`)
- **해결**: 테스트/타입체크는 블로킹 이슈로 기록하고, 코드 정합성은 정적 검토와 diff 검증으로 대체

- **이슈**: `scripts/db-env.ts`의 env 파일 로딩 로직이 `src/shared/env.ts`와 분리 관리되어 변경 시 drift 위험
- **해결**: `src/shared/env-loader.ts`로 로딩 로직을 단일화하고 server 런타임/스크립트 양쪽에서 공용 사용

- **이슈**: PR #19가 `mergeable=CONFLICTING` 상태여서 GitHub merge 불가
- **해결**: `origin/main` 병합 후 `src/app.ts` 충돌 수동 해결, 리뷰 지적사항(health memory requirement) 동시 반영 후 커밋

## 기술 결정
- `.github/workflows/db-migrate.yml`에서 migration 상태 확인 후 `pending_count != 0`일 때만 Apply를 실행하도록 변경하여, main push마다 불필요한 프로덕션 DB 연결을 줄이기로 결정
- `/api/health`의 메모리 필드는 이전 리뷰에서 정보노출 위험으로 제거된 상태를 유지하고, 이번 라운드에서는 중복 핸들러 로직 정리에 집중
- Issue #12 완료기준을 우선해 `/api/health` 응답에 메모리 사용량을 다시 포함하기로 결정하고, 보안상 민감 메시지(DB 에러 원문)는 계속 비노출 정책 유지

## 다음 단계
- [ ] 네트워크 가능한 환경에서 `pnpm install --frozen-lockfile` 재시도
- [ ] `pnpm test` 및 `pnpm compile:types` 재검증
- [ ] `git push -u origin feat/issue-12-deploy-infra` 및 PR 생성 (`Closes #12`)

## 참고
- 관련 이슈: #12
