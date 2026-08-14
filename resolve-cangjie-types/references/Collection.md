---
id: CJ-COL-001
tags: Array, array, ordered, fixed-length, mutable-elements
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/array.md:3-16,131-155
fact: Array<T> 是单一元素类型的有序序列；长度固定，元素可修改；不同元素类型的 Array 是不同类型。
rule: Java T[] 的基础目标类型为 Array<T>；不得因需要增删元素自动改为 ArrayList<T>。
valid: String[] => Array<String>
invalid: T[] => ArrayList<T> without semantic redesign
---
id: CJ-COL-002
tags: Array, constructor, initializer, repeat, aliasing
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/array.md:26-49
fact: Array 可用字面量、空构造、repeat 或索引初始化函数构造；repeat 为引用类型时所有元素指向同一引用。
rule: 翻译 Java new T[n] 时必须提供符合目标元素语义的初始化策略；不能用同一可变引用 repeat 模拟逐元素构造。
valid: Array<Int64>(n, repeat: 0); Array<T>(n, {i => factory(i)})
invalid: Array<MutableRef>(n, repeat: MutableRef()) when distinct objects required
---
id: CJ-COL-003
tags: Array, index, Int64, range, bounds
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/array.md:76-129
fact: Array 下标类型必须为 Int64；合法单下标范围为 0..size-1；Range 下标返回数组片段。
rule: Java int 索引翻译后保证为 Int64 上下文或显式转换；保留越界异常语义。
valid: arr[Int64(i)] when i is Int32
invalid: arr[i:Int32] without accepted conversion
---
id: CJ-COL-004
tags: Array, reference-semantics, alias, struct
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/array.md:153-165
fact: Array 虽为 struct，但表达式使用时不复制元素存储；多个引用共享元素数据。
rule: 不把 Array 赋值误译为深拷贝；需要复制时使用目标 API 明确复制。
valid: let b = a shares Array element storage
invalid: 假定 b=a 后修改 b 不影响 a
---
id: CJ-COL-005
tags: ArrayList, list, mutable, reference-type, ordered
source: CangjieCorpus@3573e3d manual/source_zh_cn/collections/collection_arraylist.md:3-24,102-127
fact: ArrayList<T> 是可增删、可修改的引用类型有序集合；需要 import std.collection.*。
rule: 仅当 Java List 使用语义允许选择可变 ArrayList 实现时映射为 ArrayList<T>；记录实现选择。
valid: new ArrayList<String>() => ArrayList<String>()
invalid: 所有 List<T> 接口无条件等价于 ArrayList<T>
---
id: CJ-COL-006
tags: HashMap, map, key-constraint, ordering, mutable
source: CangjieCorpus@3573e3d manual/source_zh_cn/collections/collection_hashmap.md:11-22,42-46,111-140
fact: HashMap<K,V> 要求 K 实现 Hashable 与 Equatable<K>；不保证插入顺序；是可变引用类型。
rule: Java Map/LinkedHashMap/SortedMap 映射为 HashMap 前必须记录顺序与键约束语义差异。
valid: HashMap<String,Int64>
invalid: LinkedHashMap => HashMap while claiming insertion order preserved
---
id: CJ-COL-007
tags: HashSet, set, uniqueness, key-constraint, ordering
source: CangjieCorpus@3573e3d manual/source_zh_cn/collections/collection_hashset.md:11-20,40-44,100-121
fact: HashSet<T> 元素唯一，要求 T 实现 Hashable 与 Equatable<T>，不保证插入顺序，是可变引用类型。
rule: Java Set 映射为 HashSet 需验证唯一性符合且无顺序要求；不得修改集合内元素作为键身份替代。
valid: HashSet<String>
invalid: LinkedHashSet => HashSet while claiming iteration order preserved
---
id: CJ-COL-008
tags: TreeMap, TreeSet, Comparable, ordered-collection
source: CangjieCorpus@3573e3d libs/std/collection/collection_package_api/collection_package_class.md:2800,3276
fact: TreeMap<K,V> 要求 K <: Comparable<K>；TreeSet<T> 要求 T <: Comparable<T>。
rule: Java SortedMap/SortedSet 只有在目标比较契约可证明时才使用 TreeMap/TreeSet。
valid: TreeMap<String,V>; TreeSet<Int64>
invalid: TreeMap<Any,V>; TreeSet<Any> without Comparable evidence
---
id: CJ-COL-009
tags: Iterable, Iterator, for-in, Option, next
source: CangjieCorpus@3573e3d manual/source_zh_cn/collections/collection_iterable_collections.md:3-25
fact: Iterable<T>.iterator() 返回 Iterator<T>；Iterator<T>.next() 返回 Option<T>；实现 Iterable 即支持 for-in。
rule: Java Iterator.hasNext()/next() 循环翻译需适配 Option<T> 终止协议，不能假定 next 抛异常表示结束。
valid: while (let Some(v) <- it.next()) { ... }
invalid: while (it.hasNext()) when target Iterator has no verified hasNext
---
id: CJ-COL-010
tags: VArray, value-array, fixed-size, restriction
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_data_type/array.md:167-225
fact: VArray<T,$N> 是固定长度值类型数组；类型参数不可省略；元素或成员受引用/enum/lambda/未实例化泛型限制。
rule: 普通 Java 数组默认不映射为 VArray；仅在固定编译期长度和元素限制均满足时选用。
valid: VArray<Int64,$3>
invalid: Java Object[] => VArray<Any,$N>
