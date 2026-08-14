// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
// Imports End

public open class PosixParser <: Parser {
    // Fields Begin
    let tokens: ArrayList<String> = ArrayList<String>()
    var eatTheRest: Bool = false
    var currentOption: Option = throw Exception('TODO')
    var options_field: Options = throw Exception('TODO')
    // Fields End

    // Methods Begin
    protected open func burstToken(token: String, stopAtNonOption: Bool): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected override func flatten(options_param: Options, arguments: Array<Any>, stopAtNonOption: Bool): Array<Any> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func gobble(iter: Iterator<String>): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func init_(): Unit {
                this.eatTheRest = false
        this.tokens.clear()
    }

    private func processNonOptionToken(value: String, stopAtNonOption: Bool): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func processOptionToken(token: String, stopAtNonOption: Bool): Unit {
                if (stopAtNonOption && !options_field.hasOption(token)) {
        eatTheRest = true
        }
        if (options_field.hasOption(token)) {
        currentOption = options_field.getOption(token)
        }
        tokens.add(token)
    }

    // Methods End
}

