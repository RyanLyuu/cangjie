# commons-exec cjpm build 结果

```
[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/MapUtils.cj:13:70:
   [36m| [0m
[36m13[0m [36m| [0m    public static func copy(source: HashMap<Any, Any>): HashMap<Any, Any> {[0m
   [36m| [0m                                                                     [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/MapUtils.cj:13:50:
   [36m| [0m
[36m13[0m [36m| [0m    public static func copy(source: HashMap<Any, Any>): HashMap<Any, Any> {[0m
   [36m| [0m                                                 [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/MapUtils.cj:17:92:
   [36m| [0m
[36m17[0m [36m| [0m    public static func merge(lhs: HashMap<Any, Any>, rhs: HashMap<Any, Any>): HashMap<Any, Any> {[0m
   [36m| [0m                                                                                           [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/MapUtils.cj:17:48:
   [36m| [0m
[36m17[0m [36m| [0m    public static func merge(lhs: HashMap<Any, Any>, rhs: HashMap<Any, Any>): HashMap<Any, Any> {[0m
   [36m| [0m                                               [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/MapUtils.cj:17:72:
   [36m| [0m
[36m17[0m [36m| [0m    public static func merge(lhs: HashMap<Any, Any>, rhs: HashMap<Any, Any>): HashMap<Any, Any> {[0m
   [36m| [0m                                                                       [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/MapUtils.cj:21:52:
   [36m| [0m
[36m21[0m [36m| [0m    public static func prefix(source: HashMap<Any, Any>, prefix: String): HashMap<String, Any> {[0m
   [36m| [0m                                                   [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

[31merror[0m: generics type arguments do not match the constraint of 'Class-HashMap<Generics-K, Generics-V>'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/util/StringUtils.cj:34:78:
   [36m| [0m
[36m34[0m [36m| [0m    public static func stringSubstitution(argStr: String, vars: HashMap<Any, Any>, isLenient: Bool): StringBuilder {[0m
   [36m| [0m                                                                             [31m^ [0m
   [36m| [0m
[34mnote[0m: 'Interface-Any' is not a subtype of 'Interface-Hashable'
   [36m==>[0m (package std.collection)hash_map.cj:335:47:

7 errors generated, 7 errors printed.
Error: failed to compile package `commons_exec.util`, return code is 1
[31merror[0m: expected identifier or pattern after 'let', found keyword 'is'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/StreamPumper.cj:12:9:
   [36m| [0m
[36m12[0m [36m| [0m    let is: InputStream = throw Exception('TODO')[0m
   [36m| [0m    [36m~~~[0m [31m^^ expected identifier or pattern here[0m
   [36m| [0m
[32mhelp[0m: escape the keyword `is` to use it as an identifier:
   [36m| [0m
[36m12[0m [36m| [0m    let `is`: InputStream = throw Exception('TODO')[0m
   [36m| [0m        [32m~~~~ [0m
   [36m| [0m

[31merror[0m: expected identifier or pattern after 'let', found keyword 'is'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/InputStreamPumper.cj:12:9:
   [36m| [0m
[36m12[0m [36m| [0m    let is: InputStream = throw Exception('TODO')[0m
   [36m| [0m    [36m~~~[0m [31m^^ expected identifier or pattern here[0m
   [36m| [0m
[32mhelp[0m: escape the keyword `is` to use it as an identifier:
   [36m| [0m
[36m12[0m [36m| [0m    let `is`: InputStream = throw Exception('TODO')[0m
   [36m| [0m        [32m~~~~ [0m
   [36m| [0m

[31merror[0m: unclosed delimiter: '('
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/InputStreamPumper.cj:18:17:
   [36m| [0m
[36m18[0m [36m| [0m    public init(is: InputStream, os: OutputStream) {[0m
   [36m| [0m               [36m~[31m^ expected ')' here[0m
   [36m| [0m               [36m|[0m
   [36m| [0m               [36mto match this opening '('[0m
   [36m| [0m

[31merror[0m: expected a argument name after '(' in parameter list, found keyword 'is'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/InputStreamPumper.cj:18:17:
   [36m| [0m
[36m18[0m [36m| [0m    public init(is: InputStream, os: OutputStream) {[0m
   [36m| [0m               [36m~[31m^^ expected a argument name here[0m
   [36m| [0m               [36m|[0m
   [36m| [0m               [36mafter '(' in parameter list[0m
   [36m| [0m
[32mhelp[0m: you could escape keyword as a argument name using '`':
   [36m| [0m
[36m18[0m [36m| [0m    public init(`is`: InputStream, os: OutputStream) {[0m
   [36m| [0m                [32m~~~~ [0m
   [36m| [0m

[31merror[0m: unclosed delimiter: '('
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/StreamPumper.cj:20:17:
   [36m| [0m
[36m20[0m [36m| [0m    public init(is: InputStream, os: OutputStream) {[0m
   [36m| [0m               [36m~[31m^ expected ')' here[0m
   [36m| [0m               [36m|[0m
   [36m| [0m               [36mto match this opening '('[0m
   [36m| [0m

[31merror[0m: expected a argument name after '(' in parameter list, found keyword 'is'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/StreamPumper.cj:20:17:
   [36m| [0m
[36m20[0m [36m| [0m    public init(is: InputStream, os: OutputStream) {[0m
   [36m| [0m               [36m~[31m^^ expected a argument name here[0m
   [36m| [0m               [36m|[0m
   [36m| [0m               [36mafter '(' in parameter list[0m
   [36m| [0m
[32mhelp[0m: you could escape keyword as a argument name using '`':
   [36m| [0m
[36m20[0m [36m| [0m    public init(`is`: InputStream, os: OutputStream) {[0m
   [36m| [0m                [32m~~~~ [0m
   [36m| [0m

[31merror[0m: unclosed delimiter: '('
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/StreamPumper.cj:24:17:
   [36m| [0m
[36m24[0m [36m| [0m    public init(is: InputStream, os: OutputStream, closeWhenExhausted: Bool) {[0m
   [36m| [0m               [36m~[31m^ expected ')' here[0m
   [36m| [0m               [36m|[0m
   [36m| [0m               [36mto match this opening '('[0m
   [36m| [0m

[31merror[0m: expected a argument name after '(' in parameter list, found keyword 'is'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-exec/src/StreamPumper.cj:24:17:
   [36m| [0m
[36m24[0m [36m| [0m    public init(is: InputStream, os: OutputStream, closeWhenExhausted: Bool) {[0m
   [36m| [0m               [36m~[31m^^ expected a argument name here[0m
   [36m| [0m               [36m|[0m
   [36m| [0m               [36mafter '(' in parameter list[0m
   [36m| [0m
[32mhelp[0m: you could escape keyword as a argument name using '`':
   [36m| [0m
[36m24[0m [36m| [0m    public init(`is`: InputStream, os: OutputStream, closeWhenExhausted: Bool) {[0m
   [36m| [0m                [32m~~~~ [0m
   [36m| [0m

24 errors generated, 8 errors printed.
Error: failed to compile package `commons_exec`, return code is 1
Error: cjpm build failed
```
