#!/bin/bash

# Usage: ./scripts/java/crawl_java_base.sh
# Crawl Java base module documentation for RAG type resolution

echo "Crawling java.base module documentation..."
export PYTHONPATH=$(pwd)
python src/java/crawler/crawl_java_package.py --module_name java.base
