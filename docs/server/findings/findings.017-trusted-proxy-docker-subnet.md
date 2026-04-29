# Findings 017: Trusted Proxy — Docker 네트워크 서브넷 고정

**날짜**: 2026-04-24
**태그**: #trusted-proxy #docker #cloudflared #session-cookie #deployment
**관련 Issue**: #108

## 📝 요약

`TRUSTED_PROXY_RANGES`에 cloudflared 컨테이너의 특정 IP를 단일 값으로 넣으면,
Docker 네트워크가 재생성될 때마다 IP가 바뀌어 trusted proxy 체크를 통과하지 못한다.
서브넷 CIDR 전체를 고정 값으로 등록하면 IP 변동에 강건해진다.

## 🎯 증상 및 원인

### 증상

배포 환경에서 관리자 로그인은 200을 반환하지만 세션 쿠키가 브라우저에 저장되지 않아 즉시 로그아웃 상태가 된다. (PR #106/#107, v1.1.1에서 첫 발생 후 수정; v1.1.2에서 재발 방지)

### 연쇄 구조

```
cloudflared IP 변경
  → isTrustedProxyPeer(remoteAddress) === false   (src/app.ts:112)
    → onRequest 훅이 X-Forwarded-Proto 헤더 삭제  (src/app.ts:134-147)
      → Fastify가 요청을 HTTP로 간주
        → session cookie에 Secure 속성 미부여
          → 브라우저가 HTTPS 페이지에서 쿠키 수신 거부
            → /auth/me 인증 실패 → 로그인 실패
```

### 근본 원인

`blog_network`가 `external: true`로 선언되어 있어 `docker network create` 시 서브넷을 명시하지 않으면 Docker가 임의 대역을 할당한다. 네트워크 재생성 시 서브넷과 컨테이너 IP가 달라지므로, 이전에 `.env`에 기록한 단일 IP 값이 맞지 않는다.

## 🔧 해결 방법

### 네트워크 서브넷 고정

```bash
docker network create --driver bridge --subnet 172.28.0.0/24 blog_network
```

재생성 전 서브넷 확인:
```bash
docker network inspect blog_network --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

### TRUSTED_PROXY_RANGES를 서브넷 CIDR로 지정

```
# .env (production)
TRUSTED_PROXY_RANGES=172.28.0.0/24
```

단일 IP(`172.x.x.x/32`)가 아닌 서브넷 전체를 지정하면 Docker가 컨테이너에 할당하는 IP가 바뀌어도 재발하지 않는다.

## ⚠️ 주의: `external: true`의 의미

Docker Compose의 `external: true`는 "이 네트워크는 compose 바깥에서 미리 생성·관리된다"는 lifecycle 선언일 뿐, 트래픽 격리(network isolation)를 보장하지 않는다. 실제 격리는 blog_container가 외부 포트를 노출하지 않고 blog_network에만 연결되어 있다는 구성에서 비롯된다.

## ✅ 적용 결과

| 파일 | 변경 |
|------|------|
| `.env.example` | 서브넷 CIDR 예시 + external:true 의미 명시 |
| `cloudflared/docker-compose.yml` | 사전 준비 6번: 네트워크 생성 절차 추가 |
| `docker-compose.yml` | cloudflared 주석 참조 한 줄 추가 |
| `package.json` | 1.1.0 → 1.1.2 |
