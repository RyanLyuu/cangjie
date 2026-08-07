#!/usr/bin/env bash
# 调用日志转测试脚本，按给定标识处理单个日志文件。

set -euo pipefail

# $1 = name of log file or test identifier
python3 script.py "$1"
