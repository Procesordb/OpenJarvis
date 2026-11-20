#!/usr/bin/env bash
# Created by the AGI PROCESOR project in 2026.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${AGI_PROCESOR_BACKUP_DIR:-/srv/agi-procesor/backups}"
RETENTION_DAYS="${AGI_PROCESOR_BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINATION="${BACKUP_DIR}/agi-procesor-state-${STAMP}.tar.gz"
PARTIAL="${DESTINATION}.partial"

case "${BACKUP_DIR}" in
  /srv/agi-procesor/backups | /srv/agi-procesor/backups/*) ;;
  *)
    echo "Refusing backup directory outside /srv/agi-procesor/backups" >&2
    exit 1
    ;;
esac
if ! [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "AGI_PROCESOR_BACKUP_RETENTION_DAYS must be a non-negative integer" >&2
  exit 1
fi

install -d -m 0700 "${BACKUP_DIR}"
trap 'rm -f -- "${PARTIAL}"' EXIT

docker compose \
  --project-directory "${DEPLOY_DIR}" \
  --env-file "${DEPLOY_DIR}/.env" \
  -f "${DEPLOY_DIR}/compose.yml" \
  exec -T agi-procesor python -c \
  'import sys, tarfile; archive=tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); archive.add("/home/openjarvis/.openjarvis", arcname=".openjarvis"); archive.close()' \
  > "${PARTIAL}"

chmod 0600 "${PARTIAL}"
mv -- "${PARTIAL}" "${DESTINATION}"
trap - EXIT
sha256sum "${DESTINATION}" > "${DESTINATION}.sha256"

find "${BACKUP_DIR}" -maxdepth 1 -type f \
  \( -name 'agi-procesor-state-*.tar.gz' -o -name 'agi-procesor-state-*.tar.gz.sha256' \) \
  -mtime "+${RETENTION_DAYS}" -delete

echo "Backup written: ${DESTINATION}"
