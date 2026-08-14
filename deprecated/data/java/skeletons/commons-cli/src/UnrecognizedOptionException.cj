// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class UnrecognizedOptionException <: ParseException {
    // Fields Begin
    let option: String = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public init(message: String, option_param: String) {
        super()
        throw Exception('TODO')
    }

    public static func UnrecognizedOptionException1(message: String): UnrecognizedOptionException {
        throw Exception('TODO')
    }

    public open func getOption(): String {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

