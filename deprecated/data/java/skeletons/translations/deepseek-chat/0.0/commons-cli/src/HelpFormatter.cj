// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class HelpFormatter {
    // Fields Begin
    static let DEFAULT_LONG_OPT_PREFIX: String = "--"
    static let DEFAULT_LONG_OPT_SEPARATOR: String = " "
    static let DEFAULT_ARG_NAME: String = "arg"
    var defaultWidth: Int64 = DEFAULT_WIDTH
    var defaultLeftPad: Int64 = DEFAULT_LEFT_PAD
    var defaultDescPad: Int64 = DEFAULT_DESC_PAD
    var defaultSyntaxPrefix: String = DEFAULT_SYNTAX_PREFIX
    var defaultNewLine: String = throw Exception('TODO')  // Already translated, compilation failed
    var defaultOptPrefix: String = DEFAULT_OPT_PREFIX
    var defaultLongOptPrefix: String = DEFAULT_LONG_OPT_PREFIX
    var defaultArgName: String = DEFAULT_ARG_NAME
    var optionComparator: (Option, Option) -> Ordering = throw Exception('TODO')  // Already translated, compilation failed
    var longOptSeparator: String = DEFAULT_LONG_OPT_SEPARATOR
    static let DEFAULT_WIDTH: Int64 = 74
    static let DEFAULT_LEFT_PAD: Int64 = 1
    static let DEFAULT_DESC_PAD: Int64 = 3
    static let DEFAULT_SYNTAX_PREFIX: String = "usage: "
    static let DEFAULT_OPT_PREFIX: String = "-"
    // Fields End

    // Methods Begin
    private func appendOption(buff: StringBuilder, option: Option, required: Bool): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func appendOptionGroup(buff: StringBuilder, group: OptionGroup): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func createPadding(len: Int64): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func findWrapPos(text: String, width: Int64, startPos: Int64): Int64 {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getArgName(): String {
                return defaultArgName
    }

    public open func getDescPadding(): Int64 {
                return defaultDescPad
    }

    public open func getLeftPadding(): Int64 {
                return defaultLeftPad
    }

    public open func getLongOptPrefix(): String {
                return defaultLongOptPrefix
    }

    public open func getLongOptSeparator(): String {
                return longOptSeparator
    }

    public open func getNewLine(): String {
                return defaultNewLine
    }

    public open func getOptionComparator(): (Option, Option) -> Ordering {
                return optionComparator
    }

    public open func getOptPrefix(): String {
                return defaultOptPrefix
    }

    public open func getSyntaxPrefix(): String {
                return defaultSyntaxPrefix
    }

    public open func getWidth(): Int64 {
                return defaultWidth
    }

    public open func printHelp0(width: Int64, cmdLineSyntax: String, header: String, options: Options, footer: String): Unit {
                printHelp1(width, cmdLineSyntax, header, options, footer, false)
    }

    public open func printHelp1(width: Int64, cmdLineSyntax: String, header: String, options: Options, footer: String, autoUsage: Bool): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func printHelp2(pw: Any, width: Int64, cmdLineSyntax: String, header: String, options: Options, leftPad: Int64, descPad: Int64, footer: String): Unit {
                printHelp3(pw, width, cmdLineSyntax, header, options, leftPad, descPad, footer, false)
    }

    public open func printHelp3(pw: Any, width: Int64, cmdLineSyntax: String, header: String, options: Options, leftPad: Int64, descPad: Int64, footer: String, autoUsage: Bool): Unit {
                if (cmdLineSyntax == "" || cmdLineSyntax.isEmpty()) {
        throw IllegalArgumentException("cmdLineSyntax not provided")
        }
        if (autoUsage) {
        printUsage1(pw, width, cmdLineSyntax, options)
        } else {
        printUsage0(pw, width, cmdLineSyntax)
        }
        if (header != "" && !header.isEmpty()) {
        printWrapped1(pw, width, header)
        }
        printOptions(pw, width, options, leftPad, descPad)
        if (footer != "" && !footer.isEmpty()) {
        printWrapped1(pw, width, footer)
        }
    }

    public open func printHelp4(cmdLineSyntax: String, options: Options): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func printHelp5(cmdLineSyntax: String, options: Options, autoUsage: Bool): Unit {
                printHelp1(getWidth(), cmdLineSyntax, "", options, "", autoUsage)
    }

    public open func printHelp6(cmdLineSyntax: String, header: String, options: Options, footer: String): Unit {
                printHelp7(cmdLineSyntax, header, options, footer, false)
    }

    public open func printHelp7(cmdLineSyntax: String, header: String, options: Options, footer: String, autoUsage: Bool): Unit {
                printHelp1(getWidth(), cmdLineSyntax, header, options, footer, autoUsage)
    }

    public open func printOptions(pw: Any, width: Int64, options: Options, leftPad: Int64, descPad: Int64): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func printUsage0(pw: Any, width: Int64, cmdLineSyntax: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func printUsage1(pw: Any, width: Int64, app: String, options: Options): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func printWrapped0(pw: Any, width: Int64, nextLineTabStop: Int64, text: String): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func printWrapped1(pw: Any, width: Int64, text: String): Unit {
                printWrapped0(pw, width, 0, text)
    }

    protected open func renderOptions(sb: StringBuilder, width: Int64, options: Options, leftPad: Int64, descPad: Int64): StringBuilder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func renderWrappedText(sb: StringBuilder, width: Int64, nextLineTabStop: Int64, text: String): StringBuilder {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    private func renderWrappedTextBlock(sb: StringBuilder, width: Int64, nextLineTabStop: Int64, text: String): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    protected open func rtrim(s: String): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func setArgName(name: String): Unit {
                this.defaultArgName = name
    }

    public open func setDescPadding(padding: Int64): Unit {
                this.defaultDescPad = padding
    }

    public open func setLeftPadding(padding: Int64): Unit {
                this.defaultLeftPad = padding
    }

    public open func setLongOptPrefix(prefix: String): Unit {
                this.defaultLongOptPrefix = prefix
    }

    public open func setLongOptSeparator(longOptSeparator_param: String): Unit {
                this.longOptSeparator = longOptSeparator_param
    }

    public open func setNewLine(newline: String): Unit {
                this.defaultNewLine = newline
    }

    public open func setOptionComparator(comparator: (Option, Option) -> Ordering): Unit {
        throw Exception('TODO')
    }

    public open func setOptPrefix(prefix: String): Unit {
                this.defaultOptPrefix = prefix
    }

    public open func setSyntaxPrefix(prefix: String): Unit {
                this.defaultSyntaxPrefix = prefix
    }

    public open func setWidth(width: Int64): Unit {
                this.defaultWidth = width
    }

    // Methods End
}

private open class HelpFormatter_OptionComparator {
    // Fields Begin
    // Fields End

    // Methods Begin
    public open func compare(opt1: Option, opt2: Option): Int64 {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End
}

