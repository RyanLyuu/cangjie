---
id: CJ-NUM-001
tags: Java-primitive, integer, byte, short, int, long
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/integer.md:3-24
fact: Int8/Int16/Int32/Int64 分别为 8/16/32/64 位有符号整数。
rule: Java byte=>Int8; short=>Int16; int=>Int32; long=>Int64；保留位宽与符号。
valid: int => Int32
invalid: Java int => Int64 solely because Cangjie literal defaults Int64
---
id: CJ-NUM-002
tags: unsigned, UInt8, UInt16, UInt32, UInt64, native
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/integer.md:3-22
fact: UInt8/16/32/64 为对应位宽无符号整数；IntNative/UIntNative 位宽依平台。
rule: 只有源语义明确无符号时选择 UInt；Java 普通有符号 primitive 不映射为 UIntNative。
valid: unsigned 8-bit protocol value => UInt8
invalid: Java byte => UInt8; Java long => IntNative
---
id: CJ-NUM-003
tags: Float16, Float32, Float64, Java-float, Java-double, IEEE754
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/float.md:1-5
fact: Float16/Float32/Float64 对应 IEEE 754 binary16/binary32/binary64。
rule: Java float=>Float32; double=>Float64；不得为了精度偏好改变公开签名位宽。
valid: double => Float64
invalid: Java float => Float64 without semantic decision
---
id: CJ-NUM-004
tags: integer-literal, default-type, suffix, context
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/integer.md:24-59
fact: 无类型上下文的整数字面量默认 Int64；i8/i16/i32/i64/u8/u16/u32/u64 后缀固定类型；超出上下文范围时报错。
rule: Java int 字面量进入无上下文 Cangjie 表达式时补 Int32 上下文、后缀或显式转换，避免意外 Int64。
valid: 1i32; let x: Int32 = 1
invalid: 假定 Cangjie 1 默认 Int32
---
id: CJ-NUM-005
tags: float-literal, suffix, context
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/float.md:7-42
fact: 浮点字面量可由上下文确定类型；f16/f32/f64 后缀显式指定类型。
rule: 翻译 Java f/F 后缀为 f32；Java double 常量在需要消除歧义时使用 f64 或 Float64 上下文。
valid: 3.14f32
invalid: Java 3.14f => unsuffixed target literal when overload depends on Float32
---
id: CJ-NUM-006
tags: numeric-conversion, explicit-cast, overflow
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/typecast.md:1-51
fact: Cangjie 不支持不同数值类型的隐式转换；使用 T(e) 显式转换；转换溢出可编译报错或按默认策略抛异常。
rule: Java 数值提升、缩窄转换和混合运算必须显式化；不要依赖隐式 widening。
valid: Int64(i32); Int32(i64)
invalid: let x:Int64 = i32 without subtype/conversion evidence
---
id: CJ-NUM-007
tags: arithmetic, operand-types, promotion, integer-division
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/basic_operators.md:46-66
fact: 二元 + - * / % 要求两操作数类型相同；% 仅整数；整数除法向 0 舍入。
rule: Java binary numeric promotion 必须在目标操作前转换为同一类型；整数除法语义可直接保留向零截断。
valid: Int64(a) + b when b:Int64
invalid: a:Int32 + b:Int64
---
id: CJ-NUM-008
tags: overflow, arithmetic, checked
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/basic_operators.md:3-7
fact: Cangjie 算术结果会检测并禁止值溢出；Java 整数算术通常按固定位宽回绕。
rule: 依赖 Java overflow/wraparound 的代码不能仅做类型替换；标记为方法体语义重构。
valid: explicit overflow policy or checked handling
invalid: 声称 Java overflow 行为由 Cangjie 普通 + 自动保持
---
id: CJ-NUM-009
tags: Rune, UInt32, Unicode-scalar, Java-char
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/typecast.md:53-79
fact: Rune 表示 Unicode scalar；Rune=>UInt32；整数=>Rune 仅接受有效 scalar 区间，代理区无效。
rule: Java char 是 UTF-16 code unit，不能普遍视为 Rune 等价；遇到 surrogate/编码运算时保留或重构。
valid: verified Unicode scalar char => Rune
invalid: every Java char => Rune with semantic-equivalence claim
---
id: CJ-NUM-010
tags: BigInteger, BigDecimal, BigInt, Decimal, arbitrary-precision
source: CangjieCorpus@3573e3d libs/std/math_numeric/math_numeric_package_api/math_numeric_package_structs.md:3-6,2809-2812
fact: std.math_numeric 提供 BigInt 与 Decimal struct，均实现 Comparable、Hashable、ToString。
rule: Java BigInteger/BigDecimal 可作为候选映射到 BigInt/Decimal，但构造、舍入、scale 与异常语义必须另行核对 API。
valid: type candidate BigInteger=>BigInt; BigDecimal=>Decimal
invalid: 声称全部 Java BigDecimal API 与 Decimal 等价
