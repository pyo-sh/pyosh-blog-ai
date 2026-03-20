---
name: supanova-design-skill
description: Supanova Design Skill 추천 조합 로더. 상황에 맞는 서브스킬 조합을 자동으로 선택해 규칙을 적용한다. 새 랜딩페이지: taste + output. 최고 품질: taste + soft + output. 기존 페이지 업그레이드: redesign.
---

# Supanova Design Skill - 조합 로더

## 역할

이 스킬은 Supanova 서브스킬들의 조합을 자동 선택하고 규칙을 적용하는 메타 스킬이다.
직접 규칙을 정의하지 않고, 아래 경로의 SKILL.md 파일들을 Read 도구로 읽어 적용한다.

## 서브스킬 경로

```
/workspace/.agents/skills/taste-skill/SKILL.md
/workspace/.agents/skills/soft-skill/SKILL.md
/workspace/.agents/skills/output-skill/SKILL.md
/workspace/.agents/skills/redesign-skill/SKILL.md
```

## 추천 조합 (README 기준)

| 상황 | 로드할 스킬 |
|------|------------|
| 새 랜딩페이지 생성 | `taste-skill` + `output-skill` |
| 기존 페이지 업그레이드 | `redesign-skill` |
| 최고 퀄리티 | `taste-skill` + `soft-skill` + `output-skill` |

## 실행 절차

1. 사용자의 요청을 분석해 위 표에서 맞는 조합을 선택한다.
   - 새로 만드는 랜딩페이지 → taste + output
   - 기존 HTML/페이지를 개선하는 요청 → redesign
   - 사용자가 "최고 퀄리티", "premium", "고품질" 등을 언급 → taste + soft + output
   - 조합이 명확하지 않으면 사용자에게 확인 후 진행한다.

2. 선택한 스킬의 SKILL.md 파일들을 Read 도구로 순서대로 읽는다.

3. 읽은 내용의 모든 규칙을 이번 작업에 전면 적용한다.
   - 각 스킬의 금지 패턴, 디자인 규칙, 출력 규칙을 모두 준수한다.
   - 스킬 간 충돌이 있으면 나중에 읽은 스킬의 규칙을 우선한다.

4. 적용할 조합과 각 스킬의 핵심 규칙을 사용자에게 간단히 안내한 뒤 작업을 시작한다.

## 개별 스킬 직접 호출

특정 스킬만 적용하려면 개별 스킬을 직접 호출할 수 있다.

- `/taste-skill` - 메인 디자인 엔진
- `/soft-skill` - 프리미엄 에스테틱 (Double-Bezel, 스프링 애니메이션)
- `/output-skill` - 완전한 HTML 출력 강제 (플레이스홀더 금지)
- `/redesign-skill` - 기존 페이지 업그레이드
