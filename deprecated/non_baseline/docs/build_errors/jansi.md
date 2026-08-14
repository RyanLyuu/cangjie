# jansi cjpm build 结果

```
[31merror[0m: undeclared type name 'Callable'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/Ansi.cj:11:26:
   [36m| [0m
[36m11[0m [36m| [0m    static var detector: Callable<Bool> = throw Exception('TODO')[0m
   [36m| [0m                         [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'InheritableThreadLocal'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/Ansi.cj:12:24:
   [36m| [0m
[36m12[0m [36m| [0m    static let holder: InheritableThreadLocal<Bool> = throw Exception('TODO')[0m
   [36m| [0m                       [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Callable'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/Ansi.cj:20:46:
   [36m| [0m
[36m20[0m [36m| [0m    public static func setDetector(detector: Callable<Bool>): Unit {[0m
   [36m| [0m                                             [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Enum'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/AnsiRenderer.cj:99:12:
   [36m| [0m
[36m99[0m [36m| [0m    let n: Enum<Any> = throw Exception('TODO')[0m
   [36m| [0m           [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Enum'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/AnsiRenderer.cj:104:13:
    [36m| [0m
[36m104[0m [36m| [0m    init(n: Enum<Any>, background: Bool) {[0m
    [36m| [0m            [31m^ [0m
    [36m| [0m

[31merror[0m: undeclared type name 'Enum'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/AnsiRenderer.cj:108:13:
    [36m| [0m
[36m108[0m [36m| [0m    init(n: Enum<Any>) {[0m
    [36m| [0m            [31m^ [0m
    [36m| [0m

[31merror[0m: function 'a_1' has overload conflicts
   [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/Ansi.cj:369:22:
    [36m| [0m
[36m369[0m [36m| [0m    public open func a_1(value: Any): Any {[0m
    [36m| [0m                     [31m^^^ [0m
    [36m| [0m
[34mnote[0m: conflict with the declaration
   [36m==>[0m /home/x2cangjie/data/java/skeletons/jansi/src/Ansi.cj:349:22:
    [36m| [0m
[36m349[0m [36m| [0m    public open func a_1(value: Any): Any {[0m
    [36m| [0m                     [34m^^^ [0m
    [36m| [0m

7 errors generated, 7 errors printed.
Error: failed to compile package `jansi`, return code is 1
Error: cjpm build failed
```
