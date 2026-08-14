// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class BasicParser <: Parser {
    // Fields Begin
    // Fields End

    // Methods Begin
    protected override func flatten(options_param: Options, arguments: Array<Any>, stopAtNonOption: Bool): Array<Any> {
        throw Exception('TODO')
    }

    // Methods End
}

