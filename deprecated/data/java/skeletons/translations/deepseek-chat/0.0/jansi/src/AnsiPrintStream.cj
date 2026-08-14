// Package: jansi
package jansi

// Imports Begin

// Imports End

public open class AnsiPrintStream {
    // Fields Begin
    // Fields End

    // Methods Begin
    public init(out: AnsiOutputStream, autoFlush: Bool, args: Any) {
        throw Exception('TODO')
    }

    private static func determineEncoding(args: Any): String {
        throw Exception('TODO')
    }

    protected open func getOut(): AnsiOutputStream {
        throw Exception('TODO')
    }

    public open func getType(): AnsiType {
        throw Exception('TODO')
    }

    public open func getColors(): AnsiColors {
        throw Exception('TODO')
    }

    public open func getMode(): AnsiMode {
        throw Exception('TODO')
    }

    public open func setMode(ansiMode: AnsiMode): Unit {
        throw Exception('TODO')
    }

    public open func isResetAtUninstall(): Bool {
        throw Exception('TODO')
    }

    public open func setResetAtUninstall(resetAtClose: Bool): Unit {
        throw Exception('TODO')
    }

    public open func getTerminalWidth(): Int32 {
        throw Exception('TODO')
    }

    public open func install(): Unit {
        throw Exception('TODO')
    }

    public open func uninstall(): Unit {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

