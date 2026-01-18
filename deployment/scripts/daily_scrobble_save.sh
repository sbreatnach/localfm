#!/usr/bin/env bash

PROJECT_DIR=$(dirname $(dirname $(dirname "$0")))
CUR_DATE=$(date '+%F')
source $HOME/.profile

pushd ${PROJECT_DIR}
just run-command import_scrobbles "${PROJECT_DIR}/scrobbles/scrobbles_${CUR_DATE}.json" database \
     --failed-scrobbles-file="${PROJECT_DIR}/scrobbles/failed_scrobbles_${CUR_DATE}.json"
popd
