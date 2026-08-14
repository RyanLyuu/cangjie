// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
// Imports End

public open class MissingOptionException <: ParseException {
    // Fields Begin
    var missingOptions: ArrayList<Any> = throw Exception('TODO')
    // Fields End

    // Methods Begin
    private static func createMessage(missingOptions_param: ArrayList<Nothing>): String {
        throw Exception('TODO')
    }

    public init(constructorId: Int64, missingOptions_param: ArrayList<Any>, message: String) {
        super()
        throw Exception('TODO')
    }

    public static func MissingOptionException1(constructorId: Int64, missingOptions_param: ArrayList<Any>, message: String): MissingOptionException {
        throw Exception('TODO')
    }

    public open func getMissingOptions(): ArrayList<Any> {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

