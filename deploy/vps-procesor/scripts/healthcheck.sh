#!/usr/bin/env bash
# Created by the AGI PROCESOR project in 2026.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${AGI_PROCESOR_ENV_FILE:-${DEPLOY_DIR}/.env}"

BINDING="$(docker compose \
  --project-directory "${DEPLOY_DIR}" \
  --env-file "${ENV_FILE}" \
  -f "${DEPLOY_DIR}/compose.yml" \
  port agi-procesor 8000)"

curl --fail --silent --show-error \
  --max-time 10 \
  "http://${BINDING}/health"
printf '\nAGI PROCESOR healthcheck passed at %s\n' "${BINDING}"
