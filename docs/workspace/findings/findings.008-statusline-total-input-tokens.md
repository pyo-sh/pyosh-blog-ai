# Claude Code statusLine의 total_input_tokens 부정확 문제

## Metadata
- **Date**: 2026-03-04
- **Related Issue**: #42

## Problem

Claude Code statusLine JSON의 `context_window.total_input_tokens` 필드가 실제 context window 사용량을 정확히 반영하지 않음. 시스템 프롬프트 (~3k), 도구 정의 (~15k), 메모리 (~300), git status/env block 등 (~2k)이 제외되어 실제 사용량의 일부만 보고됨.

## Research

### total_input_tokens (부정확)

statusLine JSON에서 직접 제공하는 값. 대화 텍스트 정도만 포함.
- 대화 초반: 0-2k
- 대화 중반: 실제 대비 ~20k 이상 과소 보고

### transcript JSONL usage (정확)

API 응답의 usage 필드에서 직접 계산:
```jq
(.message.usage.input_tokens // 0) +
(.message.usage.cache_read_input_tokens // 0) +
(.message.usage.cache_creation_input_tokens // 0)
```
시스템 프롬프트, 도구, 메모리 포함된 전체 input tokens 반영.

## Decision

transcript JSONL의 마지막 API 응답에서 usage를 읽는 방식 채택. `context-bar.sh`가 이미 이 방식을 사용 중이었으며, agent-tracker도 동일하게 변경.

`tail -n 200`으로 부분 읽기하여 대화가 길어져도 성능을 O(고정)으로 유지.

## References

- https://github.com/anthropics/claude-code/issues/13652
- `scripts/context-bar.sh:100-102` - 기존 주석에 이 문제가 문서화됨
