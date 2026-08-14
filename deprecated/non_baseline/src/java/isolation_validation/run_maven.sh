#!/usr/bin/env bash
# 执行指定测试类和测试方法，用于 isolated validation 流程中的 Maven 校验。

set -euo pipefail

# $1 = fully-qualified test class
# $2 = test method
mvn clean install \
    -Drat.skip \
    -Dgpg.skip \
    "-Dtest=${1}#${2}"
