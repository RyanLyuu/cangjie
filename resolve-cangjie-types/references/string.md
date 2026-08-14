---
id: CJ-STR-001
tags: String, Unicode, UTF-8, text
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/strings.md:1-4; libs/std/core/core_package_api/core_package_structs.md:2399-2415
fact: String 表达 Unicode 文本；标准 String 仅支持 UTF-8 编码。
rule: Java String 基础映射为 String；涉及底层编码时显式适配 UTF-16(Java) 与 UTF-8(Cangjie)差异。
valid: java.lang.String => String
invalid: 把 Java String 的 UTF-16 code-unit 索引语义视为 Cangjie String 字节索引等价
---
id: CJ-STR-002
tags: String-size, byte-length, UTF-8-index
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_structs.md:2435-2443
fact: String.size 返回 UTF-8 编码后的字节长度，类型 Int64。
rule: Java String.length()（UTF-16 code unit 数）不能机械映射为 size；需根据用途改为 rune 计数或字节长度。
valid: byteLength semantics => s.size
invalid: Java s.length() => s.size for arbitrary Unicode
---
id: CJ-STR-003
tags: Rune, character, Unicode-scalar, Java-char
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/characters.md:1-49
fact: Rune 表示 Unicode 字符/scalar，比较依据 Unicode 值。
rule: 仅当 Java char 使用值已验证为单 Unicode scalar 时映射 Rune；UTF-16 surrogate 处理不能直接映射。
valid: Unicode code point => Rune
invalid: surrogate code unit => Rune
---
id: CJ-STR-004
tags: UTF-8, bytes, decode, fromUtf8
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_structs.md:2485-2525
fact: String.fromUtf8(Array<UInt8>) 验证 UTF-8；非法序列抛 IllegalArgumentException；fromUtf8Unchecked 是 unsafe 且不验证。
rule: Java byte[]+charset 只有 charset 确认为 UTF-8 时才直接使用 fromUtf8；默认使用安全版本。
valid: UTF-8 byte[] => String.fromUtf8(bytes)
invalid: arbitrary charset bytes => String.fromUtf8; 默认使用 fromUtf8Unchecked
---
id: CJ-STR-005
tags: encode, bytes, toArray, rawData, immutable
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_structs.md:3041-3055,3186-3196
fact: String.toArray() 返回 UTF-8 Byte 数组；rawData() 是 unsafe 原始数据，禁止修改以免破坏 String 不可变性。
rule: Java getBytes(UTF_8) 可适配 toArray；非 UTF-8 charset 不可；不使用 rawData 作为可变缓冲区。
valid: s.toArray(): Array<Byte>
invalid: mutate s.rawData(); Java getBytes(UTF_16)=>toArray
---
id: CJ-STR-006
tags: Rune-array, runes, code-point, iterator
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_structs.md:3110-3124,3236-3243
fact: String.runes() 返回 Iterator<Rune>；toRuneArray() 返回 Array<Rune>；非法 UTF-8 可抛 IllegalArgumentException。
rule: Java codePoints/Unicode scalar 遍历适配 runes/toRuneArray；Java chars() 的 UTF-16 code-unit 流不等价。
valid: Unicode scalar iteration => s.runes()
invalid: Java s.chars() => s.runes() with equivalence claim
---
id: CJ-STR-007
tags: String-constructor, Rune-array, collection
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_structs.md:2401-2407,2453-2483
fact: String 可由 Array<Rune> 或 Collection<Rune> 构造。
rule: 已按 Unicode scalar 解码的 Java 字符序列可先构造 Rune 集合再生成 String。
valid: String(runeArray)
invalid: String(byteArray) without fromUtf8
---
id: CJ-STR-008
tags: interpolation, concatenation, toString
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/strings.md:68-102
fact: 插值字符串结果为 String；String 支持 + 拼接与关系操作。
rule: Java 字符串拼接可使用 + 或插值；插值表达式必须具有目标可字符串化语义。
valid: "value=${x}"
invalid: 假定任意函数类型可插值；泛型 T 无 ToString 约束直接插值
---
id: CJ-STR-009
tags: String, Hashable, Equatable, Comparable, map-key
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_structs.md:2401-2423
fact: String 实现 Equatable<String>、Comparable<String>、Hashable、ToString。
rule: String 可作为 HashMap/HashSet/TreeMap/TreeSet 的约束满足类型。
valid: HashMap<String,V>; TreeSet<String>
invalid: 因 String 是 struct 而假定其不支持 hash/compare
