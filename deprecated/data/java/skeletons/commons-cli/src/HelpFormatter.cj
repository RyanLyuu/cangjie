// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class HelpFormatter {
    // Fields Begin
    static let DEFAULT_LONG_OPT_PREFIX: String = throw Exception('TODO')
    static let DEFAULT_LONG_OPT_SEPARATOR: String = throw Exception('TODO')
    static let DEFAULT_ARG_NAME: String = throw Exception('TODO')
    var defaultWidth: Int64 = throw Exception('TODO')
    var defaultLeftPad: Int64 = throw Exception('TODO')
    var defaultDescPad: Int64 = throw Exception('TODO')
    var defaultSyntaxPrefix: String = throw Exception('TODO')
    var defaultNewLine: String = throw Exception('TODO')
    var defaultOptPrefix: String = throw Exception('TODO')
    var defaultLongOptPrefix: String = throw Exception('TODO')
    var defaultArgName: String = throw Exception('TODO')
    var optionComparator: (Option, Option) -> Ordering = throw Exception('TODO')
    var longOptSeparator: String = throw Exception('TODO')
    static let DEFAULT_WIDTH: Int64 = throw Exception('TODO')
    static let DEFAULT_LEFT_PAD: Int64 = throw Exception('TODO')
    static let DEFAULT_DESC_PAD: Int64 = throw Exception('TODO')
    static let DEFAULT_SYNTAX_PREFIX: String = throw Exception('TODO')
    static let DEFAULT_OPT_PREFIX: String = throw Exception('TODO')
    // Fields End

    // Methods Begin
    private func appendOption(buff: StringBuilder, option: Option, required: Bool): Unit {
        throw Exception('TODO')
    }

    private func appendOptionGroup(buff: StringBuilder, group: OptionGroup): Unit {
        throw Exception('TODO')
    }

    protected open func createPadding(len: Int64): String {
        throw Exception('TODO')
    }

    protected open func findWrapPos(text: String, width: Int64, startPos: Int64): Int64 {
        throw Exception('TODO')
    }

    public open func getArgName(): String {
        throw Exception('TODO')
    }

    public open func getDescPadding(): Int64 {
        throw Exception('TODO')
    }

    public open func getLeftPadding(): Int64 {
        throw Exception('TODO')
    }

    public open func getLongOptPrefix(): String {
        throw Exception('TODO')
    }

    public open func getLongOptSeparator(): String {
        throw Exception('TODO')
    }

    public open func getNewLine(): String {
        throw Exception('TODO')
    }

    public open func getOptionComparator(): (Option, Option) -> Ordering {
        throw Exception('TODO')
    }

    public open func getOptPrefix(): String {
        throw Exception('TODO')
    }

    public open func getSyntaxPrefix(): String {
        throw Exception('TODO')
    }

    public open func getWidth(): Int64 {
        throw Exception('TODO')
    }

    public open func printHelp0(width: Int64, cmdLineSyntax: String, header: String, options: Options, footer: String): Unit {
        throw Exception('TODO')
    }

    public open func printHelp1(width: Int64, cmdLineSyntax: String, header: String, options: Options, footer: String, autoUsage: Bool): Unit {
        throw Exception('TODO')
    }

    public open func printHelp2(pw: Any, width: Int64, cmdLineSyntax: String, header: String, options: Options, leftPad: Int64, descPad: Int64, footer: String): Unit {
        throw Exception('TODO')
    }

    public open func printHelp3(pw: Any, width: Int64, cmdLineSyntax: String, header: String, options: Options, leftPad: Int64, descPad: Int64, footer: String, autoUsage: Bool): Unit {
        throw Exception('TODO')
    }

    public open func printHelp4(cmdLineSyntax: String, options: Options): Unit {
        throw Exception('TODO')
    }

    public open func printHelp5(cmdLineSyntax: String, options: Options, autoUsage: Bool): Unit {
        throw Exception('TODO')
    }

    public open func printHelp6(cmdLineSyntax: String, header: String, options: Options, footer: String): Unit {
        throw Exception('TODO')
    }

    public open func printHelp7(cmdLineSyntax: String, header: String, options: Options, footer: String, autoUsage: Bool): Unit {
        throw Exception('TODO')
    }

    public open func printOptions(pw: Any, width: Int64, options: Options, leftPad: Int64, descPad: Int64): Unit {
        throw Exception('TODO')
    }

    public open func printUsage0(pw: Any, width: Int64, cmdLineSyntax: String): Unit {
        throw Exception('TODO')
    }

    public open func printUsage1(pw: Any, width: Int64, app: String, options: Options): Unit {
        throw Exception('TODO')
    }

    public open func printWrapped0(pw: Any, width: Int64, nextLineTabStop: Int64, text: String): Unit {
        throw Exception('TODO')
    }

    public open func printWrapped1(pw: Any, width: Int64, text: String): Unit {
        throw Exception('TODO')
    }

    protected open func renderOptions(sb: StringBuilder, width: Int64, options: Options, leftPad: Int64, descPad: Int64): StringBuilder {
        throw Exception('TODO')
    }

    protected open func renderWrappedText(sb: StringBuilder, width: Int64, nextLineTabStop: Int64, text: String): StringBuilder {
        throw Exception('TODO')
    }

    private func renderWrappedTextBlock(sb: StringBuilder, width: Int64, nextLineTabStop: Int64, text: String): Any {
        throw Exception('TODO')
    }

    protected open func rtrim(s: String): String {
        throw Exception('TODO')
    }

    public open func setArgName(name: String): Unit {
        throw Exception('TODO')
    }

    public open func setDescPadding(padding: Int64): Unit {
        throw Exception('TODO')
    }

    public open func setLeftPadding(padding: Int64): Unit {
        throw Exception('TODO')
    }

    public open func setLongOptPrefix(prefix: String): Unit {
        throw Exception('TODO')
    }

    public open func setLongOptSeparator(longOptSeparator_param: String): Unit {
        throw Exception('TODO')
    }

    public open func setNewLine(newline: String): Unit {
        throw Exception('TODO')
    }

    public open func setOptionComparator(comparator: (Option, Option) -> Ordering): Unit {
        throw Exception('TODO')
    }

    public open func setOptPrefix(prefix: String): Unit {
        throw Exception('TODO')
    }

    public open func setSyntaxPrefix(prefix: String): Unit {
        throw Exception('TODO')
    }

    public open func setWidth(width: Int64): Unit {
        throw Exception('TODO')
    }

    // Methods End
}

private open class HelpFormatter_OptionComparator {
    // Fields Begin
    // Fields End

    // Methods Begin
    public open func compare(opt1: Option, opt2: Option): Int64 {
        throw Exception('TODO')
    }

    // Methods End
}

