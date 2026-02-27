#!/bin/bash
set -e

# .bash_aliases 로드 (dev-update 함수 사용)
[ -f /home/dev/.bash_aliases ] && . /home/dev/.bash_aliases

# 도구 업데이트
dev-update

# 기존 명령 실행 (TPM 설치 → tmuxinator → tail)
exec "$@"
