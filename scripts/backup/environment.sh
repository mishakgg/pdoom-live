#!/usr/bin/env bash
# lib.sh must be sourced first. Parse KEY=VALUE data; never source an env file.
# Production defaults come from the validated file. Throwaway drills explicitly
# opt into process mode; CLI options are parsed afterward and remain overrides.
case "${PDOOM_OPS_ENV_MODE:-file}" in
  file)
    "$ROOT/scripts/deploy/check-env.sh" "$ENV_FILE" >/dev/null
    load_env_file
    ;;
  process) ;;
  *) die "PDOOM_OPS_ENV_MODE must be file or process" ;;
esac
