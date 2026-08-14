// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.HashMap
// Imports End

public open class OptionGroup {
    // Fields Begin
    let optionMap: HashMap<String, Option> = HashMap<String, Option>()
    var selected: String = throw Exception('TODO')
    var required: Bool = false
    // Fields End

    // Methods Begin
    public open func addOption(option: Option): OptionGroup {
                optionMap[option.getKey()] = option
        return this
    }

    public open func getNames(): Array<String> {
                return optionMap.keys().toArray()
    }

    public open func getOptions(): Collection<Option> {
                return optionMap.values()
    }

    public open func getSelected(): String {
                return this.selected
    }

    public open func isRequired(): Bool {
                return this.required
    }

    public open func setRequired(required_param: Bool): Unit {
                this.required = required_param
    }

    public open func setSelected(option: Option): Unit {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func toString(): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End
}

