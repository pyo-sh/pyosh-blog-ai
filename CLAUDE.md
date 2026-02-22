# pyosh-blog - 전역 규칙

## 프로젝트 개요

이 프로젝트는 **모노레포(monorepo)** 구조로, 다음 3개 디렉토리로 구성됩니다:

- **client**: Next.js 프론트엔드 (블로그 공개 페이지 + 관리자 페이지)
- **server**: Fastify API 서버 (Drizzle ORM + MySQL)
- **docs**: 프로젝트 메모리 및 문서 저장소 (client/server 분리)

## 디렉토리 구조

```
pyosh-blog/
├── .claudeignore # 무시 패턴
├── CLAUDE.md # (현재 파일) 전역 규칙
├── .claude/
│ └── settings.local.json # 권한 설정
├── docs/
│ ├── client/ # client 작업 메모리
│ │ ├── tasks.md
│ │ ├── progress.index.md
│ │ ├── findings.index.md
│ │ ├── progress/
│ │ └── findings/
│ └── server/ # server 작업 메모리
│ │ ├── tasks.md
│ │ ├── progress.index.md
│ │ ├── findings.index.md
│ │ ├── progress/
│ │ └── findings/
├── client/
│ ├── CLAUDE.md # client 전용 규칙 (gitignore)
│ └── ...
├── server/
│ ├── CLAUDE.md # server 전용 규칙 (gitignore)
│ └── ...
└── pyosh-blog.code-workspace
```

## 무시 규칙

- `@.claudeignore` 참조

## 작업 선택 규칙

## 공통 개발 원칙

- **TypeScript Strict Mode** 사용
- **pnpm** 패키지 매니저
- **ESLint + Prettier** 자동 포맷팅

## 권한 설정

- `@.claude/settings.local.json` 참조

