#!/usr/bin/env bash

PROJECT_DIR=$(dirname "$(dirname "$(dirname "$0")")")
CUR_DATE=$(date '+%F')
[ -f "$HOME/.profile" ] && source "$HOME/.profile"

pushd "${PROJECT_DIR}" || exit
  just run-command import_scrobbles lastfm "${PROJECT_DIR}/scrobbles/scrobbles_${CUR_DATE}.json"
popd || exit
