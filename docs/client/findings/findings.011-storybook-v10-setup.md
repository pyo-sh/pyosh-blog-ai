---
id: "011"
title: "Storybook v10 설정 시 발생하는 비직관적 이슈"
date: 2026-03-27
tags: ["#storybook", "#msw", "#tanstack-query", "#typescript"]
---

# Storybook v10 설정 시 발생하는 비직관적 이슈

이슈 #180 ([F-38] Storybook 환경 구성) 구현 중 Storybook v10에서 발생한 세 가지 비직관적 이슈를 정리한다.

## 1. `@storybook/addon-essentials`가 v10에 존재하지 않음

스펙 문서는 Storybook v8 기준으로 작성되었으나 pnpm이 `storybook@10.x`를 설치했다. v10에서는 `@storybook/addon-essentials`(controls, actions, viewport, backgrounds 등)가 `storybook` 코어 패키지에 통합되었다. 별도 설치 시 v8.x가 설치되어 peer dependency 충돌이 발생한다.

**해결:** `@storybook/addon-essentials`를 제거하고 `main.ts` addons 목록에서도 삭제. 코어에 이미 포함되어 있으므로 동작에 영향 없음.

## 2. `tsconfig.json`의 `moduleResolution: node`가 Storybook v10 패키지와 호환되지 않음

`tsconfig.json`에 `stories/`와 `.storybook/`을 `include`에 추가하면 `@storybook/react` 타입이 해석되지 않는다. Storybook v10 패키지는 `package.json exports` 필드를 사용하는데, `moduleResolution: node`는 이를 지원하지 않는다.

**해결:** 별도 `tsconfig.storybook.json`을 생성하고 `moduleResolution: bundler`로 설정. `main.ts`에서 `typescript.reactDocgenTypescriptOptions.tsconfigPath`로 참조. 프로덕션 `tsconfig.json`은 변경하지 않음.

```json
// tsconfig.storybook.json
{
  "extends": "./tsconfig.alias.json",
  "compilerOptions": {
    "moduleResolution": "bundler",
    "jsx": "react-jsx"
  },
  "include": ["stories", ".storybook"]
}
```

## 3. `QueryClient` 싱글톤 / 직접 생성 패턴이 스토리 간 캐시를 오염시킴

**싱글톤 패턴** (모듈 레벨 생성): `staleTime: Infinity` + 싱글톤 조합으로 Default 스토리를 본 후 Empty 스토리로 이동하면 캐시된 데이터가 MSW 빈 응답을 무시한다.

**직접 생성 패턴** (decorator 함수 내 `new QueryClient()`): 스토리 마운트당 한 번 생성되지만 Storybook이 re-render를 트리거할 때(HMR, arg 변경 등)마다 새 인스턴스가 생성되어 캐시가 초기화된다.

**해결:** `useState` factory 패턴을 사용하여 스토리 마운트당 한 번만 생성하고 re-render 시 유지한다.

```tsx
(Story) => {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    })
  );
  return (
    <QueryClientProvider client={queryClient}>
      <Story />
    </QueryClientProvider>
  );
},
```

## 4. MSW `initialize()`의 기본 `onUnhandledRequest` 설정

기본값은 `warn`으로 Storybook 내부 HMR 요청, 에셋 로드 등이 콘솔을 오염시킨다. `bypass`로 설정하면 핸들러가 없는 요청은 네트워크로 통과시킨다.

```ts
initialize({ onUnhandledRequest: "bypass" });
```
