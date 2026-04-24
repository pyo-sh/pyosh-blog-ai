# Server Progress - 2026-04-24

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
