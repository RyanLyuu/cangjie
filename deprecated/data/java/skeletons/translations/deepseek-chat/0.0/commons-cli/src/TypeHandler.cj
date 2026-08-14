// Package: commons_cli
package commons_cli

// Imports Begin
import std.fs.*
// Imports End

public open class TypeHandler {
    // Fields Begin
    // Fields End

    // Methods Begin
    public static func createClass(classname: String): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func createDate(str: String): Any {
                throw Exception("Not yet implemented")
    }

    public static func createFile(str: String): File {
                return File(str, OpenMode.Read)
    }

    public static func createFiles(str: String): Array<File> {
                throw Exception("Not yet implemented")
    }

    public static func createNumber(str: String): Int64 {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func createObject(classname: String): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func createURL(str: String): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func createValue0(str: String, clazz: Any): Any {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func createValue1(str: String, obj: Any): Any {
                return createValue0(str, obj)
    }

    public static func openFile(str: String): File {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End
}

