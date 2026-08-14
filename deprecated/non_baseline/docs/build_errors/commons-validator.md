# commons-validator cjpm build 结果

```
[31merror[0m: undeclared type name 'Set'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/UrlValidator.cj:36:25:
   [36m| [0m
[36m36[0m [36m| [0m    let allowedSchemes: Set<String> = throw Exception('TODO')[0m
   [36m| [0m                        [31m^ [0m
   [36m| [0m

[31merror[0m: undeclared type name 'Set'
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/ValidatorResults.cj:31:42:
   [36m| [0m
[36m31[0m [36m| [0m    public open func getPropertyNames(): Set<String> {[0m
   [36m| [0m                                         [31m^ [0m
   [36m| [0m

2 errors generated, 2 errors printed.
Error: failed to compile package `commons_validator`, return code is 1
[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/ABANumberCheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/CUSIPCheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/EAN13CheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/ISBN10CheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/ISINCheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/ISSNCheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/LuhnCheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

[31merror[0m: the variable 'serialVersionUID' must not shadow a member variable of the supertype
  [36m==>[0m /home/x2cangjie/data/java/skeletons/commons-validator/src/checkdigit/ModulusTenCheckDigit.cj:10:5:
   [36m| [0m
[36m10[0m [36m| [0m    static let serialVersionUID: Int64 = throw Exception('TODO')[0m
   [36m| [0m    [31m^ [0m
   [36m| [0m

9 errors generated, 8 errors printed.
Error: failed to compile package `commons_validator.checkdigit`, return code is 1
Error: cjpm build failed
```
