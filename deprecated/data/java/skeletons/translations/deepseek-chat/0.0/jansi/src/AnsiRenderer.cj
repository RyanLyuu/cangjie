// Package: jansi
package jansi

// Imports Begin

// Imports End

public open class AnsiRenderer {
    // Fields Begin
    static let BEGIN_TOKEN: String = throw Exception('TODO')
    static let END_TOKEN: String = throw Exception('TODO')
    static let CODE_TEXT_SEPARATOR: String = throw Exception('TODO')
    static let CODE_LIST_SEPARATOR: String = throw Exception('TODO')
    static let BEGIN_TOKEN_LEN: Int32 = throw Exception('TODO')
    static let END_TOKEN_LEN: Int32 = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public static func render0(input: String): String {
        throw Exception('TODO')
    }

    public static func render1(input: String, target: Any): Any {
        throw Exception('TODO')
    }

    public static func render2(text: String): String {
        throw Exception('TODO')
    }

    public static func renderCodes0(): String {
        throw Exception('TODO')
    }

    public static func renderCodes1(codes: String): String {
        throw Exception('TODO')
    }

    private static func render3(ansi: Ansi): Ansi {
        throw Exception('TODO')
    }

    public static func test(text: String): Bool {
        throw Exception('TODO')
    }

    private init() {
        throw Exception('TODO')
    }

    // Methods End
}

public open class Code {
    // Fields Begin
    var BLACK: Any = throw Exception('TODO')
    var RED: Any = throw Exception('TODO')
    var GREEN: Any = throw Exception('TODO')
    var YELLOW: Any = throw Exception('TODO')
    var BLUE: Any = throw Exception('TODO')
    var MAGENTA: Any = throw Exception('TODO')
    var CYAN: Any = throw Exception('TODO')
    var WHITE: Any = throw Exception('TODO')
    var DEFAULT: Any = throw Exception('TODO')
    var FG_BLACK: Any = throw Exception('TODO')
    var FG_RED: Any = throw Exception('TODO')
    var FG_GREEN: Any = throw Exception('TODO')
    var FG_YELLOW: Any = throw Exception('TODO')
    var FG_BLUE: Any = throw Exception('TODO')
    var FG_MAGENTA: Any = throw Exception('TODO')
    var FG_CYAN: Any = throw Exception('TODO')
    var FG_WHITE: Any = throw Exception('TODO')
    var FG_DEFAULT: Any = throw Exception('TODO')
    var BG_BLACK: Any = throw Exception('TODO')
    var BG_RED: Any = throw Exception('TODO')
    var BG_GREEN: Any = throw Exception('TODO')
    var BG_YELLOW: Any = throw Exception('TODO')
    var BG_BLUE: Any = throw Exception('TODO')
    var BG_MAGENTA: Any = throw Exception('TODO')
    var BG_CYAN: Any = throw Exception('TODO')
    var BG_WHITE: Any = throw Exception('TODO')
    var BG_DEFAULT: Any = throw Exception('TODO')
    var RESET: Any = throw Exception('TODO')
    var INTENSITY_BOLD: Any = throw Exception('TODO')
    var INTENSITY_FAINT: Any = throw Exception('TODO')
    var ITALIC: Any = throw Exception('TODO')
    var UNDERLINE: Any = throw Exception('TODO')
    var BLINK_SLOW: Any = throw Exception('TODO')
    var BLINK_FAST: Any = throw Exception('TODO')
    var BLINK_OFF: Any = throw Exception('TODO')
    var NEGATIVE_ON: Any = throw Exception('TODO')
    var NEGATIVE_OFF: Any = throw Exception('TODO')
    var CONCEAL_ON: Any = throw Exception('TODO')
    var CONCEAL_OFF: Any = throw Exception('TODO')
    var UNDERLINE_DOUBLE: Any = throw Exception('TODO')
    var UNDERLINE_OFF: Any = throw Exception('TODO')
    var BOLD: Any = throw Exception('TODO')
    var FAINT: Any = throw Exception('TODO')
    var n: Enum<Any> = throw Exception('TODO')
    var background: Bool = throw Exception('TODO')
    // Fields End

    // Methods Begin
    init(n: Enum<Any>, background: Bool) {
        throw Exception('TODO')
    }

    public open func isColor(): Bool {
        throw Exception('TODO')
    }

    public open func getColor(): Color {
        throw Exception('TODO')
    }

    public open func isAttribute(): Bool {
        throw Exception('TODO')
    }

    public open func getAttribute(): Attribute {
        throw Exception('TODO')
    }

    public open func isBackground(): Bool {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

