// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
import std.collection.HashMap
// Imports End

public open class CommandLine {
    // Fields Begin
    let args: ArrayList<String> = throw Exception('TODO')
    let options: ArrayList<Option> = throw Exception('TODO')
    // Fields End

    // Methods Begin
    protected init() {
        throw Exception('TODO')
    }

    protected open func addArg(arg: String): Unit {
        throw Exception('TODO')
    }

    protected open func addOption(opt: Option): Unit {
        throw Exception('TODO')
    }

    public open func getArgList(): ArrayList<String> {
        throw Exception('TODO')
    }

    public open func getArgs(): Array<Any> {
        throw Exception('TODO')
    }

    public open func getOptionObject0(opt: Rune): Any {
        throw Exception('TODO')
    }

    public open func getOptionObject1(opt: String): Any {
        throw Exception('TODO')
    }

    public open func getOptionProperties0(option: Option): HashMap<String, String> {
        throw Exception('TODO')
    }

    public open func getOptionProperties1(opt: String): HashMap<String, String> {
        throw Exception('TODO')
    }

    public open func getOptions(): Array<Any> {
        throw Exception('TODO')
    }

    public open func getOptionValue0(opt: Rune): String {
        throw Exception('TODO')
    }

    public open func getOptionValue1(opt: Rune, defaultValue: String): String {
        throw Exception('TODO')
    }

    public open func getOptionValue2(option: Option): String {
        throw Exception('TODO')
    }

    public open func getOptionValue3(option: Option, defaultValue: String): String {
        throw Exception('TODO')
    }

    public open func getOptionValue4(opt: String): String {
        throw Exception('TODO')
    }

    public open func getOptionValue5(opt: String, defaultValue: String): String {
        throw Exception('TODO')
    }

    public open func getOptionValues0(opt: Rune): Array<Any> {
        throw Exception('TODO')
    }

    public open func getOptionValues1(option: Option): Array<Any> {
        throw Exception('TODO')
    }

    public open func getOptionValues2(opt: String): Array<Any> {
        throw Exception('TODO')
    }

    public open func getParsedOptionValue0(opt: Rune): Any {
        throw Exception('TODO')
    }

    public open func getParsedOptionValue1(option: Option): Any {
        throw Exception('TODO')
    }

    public open func getParsedOptionValue2(opt: String): Any {
        throw Exception('TODO')
    }

    public open func hasOption0(opt: Rune): Bool {
        throw Exception('TODO')
    }

    public open func hasOption1(opt: Option): Bool {
        throw Exception('TODO')
    }

    public open func hasOption2(opt: String): Bool {
        throw Exception('TODO')
    }

    public open func iterator(): ArrayList<Option> {
        throw Exception('TODO')
    }

    private func resolveOption(opt: String): Option {
        throw Exception('TODO')
    }

    // Methods End
}

public class CommandLine_Builder {
    // Fields Begin
    let commandLine: CommandLine = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public open func addArg(arg: String): CommandLine_Builder {
        throw Exception('TODO')
    }

    public open func addOption(opt: Option): CommandLine_Builder {
        throw Exception('TODO')
    }

    public open func build(): CommandLine {
        throw Exception('TODO')
    }

    // Methods End
}

