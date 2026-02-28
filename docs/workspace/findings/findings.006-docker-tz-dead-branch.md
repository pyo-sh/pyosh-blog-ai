# Docker 컨테이너 타임존 UTC 고정 버그

## Metadata
- **Date**: 2026-03-01
- **Related Issue**: N/A

## Problem

Docker 컨테이너 타임존이 `.env`에 TZ를 설정하지 않으면 항상 UTC로 유지됨.
ARCHITECTURE.md에는 기본값 `Asia/Seoul`로 문서화되어 있지만 실제 동작하지 않음.

## Research

### 원인 1: `docker-compose.yaml` 빈 기본값

```yaml
environment:
  - TZ=${TZ:-}  # .env에 TZ 없으면 빈 문자열 전달
```

`${TZ:-}`는 빈 문자열이 기본값. 문서화된 `Asia/Seoul`과 불일치.

### 원인 2: `entrypoint.sh` 데드 브랜치

```bash
if [ -n "$TZ" ]; then          # TZ="" → false (빈 문자열)
  # ...
elif [ ! -f /etc/localtime ]; then  # Ubuntu 24.04는 항상 존재 → false
  # DEFAULT_TZ="Asia/Seoul" 적용 (도달 불가!)
fi
```

- `$TZ`가 빈 문자열 → 첫 번째 분기 실패
- Ubuntu 24.04 base image에 `/etc/localtime`이 UTC로 이미 존재 → elif 조건도 false
- 결과: 아무 분기도 실행되지 않고 UTC 유지

### 호스트 TZ 자동 감지 검토

컨테이너 내부에서 호스트 타임존을 읽는 방법:
1. **Volume mount** (`/etc/localtime:/etc/host-localtime:ro`) — 호스트에 파일 없으면 docker-compose 시작 실패
2. **호스트 측 스크립트** — `TZ=$(detect-tz.sh) docker compose up` — 별도 스크립트 의존성 발생
3. **`.env` 수동 설정 + 기본값** — 가장 단순, 호스트 자동 감지는 포기

## Decision

`.env` 수동 + Seoul 기본값 방식 채택.

- `docker-compose.yaml`: `TZ=${TZ:-Asia/Seoul}`로 기본값 명시
- `entrypoint.sh`: 데드 브랜치 제거, zoneinfo 파일 존재 검증 추가
- 호스트 자동 감지는 직관성 부족으로 미적용

## References

- `tools/docker/docker-compose.yaml` — TZ 환경변수 설정
- `tools/docker/entrypoint.sh` — 타임존 적용 로직
- `tools/ARCHITECTURE.md` — 환경변수 문서
