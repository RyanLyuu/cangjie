// Package: commons_cli
package commons_cli

// Imports Begin

// Imports End

public open class AlreadySelectedException <: ParseException {
    // Fields Begin
    let group: OptionGroup = throw Exception('TODO')
    let option: Option = throw Exception('TODO')
    // Fields End

    // Methods Begin
    public init(message: String, group_param: OptionGroup, option_param: Option) {
        super()
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func AlreadySelectedException0(message: String): AlreadySelectedException {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public static func AlreadySelectedException1(group_param: OptionGroup, option_param: Option): AlreadySelectedException {
                return AlreadySelectedException(
        "The option '" + option_param.getKey() + "' was specified but an option from this group has already been selected: '" + group_param.getSelected() + "'",
        group_param,
        option_param)
    }

    public open func getOption(): Option {
                return this.option
    }

    public open func getOptionGroup(): OptionGroup {
                return this.group
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

