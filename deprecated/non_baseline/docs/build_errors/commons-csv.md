# commons-csv cjpm build 结果

```
[31merror[0m: undeclared type name 'Stream'
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVParser.cj:137:32:
    [36m| [0m
[36m137[0m [36m| [0m    public open func stream(): Stream<Any> {[0m
    [36m| [0m                               [31m^ [0m
    [36m| [0m

[31merror[0m: undeclared type name 'Stream'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVPrinter.cj:56:42:
   [36m| [0m
[36m56[0m [36m| [0m    public open func printRecord(values: Stream<Any>): Unit {[0m
   [36m| [0m                                         [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Enum'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVRecord.cj:24:29:
   [36m| [0m
[36m24[0m [36m| [0m    public open func get(e: Enum<Any>): String {[0m
   [36m| [0m                            [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Stream'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVRecord.cj:88:32:
   [36m| [0m
[36m88[0m [36m| [0m    public open func stream(): Stream<String> {[0m
   [36m| [0m                               [31m^ [0m
   [36m| [0m

[31merror[0m: function 'parse_1' has overload conflicts
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVParser.cj:45:24:
   [36m| [0m
[36m45[0m [36m| [0m    public static func parse_1(url: Any, charset: Any, format: Any): Any {[0m
   [36m| [0m                       [31m^^^^^^^ [0m
   [36m| [0m
[34mnote[0m: conflict with the declaration
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVParser.cj:33:24:
   [36m| [0m
[36m33[0m [36m| [0m    public static func parse_1(path: Any, charset: Any, format: Any): Any {[0m
   [36m| [0m                       [34m^^^^^^^ [0m
   [36m| [0m

[31merror[0m: overloaded functions 'trim_method' cannot mix static and non-static
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVFormat.cj:85:17:
   [36m| [0m
[36m85[0m [36m| [0m    static func trim_method(charSequence: Any): Any {[0m
   [36m| [0m                [31m^^^^^^^^^^^ [0m
   [36m| [0m
[34mnote[0m: non-static function is here
   [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-csv/src/CSVFormat.cj:289:22:
    [36m| [0m
[36m289[0m [36m| [0m    public open func trim_method(value: String): String {[0m
    [36m| [0m                     [34m^^^^^^^^^^^ [0m
    [36m| [0m

6 errors generated, 6 errors printed.
Error: failed to compile package `commons_csv`, return code is 1
Error: cjpm build failed
```
