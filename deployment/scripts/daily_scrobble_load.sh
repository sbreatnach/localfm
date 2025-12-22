#!/usr/bin/env bash

PROJECT_DIR=$(dirname $(dirname $(dirname "$0")))
CUR_DATE=$(date '+%F')

pushd ${PROJECT_DIR}
  just run-command import_scrobbles lastfm scrobbles_${CUR_DATE}.json
popd
