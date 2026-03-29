---
id: "012"
title: "패널/모달 닫힐 때 포커스 반환 - 트리거 요소 ref 패턴"
date: 2026-03-27
tags: ["#accessibility", "#focus-trap", "#wcag", "#react", "#useRef"]
related_issues: [185]
---

# 패널/모달 닫힐 때 포커스 반환 - 트리거 요소 ref 패턴

## 문제

조건부로 마운트/언마운트되는 슬라이드-인 패널(또는 모달)이 닫힐 때 포커스를 패널 내부 닫기 버튼에 반환하려 했으나, 패널이 `return null`로 언마운트되면 버튼도 DOM에서 제거된다. `useEffect`가 실행될 시점에 ref가 이미 `null`이어서 `focus()` 호출이 no-op이 되고 포커스가 `<body>`로 이동해 WCAG 2.4.3(포커스 순서) 위반이 발생했다.

```tsx
// 잘못된 패턴: 패널 내부 닫기 버튼에 ref
const closeBtnRef = useRef<HTMLButtonElement>(null);

useEffect(() => {
  if (!isSidebarOpen && didOpenRef.current) {
    closeBtnRef.current?.focus(); // 패널이 null을 반환하므로 이미 null
  }
}, [isSidebarOpen]);
```

## 해결

패널을 열었던 트리거(햄버거 버튼)에 ref를 달아야 한다. 트리거는 항상 마운트되어 있으므로 패널이 닫힌 후에도 `focus()`가 정상 동작한다.

```tsx
// 올바른 패턴: 항상 마운트된 트리거에 ref
const hamburgerBtnRef = useRef<HTMLButtonElement>(null);

useEffect(() => {
  if (isSidebarOpen) {
    didOpenRef.current = true;
  } else if (didOpenRef.current) {
    hamburgerBtnRef.current?.focus(); // 햄버거는 항상 마운트됨
  }
}, [isSidebarOpen]);

// Header에 ref 전달
<Header hamburgerRef={hamburgerBtnRef} ... />
```

## 핵심 원칙

- 조건부 마운트 컴포넌트(`if (!isOpen) return null`) 내부에는 포커스 반환 ref를 걸면 안 된다.
- 포커스 반환은 항상 마운트된 트리거(열기 버튼)를 대상으로 해야 한다.
- 이 패턴은 관리자 사이드바처럼 항상 마운트된 오버레이와는 다르다. 마운트 여부를 먼저 확인할 것.
