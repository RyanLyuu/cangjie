// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.HashMap
// Imports End

public open class OptionGroup {
    // Fields Begin
    let optionMap: HashMap<String, Option> = throw Exception('TODO')
    var selected: String = throw Exception('TODO')
    var required: Bool = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public open func addOption(option: Option): OptionGroup {
        throw Exception('TODO')
    }

    public open func getNames(): Array<String> {
        throw Exception('TODO')
    }

    public open func getOptions(): Collection<Option> {
        throw Exception('TODO')
    }

    public open func getSelected(): String {
        throw Exception('TODO')
    }

    public open func isRequired(): Bool {
        throw Exception('TODO')
    }

    public open func setRequired(required_param: Bool): Unit {
        throw Exception('TODO')
    }

    public open func setSelected(option: Option): Unit {
        throw Exception('TODO')
    }

    public open func toString(): String {
        throw Exception('TODO')
    }

    // Methods End
}

