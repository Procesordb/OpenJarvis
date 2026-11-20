#!/usr/bin/env bash
# Created by the AGI PROCESOR project in 2026.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE_INPUT="${1:-${AGI_PROCESOR_ENV_FILE:-${DEPLOY_DIR}/.env}}"

if [[ ! -f "${ENV_FILE_INPUT}" ]]; then
  echo "Environment file not found: ${ENV_FILE_INPUT}" >&2
  exit 1
fi
ENV_FILE="$(cd -- "$(dirname -- "${ENV_FILE_INPUT}")" && pwd)/$(basename -- "${ENV_FILE_INPUT}")"

if [[ "$(basename -- "${ENV_FILE}")" != ".env.example" ]] && \
   grep -Eq '(^|=)CHANGE_ME([_=]|$)' "${ENV_FILE}"; then
  echo "Replace every CHANGE_ME value before deployment." >&2
  exit 1
fi

if [[ "$(basename -- "${ENV_FILE}")" != ".env.example" ]]; then
  API_KEY_LINE="$(grep -E '^OPENJARVIS_API_KEY=' "${ENV_FILE}" | tail -n 1 || true)"
  API_KEY="${API_KEY_LINE#*=}"
  if ! [[ "${API_KEY}" =~ ^[[:xdigit:]]{64}$ ]] && \
     ! [[ "${API_KEY}" =~ ^oj_sk_[A-Za-z0-9_-]{43}$ ]]; then
    echo "OPENJARVIS_API_KEY must be 64 hex characters or an oj_sk_ key." >&2
    exit 1
  fi
  if [[ "$(stat -c '%a' "${ENV_FILE}")" != "600" ]]; then
    echo "Set mode 0600 on ${ENV_FILE}." >&2
    exit 1
  fi
fi

command -v docker >/dev/null || {
  echo "docker is required" >&2
  exit 1
}

bash -n "${SCRIPT_DIR}/backup.sh"
bash -n "${SCRIPT_DIR}/healthcheck.sh"
bash -n "${SCRIPT_DIR}/validate.sh"

AGI_PROCESOR_ENV_FILE="${ENV_FILE}" docker compose \
  --project-directory "${DEPLOY_DIR}" \
  --env-file "${ENV_FILE}" \
  -f "${DEPLOY_DIR}/compose.yml" \
  config --quiet

echo "Compose and shell configuration validated."
echo "Run 'sudo nginx -t' after installing the nginx site."
