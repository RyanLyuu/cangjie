// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public class OptionBuilder {
    // Fields Begin
    static var longOption: String = throw Exception('TODO')
    static var description: String = throw Exception('TODO')
    static var argName: String = throw Exception('TODO')
    static var required: Bool = throw Exception('TODO')
    static var argCount: Int64 = throw Exception('TODO')
    static var type__: Any = throw Exception('TODO')
    static var optionalArg: Bool = throw Exception('TODO')
    static var valueSeparator: Rune = throw Exception('TODO')
    static let INSTANCE: OptionBuilder = throw Exception('TODO')
    // Fields End

    // Static Initializer Begin
    static init() {
        throw Exception('TODO')
    }

    // Static Initializer End

    // Methods Begin
    public static func create0(): Option {
        throw Exception('TODO')
    }

    public static func create1(opt: Rune): Option {
        throw Exception('TODO')
    }

    public static func create2(opt: String): Option {
        throw Exception('TODO')
    }

    public static func hasArg0(): OptionBuilder {
        throw Exception('TODO')
    }

    public static func hasArg1(hasArg: Bool): OptionBuilder {
        throw Exception('TODO')
    }

    public static func hasArgs0(): OptionBuilder {
        throw Exception('TODO')
    }

    public static func hasArgs1(num: Int64): OptionBuilder {
        throw Exception('TODO')
    }

    public static func hasOptionalArg(): OptionBuilder {
        throw Exception('TODO')
    }

    public static func hasOptionalArgs0(): OptionBuilder {
        throw Exception('TODO')
    }

    public static func hasOptionalArgs1(numArgs: Int64): OptionBuilder {
        throw Exception('TODO')
    }

    public static func isRequired0(): OptionBuilder {
        throw Exception('TODO')
    }

    public static func isRequired1(newRequired: Bool): OptionBuilder {
        throw Exception('TODO')
    }

    private static func reset(): Unit {
        throw Exception('TODO')
    }

    public static func withArgName(name: String): OptionBuilder {
        throw Exception('TODO')
    }

    public static func withDescription(newDescription: String): OptionBuilder {
        throw Exception('TODO')
    }

    public static func withLongOpt(newLongopt: String): OptionBuilder {
        throw Exception('TODO')
    }

    public static func withType0(newType: Any): OptionBuilder {
        throw Exception('TODO')
    }

    public static func withType1(newType: Any): OptionBuilder {
        throw Exception('TODO')
    }

    public static func withValueSeparator0(): OptionBuilder {
        throw Exception('TODO')
    }

    public static func withValueSeparator1(sep: Rune): OptionBuilder {
        throw Exception('TODO')
    }

    private init() {
        throw Exception('TODO')
    }

    // Methods End
}

