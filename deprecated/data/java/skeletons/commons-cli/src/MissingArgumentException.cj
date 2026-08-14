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
        throw Exception('TODO')
    }

    public static func MissingArgumentException1(constructorId: Int64, message: String, option_param: Option): MissingArgumentException {
        throw Exception('TODO')
    }

    public open func getOption(): Option {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

