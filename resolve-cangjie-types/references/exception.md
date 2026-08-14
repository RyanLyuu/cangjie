---
id: CJ-EXC-001
tags: Exception, Error, hierarchy, custom-exception
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/exception_overview.md:3-37
fact: Error 表示运行时内部/资源耗尽错误且不可继承自定义；Exception 表示逻辑/IO异常且可继承自定义。
rule: Java 应用异常映射为 Exception 子类；不要通过继承 Error 创建业务异常。
valid: class MyException <: Exception
invalid: class MyError <: Error
---
id: CJ-EXC-002
tags: throw, Exception, Error, unchecked
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:3-12
fact: throw 后表达式必须是 Exception 子类型；Error 不能手动 throw；未捕获异常交给系统默认处理。
rule: Java throw 的目标值必须映射到 Exception 层级；Java Error/Throwable 不能仅按名称直接替换。
valid: throw IllegalArgumentException("msg")
invalid: throw Error(...)
---
id: CJ-EXC-003
tags: try, catch, finally, propagation
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:14-24
fact: 普通 try 可含多个 catch；无 catch 时必须有 finally；finally 总执行；未捕获异常在 finally 后继续抛出。
rule: 保留 Java catch 顺序与 finally 控制流；不得吞掉未匹配异常。
valid: try {...} catch (e:E) {...} finally {...}
invalid: try block without catch/finally; remove rethrow behavior
---
id: CJ-EXC-004
tags: catch-pattern, subtype, unreachable-catch, order
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:18-22,255-262
fact: catchPattern 以类型模式匹配该类型及子类；首次匹配后忽略后续 catch；被前序完全覆盖的 catch 不可达并警告。
rule: Java 多 catch 翻译保持从具体到宽泛顺序；不要把 Exception 放在具体异常之前。
valid: catch(Sub) before catch(Exception)
invalid: catch(Exception) before catch(Sub)
---
id: CJ-EXC-005
tags: multi-catch, union, least-common-supertype
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:259-323
fact: catch(e:E1|E2) 可捕获各类型及子类；绑定变量静态类型为这些异常类型的最小公共父类。
rule: Java multi-catch 可映射 | 模式，但 catch 体只能直接访问最小公共父类成员。
valid: catch (e: E1 | E2) { println(e.message) }
invalid: 在 union catch 变量上访问仅 E1 存在的成员
---
id: CJ-EXC-006
tags: wildcard-catch, catch-all, Exception
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:325-336
fact: catch(_) 捕获任意 Exception 子类型，等价于 e:Exception 但不绑定变量。
rule: Java catch(Exception ignored) 且不使用变量时可映射 catch(_)；不等同捕获 Error。
valid: catch (_) { ... }
invalid: 声称 catch(_) 捕获 Error
---
id: CJ-EXC-007
tags: try-expression, result-type, finally
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:91-110
fact: try 是表达式；其类型为 try/catch 分支最小公共父类型，finally 不参与；值未使用时类型 Unit。
rule: Java try 语句转为值表达式时统一 try/catch 分支目标类型，不以 finally 值推断。
valid: let x=try{Sub()}catch(e:E){Base()}
invalid: 用 finally 表达式决定 try 返回类型
---
id: CJ-EXC-008
tags: try-with-resources, Resource, close, Unit
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:113-167,210-253
fact: try-with-resources 资源类型必须实现 Resource(isClosed,close)；离开作用域自动关闭；整个表达式类型 Unit。
rule: Java AutoCloseable 不能只改类型名；需适配 Resource 完整协议与关闭语义。
valid: class R <: Resource with isClosed and close
invalid: AutoCloseable => Resource without implementing isClosed
---
id: CJ-EXC-009
tags: checked-exception, throws-clause, signature
source: CangjieCorpus@3573e3d manual/source_zh_cn/error_handle/handle.md:3-22
fact: Corpus 的函数声明与 throw/try 规则未定义 Java throws 声明或 checked-exception 签名机制。
rule: 移除 Java throws 子句的语法，但保留实际 throw、catch、传播和 API 行为；不得声称异常被消除。
valid: body retains throw/catch behavior without Java throws syntax
invalid: delete exception paths because target signature has no throws clause
