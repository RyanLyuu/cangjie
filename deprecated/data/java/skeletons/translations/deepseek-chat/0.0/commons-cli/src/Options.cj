// Package: commons_cli
package commons_cli

// Imports Begin
import std.collection.ArrayList
import std.collection.HashMap
// Imports End

public open class Options {
    // Fields Begin
    let shortOpts: HashMap<String, Option> = HashMap<String, Option>()
    let longOpts: HashMap<String, Option> = HashMap<String, Option>()
    let requiredOpts: ArrayList<Object> = ArrayList<Object>()
    let optionGroups: HashMap<String, OptionGroup> = HashMap<String, OptionGroup>()
    // Fields End

    // Methods Begin
    public open func addOption0(opt: Option): Options {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func addOption1(opt: String, hasArg: Bool, description: String): Options {
                addOption3(opt, "", hasArg, description); return this
    }

    public open func addOption2(opt: String, description: String): Options {
                addOption3(opt, "", false, description)
        return this
    }

    public open func addOption3(opt: String, longOpt: String, hasArg: Bool, description: String): Options {
                addOption0(Option(0, opt, longOpt, description, hasArg, Option_Builder()))
        return this
    }

    public open func addOptionGroup(group: OptionGroup): Options {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func addRequiredOption(opt: String, longOpt: String, hasArg: Bool, description: String): Options {
                let option = Option(0, opt, longOpt, description, hasArg, Option_Builder())
        option.required = true
        addOption0(option)
        return this
    }

    public open func getMatchingOptions(opt: String): ArrayList<String> {
                var strippedOpt = Util.stripLeadingHyphens(opt)
        let matchingOpts = ArrayList<String>()
        if (longOpts.contains(strippedOpt)) {
        let result = ArrayList<String>()
        result.add(strippedOpt)
        return result
        }
        for (longOpt in longOpts.keys()) {
        if (longOpt.startsWith(strippedOpt)) {
        matchingOpts.add(longOpt)
        }
        }
        return matchingOpts
    }

    public open func getOption(opt: String): Option {
                let stripped = Util.stripLeadingHyphens(opt)
        if (shortOpts.contains(stripped)) {
        return shortOpts.get(stripped).getOrThrow()
        }
        return longOpts.get(stripped).getOrThrow()
    }

    public open func getOptionGroup(opt: Option): OptionGroup {
                return optionGroups.get(opt.getKey()).getOrThrow()
    }

    public open func getOptionGroups(): ArrayList<OptionGroup> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func getOptions(): Collection<Option> {
                return ArrayList<Option>(shortOpts.values())
    }

    public open func getRequiredOptions(): ArrayList<Any> {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    public open func hasLongOption(opt: String): Bool {
                let stripped = Util.stripLeadingHyphens(opt)
        return longOpts.contains(stripped)
    }

    public open func hasOption(opt: String): Bool {
                let stripped = Util.stripLeadingHyphens(opt)
        return shortOpts.contains(stripped) || longOpts.contains(stripped)
    }

    public open func hasShortOption(opt: String): Bool {
                let stripped = Util.stripLeadingHyphens(opt)
        return shortOpts.contains(stripped)
    }

    public open func helpOptions(): ArrayList<Option> {
                return ArrayList<Option>(shortOpts.values())
    }

    public open func toString(): String {
        throw Exception('TODO')  // Already translated, compilation failed
    }

    // Methods End
}

