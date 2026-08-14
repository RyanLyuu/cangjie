// Package: jansi
package jansi

// Imports Begin

// Imports End

public open class AnsiConsole {
    // Fields Begin
    static let JANSI_OUT_COLORS: String = throw Exception('TODO')
    static let JANSI_ERR_COLORS: String = throw Exception('TODO')
    static let JANSI_COLORS_16: String = throw Exception('TODO')
    static let JANSI_COLORS_256: String = throw Exception('TODO')
    static let JANSI_COLORS_TRUECOLOR: String = throw Exception('TODO')
    static let JANSI_PASSTHROUGH: String = throw Exception('TODO')
    static let JANSI_STRIP: String = throw Exception('TODO')
    static let JANSI_FORCE: String = throw Exception('TODO')
    static let JANSI_EAGER: String = throw Exception('TODO')
    static let JANSI_NORESET: String = throw Exception('TODO')
    static let JANSI_GRACEFUL: String = throw Exception('TODO')
    static var system_out: Any = throw Exception('TODO')
    static var out: Any = throw Exception('TODO')
    static var system_err: Any = throw Exception('TODO')
    static var err: Any = throw Exception('TODO')
    static let IS_WINDOWS: Bool = throw Exception('TODO')
    static let IS_CYGWIN: Bool = throw Exception('TODO')
    static let IS_MSYSTEM: Bool = throw Exception('TODO')
    static let IS_CONEMU: Bool = throw Exception('TODO')
    static let ENABLE_VIRTUAL_TERMINAL_PROCESSING: Int32 = throw Exception('TODO')
    static var STDOUT_FILENO: Int32 = throw Exception('TODO')
    static var STDERR_FILENO: Int32 = throw Exception('TODO')
    static var initialized: Bool = throw Exception('TODO')
    static var installed: Int32 = throw Exception('TODO')
    static var virtualProcessing: Int32 = throw Exception('TODO')
    static let JANSI_MODE: String = throw Exception('TODO')
    static let JANSI_OUT_MODE: String = throw Exception('TODO')
    static let JANSI_ERR_MODE: String = throw Exception('TODO')
    static let JANSI_MODE_STRIP: String = throw Exception('TODO')
    static let JANSI_MODE_FORCE: String = throw Exception('TODO')
    static let JANSI_MODE_DEFAULT: String = throw Exception('TODO')
    static let JANSI_COLORS: String = throw Exception('TODO')
    // Fields End

    // Static Initializer Begin
    static init() {
        throw Exception('TODO')
    }

    // Static Initializer End

    // Methods Begin
    public static func getTerminalWidth(): Int32 {
        throw Exception('TODO')
    }

    private init() {
        throw Exception('TODO')
    }

    private static func ansiStream(stdout: Bool): AnsiPrintStream {
        throw Exception('TODO')
    }

    private static func newPrintStream(out_param: AnsiOutputStream, enc: String): AnsiPrintStream {
        throw Exception('TODO')
    }

    static func getBoolean(name: String): Bool {
        throw Exception('TODO')
    }

    public static func out_method(): AnsiPrintStream {
        throw Exception('TODO')
    }

    public static func sysOut(): Any {
        throw Exception('TODO')
    }

    public static func err_method(): AnsiPrintStream {
        throw Exception('TODO')
    }

    public static func sysErr(): Any {
        throw Exception('TODO')
    }

    public static func systemInstall(): Unit {
        throw Exception('TODO')
    }

    public static func isInstalled(): Bool {
        throw Exception('TODO')
    }

    public static func systemUninstall(): Unit {
        throw Exception('TODO')
    }

    static func initStreams(): Unit {
        throw Exception('TODO')
    }

    // Methods End
}

