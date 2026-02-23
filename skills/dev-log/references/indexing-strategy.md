# 인덱싱 전략

## 왜 인덱스/폴더를 사용하는가?

- **토큰 효율성**: 대용량 문서를 전체 읽지 않고 필요한 부분만 선택적 참조
- **빠른 스캔**: 인덱스만 읽어 현재 작업과 관련된 항목 신속 파악
- **유지보수성**: 새 항목 추가 시 하위 파일만 생성하고 인덱스에 한 줄 추가
- **독립적 관리**: 각 파일이 독립적이므로 병렬 작업, 재정렬, 삭제가 용이

## 파일 읽기 규칙

### findings/, progress/, decisions/ 인덱스
1. **항상 인덱스 먼저 읽기**: `findings.index.md`, `progress.index.md`, `decisions.index.md`를 먼저 읽어라
2. **선택적 하위 파일 읽기**: 인덱스에서 현재 작업과 관련된 키워드/태그를 찾아 해당 하위 파일만 읽어라
3. **전체 읽기 금지**: 디렉토리의 모든 파일을 한 번에 읽지 마라

## 인덱스 갱신 규칙

### findings 추가 시
1. 기존 findings 파일들을 스캔하여 최대 순번 확인
2. `findings/findings.NNN-topic.md` 생성 (최대값 + 1)
3. `findings.index.md`에 항목 추가:
   - 번호 (NNN)
   - 파일 경로
   - 날짜
   - 한줄 요약 (30자 이내)
   - 키워드 (3-5개)

### progress 추가 시
1. 오늘 날짜의 progress 파일이 이미 있는지 확인
2. **있으면**: 기존 파일에 내용 추가
3. **없으면**: `progress/progress.YYYY-MM-DD.md` 생성
4. `progress.index.md` **최상단**에 항목 추가:
   - 날짜 (YYYY-MM-DD)
   - 파일 경로
   - 한줄 요약 (30자 이내)
   - 태그 (3-5개)

### decisions 추가 시
1. 기존 decisions 파일들을 스캔하여 최대 순번 확인
2. `decisions/decision-NNN-topic.md` 생성 (최대값 + 1)
3. `decisions.index.md`에 항목 추가:
   - 번호 (NNN)
   - 파일 경로
   - 날짜
   - 상태 (draft / accepted / rejected)
   - 한줄 요약 (30자 이내)
   - 키워드 (3-5개)
4. 상태 변경 시 인덱스의 상태 필드도 함께 갱신

## 검색 전략

### 키워드 기반 검색
1. 현재 작업의 핵심 키워드 추출 (예: "Drizzle", "인증", "라우팅")
2. findings.index.md / decisions.index.md에서 해당 키워드가 포함된 항목 찾기
3. 찾은 항목의 하위 파일만 읽기

### 날짜 기반 검색 (progress)
1. 최근 3개 항목만 읽어 현재 진행 상황 파악
2. 특정 날짜 범위의 작업 내역이 필요하면 해당 파일만 선택적 읽기

## 예시

### 좋은 패턴 ✓
```
1. findings.index.md 읽기
2. "Drizzle" 키워드 발견 → findings.003 확인
3. findings/findings.003-drizzle-vs-prisma.md만 읽기
```

### 나쁜 패턴 ✗
```
1. findings/ 디렉토리의 모든 파일 읽기 (토큰 낭비)
2. 인덱스 건너뛰고 바로 하위 파일 읽기 (맥락 없음)
```

## 순번 충돌 방지

### findings / decisions 파일
파일 생성 전 항상 다음을 실행:
1. 해당 디렉토리 리스트 확인
2. 파일명에서 순번 추출 (예: findings.015-topic.md → 15, decision-003-topic.md → 3)
3. 최대 순번 + 1로 새 파일 생성
4. 인덱스에 항목 추가 시 순번 순서대로 정렬 유지
