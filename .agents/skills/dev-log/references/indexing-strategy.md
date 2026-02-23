# 인덱싱 전략

## 인덱스 갱신 규칙

### findings 추가 시
1. 기존 findings 파일 스캔 → 최대 순번 확인
2. `findings/findings.NNN-topic.md` 생성 (최대값 + 1)
3. `findings.index.md`에 항목 추가:
   - 번호 (NNN), 파일 경로, 날짜, 한줄 요약 (30자 이내), 키워드 (3-5개)

### progress 추가 시
1. 오늘 날짜의 progress 파일 존재 확인
2. **있으면** 기존 파일에 추가, **없으면** 새 파일 생성
3. `progress.index.md` **최상단**에 항목 추가:
   - 날짜, 파일 경로, 한줄 요약 (30자 이내), 태그 (3-5개)

### decisions 추가 시
1. 기존 decisions 파일 스캔 → 최대 순번 확인
2. `decisions/decision-NNN-topic.md` 생성 (최대값 + 1)
3. `decisions.index.md`에 항목 추가:
   - 번호 (NNN), 파일 경로, 날짜, 상태 (draft/accepted/rejected), 한줄 요약, 키워드
4. 상태 변경 시 인덱스의 상태 필드도 함께 갱신

## 순번 충돌 방지

findings / decisions 파일 생성 전:
1. 해당 디렉토리 리스트 확인
2. 파일명에서 순번 추출 (예: `findings.015-topic.md` → 15)
3. 최대 순번 + 1로 새 파일 생성
4. 인덱스에 순번 순서대로 정렬 유지
