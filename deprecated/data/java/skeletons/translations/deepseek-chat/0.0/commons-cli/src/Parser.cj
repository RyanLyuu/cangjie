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
    var requiredOptions: ArrayList<Any> = ArrayList<Any>()
    // Fields End

    // Methods Begin
    protected open func checkRequiredOptions(): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func flatten(opts: Options, arguments: Array<Any>, stopAtNonOption: Bool): Array<Any> {
                throw Exception("TODO")
    }

    protected open func getOptions(): Options {
                return this.options
    }

    protected open func getRequiredOptions(): ArrayList<Any> {
                return requiredOptions
    }

    public open func parse0(options_param: Options, arguments: Array<Any>): CommandLine {
                return parse3(options_param, arguments, HashMap<String, String>(), false)
    }

    public open func parse1(options_param: Options, arguments: Array<Any>, stopAtNonOption: Bool): CommandLine {
                return parse3(options_param, arguments, HashMap<String, String>(), stopAtNonOption)
    }

    public open func parse2(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>): CommandLine {
                return parse3(options_param, arguments, properties, false)
    }

    public open func parse3(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>, stopAtNonOption: Bool): CommandLine {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func processArgs(opt: Option, iter: Any): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func processOption(arg: String, iter: Any): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func processProperties(properties: HashMap<String, String>): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func setOptions(options_param: Options): Unit {
                this.options = options_param
        this.requiredOptions = ArrayList<Any>(options_param.getRequiredOptions())
    }

    private func updateRequiredOptions(opt: Option): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End
}

