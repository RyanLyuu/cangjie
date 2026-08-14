# commons-pool cjpm build 结果

```
[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BaseKeyedPooledObjectFactory.cj:13:50:
   [36m| [0m
[36m13[0m [36m| [0m    public open func activateObject(key: Any, p: PooledObject<Any>): Unit {[0m
   [36m| [0m                                                 [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BaseKeyedPooledObjectFactory.cj:21:49:
   [36m| [0m
[36m21[0m [36m| [0m    public open func destroyObject(key: Any, p: PooledObject<Any>): Unit {[0m
   [36m| [0m                                                [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BaseKeyedPooledObjectFactory.cj:25:44:
   [36m| [0m
[36m25[0m [36m| [0m    public open func makeObject(key: Any): PooledObject<Any> {[0m
   [36m| [0m                                           [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BaseKeyedPooledObjectFactory.cj:29:51:
   [36m| [0m
[36m29[0m [36m| [0m    public open func passivateObject(key: Any, p: PooledObject<Any>): Unit {[0m
   [36m| [0m                                                  [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BaseKeyedPooledObjectFactory.cj:33:50:
   [36m| [0m
[36m33[0m [36m| [0m    public open func validateObject(key: Any, p: PooledObject<Any>): Bool {[0m
   [36m| [0m                                                 [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BaseKeyedPooledObjectFactory.cj:37:40:
   [36m| [0m
[36m37[0m [36m| [0m    public open func wrap(value: Any): PooledObject<Any> {[0m
   [36m| [0m                                       [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BasePooledObjectFactory.cj:13:40:
   [36m| [0m
[36m13[0m [36m| [0m    public open func activateObject(p: PooledObject<Any>): Unit {[0m
   [36m| [0m                                       [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

[31merror[0m: type argument's number does not match type parameter's number
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-pool/src/BasePooledObjectFactory.cj:21:39:
   [36m| [0m
[36m21[0m [36m| [0m    public open func destroyObject(p: PooledObject<Any>): Unit {[0m
   [36m| [0m                                      [31m^^^^^^^^^^^^^^^^^ [0m
   [36m| [0m

81 errors generated, 8 errors printed.
Error: failed to compile package `commons_pool`, return code is 1
Error: cjpm build failed
```
