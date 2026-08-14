// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
import std.collection.HashMap
// Imports End

public open class DefaultParser <: CommandLineParser {
    // Fields Begin
    var cmd: CommandLine = throw Exception('TODO')
    var options: Options = throw Exception('TODO')
    var stopAtNonOption: Bool = throw Exception('TODO')
    var currentToken: String = throw Exception('TODO')
    var currentOption: Option = throw Exception('TODO')
    var skipParsing: Bool = throw Exception('TODO')
    var expectedOpts: ArrayList<Any> = throw Exception('TODO')
    let allowPartialMatching: Bool = throw Exception('TODO')
    let stripLeadingAndTrailingQuotes: Bool = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public static func builder(): DefaultParser_Builder {
        throw Exception('TODO')
    }

    public init(constructorId: Int64, allowPartialMatching_param: Bool, stripLeadingAndTrailingQuotes_param: Bool) {
        throw Exception('TODO')
    }

    private func checkRequiredArgs(): Unit {
        throw Exception('TODO')
    }

    protected open func checkRequiredOptions(): Unit {
        throw Exception('TODO')
    }

    private func getLongPrefix(token: String): String {
        throw Exception('TODO')
    }

    private func getMatchingLongOptions(token: String): ArrayList<String> {
        throw Exception('TODO')
    }

    protected open func handleConcatenatedOptions(token: String): Unit {
        throw Exception('TODO')
    }

    private func handleLongOption(token: String): Unit {
        throw Exception('TODO')
    }

    private func handleLongOptionWithEqual(token: String): Unit {
        throw Exception('TODO')
    }

    private func handleLongOptionWithoutEqual(token: String): Unit {
        throw Exception('TODO')
    }

    private func handleOption(option: Option): Unit {
        throw Exception('TODO')
    }

    private func handleProperties(properties: HashMap<String, String>): Unit {
        throw Exception('TODO')
    }

    private func handleShortAndLongOption(token: String): Unit {
        throw Exception('TODO')
    }

    private func handleToken(token: String): Unit {
        throw Exception('TODO')
    }

    private func handleUnknownToken(token: String): Unit {
        throw Exception('TODO')
    }

    private func isArgument(token: String): Bool {
        throw Exception('TODO')
    }

    private func isJavaProperty(token: String): Bool {
        throw Exception('TODO')
    }

    private func isLongOption(token: String): Bool {
        throw Exception('TODO')
    }

    private func isNegativeNumber(token: String): Bool {
        throw Exception('TODO')
    }

    private func isOption(token: String): Bool {
        throw Exception('TODO')
    }

    private func isShortOption(token: String): Bool {
        throw Exception('TODO')
    }

    public open func parse0(options_param: Options, arguments: Array<Any>): CommandLine {
        throw Exception('TODO')
    }

    public open func parse1(options_param: Options, arguments: Array<Any>, stopAtNonOption_param: Bool): CommandLine {
        throw Exception('TODO')
    }

    public open func parse2(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>): CommandLine {
        throw Exception('TODO')
    }

    public open func parse3(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>, stopAtNonOption_param: Bool): CommandLine {
        throw Exception('TODO')
    }

    private func stripLeadingAndTrailingQuotesDefaultOff(token: String): String {
        throw Exception('TODO')
    }

    private func stripLeadingAndTrailingQuotesDefaultOn(token: String): String {
        throw Exception('TODO')
    }

    private func updateRequiredOptions(option: Option): Unit {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

public class DefaultParser_Builder {
    // Fields Begin
    var allowPartialMatching: Bool = throw Exception('TODO')
    var stripLeadingAndTrailingQuotes: Bool = throw Exception('TODO')
    // Fields End

    // Methods Begin
    private init() {
        throw Exception('TODO')
    }

    public open func build(): DefaultParser {
        throw Exception('TODO')
    }

    public open func setAllowPartialMatching(allowPartialMatching_param: Bool): DefaultParser_Builder {
        throw Exception('TODO')
    }

    public open func setStripLeadingAndTrailingQuotes(stripLeadingAndTrailingQuotes_param: Bool): DefaultParser_Builder {
        throw Exception('TODO')
    }

    // Methods End
}

