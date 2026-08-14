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
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func UnrecognizedOptionException1(message: String): UnrecognizedOptionException {
                return UnrecognizedOptionException(message, "")
    }

    public open func getOption(): String {
                return this.option
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

