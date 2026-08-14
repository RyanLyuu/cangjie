// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class MissingArgumentException <: ParseException {
    // Fields Begin
    var option: Option = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public init(constructorId: Int64, message: String, option_param: Option) {
        super()
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func MissingArgumentException1(constructorId: Int64, message: String, option_param: Option): MissingArgumentException {
                if (constructorId == 1) {
        return MissingArgumentException(constructorId, "Missing argument for option: " + option_param.getKey(), option_param)
        }
        return MissingArgumentException(constructorId, message, option_param)
    }

    public open func getOption(): Option {
                return this.option
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

