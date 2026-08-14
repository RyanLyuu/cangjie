// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
// Imports End

public open class Option {
    // Fields Begin
    static let UNINITIALIZED: Int64 = -1
    static let UNLIMITED_VALUES: Int64 = -2
    let option: String = throw Exception('TODO')
    var longOption: String = throw Exception('TODO')
    var argName: String = throw Exception('TODO')
    var description: String = throw Exception('TODO')
    var required: Bool = false
    var optionalArg: Bool = false
    var argCount: Int64 = -1  // Already translated, compilation failed
    var type__: Any = String()  // Already translated, compilation failed
    var values: ArrayList<String> = ArrayList<String>()
    var valuesep: Rune = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public static func builder0(): Option_Builder {
                return builder1("")
    }

    public static func builder1(option_param: String): Option_Builder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public init(constructorId: Int64, option_param: String, longOption_param: String, description_param: String, hasArg: Bool, builder: Option_Builder) {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func Option1(option_param: String, description_param: String): Option {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func Option2(option_param: String, hasArg: Bool, description_param: String): Option {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func acceptsArg(): Bool {
                return (hasArg() || hasArgs() || hasOptionalArg()) && (argCount <= 0 || values.size < argCount)
    }

    private func add(value: String): Unit {
                if (!acceptsArg()) {
        throw Exception("Cannot add value, list full.")
        }
        values.add(value)
    }

    public open func addValue(value: String): Bool {
                throw Exception("The addValue method is not intended for client use. Subclasses should use the addValueForProcessing method instead.")
    }

    public open func addValueForProcessing(value: String): Unit {
                if (argCount == UNINITIALIZED) {
        throw Exception("NO_ARGS_ALLOWED")
        }
        processValue(value)
    }

    public open func clearValues(): Unit {
                values.clear()
    }

    public open func clone(): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func equals(obj: Any): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getArgName(): String {
                return argName
    }

    public open func getArgs(): Int64 {
                return argCount
    }

    public open func getDescription(): String {
                return this.description
    }

    public open func getId(): Int64 {
                return Int64(getKey()[0])
    }

    public open func getKey(): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getLongOpt(): String {
                return longOption
    }

    public open func getOpt(): String {
                return this.option
    }

    public open func getType(): Any {
                return type__
    }

    public open func getValue0(): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getValue1(index: Int64): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getValue2(defaultValue: String): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getValues(): Array<Any> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getValueSeparator(): Rune {
                return valuesep
    }

    public open func getValuesList(): ArrayList<String> {
                return this.values
    }

    public open func hasArg(): Bool {
                return argCount > 0 || argCount == UNLIMITED_VALUES
    }

    public open func hasArgName(): Bool {
                return argName != "" && !argName.isEmpty()
    }

    public open func hasArgs(): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func hashCode(): Int64 {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func hasLongOpt(): Bool {
                return longOption != ""
    }

    private func hasNoValues(): Bool {
                return values.isEmpty()
    }

    public open func hasOptionalArg(): Bool {
                return optionalArg
    }

    public open func hasValueSeparator(): Bool {
                return valuesep > Rune(0)
    }

    public open func isRequired(): Bool {
                return this.required
    }

    private func processValue(value: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func requiresArg(): Bool {
                if (optionalArg) {
        return false
        }
        if (argCount == UNLIMITED_VALUES) {
        return values.isEmpty()
        }
        return acceptsArg()
    }

    public open func setArgName(argName_param: String): Unit {
                this.argName = argName_param
    }

    public open func setArgs(num: Int64): Unit {
                this.argCount = num
    }

    public open func setDescription(description_param: String): Unit {
                this.description = description_param
    }

    public open func setLongOpt(longOpt: String): Unit {
                this.longOption = longOpt
    }

    public open func setOptionalArg(optionalArg_param: Bool): Unit {
                this.optionalArg = optionalArg_param
    }

    public open func setRequired(required_param: Bool): Unit {
                this.required = required_param
    }

    public open func setType0(type___param: Any): Unit {
                this.type__ = type___param
    }

    public open func setType1(type___param: Any): Unit {
                setType0(type___param as Any)
    }

    public open func setValueSeparator(sep: Rune): Unit {
                this.valuesep = sep
    }

    public open func toString(): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

public class Option_Builder {
    // Fields Begin
    var option: String = throw Exception('TODO')
    var description: String = throw Exception('TODO')
    var longOption: String = throw Exception('TODO')
    var argName: String = throw Exception('TODO')
    var required: Bool = false
    var optionalArg: Bool = throw Exception('TODO')
    var argCount: Int64 = throw Exception('TODO')
    var type__: Any = throw Exception('TODO')
    var valueSeparator: Rune = ':'
    // Fields End

    // Methods Begin
    private init(option_param: String) {
        throw Exception('TODO')
    }

    public open func argName_method(argName_param: String): Option_Builder {
        throw Exception('TODO')
    }

    public open func build(): Option {
                if (option == "" && longOption == "") {
        throw IllegalArgumentException("Either opt or longOpt must be specified")
        }
        return Option(3, "", "", "", false, this)
    }

    public open func desc(description_param: String): Option_Builder {
                this.description = description_param
        return this
    }

    public open func hasArg0(): Option_Builder {
                return hasArg1(true)
    }

    public open func hasArg1(hasArg: Bool): Option_Builder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func hasArgs(): Option_Builder {
        throw Exception('TODO')
    }

    public open func longOpt(longOpt: String): Option_Builder {
                this.longOption = longOpt
        return this
    }

    public open func numberOfArgs(numberOfArgs: Int64): Option_Builder {
                this.argCount = numberOfArgs
        return this
    }

    public open func option_method(option_param: String): Option_Builder {
        throw Exception('TODO')
    }

    public open func optionalArg_method(isOptional: Bool): Option_Builder {
        throw Exception('TODO')
    }

    public open func required0(): Option_Builder {
                return required1(true)
    }

    public open func required1(required_param: Bool): Option_Builder {
                this.required = required_param
        return this
    }

    public open func type_(type___param: Any): Option_Builder {
                this.type__ = type___param
        return this
    }

    public open func valueSeparator0(): Option_Builder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func valueSeparator1(sep: Rune): Option_Builder {
                this.valueSeparator = sep
        return this
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

