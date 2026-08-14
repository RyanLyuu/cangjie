# 错误分析工具使用说明

## 概述

`analyze_errors.py` 是 对项目翻译结果的自动错误分析工具，覆盖翻译错误分析的完整流程。

## 功能

| 章节 | 功能 | 说明 |
|------|------|------|
| TRANSLATION RESULT STATISTICS | 翻译结果统计 | 统计 completed / attempted / pending 片段数、耗时分布 |
| COMPILATION VALIDATION | 编译验证 | 在翻译后的 skeletons 目录下运行 `cjpm build`，输出编译通过/失败 |
| COMPILATION ERROR CATEGORIES | 错误模式分类 | 按 20+ 种 Cangjie 编译错误模式自动归类（syntax_error、undefined_identifier、hashable_error 等） |
| TOP ERROR CATEGORIES WITH EXAMPLES | 错误详情 | 每类错误展示最多 5 个具体示例（含文件名、片段名、错误摘要） |
| PER-FRAGMENT ERROR DETAIL | 逐片段错误 | 列出所有编译失败的片段及错误信息前 100 字 |
| RESIDUAL TODO IN .cj FILES | 残留 TODO 检查 | 扫描 skeleton 和 translations 目录下 .cj 文件中残留的 `throw Exception('TODO')` 占位符 |
| TRANSLATION LOG TRACKING | 翻译日志追踪 | 解析 `jansi_<model>_body.log`，统计编译/测试的 ✅❌ 次数和 ERROR 行 |
| PER-FRAGMENT DATA (CSV) | CSV 数据导出 | 每个片段一行，含 schema、class、fragment、status、compilation_outcome 等字段 |

## 使用方法

### 基本用法

```bash
export PYTHONPATH=$(pwd)

# 完整分析（含 cjpm build 编译验证）
python -m src.java.analysis.analyze_errors \
    --project jansi \
    --model gpt-4o-2024-11-20 \
    --temperature 0.0

# 不跑 cjpm build（cjpm 不在 PATH 或不想编译时）
python -m src.java.analysis.analyze_errors \
    --project jansi \
    --model gpt-4o-2024-11-20 \
    --temperature 0.0 \
    --skip-build
```

### 通过 Shell 脚本

```bash
# 完整分析
bash scripts/java/analyze_errors.sh jansi gpt-4o-2024-11-20 0.0

# 跳过编译验证
bash scripts/java/analyze_errors.sh jansi gpt-4o-2024-11-20 0.0 "" --skip-build

# 指定输出文件路径
bash scripts/java/analyze_errors.sh jansi gpt-4o-2024-11-20 0.0 "" /path/to/report.txt

# 使用 deepseek-chat 模型
bash scripts/java/analyze_errors.sh jansi deepseek-chat 0.0
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--project` | 是 | 项目名，如 `jansi` |
| `--model` | 是 | 模型名，如 `gpt-4o-2024-11-20`、`deepseek-chat` |
| `--temperature` | 是 | 温度值，如 `0.0` |
| `--suffix` | 否 | Schema 后缀，默认为空 |
| `--output` | 否 | 输出文件路径，默认自动生成到 `data/java/analysis/` |
| `--skip-build` | 否 | 跳过 `cjpm build` 编译验证步骤 |

## 输入文件

工具读取以下位置的数据：

| 数据 | 路径 | 说明 |
|------|------|------|
| Schema JSON | `data/java/schemas{suffix}/{model}/{temp}/{project}/*.json` | 每个片段的翻译状态、编译结果、测试结果 |
| Skeleton .cj | `data/java/skeletons/{project}/src/*.cj` | 原始骨架文件 |
| 翻译后 .cj | `data/java/skeletons/translations/{model}/{temp}/{project}/src/*.cj` | 实际翻译结果（cjpm build 在此目录运行） |
| 翻译日志 | `{project}_{model}_body.log` | 当前目录下的翻译过程日志 |

## 输出

- 自动保存到 `data/java/analysis/{project}_{model}_{temp}{suffix}_errors.txt`
- 同时打印到终端

## 错误分类体系

工具内置 20+ 种 Cangjie 编译错误模式：

| 类别 | 模式 | 典型原因 |
|------|------|---------|
| syntax_error | 通用语法错误 | `static` 误用、括号/分号语法差异、`if let` 等 |
| undefined_identifier | 未声明标识符 | `self` 不存在、缺少 import、类型映射遗漏 |
| type_mismatch | 类型不匹配 | 接口类型赋值给类类型、泛型参数不匹配 |
| hashable_error | Hashable 约束 | `HashMap<Any, V>` 应为 `HashMap<AnyHashable, V>` |
| init_keyword | init 关键字冲突 | Java 方法名 `init` 与仓颉构造器关键字冲突 |
| arg_count_mismatch | 参数数量错误 | 方法调用参数数量不匹配 |
| member_not_found | 成员未找到 | 调用了仓颉类型中不存在的方法 |
| override_error | 重载/重写冲突 | Java 方法重载在仓颉中不兼容 |
| import_error | import 错误 | 缺少或错误的 import 语句 |
| nested_class_error | 嵌套类错误 | Java 内部类未展平到顶层 |
| mutability_error | 不可变赋值 | `let` 声明的变量被重新赋值 |
| enum_error | 枚举映射错误 | Java `Enum` 类型未正确映射 |
| constructor_error | 构造器错误 | Java 构造函数 → 仓颉 `init()` 映射有误 |
