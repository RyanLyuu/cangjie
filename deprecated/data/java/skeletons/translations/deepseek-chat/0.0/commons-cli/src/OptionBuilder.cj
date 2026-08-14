// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public class OptionBuilder {
    // Fields Begin
    static var longOption: String = throw Exception('TODO')
    static var description: String = throw Exception('TODO')
    static var argName: String = throw Exception('TODO')
    static var required: Bool = false
    static var argCount: Int64 = Option.UNINITIALIZED
    static var type__: Any = throw Exception('TODO')
    static var optionalArg: Bool = false
    static var valueSeparator: Rune = throw Exception('TODO')
    static let INSTANCE: OptionBuilder = OptionBuilder()
    // Fields End

    // Static Initializer Begin
    static init() {
                reset()
    }

    // Static Initializer End

    // Methods Begin
    public static func create0(): Option {
                if (longOption == "") {
        OptionBuilder.reset()
        throw IllegalArgumentException("must specify longopt")
        }
        return create2("")
    }

    public static func create1(opt: Rune): Option {
                return create2(String(opt))
    }

    public static func create2(opt: String): Option {
                var option: Option = try {
        Option.Option1(opt, description)
        } catch (e: Exception) {
        throw IllegalArgumentException(e.message)
        }
        try {
        option.setLongOpt(longOption)
        option.setRequired(required)
        option.setOptionalArg(optionalArg)
        option.setArgs(argCount)
        option.setType0(type__)
        option.setValueSeparator(valueSeparator)
        option.setArgName(argName)
        } finally {
        OptionBuilder.reset()
        }
        return option
    }

    public static func hasArg0(): OptionBuilder {
                OptionBuilder.argCount = 1; return INSTANCE
    }

    public static func hasArg1(hasArg: Bool): OptionBuilder {
                OptionBuilder.argCount = if (hasArg) { 1 } else { Option.UNINITIALIZED }
        return INSTANCE
    }

    public static func hasArgs0(): OptionBuilder {
                OptionBuilder.argCount = Option.UNLIMITED_VALUES; return INSTANCE
    }

    public static func hasArgs1(num: Int64): OptionBuilder {
                OptionBuilder.argCount = num; return INSTANCE
    }

    public static func hasOptionalArg(): OptionBuilder {
                OptionBuilder.argCount = 1; OptionBuilder.optionalArg = true; return INSTANCE
    }

    public static func hasOptionalArgs0(): OptionBuilder {
                OptionBuilder.argCount = Option.UNLIMITED_VALUES
        OptionBuilder.optionalArg = true
        return INSTANCE
    }

    public static func hasOptionalArgs1(numArgs: Int64): OptionBuilder {
                OptionBuilder.argCount = numArgs; OptionBuilder.optionalArg = true; return INSTANCE
    }

    public static func isRequired0(): OptionBuilder {
                OptionBuilder.required = true; return INSTANCE
    }

    public static func isRequired1(newRequired: Bool): OptionBuilder {
                OptionBuilder.required = newRequired; return INSTANCE
    }

    private static func reset(): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func withArgName(name: String): OptionBuilder {
                OptionBuilder.argName = name; return INSTANCE
    }

    public static func withDescription(newDescription: String): OptionBuilder {
                OptionBuilder.description = newDescription; return INSTANCE
    }

    public static func withLongOpt(newLongopt: String): OptionBuilder {
                OptionBuilder.longOption = newLongopt; return INSTANCE
    }

    public static func withType0(newType: Any): OptionBuilder {
                OptionBuilder.type__ = newType; return INSTANCE
    }

    public static func withType1(newType: Any): OptionBuilder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func withValueSeparator0(): OptionBuilder {
                OptionBuilder.valueSeparator = '='; return INSTANCE
    }

    public static func withValueSeparator1(sep: Rune): OptionBuilder {
                OptionBuilder.valueSeparator = sep; return INSTANCE
    }

    private init() {
                throw Exception("TODO")
    }

    // Methods End
}

