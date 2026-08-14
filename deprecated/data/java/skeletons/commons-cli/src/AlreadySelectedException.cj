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
        throw Exception('TODO')
    }

    public static func AlreadySelectedException0(message: String): AlreadySelectedException {
        throw Exception('TODO')
    }

    public static func AlreadySelectedException1(group_param: OptionGroup, option_param: Option): AlreadySelectedException {
        throw Exception('TODO')
    }

    public open func getOption(): Option {
        throw Exception('TODO')
    }

    public open func getOptionGroup(): OptionGroup {
        throw Exception('TODO')
    }

    // Methods End

    protected init() {
        throw Exception('TODO')
    }
}

