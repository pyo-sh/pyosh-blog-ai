# Server Progress - 2026-04-24

## Issue #111 — 카테고리/태그 유니코드 slug 복구 및 관리자 category slug override (PR #112 머지)

**Status**: Merged

### What was done

한글·이모지 등 비-ASCII 이름으로 category/tag를 만들 때 빈 slug 또는 `-2` 형태 legacy slug가 생성되던 서버 버그를 복구했다. category 생성/수정은 유니코드 slug를 기본으로 사용하고, 빈 결과만 `id` fallback으로 처리하도록 정리했다. 또한 관리자 category API에 수동 slug override를 추가했다.

**파일 변경:**
- `src/shared/slug.ts`: `needsLegacySlugRepair()` 추가로 post/category/tag가 동일한 legacy slug 판정 규칙을 공유.
- `src/routes/categories/category.*`: create/update를 Unicode slug + retryable finalization 흐름으로 전환, 자동 충돌은 readable suffix(`slug-2`) 유지, manual override 충돌은 `400`으로 제어.
- `src/routes/tags/tag.service.ts`: tag 생성/legacy repair를 Unicode slug 기반으로 전환하고, 같은 요청 내 slug 충돌을 순차 생성으로 직렬화.
- `scripts/repair-taxonomy-slugs.ts`: dry-run 기본, `--apply`, `--target=categories|tags|all` 지원하는 one-off 복구 스크립트 추가.
- `test/routes/categories.test.ts`, `test/routes/tags.test.ts`, `test/shared/slug.test.ts`: 한글 slug, 빈 결과 `id` fallback, readable suffix 유지, legacy repair, colliding tag 생성 회귀 테스트 추가.

### Review

- 리뷰 1차: category 자동 충돌이 숫자 slug로 퇴행하고 repair 스크립트가 부분 적용될 수 있다는 warning → readable suffix 복원, in-memory reservation + single transaction apply로 수정.
- 리뷰 2차: category/tag 최종 slug update가 concurrent duplicate에서 raw DB error로 실패할 수 있다는 warning → duplicate-entry retry finalize 로직 추가.
- 리뷰 3차: 같은 요청 내 신규 tag 생성이 병렬 실행되어 colliding normalized slug에서 stale snapshot 문제를 일으킬 수 있다는 warning → `newNames` 생성 경로를 순차화하고 회귀 테스트 추가.
- 리뷰 4차: `0 critical / 0 warning / 0 suggestion` clean.

### Verification

- `pnpm compile:types`
- `pnpm test` → `19` files, `282` tests passed
- PR #112 squash merge → `main`

## Issue #108 — cloudflared trusted proxy 서브넷 고정 (PR #109 머지, v1.1.2)

**Status**: Merged

### What was done

배포 환경에서 관리자 로그인이 안되는 버그 재발을 방지했다. cloudflared 컨테이너 IP 변동에 강건하도록 `TRUSTED_PROXY_RANGES` 설정 가이드를 단일 IP에서 서브넷 CIDR 기반으로 전환했다.

**파일 변경:**
- `.env.example`: Docker Compose 배포 환경용 `TRUSTED_PROXY_RANGES` 서브넷 CIDR 예시(`172.28.0.0/24`)와 주석 가이드 추가. `external: true`의 lifecycle 의미와 실제 격리 근거를 분리 명시.
- `cloudflared/docker-compose.yml`: 사전 준비 6번으로 `blog_network` 고정 서브넷 생성 명령과 확인·재생성 절차 추가.
- `docker-compose.yml`: `blog_network` 생성 절차 참조 주석 한 줄 추가.
- `package.json`: `version` 1.1.0 → 1.1.2 (tag v1.1.1과 파일 불일치 동시 정정).

**운영 호스트 수동 작업 (배포 절차):**
1. `docker network rm blog_network` (컨테이너 stop 후)
2. `docker network create --driver bridge --subnet 172.28.0.0/24 blog_network`
3. `.env`에 `TRUSTED_PROXY_RANGES=172.28.0.0/24` 설정
4. cloudflared → blog_container 순서로 기동
5. 로그인 응답 `Set-Cookie`에 `Secure; Domain=.pyosh.com` 포함 확인

### Findings

- Findings 017 참고: Docker `external: true` 네트워크는 서브넷 고정 없이 생성하면 IP 대역이 재생성 시 변경됨 → `TRUSTED_PROXY_RANGES`는 단일 IP 대신 서브넷 CIDR로 지정해야 함.

### Review

- 1라운드 `[SUGGESTION] 1`: `external: true`를 "내부 전용"으로 표현해 트래픽 격리를 보장하는 것처럼 읽힐 수 있다는 지적 → 주석에 external:true의 실제 의미(lifecycle 선언) 명시로 수정 후 skip-review 머지.

### Verification

- PR #109 squash merge → `main`
- `git tag v1.1.2` → `origin` push 완료
