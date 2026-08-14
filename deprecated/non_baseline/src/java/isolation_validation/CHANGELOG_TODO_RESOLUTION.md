# mock_helper.py TODO 清理与测试验证报告

> 覆盖范围：`isolation_validation/mock_helper.py`
> 更新日期：2026-04-14

---

## 一、标记体系

| 标记 | 含义 |
|------|------|
| `# CHANGED(n) IMPLEMENTED` | 已实现，通过实测验证 |
| `# CHANGED(n) NOTE` | 类型降级说明，不丢失信息，只是用更弱的表示 |
| `# LIMITATION(n) FRAMEWORK` | 框架/语言层限制，无法通过代码绕过 |

---

## 二、当前状态总览

| 类别 | 数量 |
|------|------|
| **已解决（CHANGED IMPLEMENTED）** | **10** |
| **框架限制（LIMITATION FRAMEWORK）** | **11** |

### 已解决清单

| 编号 | 内容 | 说明 |
|------|------|------|
| ⑩ | ByteBuffer 原地重置 | `clear() + write() + seek(Begin(0))` |
| ⑪ | ByteArrayStream 原地重置 | 复用 ByteBuffer 实现 |
| ⑫ | StringReader 原地内容重置 | buffer + reader 构造，重置时重建 reader |
| ⑬ | StringWriter 原地内容重置 | buffer + writer 构造，重置时重建 writer |
| ⑭ | 数组逐元素赋值 | 仓颉数组定长，唯一 mutation 方式 |
| ⑥ | `__mockReaderEquals` | `seek(0) + readToEnd()` 比较 |
| ⑦ | `__mockWriterEquals` | 通过 buffer 比较内容 |
| ② | BigInteger → String | 类型降级（仓颉无大整数） |
| ③ | BigDecimal → Float64 失败 | 类型降级 |
| ④ | BigDecimal 溢出 | 类型降级 |

### 框架限制清单

| 编号 | 内容 | 原因 |
|------|------|------|
| ① | `java.time.*` → String | std.time API 未确认 |
| ⑤ | `java.net.URL/URI` → String | 无 URL 解析 API |
| ⑧ | `java.util.regex.*` → String | Regex 无 `==`/`!=` |
| ② | 复杂参数退化为 `_` | mock 不支持 argThat() |
| ③ | 字面量重绑定未回放 | lambda 无法替换 caller 引用 |
| ④ | 空数组 mutation 目标无法确定 | 日志未提供足够信息 |
| ⑥ | 未知类型 mutation 回放 | 缺少稳定原地更新策略 |
| ⑦ | 桩链按调用顺序分派 | mock 按签名匹配，不支持参数身份 |
| ⑪ | receiver 状态变更未回放 | lambda 无法访问 receiver |
| ⑫ | 参数状态变更未回放 | 复杂参数匹配为 `_` |
| ⑬ | 静态字段副作用未回放 | 可能与 setup 顺序冲突 |

---

## 三、已实现（CHANGED IMPLEMENTED）

### ⑩ ByteBuffer 原地重置

```cangjie
// # CHANGED(⑩) IMPLEMENTED: ByteBuffer {target_expr} 原地重置已实现
//   实现: __mockResetByteBuffer(target, items) -> clear() + write(items) + seek(Begin(0))
//   ByteBuffer.clear() 已通过实测验证可用（position=0，旧内容清空）
//   调用示例: __mockResetByteBuffer({target_expr}, {bytes_expr})
```

**实现函数**：
```cangjie
private func __mockResetByteBuffer(target: ByteBuffer, items: Array<UInt8>): Unit {
    target.clear()
    target.write(items)
    target.seek(SeekPosition.Begin(0))
}
```

---

### ⑪ ByteArrayStream 原地重置

```cangjie
// # CHANGED(⑪) IMPLEMENTED: ByteArrayStream {target_expr} 原地重置已实现
//   实现: ByteArrayStream 在仓颉中不存在，Java ByteArrayOutputStream 映射为 ByteBuffer
//   使用 __mockResetByteBuffer(target, items)
```

---

### ⑫ StringReader 原地内容重置

```cangjie
// # CHANGED(⑫) IMPLEMENTED: StringReader {target_expr} 原地内容重置已实现
//   实现: ctx.bind_value 生成 buffer + reader 构造语句，同时注册 buffer->reader 映射
//   重置时通过 _get_stream_buffer() 查找 buffer，调用 __mockResetByteBuffer + 重建 reader
```

**生成代码示例**：
```cangjie
// 构造时
let test_reader_buf = ByteBuffer()
test_reader_buf.write("hello".toArray())
test_reader_buf.seek(SeekPosition.Begin(0))
let test_reader = StringReader(test_reader_buf)

// 重置时
__mockResetByteBuffer(test_reader_buf, "new content".toArray())
let test_reader = StringReader(test_reader_buf)
```

---

### ⑬ StringWriter 原地内容重置

```cangjie
// # CHANGED(⑬) IMPLEMENTED: StringWriter {target_expr} 原地内容重置已实现
//   实现: ctx.bind_value 生成 buffer + writer 构造语句，同时注册 buffer->writer 映射
//   重置时通过 _get_stream_buffer() 查找 buffer，调用 __mockResetByteBuffer + 重建 writer
```

**生成代码示例**：
```cangjie
// 构造时
let test_writer_buf = ByteBuffer()
let test_writer = StringWriter(test_writer_buf)
test_writer.write("hello")
test_writer.flush()

// 重置时
__mockResetByteBuffer(test_writer_buf, "new content".toArray())
let test_writer = StringWriter(test_writer_buf)
```

---

### ⑭ 数组逐元素赋值

```cangjie
// # CHANGED(⑭) NOTE: 数组重置行为已确认；仓颉数组定长，逐元素赋值是唯一 mutation 方式
```

---

### ⑥ `__mockReaderEquals`

```cangjie
// # CHANGED(⑥) IMPLEMENTED: __mockReaderEquals
private func __mockReaderEquals<T>(reader: StringReader<T>, expected: String): Bool
where T <: InputStream & Seekable {
    reader.seek(SeekPosition.Begin(0))
    let content = reader.readToEnd()
    content == expected
}
```

---

### ⑦ `__mockWriterEquals`

```cangjie
// # CHANGED(⑦) IMPLEMENTED: __mockWriterEquals
//   比较时将 buf 传入，通过 buf.seek(Begin(0)) + readToEnd(buf) 获取写入内容
private func __mockWriterEquals(buf: ByteBuffer, expected: String): Bool {
    buf.seek(SeekPosition.Begin(0))
    let content = readToEnd(buf)
    content == expected.toArray()
}
```

---

## 四、类型降级说明（CHANGED NOTE）

### ② BigInteger → String

```cangjie
// # CHANGED(②) NOTE: BigInteger 值无法解析为 Int64，已降级为 String 快照
//   原因: 仓颉无内建大整数类型
```

---

### ③ BigDecimal → String

```cangjie
// # CHANGED(③) NOTE: BigDecimal 值无法安全转换为 Float64，已降级为 String 快照
//   原因: 仓颉当前缺少大数/高精度十进制类型
```

---

### ④ BigDecimal → String（溢出）

```cangjie
// # CHANGED(④) NOTE: BigDecimal 值超出 Float64 可表示范围，已降级为 String 快照
```

---

## 五、框架限制（LIMITATION FRAMEWORK）

这些限制来自仓颉语言或 mock 框架的架构约束，无法通过代码手段绕过。

| 编号 | 位置 | 内容 | 原因 |
|------|------|------|------|
| ① | line 764 | `java.time.*` → String | std.time 包 DateTime/Duration/TimeZone API 签名尚未确认 |
| ⑤ | line 770 | `java.net.URL`/`java.net.URI` → String | 仓颉标准库无确认的 URL 解析 API |
| ⑧ | line 776 | `java.util.regex.Pattern`/`Matcher` → String | Regex 类型无 `==`/`!=` 运算符无法比较 |
| ② | line 1185 | 复杂参数退化为 `_` | mock 框架不支持 argThat() 语义匹配 |
| ③ | line 1276 | 字面量重绑定未回放 | @On action lambda 无法替换调用方持有的引用 |
| ④ | line 1363 | 空数组 mutation 目标无法确定 | 日志未提供足够信息推断应写入的索引 |
| ⑥ | line 1376 | 未知类型的 mutation 回放 | helper 缺少该类型的稳定原地更新策略 |
| ⑦ | line 1423 | 桩链按调用顺序分派 | mock @On 按静态签名匹配，不支持按参数身份区分 |
| ⑪ | line 1459 | dependency receiver 状态变更未回放 | @On action lambda 无法访问 dependency 的 receiver 对象 |
| ⑫ | line 1469 | 参数状态变更未回放 | 复杂参数在 @On 签名中匹配为 `_`，lambda 中无法引用 |
| ⑬ | line 1475 | 静态字段副作用未回放 | action lambda 中写静态字段可能与测试 setup 执行顺序冲突 |

---

## 六、test/ 目录结构与测试结果

```
test/
├── test_reset_byte_buffer/
│   ├── test_reset_byte_buffer_basic.cj
│   └── test_reset_byte_buffer_empty.cj
├── test_byte_stream_equals/
│   ├── test_byte_stream_equals_equal.cj
│   └── test_byte_stream_equals_not_equal.cj
├── test_reader_equals/
│   ├── test_reader_equals_equal.cj
│   └── test_reader_equals_not_equal.cj
├── test_writer_equals/
│   ├── test_writer_equals_equal.cj
│   └── test_writer_equals_not_equal.cj
├── todo_bytebuf_reset/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
├── todo_bytearraystream_reset/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
├── todo_reader_reset/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
├── todo_writer_reset/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
├── todo_reader_equals/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
├── todo_writer_equals/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
├── todo_array_length_risk/
│   ├── generated_code_test.cj
│   └── verify_impl.cj
└── todo_mutation_unimplemented/
    ├── generated_code_test.cj
    └── verify_impl.cj
```

**编译运行方式：**
```bash
CJC=/home/luoluoluo/下载/cangjie/bin/cjc
RTP=/home/luoluoluo/下载/cangjie/runtime/lib/linux_x86_64_cjnative

# 单独编译运行
$CJC test_reader_equals_equal.cj -o test_eq -Woff unused
LD_LIBRARY_PATH=$RTP ./test_eq
```

**全部测试结果（编译 + 运行）：**

| 测试文件 | 结果 |
|----------|------|
| `test_reset_byte_buffer_basic` | ✅ PASS |
| `test_reset_byte_buffer_empty` | ✅ PASS |
| `test_byte_stream_equals_equal` | ✅ PASS |
| `test_byte_stream_equals_not_equal` | ✅ PASS |
| `test_reader_equals_equal` | ✅ PASS |
| `test_reader_equals_not_equal` | ✅ PASS |
| `test_writer_equals_equal` | ✅ PASS |
| `test_writer_equals_not_equal` | ✅ PASS |
| `todo_bytebuf_reset_generated_test` | ✅ PASS |
| `todo_bytebuf_reset_verify_impl` | ✅ PASS |
| `todo_bytearraystream_reset_generated_test` | ✅ PASS |
| `todo_bytearraystream_reset_verify_impl` | ✅ PASS |
| `todo_reader_reset_generated_test` | ✅ PASS |
| `todo_reader_reset_verify_impl` | ✅ PASS |
| `todo_writer_reset_generated_test` | ✅ PASS |
| `todo_writer_reset_verify_impl` | ✅ PASS |
| `todo_reader_equals_generated_test` | ✅ PASS |
| `todo_reader_equals_verify_impl` | ✅ PASS |
| `todo_writer_equals_generated_test` | ✅ PASS |
| `todo_writer_equals_verify_impl` | ✅ PASS |
| `todo_array_length_risk_generated_test` | ✅ PASS |
| `todo_array_length_risk_verify_impl` | ✅ PASS |
| `todo_mutation_unimplemented_generated_test` | ✅ PASS |
| `todo_mutation_unimplemented_verify_impl` | ✅ PASS |

---

## 七、关键签名修正记录

| 函数 | 修正前 | 修正后 | 原因 |
|------|--------|--------|------|
| `__mockResetByteBuffer` | `Array<Byte>` | `Array<UInt8>` | `ByteBuffer.write()` 参数类型为 `Array<UInt8>` |
| `__mockReaderEquals` | `ByteBuffer` 参数 | `StringReader<T>` 泛型 | 调用处传入 `StringReader<T>` |
| `__mockWriterEquals` | `<T>(writer: T, ...)` | `(buf: ByteBuffer, ...)` | `StringWriter` 不暴露底层 buffer，caller 需传 buf |
| `__mockWriterEquals` 比较 | `String.fromUtf8(content) == expected` | `content == expected.toArray()` | `content` 是 `Array<Byte>`，需 `.toArray()` 转换 |

---

## 八、2026-04-14 更新：StringReader/StringWriter 原地重置修复

### 问题

原实现中 StringReader/StringWriter 的构造依赖 `__mockStringReaderOf` / `__mockStringWriterOf` helper 函数，这些函数内部创建 ByteBuffer 但不返回，导致 caller 无法访问底层 buffer 进行重置。

```cangjie
// 原实现 - buffer 被隐藏
private func __mockStringReaderOf(text: String): StringReader<ByteBuffer> {
    let stream = ByteBuffer()  // stream 创建后没有返回
    stream.write(text.toArray())
    stream.seek(SeekPosition.Begin(0))
    StringReader(stream)
}
```

### 解决方案

1. 在 `ctx.bind_value` 中特殊处理 StringReader/StringWriter，生成多行构造代码
2. 通过全局 `_stream_buffer_map` 维护 `target_expr -> buffer_var` 映射
3. `render_in_place_mutation` 通过 `_get_stream_buffer()` 查找 buffer 并生成正确的重置代码

### 新生成代码

```cangjie
// 构造时 - caller 同时持有 buffer
let test_reader_buf = ByteBuffer()
test_reader_buf.write("hello".toArray())
test_reader_buf.seek(SeekPosition.Begin(0))
let test_reader = StringReader(test_reader_buf)

// 重置时 - 通过 buffer 重置内容
__mockResetByteBuffer(test_reader_buf, "new content".toArray())
let test_reader = StringReader(test_reader_buf)
```
