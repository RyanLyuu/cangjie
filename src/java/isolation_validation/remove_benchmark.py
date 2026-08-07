"""删除已知会引入依赖冲突的基准测试文件。"""

import os

PROJECT_ROOT = "."
BENCHMARK_FILE = os.path.join(PROJECT_ROOT, "src/test/java/org/apache/commons/csv/CSVBenchmark.java")

def remove_benchmark_file():
    """Removes CSV's benchmark file if it exists (containing 3rd part lib dependencies causing version conflicts)."""
    if os.path.exists(BENCHMARK_FILE):
        os.remove(BENCHMARK_FILE)
        print(f"Removed benchmark file: {BENCHMARK_FILE}")
    else:
        print("Benchmark file not found. Skipping removal.")

if __name__ == "__main__":
    remove_benchmark_file()
