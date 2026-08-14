// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
// Imports End

public open class MissingOptionException <: ParseException {
    // Fields Begin
    var missingOptions: ArrayList<Any> = ArrayList<Any>()
    // Fields End

    // Methods Begin
    private static func createMessage(missingOptions_param: ArrayList<Nothing>): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public init(constructorId: Int64, missingOptions_param: ArrayList<Any>, message: String) {
        super()
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func MissingOptionException1(constructorId: Int64, missingOptions_param: ArrayList<Any>, message: String): MissingOptionException {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getMissingOptions(): ArrayList<Any> {
                return missingOptions
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

