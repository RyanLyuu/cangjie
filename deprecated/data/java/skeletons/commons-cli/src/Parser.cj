// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
import std.collection.HashMap
// Imports End

public abstract class Parser <: CommandLineParser {
    // Fields Begin
    var cmd: CommandLine = throw Exception('TODO')
    var options: Options = throw Exception('TODO')
    var requiredOptions: ArrayList<Any> = throw Exception('TODO')
    // Fields End

    // Methods Begin
    protected open func checkRequiredOptions(): Unit {
        throw Exception('TODO')
    }

    protected open func flatten(opts: Options, arguments: Array<Any>, stopAtNonOption: Bool): Array<Any> {
        throw Exception('TODO')
    }

    protected open func getOptions(): Options {
        throw Exception('TODO')
    }

    protected open func getRequiredOptions(): ArrayList<Any> {
        throw Exception('TODO')
    }

    public open func parse0(options_param: Options, arguments: Array<Any>): CommandLine {
        throw Exception('TODO')
    }

    public open func parse1(options_param: Options, arguments: Array<Any>, stopAtNonOption: Bool): CommandLine {
        throw Exception('TODO')
    }

    public open func parse2(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>): CommandLine {
        throw Exception('TODO')
    }

    public open func parse3(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>, stopAtNonOption: Bool): CommandLine {
        throw Exception('TODO')
    }

    public open func processArgs(opt: Option, iter: Any): Unit {
        throw Exception('TODO')
    }

    protected open func processOption(arg: String, iter: Any): Unit {
        throw Exception('TODO')
    }

    protected open func processProperties(properties: HashMap<String, String>): Unit {
        throw Exception('TODO')
    }

    protected open func setOptions(options_param: Options): Unit {
        throw Exception('TODO')
    }

    private func updateRequiredOptions(opt: Option): Unit {
        throw Exception('TODO')
    }

    // Methods End
}

