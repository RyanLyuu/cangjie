// Package: jansi
package jansi

// Imports Begin

// Imports End

public open class AnsiType {
    // Fields Begin
    var Native: Any = throw Exception('TODO')
    var Unsupported: Any = throw Exception('TODO')
    var VirtualTerminal: Any = throw Exception('TODO')
    var Emulation: Any = throw Exception('TODO')
    var Redirected: Any = throw Exception('TODO')
    var description: String = throw Exception('TODO')
    // Fields End

    // Methods Begin
    init(description: String) {
        throw Exception('TODO')
    }

    public open func getDescription(): String {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

