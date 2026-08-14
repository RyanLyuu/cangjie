// Package: jansi
package jansi

// Imports Begin

// Imports End

public open class Ansi {
    // Fields Begin
    static let DISABLE: String = throw Exception('TODO')
    static var detector: () -> Bool = throw Exception('TODO')
    static let holder: InheritableThreadLocal<Bool> = throw Exception('TODO')
    static let FIRST_ESC_CHAR: Rune = throw Exception('TODO')
    static let SECOND_ESC_CHAR: Rune = throw Exception('TODO')
    var builder: Any = throw Exception('TODO')
    var attributeOptions: ArrayList<Int32> = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public static func setDetector<Boolean>(detector_param: () -> Bool): Unit {
        throw Exception('TODO')
    }

    public static func isDetected(): Bool {
        throw Exception('TODO')
    }

    public static func setEnabled(flag: Bool): Unit {
        throw Exception('TODO')
    }

    public static func isEnabled(): Bool {
        throw Exception('TODO')
    }

    public static func ansi0(): Ansi {
        throw Exception('TODO')
    }

    public static func ansi1(builder_param: Any): Ansi {
        throw Exception('TODO')
    }

    public static func ansi2(size: Int32): Ansi {
        throw Exception('TODO')
    }

    public static func Ansi0(): Ansi {
        throw Exception('TODO')
    }

    public static func Ansi1(parent: Ansi): Ansi {
        throw Exception('TODO')
    }

    public static func Ansi2(size: Int32): Ansi {
        throw Exception('TODO')
    }

    public init(constructorId: Int32, builder_param: Any, parent: Ansi) {
        throw Exception('TODO')
    }

    public open func fg0(color: Color): Ansi {
        throw Exception('TODO')
    }

    public open func fg1(color: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func fgRgb0(color: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func fgRgb1(r: Int32, g: Int32, b: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func fgBlack(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBlue(): Ansi {
        throw Exception('TODO')
    }

    public open func fgCyan(): Ansi {
        throw Exception('TODO')
    }

    public open func fgDefault(): Ansi {
        throw Exception('TODO')
    }

    public open func fgGreen(): Ansi {
        throw Exception('TODO')
    }

    public open func fgMagenta(): Ansi {
        throw Exception('TODO')
    }

    public open func fgRed(): Ansi {
        throw Exception('TODO')
    }

    public open func fgYellow(): Ansi {
        throw Exception('TODO')
    }

    public open func bg0(color: Color): Ansi {
        throw Exception('TODO')
    }

    public open func bg1(color: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func bgRgb0(color: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func bgRgb1(r: Int32, g: Int32, b: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func bgCyan(): Ansi {
        throw Exception('TODO')
    }

    public open func bgDefault(): Ansi {
        throw Exception('TODO')
    }

    public open func bgGreen(): Ansi {
        throw Exception('TODO')
    }

    public open func bgMagenta(): Ansi {
        throw Exception('TODO')
    }

    public open func bgRed(): Ansi {
        throw Exception('TODO')
    }

    public open func bgYellow(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBright(color: Color): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightBlack(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightBlue(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightCyan(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightDefault(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightGreen(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightMagenta(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightRed(): Ansi {
        throw Exception('TODO')
    }

    public open func fgBrightYellow(): Ansi {
        throw Exception('TODO')
    }

    public open func bgBright(color: Color): Ansi {
        throw Exception('TODO')
    }

    public open func bgBrightCyan(): Ansi {
        throw Exception('TODO')
    }

    public open func bgBrightDefault(): Ansi {
        throw Exception('TODO')
    }

    public open func bgBrightGreen(): Ansi {
        throw Exception('TODO')
    }

    public open func bgBrightMagenta(): Ansi {
        throw Exception('TODO')
    }

    public open func bgBrightRed(): Ansi {
        throw Exception('TODO')
    }

    public open func bgBrightYellow(): Ansi {
        throw Exception('TODO')
    }

    public open func a0(attribute: Attribute): Ansi {
        throw Exception('TODO')
    }

    public open func cursor(row: Int32, column: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorToColumn(x: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorUp(y: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorDown(y: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorRight(x: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorLeft(x: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorMove(x: Int32, y: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorDownLine0(): Ansi {
        throw Exception('TODO')
    }

    public open func cursorDownLine1(n: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func cursorUpLine0(): Ansi {
        throw Exception('TODO')
    }

    public open func cursorUpLine1(n: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func eraseScreen0(): Ansi {
        throw Exception('TODO')
    }

    public open func eraseScreen1(kind: Erase): Ansi {
        throw Exception('TODO')
    }

    public open func eraseLine0(): Ansi {
        throw Exception('TODO')
    }

    public open func eraseLine1(kind: Erase): Ansi {
        throw Exception('TODO')
    }

    public open func scrollUp(rows: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func scrollDown(rows: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func restorCursorPosition(): Ansi {
        throw Exception('TODO')
    }

    public open func saveCursorPosition(): Ansi {
        throw Exception('TODO')
    }

    public open func saveCursorPositionSCO(): Ansi {
        throw Exception('TODO')
    }

    public open func saveCursorPositionDEC(): Ansi {
        throw Exception('TODO')
    }

    public open func restoreCursorPosition(): Ansi {
        throw Exception('TODO')
    }

    public open func restoreCursorPositionSCO(): Ansi {
        throw Exception('TODO')
    }

    public open func restoreCursorPositionDEC(): Ansi {
        throw Exception('TODO')
    }

    public open func reset(): Ansi {
        throw Exception('TODO')
    }

    public open func bold(): Ansi {
        throw Exception('TODO')
    }

    public open func boldOff(): Ansi {
        throw Exception('TODO')
    }

    public open func a1(value: String): Ansi {
        throw Exception('TODO')
    }

    public open func a2(value: Bool): Ansi {
        throw Exception('TODO')
    }

    public open func a3(value: Rune): Ansi {
        throw Exception('TODO')
    }

    public open func a4(value: Array<Rune>, offset: Int32, len: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func a5(value: Array<Rune>): Ansi {
        throw Exception('TODO')
    }

    public open func a6(value: Any, start: Int32, end: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func a7(value: Any): Ansi {
        throw Exception('TODO')
    }

    public open func a8(value: Float64): Ansi {
        throw Exception('TODO')
    }

    public open func a9(value: Float32): Ansi {
        throw Exception('TODO')
    }

    public open func a10(value: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func a11(value: Int64): Ansi {
        throw Exception('TODO')
    }

    public open func a12(value: Any): Ansi {
        throw Exception('TODO')
    }

    public open func a13(value: Any): Ansi {
        throw Exception('TODO')
    }

    public open func newline(): Ansi {
        throw Exception('TODO')
    }

    public open func format(pattern: String): Ansi {
        throw Exception('TODO')
    }

    public open func apply(fun: Ansi_Consumer): Ansi {
        throw Exception('TODO')
    }

    public open func render0(text: String): Ansi {
        throw Exception('TODO')
    }

    public open func render1(text: String): Ansi {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
    }

    private func appendEscapeSequence0(command: Rune): Ansi {
        throw Exception('TODO')
    }

    private func appendEscapeSequence1(command: Rune, option: Int32): Ansi {
        throw Exception('TODO')
    }

    private func appendEscapeSequence2(command: Rune): Ansi {
        throw Exception('TODO')
    }

    private func flushAttributes(): Unit {
        throw Exception('TODO')
    }

    private func _appendEscapeSequence(command: Rune): Ansi {
        throw Exception('TODO')
    }

    public open func append(csq: Any): Ansi {
        throw Exception('TODO')
    }

    public open func append0(csq: Any): Ansi {
        throw Exception('TODO')
    }

    public open func append(csq: Any, start: Int32, end: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func append1(csq: Any, start: Int32, end: Int32): Ansi {
        throw Exception('TODO')
    }

    public open func append(c: Rune): Ansi {
        throw Exception('TODO')
    }

    public open func append2(c: Rune): Ansi {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

public open class Color {
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
    var value: Int32 = throw Exception('TODO')
    var name: String = throw Exception('TODO')
    // Fields End

    // Methods Begin
    init(index: Int32, name: String) {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
    }

    public open func value_method(): Int32 {
        throw Exception('TODO')
    }

    public open func fg(): Int32 {
        throw Exception('TODO')
    }

    public open func bg(): Int32 {
        throw Exception('TODO')
    }

    public open func fgBright(): Int32 {
        throw Exception('TODO')
    }

    public open func bgBright(): Int32 {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

public open class Attribute {
    // Fields Begin
    var ITALIC_OFF: Any = throw Exception('TODO')
    var UNDERLINE_OFF: Any = throw Exception('TODO')
    var BLINK_OFF: Any = throw Exception('TODO')
    var NEGATIVE_OFF: Any = throw Exception('TODO')
    var CONCEAL_OFF: Any = throw Exception('TODO')
    var STRIKETHROUGH_OFF: Any = throw Exception('TODO')
    var value: Int32 = throw Exception('TODO')
    var name: String = throw Exception('TODO')
    var RESET: Any = throw Exception('TODO')
    var INTENSITY_BOLD: Any = throw Exception('TODO')
    var INTENSITY_FAINT: Any = throw Exception('TODO')
    var ITALIC: Any = throw Exception('TODO')
    var UNDERLINE: Any = throw Exception('TODO')
    var BLINK_SLOW: Any = throw Exception('TODO')
    var BLINK_FAST: Any = throw Exception('TODO')
    var NEGATIVE_ON: Any = throw Exception('TODO')
    var CONCEAL_ON: Any = throw Exception('TODO')
    var STRIKETHROUGH_ON: Any = throw Exception('TODO')
    var UNDERLINE_DOUBLE: Any = throw Exception('TODO')
    var INTENSITY_BOLD_OFF: Any = throw Exception('TODO')
    // Fields End

    // Methods Begin
    init(index: Int32, name: String) {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
    }

    public open func value_method(): Int32 {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

public open class Erase {
    // Fields Begin
    var FORWARD: Any = throw Exception('TODO')
    var BACKWARD: Any = throw Exception('TODO')
    var ALL: Any = throw Exception('TODO')
    var value: Int32 = throw Exception('TODO')
    var name: String = throw Exception('TODO')
    // Fields End

    // Methods Begin
    init(index: Int32, name: String) {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
    }

    public open func value_method(): Int32 {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

public interface Ansi_Consumer {
    // Methods Begin
    func apply(ansi: Ansi): Unit {
        throw Exception('TODO')
    }

    // Methods End
}

open class Ansi_NoAnsi <: Ansi {
    // Fields Begin
    // Fields End

    // Methods Begin
    public init(args: Any) {
        super()
        throw Exception('TODO')
    }

    private static func determineStringBuilder(args: Any): Any {
        throw Exception('TODO')
    }

    public override func fg0(color: Color): Ansi {
        throw Exception('TODO')
    }

    public override func bg0(color: Color): Ansi {
        throw Exception('TODO')
    }

    public override func fgBright(color: Color): Ansi {
        throw Exception('TODO')
    }

    public override func bgBright(color: Color): Ansi {
        throw Exception('TODO')
    }

    public override func fg1(color: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func fgRgb1(r: Int32, g: Int32, b: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func bg1(color: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func bgRgb1(r: Int32, g: Int32, b: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func a0(attribute: Attribute): Ansi {
        throw Exception('TODO')
    }

    public override func cursor(row: Int32, column: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorToColumn(x: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorUp(y: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorRight(x: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorDown(y: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorLeft(x: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorDownLine0(): Ansi {
        throw Exception('TODO')
    }

    public override func cursorDownLine1(n: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func cursorUpLine0(): Ansi {
        throw Exception('TODO')
    }

    public override func cursorUpLine1(n: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func eraseScreen0(): Ansi {
        throw Exception('TODO')
    }

    public override func eraseScreen1(kind: Erase): Ansi {
        throw Exception('TODO')
    }

    public override func eraseLine0(): Ansi {
        throw Exception('TODO')
    }

    public override func eraseLine1(kind: Erase): Ansi {
        throw Exception('TODO')
    }

    public override func scrollUp(rows: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func scrollDown(rows: Int32): Ansi {
        throw Exception('TODO')
    }

    public override func saveCursorPosition(): Ansi {
        throw Exception('TODO')
    }

    public override func restorCursorPosition(): Ansi {
        throw Exception('TODO')
    }

    public override func restoreCursorPosition(): Ansi {
        throw Exception('TODO')
    }

    public override func reset(): Ansi {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

