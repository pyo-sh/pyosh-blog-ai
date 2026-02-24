# Progress: 2026-02-24

## 완료 작업
- [x] Issue #12 요구사항 분석 및 server 워크트리(`feat/issue-12-deploy-infra`) 생성 (#12)
- [x] Health Check 확장: `/api/health`, `/api/health/live`, `/api/health/ready` 추가 및 DB/uptime/memory/version 응답 반영 (#12)
- [x] DB 마이그레이션 자동화 스크립트 추가: `scripts/db-migrate.ts`, `scripts/db-migration-status.ts` + `package.json` 스크립트 등록 (#12)
- [x] GitHub Actions 워크플로 추가: `.github/workflows/db-migrate.yml` (main push/workflow_dispatch 시 마이그레이션 상태 확인 및 적용) (#12)
- [x] 환경 변수 샘플 파일 추가: `server/.env.example` (#12)
- [x] Health 엔드포인트 테스트 추가: `test/routes/health.test.ts` (#12)

## 발견 사항
- 워크트리 환경에서 외부 네트워크(DNS) 제한으로 npm registry 접근이 불가해 `pnpm install`, `vitest`, `compile:types` 재검증을 완료하지 못함.
- 기존 `compile:types`는 현재 환경의 TypeScript/의존성 상태에서도 Fastify 타입 파싱 에러가 재현되어, 이번 변경과 무관한 기존 환경 이슈 가능성이 높음.

## 이슈 및 해결
- **이슈**: `gh issue view` 초기 호출 실패 (api.github.com 연결 불가)
- **해결**: 권한 상승 실행으로 `--repo pyo-sh/pyosh-blog-be` 직접 조회해 Issue #12 요구사항 확보

- **이슈**: 워크트리에서 `pnpm install --frozen-lockfile` 실패 (`ENOTFOUND registry.npmjs.org`)
- **해결**: 테스트/타입체크는 블로킹 이슈로 기록하고, 코드 정합성은 정적 검토와 diff 검증으로 대체

## 다음 단계
- [ ] 네트워크 가능한 환경에서 `pnpm install --frozen-lockfile` 재시도
- [ ] `pnpm test` 및 `pnpm compile:types` 재검증
- [ ] `git push -u origin feat/issue-12-deploy-infra` 및 PR 생성 (`Closes #12`)

## 참고
- 관련 이슈: #12
