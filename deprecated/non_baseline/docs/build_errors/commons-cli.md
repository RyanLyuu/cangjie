# commons-cli cjpm build 结果

```
[31merror[0m: redefinition of declaration 'Builder'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/DefaultParser.cj:146:14:
    [36m| [0m
[36m146[0m [36m| [0mpublic class Builder {[0m
    [36m| [0m             [31m^^^^^^^ [0m
    [36m| [0m
[34mnote[0m: 'Builder' is previously declared here
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/CommandLine.cj:128:14:
    [36m| [0m
[36m128[0m [36m| [0mpublic class Builder {[0m
    [36m| [0m             [34m^^^^^^^ [0m
    [36m| [0m

[31merror[0m: redefinition of declaration 'Builder'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/Option.cj:225:14:
    [36m| [0m
[36m225[0m [36m| [0mpublic class Builder {[0m
    [36m| [0m             [31m^^^^^^^ [0m
    [36m| [0m
[34mnote[0m: 'Builder' is previously declared here
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/CommandLine.cj:128:14:
    [36m| [0m
[36m128[0m [36m| [0mpublic class Builder {[0m
    [36m| [0m             [34m^^^^^^^ [0m
    [36m| [0m

[31merror[0m: undeclared type name 'Class'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/Option.cj:20:17:
   [36m| [0m
[36m20[0m [36m| [0m    var type__: Class<Any> = throw Exception('TODO')[0m
   [36m| [0m                [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Class'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/Option.cj:202:38:
    [36m| [0m
[36m202[0m [36m| [0m    public open func setType(type__: Class<Any>): Unit {[0m
    [36m| [0m                                     [31m^ [0m
    [36m| [0m

[31merror[0m: undeclared type name 'Class'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/Option.cj:234:17:
    [36m| [0m
[36m234[0m [36m| [0m    var type__: Class<Any> = throw Exception('TODO')[0m
    [36m| [0m                [31m^ [0m
    [36m| [0m

[31merror[0m: undeclared type name 'Class'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/Option.cj:291:36:
    [36m| [0m
[36m291[0m [36m| [0m    public open func type_(type__: Class<Any>): Any {[0m
    [36m| [0m                                   [31m^ [0m
    [36m| [0m

[31merror[0m: undeclared type name 'Class'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/OptionBuilder.cj:15:24:
   [36m| [0m
[36m15[0m [36m| [0m    static var type__: Class<Any> = throw Exception('TODO')[0m
   [36m| [0m                       [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Class'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-cli/src/OptionBuilder.cj:93:42:
   [36m| [0m
[36m93[0m [36m| [0m    public static func withType(newType: Class<Any>): Any {[0m
   [36m| [0m                                         [31m^ [0m
   [36m| [0m

28 errors generated, 8 errors printed.
Error: failed to compile package `commons_cli`, return code is 1
Error: cjpm build failed
```
