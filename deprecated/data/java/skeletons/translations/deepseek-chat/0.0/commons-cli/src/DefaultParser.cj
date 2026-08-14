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
    var stopAtNonOption: Bool = false
    var currentToken: String = throw Exception('TODO')
    var currentOption: Option = throw Exception('TODO')
    var skipParsing: Bool = false
    var expectedOpts: ArrayList<Any> = ArrayList<Any>()
    let allowPartialMatching: Bool = true
    let stripLeadingAndTrailingQuotes: Bool = false  // Already translated, compilation failed
    // Fields End

    // Methods Begin
    public static func builder(): DefaultParser_Builder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public init(constructorId: Int64, allowPartialMatching_param: Bool, stripLeadingAndTrailingQuotes_param: Bool) {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func checkRequiredArgs(): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func checkRequiredOptions(): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func getLongPrefix(token: String): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func getMatchingLongOptions(token: String): ArrayList<String> {
                if (allowPartialMatching) {
        return options.getMatchingOptions(token)
        }
        let matches = ArrayList<String>(1)
        if (options.hasLongOption(token)) {
        let option = options.getOption(token)
        matches.add(option.getLongOpt())
        }
        return matches
    }

    protected open func handleConcatenatedOptions(token: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleLongOption(token: String): Unit {
                if (token.indexOf('=') == -1) {
        handleLongOptionWithoutEqual(token)
        } else {
        handleLongOptionWithEqual(token)
        }
    }

    private func handleLongOptionWithEqual(token: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleLongOptionWithoutEqual(token: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleOption(option: Option): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleProperties(properties: HashMap<String, String>): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleShortAndLongOption(token: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleToken(token: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func handleUnknownToken(token: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func isArgument(token: String): Bool {
                return !isOption(token) || isNegativeNumber(token)
    }

    private func isJavaProperty(token: String): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func isLongOption(token: String): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func isNegativeNumber(token: String): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func isOption(token: String): Bool {
                return isLongOption(token) || isShortOption(token)
    }

    private func isShortOption(token: String): Bool {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func parse0(options_param: Options, arguments: Array<Any>): CommandLine {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func parse1(options_param: Options, arguments: Array<Any>, stopAtNonOption_param: Bool): CommandLine {
                return parse3(options_param, arguments, HashMap<String, String>(), stopAtNonOption_param)
    }

    public open func parse2(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>): CommandLine {
                return parse3(options_param, arguments, properties, false)
    }

    public open func parse3(options_param: Options, arguments: Array<Any>, properties: HashMap<String, String>, stopAtNonOption_param: Bool): CommandLine {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func stripLeadingAndTrailingQuotesDefaultOff(token: String): String {
                if (stripLeadingAndTrailingQuotes) {
        return Util.stripLeadingAndTrailingQuotes(token)
        }
        return token
    }

    private func stripLeadingAndTrailingQuotesDefaultOn(token: String): String {
                if (stripLeadingAndTrailingQuotes == false || stripLeadingAndTrailingQuotes) {
        return Util.stripLeadingAndTrailingQuotes(token)
        }
        return token
    }

    private func updateRequiredOptions(option: Option): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
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
                return DefaultParser(1, allowPartialMatching, stripLeadingAndTrailingQuotes)
    }

    public open func setAllowPartialMatching(allowPartialMatching_param: Bool): DefaultParser_Builder {
                this.allowPartialMatching = allowPartialMatching_param
        return this
    }

    public open func setStripLeadingAndTrailingQuotes(stripLeadingAndTrailingQuotes_param: Bool): DefaultParser_Builder {
                this.stripLeadingAndTrailingQuotes = stripLeadingAndTrailingQuotes_param; return this
    }

    // Methods End
}

