# Decision 004: Admin Routes Must Not Render Public Header

## Metadata
- **Date**: 2026-04-10
- **Status**: accepted
- **Related Issue**: -

## Background
관리자 영역에서도 public 헤더가 남아 있어, `body > div > div.pt-14 > header > div` 구조가 admin 화면에 함께 렌더링되는 문제가 확인되었다.

관리자 라우트는 자체 chrome을 가지므로 public 헤더를 중복 노출하면 안 된다.

## Option Comparison

### Option A: admin route에서 public 헤더 주입을 명시적으로 제외
- **Pros**: 관리자 chrome이 단일화된다.
- **Pros**: route 책임이 명확해진다.
- **Pros**: admin 화면에서 불필요한 상단 여백과 중복 내비게이션이 사라진다.
- **Cons**: 전역 provider 또는 공용 shell의 route 분기 정리가 필요할 수 있다.
- **Cost/Complexity**: low

### Option B: public 헤더를 유지하되 admin chrome과 공존하게 둠
- **Pros**: 변경량이 적다.
- **Cons**: 중복 내비게이션과 상단 구조 충돌이 계속 남는다.
- **Cons**: 관리자 정보 구조가 불명확해진다.
- **Cost/Complexity**: low

## AI Recommendation
> Option A를 권장한다. `/manage` 이하 라우트는 public shell과 분리된 admin shell만 렌더링해야 한다.

## Final Decision
> 관리자 영역(`/manage` 이하)에서는 public `Header`를 렌더링하지 않는다.
>
> public 헤더 주입이 전역 provider 또는 공용 shell에 걸려 있더라도 admin route에서는 명시적으로 제외해, `body > div > div.pt-14 > header > div` 구조가 관리자 화면에 남지 않도록 한다.

## Follow-up Actions
- [ ] 관리자 영역에서 public `Header`가 렌더링되는 경로를 제거한다.
- [ ] admin route와 public route의 공용 provider 책임을 재정리한다.
- [ ] admin shell만 단독으로 노출되는지 확인한다.
