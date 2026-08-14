// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class AmbiguousOptionException <: UnrecognizedOptionException {
    // Fields Begin
    let matchingOptions: Array<String> = throw Exception('TODO')
    // Fields End

    // Methods Begin
    private static func createMessage(option_param: String, matchingOptions_param: Array<String>): String {
        throw Exception('TODO')
    }

    public init(option_param: String, matchingOptions_param: Array<String>) {
        super()
        throw Exception('TODO')
    }

    public open func getMatchingOptions(): Array<String> {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

