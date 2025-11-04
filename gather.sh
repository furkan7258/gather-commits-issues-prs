#!/usr/bin/env bash
set -euo pipefail

IMAGE="gather-cip"
CONTAINER_NAME="gather-cip-job"
DATA_DIR="${DATA_DIR:-$(pwd)}"
ENV_FILE="${ENV_FILE:-.env}"
EXTRA_ARGS=()

usage() {
  cat <<USAGE
Usage: $0 <start|run|resume|stop|status|logs|rebuild> [extra gather.py args]

Commands:
  start    Run in background (-d) with name ${CONTAINER_NAME}. Pass extra args to gather.py.
  run      Run in foreground (attached). Pass extra args to gather.py.
  resume   Start previously stopped/background container by name ${CONTAINER_NAME}.
  stop     Stop and remove the background container ${CONTAINER_NAME}.
  status   Show container status for ${CONTAINER_NAME}.
  logs     Show logs for ${CONTAINER_NAME}. Use: $0 logs -f
  rebuild  docker build -t ${IMAGE} .

Environment overrides:
  DATA_DIR   Host directory to mount at /data (default: current directory)
  ENV_FILE   .env file path (default: ./.env if exists; else omitted)

Examples:
  $0 start --only-issues
  $0 run   --only-prs -r /data/repos.json
  $0 logs -f
USAGE
}

ensure_image() {
  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "Docker image ${IMAGE} not found. Building..." >&2
    docker build -t "${IMAGE}" .
  fi
}

mount_env_args() {
  local args=("-v" "${DATA_DIR}:/data" "-e" "NON_INTERACTIVE=1" "-e" "LOG_PATH=/dev/stdout")
  if [[ -f "${ENV_FILE}" ]]; then
    args+=("--env-file" "${ENV_FILE}")
  fi
  printf '%s\n' "${args[@]}"
}

cmd_start() {
  ensure_image
  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    echo "Container ${CONTAINER_NAME} already exists. Use '$0 resume' to start it, or '$0 stop' then '$0 start'." >&2
    exit 1
  fi
  docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    $(mount_env_args | xargs -r) \
    "${IMAGE}" "${EXTRA_ARGS[@]}"
  echo "Started ${CONTAINER_NAME}. View logs: $0 logs -f"
}

cmd_run() {
  ensure_image
  docker run --rm \
    $(mount_env_args | xargs -r) \
    "${IMAGE}" "${EXTRA_ARGS[@]}"
}

cmd_resume() {
  if ! docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    echo "Container ${CONTAINER_NAME} does not exist. Use '$0 start' to create it." >&2
    exit 1
  fi
  docker start "${CONTAINER_NAME}"
  echo "Resumed ${CONTAINER_NAME}. View logs: $0 logs -f"
}

cmd_stop() {
  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
    docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    docker rm   "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    echo "Stopped and removed ${CONTAINER_NAME}."
  else
    echo "No such container ${CONTAINER_NAME}."
  fi
}

cmd_status() {
  docker ps -a --filter "name=${CONTAINER_NAME}"
}

cmd_logs() {
  docker logs "$@" "${CONTAINER_NAME}"
}

cmd_rebuild() {
  docker build -t "${IMAGE}" .
}

main() {
  if [[ $# -lt 1 ]]; then
    usage; exit 1
  fi
  local cmd="$1"; shift || true
  EXTRA_ARGS=($@)
  case "${cmd}" in
    start)  cmd_start;;
    run)    cmd_run;;
    resume) cmd_resume;;
    stop)   cmd_stop;;
    status) cmd_status;;
    logs)   cmd_logs "$@";;
    rebuild) cmd_rebuild;;
    -h|--help|help) usage;;
    *) echo "Unknown command: ${cmd}" >&2; usage; exit 1;;
  esac
}

main "$@"
