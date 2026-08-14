// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

class OptionValidator {
    // Fields Begin
    // Fields End

    // Methods Begin
    private static func isValidChar(c: Rune): Bool {
                return (c >= r'a' && c <= r'z') || (c >= r'A' && c <= r'Z') || (c >= r'0' && c <= r'9') || c == r'_' || c == r'-'
    }

    private static func isValidOpt(c: Rune): Bool {
                return isValidChar(c) || c == r'?' || c == r'@'
    }

    static func validate(option: String): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End
}

