#!/usr/bin/env bash
set -x

docker --version
docker-compose --version

export COMPOSE_PROJECT_NAME=$BUILD_TAG
docker-compose up --build --detach --no-color
docker-compose run -e LOCAL_USER_ID=`id -u $USER` api waldur-test
result=$?
docker-compose down &> /dev/null || true &> /dev/null
exit $result
