// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
// Imports End

public open class Option {
    // Fields Begin
    static let UNINITIALIZED: Int64 = throw Exception('TODO')
    static let UNLIMITED_VALUES: Int64 = throw Exception('TODO')
    let option: String = throw Exception('TODO')
    var longOption: String = throw Exception('TODO')
    var argName: String = throw Exception('TODO')
    var description: String = throw Exception('TODO')
    var required: Bool = throw Exception('TODO')
    var optionalArg: Bool = throw Exception('TODO')
    var argCount: Int64 = throw Exception('TODO')
    var type__: Any = throw Exception('TODO')
    var values: ArrayList<String> = throw Exception('TODO')
    var valuesep: Rune = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public static func builder0(): Option_Builder {
        throw Exception('TODO')
    }

    public static func builder1(option_param: String): Option_Builder {
        throw Exception('TODO')
    }

    public init(constructorId: Int64, option_param: String, longOption_param: String, description_param: String, hasArg: Bool, builder: Option_Builder) {
        throw Exception('TODO')
    }

    public static func Option1(option_param: String, description_param: String): Option {
        throw Exception('TODO')
    }

    public static func Option2(option_param: String, hasArg: Bool, description_param: String): Option {
        throw Exception('TODO')
    }

    public open func acceptsArg(): Bool {
        throw Exception('TODO')
    }

    private func add(value: String): Unit {
        throw Exception('TODO')
    }

    public open func addValue(value: String): Bool {
        throw Exception('TODO')
    }

    public open func addValueForProcessing(value: String): Unit {
        throw Exception('TODO')
    }

    public open func clearValues(): Unit {
        throw Exception('TODO')
    }

    public open func clone(): Any {
        throw Exception('TODO')
    }

    public open func equals(obj: Any): Bool {
        throw Exception('TODO')
    }

    public open func getArgName(): String {
        throw Exception('TODO')
    }

    public open func getArgs(): Int64 {
        throw Exception('TODO')
    }

    public open func getDescription(): String {
        throw Exception('TODO')
    }

    public open func getId(): Int64 {
        throw Exception('TODO')
    }

    public open func getKey(): String {
        throw Exception('TODO')
    }

    public open func getLongOpt(): String {
        throw Exception('TODO')
    }

    public open func getOpt(): String {
        throw Exception('TODO')
    }

    public open func getType(): Any {
        throw Exception('TODO')
    }

    public open func getValue0(): String {
        throw Exception('TODO')
    }

    public open func getValue1(index: Int64): String {
        throw Exception('TODO')
    }

    public open func getValue2(defaultValue: String): String {
        throw Exception('TODO')
    }

    public open func getValues(): Array<Any> {
        throw Exception('TODO')
    }

    public open func getValueSeparator(): Rune {
        throw Exception('TODO')
    }

    public open func getValuesList(): ArrayList<String> {
        throw Exception('TODO')
    }

    public open func hasArg(): Bool {
        throw Exception('TODO')
    }

    public open func hasArgName(): Bool {
        throw Exception('TODO')
    }

    public open func hasArgs(): Bool {
        throw Exception('TODO')
    }

    public open func hashCode(): Int64 {
        throw Exception('TODO')
    }

    public open func hasLongOpt(): Bool {
        throw Exception('TODO')
    }

    private func hasNoValues(): Bool {
        throw Exception('TODO')
    }

    public open func hasOptionalArg(): Bool {
        throw Exception('TODO')
    }

    public open func hasValueSeparator(): Bool {
        throw Exception('TODO')
    }

    public open func isRequired(): Bool {
        throw Exception('TODO')
    }

    private func processValue(value: String): Unit {
        throw Exception('TODO')
    }

    public open func requiresArg(): Bool {
        throw Exception('TODO')
    }

    public open func setArgName(argName_param: String): Unit {
        throw Exception('TODO')
    }

    public open func setArgs(num: Int64): Unit {
        throw Exception('TODO')
    }

    public open func setDescription(description_param: String): Unit {
        throw Exception('TODO')
    }

    public open func setLongOpt(longOpt: String): Unit {
        throw Exception('TODO')
    }

    public open func setOptionalArg(optionalArg_param: Bool): Unit {
        throw Exception('TODO')
    }

    public open func setRequired(required_param: Bool): Unit {
        throw Exception('TODO')
    }

    public open func setType0(type___param: Any): Unit {
        throw Exception('TODO')
    }

    public open func setType1(type___param: Any): Unit {
        throw Exception('TODO')
    }

    public open func setValueSeparator(sep: Rune): Unit {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
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
    var required: Bool = throw Exception('TODO')
    var optionalArg: Bool = throw Exception('TODO')
    var argCount: Int64 = throw Exception('TODO')
    var type__: Any = throw Exception('TODO')
    var valueSeparator: Rune = throw Exception('TODO')
    // Fields End

    // Methods Begin
    private init(option_param: String) {
        throw Exception('TODO')
    }

    public open func argName_method(argName_param: String): Option_Builder {
        throw Exception('TODO')
    }

    public open func build(): Option {
        throw Exception('TODO')
    }

    public open func desc(description_param: String): Option_Builder {
        throw Exception('TODO')
    }

    public open func hasArg0(): Option_Builder {
        throw Exception('TODO')
    }

    public open func hasArg1(hasArg: Bool): Option_Builder {
        throw Exception('TODO')
    }

    public open func hasArgs(): Option_Builder {
        throw Exception('TODO')
    }

    public open func longOpt(longOpt: String): Option_Builder {
        throw Exception('TODO')
    }

    public open func numberOfArgs(numberOfArgs: Int64): Option_Builder {
        throw Exception('TODO')
    }

    public open func option_method(option_param: String): Option_Builder {
        throw Exception('TODO')
    }

    public open func optionalArg_method(isOptional: Bool): Option_Builder {
        throw Exception('TODO')
    }

    public open func required0(): Option_Builder {
        throw Exception('TODO')
    }

    public open func required1(required_param: Bool): Option_Builder {
        throw Exception('TODO')
    }

    public open func type_(type___param: Any): Option_Builder {
        throw Exception('TODO')
    }

    public open func valueSeparator0(): Option_Builder {
        throw Exception('TODO')
    }

    public open func valueSeparator1(sep: Rune): Option_Builder {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

