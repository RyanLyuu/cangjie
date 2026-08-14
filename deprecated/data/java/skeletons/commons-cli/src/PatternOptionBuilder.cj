// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class PatternOptionBuilder {
    // Fields Begin
    static let STRING_VALUE: String = throw Exception('TODO')
    static let OBJECT_VALUE: Any = throw Exception('TODO')
    static let NUMBER_VALUE: Any = throw Exception('TODO')
    static let DATE_VALUE: Any = throw Exception('TODO')
    static let CLASS_VALUE: Any = throw Exception('TODO')
    static let EXISTING_FILE_VALUE: Any = throw Exception('TODO')
    static let FILE_VALUE: Any = throw Exception('TODO')
    static let FILES_VALUE: Any = throw Exception('TODO')
    static let URL_VALUE: Any = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public static func getValueClass(ch: Rune): Any {
        throw Exception('TODO')
    }

    public static func isValueCode(ch: Rune): Bool {
        throw Exception('TODO')
    }

    public static func parsePattern(pattern: String): Options {
        throw Exception('TODO')
    }

    // Methods End
}

