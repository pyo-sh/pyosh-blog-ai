# Task 08: 로깅 체계화

> 구조화된 로깅(pino) 도입 및 에러 트래킹 설정

## 선행 조건

- [x] Fastify 전환 완료 (Fastify 내장 pino 활용 가능)

## 작업 항목

### 1. 로깅 설정

- [ ] **Fastify 내장 pino 로거 설정 최적화**
  - 개발 환경: pino-pretty (human-readable)
  - 프로덕션: JSON 포맷 (파싱 용이)
- [ ] **로그 레벨 환경별 분리**
  - development: debug
  - production: info
  - test: warn

### 2. 요청/응답 로깅

- [ ] **요청 로그 표준화**
  - method, url, statusCode, responseTime
  - 민감 정보 마스킹 (Authorization, Cookie 등)
- [ ] **에러 로그 강화**
  - stack trace 포함
  - 요청 컨텍스트 (userId, IP) 포함

### 3. 에러 트래킹 (선택)

- [ ] **외부 에러 트래킹 서비스 연동 검토**
  - Sentry vs 자체 로그 수집
- [ ] **uncaughtException / unhandledRejection 핸들링**

## 검증

- [ ] 개발 환경에서 읽기 쉬운 로그 출력
- [ ] 프로덕션 환경에서 JSON 로그 출력
- [ ] 에러 발생 시 컨텍스트 포함 확인
- [ ] 민감 정보 마스킹 확인
