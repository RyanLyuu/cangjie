// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
// Imports End

public open class PosixParser <: Parser {
    // Fields Begin
    let tokens: ArrayList<String> = throw Exception('TODO')
    var eatTheRest: Bool = throw Exception('TODO')
    var currentOption: Option = throw Exception('TODO')
    var options_field: Options = throw Exception('TODO')
    // Fields End

    // Methods Begin
    protected open func burstToken(token: String, stopAtNonOption: Bool): Unit {
        throw Exception('TODO')
    }

    protected override func flatten(options_param: Options, arguments: Array<Any>, stopAtNonOption: Bool): Array<Any> {
        throw Exception('TODO')
    }

    private func gobble(iter: Iterator<String>): Unit {
        throw Exception('TODO')
    }

    private func init_(): Unit {
        throw Exception('TODO')
    }

    private func processNonOptionToken(value: String, stopAtNonOption: Bool): Unit {
        throw Exception('TODO')
    }

    private func processOptionToken(token: String, stopAtNonOption: Bool): Unit {
        throw Exception('TODO')
    }

    // Methods End
}

