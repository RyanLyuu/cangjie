// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
import std.collection.HashMap
// Imports End

public open class CommandLine {
    // Fields Begin
    let args: ArrayList<String> = ArrayList<String>()
    let options: ArrayList<Option> = ArrayList<Option>()
    // Fields End

    // Methods Begin
    protected init() {
                throw Exception("TODO")
    }

    protected open func addArg(arg: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func addOption(opt: Option): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getArgList(): ArrayList<String> {
                return args
    }

    public open func getArgs(): Array<Any> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptionObject0(opt: Rune): Any {
                return getOptionObject1(opt.toString())
    }

    public open func getOptionObject1(opt: String): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptionProperties0(option: Option): HashMap<String, String> {
                let props = HashMap<String, String>()
        for (processedOption in options) {
        if (processedOption.equals(option)) {
        let values = processedOption.values
        if (values.size >= 2) {
        props[values[0]] = values[1]
        } else if (values.size == 1) {
        props[values[0]] = "true"
        }
        }
        }
        return props
    }

    public open func getOptionProperties1(opt: String): HashMap<String, String> {
                let props = HashMap<String, String>()
        for (option in options) {
        if (opt == option.getOpt() || opt == option.getLongOpt()) {
        let values = option.getValuesList()
        if (values.size >= 2) {
        props[values[0]] = values[1]
        } else if (values.size == 1) {
        props[values[0]] = "true"
        }
        }
        }
        return props
    }

    public open func getOptions(): Array<Any> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptionValue0(opt: Rune): String {
                return getOptionValue4(String(opt))
    }

    public open func getOptionValue1(opt: Rune, defaultValue: String): String {
                return getOptionValue5(String(opt), defaultValue)
    }

    public open func getOptionValue2(option: Option): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptionValue3(option: Option, defaultValue: String): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptionValue4(opt: String): String {
                return getOptionValue2(resolveOption(opt))
    }

    public open func getOptionValue5(opt: String, defaultValue: String): String {
                return getOptionValue3(resolveOption(opt), defaultValue)
    }

    public open func getOptionValues0(opt: Rune): Array<Any> {
                return getOptionValues2(String(opt))
    }

    public open func getOptionValues1(option: Option): Array<Any> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptionValues2(opt: String): Array<Any> {
                return getOptionValues1(resolveOption(opt))
    }

    public open func getParsedOptionValue0(opt: Rune): Any {
                return getParsedOptionValue2(String(opt))
    }

    public open func getParsedOptionValue1(option: Option): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getParsedOptionValue2(opt: String): Any {
                return getParsedOptionValue1(resolveOption(opt))
    }

    public open func hasOption0(opt: Rune): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func hasOption1(opt: Option): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func hasOption2(opt: String): Bool {
                return hasOption1(resolveOption(opt))
    }

    public open func iterator(): ArrayList<Option> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func resolveOption(opt: String): Option {
                var strippedOpt = Util.stripLeadingHyphens(opt)
        for (option in options) {
        if (strippedOpt == option.option || strippedOpt == option.longOption) {
        return option
        }
        }
        return Option()
    }

    // Methods End
}

public class CommandLine_Builder {
    // Fields Begin
    let commandLine: CommandLine = CommandLine()
    // Fields End

    // Methods Begin
    public open func addArg(arg: String): CommandLine_Builder {
        throw Exception('TODO')
    }

    public open func addOption(opt: Option): CommandLine_Builder {
        throw Exception('TODO')
    }

    public open func build(): CommandLine {
                return commandLine
    }

    // Methods End
}

