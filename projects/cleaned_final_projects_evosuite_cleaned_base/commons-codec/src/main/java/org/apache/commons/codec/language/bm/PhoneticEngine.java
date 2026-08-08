/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.commons.codec.language.bm;

import org.apache.commons.codec.language.bm.Languages.Languages_LanguageSet;
import org.apache.commons.codec.language.bm.Rule.Rule_Phoneme;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

/**
 * Converts words into potential phonetic representations.
 *
 * <p>This is a two-stage process. Firstly, the word is converted into a phonetic representation
 * that takes into account the likely source language. Next, this phonetic representation is
 * converted into a pan-European 'average' representation, allowing comparison between different
 * versions of essentially the same word from different languages.
 *
 * <p>This class is intentionally immutable and thread-safe. If you wish to alter the settings for a
 * PhoneticEngine, you must make a new one with the updated settings.
 *
 * <p>Ported from phoneticengine.php
 *
 * @since 1.6
 */
public class PhoneticEngine {

    /**
     * Utility for manipulating a set of phonemes as they are being built up. Not intended for use
     * outside this package, and probably not outside the {@link PhoneticEngine} class.
     *
     * @since 1.6
     */
    static final class PhoneticEngine_PhonemeBuilder {

        /**
         * An empty builder where all phonemes must come from some set of languages. This will
         * contain a single phoneme of zero characters. This can then be appended to. This should be
         * the only way to create a new phoneme from scratch.
         *
         * @param languages the set of languages
         * @return a new, empty phoneme builder
         */
        public static PhoneticEngine_PhonemeBuilder empty(final Languages.Languages_LanguageSet languages) {
            return new PhoneticEngine_PhonemeBuilder(3, null, new Rule.Rule_Phoneme(2, "", languages, null));
        }

        private final Set<Rule.Rule_Phoneme> phonemes;

        public PhoneticEngine_PhonemeBuilder(
                int constructorId, final Set<Rule.Rule_Phoneme> phonemes_param, final Rule.Rule_Phoneme phoneme) {
            if (constructorId == 0) {
                this.phonemes = phonemes_param;
            } else {
                this.phonemes = new LinkedHashSet<>();
                this.phonemes.add(phoneme);
            }
        }

        /**
         * Creates a new phoneme builder containing all phonemes in this one extended by {@code
         * str}.
         *
         * @param str the characters to append to the phonemes
         */
        public void append(final CharSequence str) {
            for (final Rule.Rule_Phoneme ph : this.phonemes) {
                ph.append(str);
            }
        }

        /**
         * Applies the given phoneme expression to all phonemes in this phoneme builder.
         *
         * <p>This will lengthen phonemes that have compatible language sets to the expression, and
         * drop those that are incompatible.
         *
         * @param phonemeExpr the expression to apply
         * @param maxPhonemes the maximum number of phonemes to build up
         */
        public void apply(final Rule.Rule_PhonemeExpr phonemeExpr, final int maxPhonemes) {
            final Set<Rule.Rule_Phoneme> newPhonemes = new LinkedHashSet<>(maxPhonemes);

            EXPR:
            for (final Rule.Rule_Phoneme left : this.phonemes) {
                for (final Rule.Rule_Phoneme right : phonemeExpr.getPhonemes()) {
                    final Languages_LanguageSet languages =
                            left.getLanguages().restrictTo(right.getLanguages());
                    if (!languages.isEmpty()) {
                        final Rule.Rule_Phoneme join = Rule_Phoneme.Phoneme1(left, right, languages);
                        if (newPhonemes.size() < maxPhonemes) {
                            newPhonemes.add(join);
                            if (newPhonemes.size() >= maxPhonemes) {
                                break EXPR;
                            }
                        }
                    }
                }
            }

            this.phonemes.clear();
            this.phonemes.addAll(newPhonemes);
        }

        /**
         * Gets underlying phoneme set. Please don't mutate.
         *
         * @return the phoneme set
         */
        public Set<Rule.Rule_Phoneme> getPhonemes() {
            return this.phonemes;
        }

        /**
         * Stringifies the phoneme set. This produces a single string of the strings of each
         * phoneme, joined with a pipe. This is explicitly provided in place of toString as it is a
         * potentially expensive operation, which should be avoided when debugging.
         *
         * @return the stringified phoneme set
         */
        public String makeString() {
            final StringBuilder sb = new StringBuilder();

            for (final Rule.Rule_Phoneme ph : this.phonemes) {
                if (sb.length() > 0) {
                    sb.append("|");
                }
                sb.append(ph.getPhonemeText());
            }

            return sb.toString();
        }
    }

    /**
     * A function closure capturing the application of a list of rules to an input sequence at a
     * particular offset. After invocation, the values {@code i} and {@code found} are updated.
     * {@code i} points to the index of the next char in {@code input} that must be processed next
     * (the input up to that index having been processed already), and {@code found} indicates if a
     * matching rule was found or not. In the case where a matching rule was found, {@code
     * phonemeBuilder} is replaced with a new builder containing the phonemes updated by the
     * matching rule.
     *
     * <p>Although this class is not thread-safe (it has mutable unprotected fields), it is not
     * shared between threads as it is constructed as needed by the calling methods.
     *
     * @since 1.6
     */
    private static final class PhoneticEngine_RulesApplication {
        private final Map<String, List<Rule>> finalRules;
        private final CharSequence input;

        private final PhoneticEngine_PhonemeBuilder phonemeBuilder;
        private int i;
        private final int maxPhonemes;
        private boolean found;

        public PhoneticEngine_RulesApplication(
                final Map<String, List<Rule>> finalRules_param,
                final CharSequence input_param,
                final PhoneticEngine_PhonemeBuilder phonemeBuilder_param,
                final int i_param,
                final int maxPhonemes_param) {
            Objects.requireNonNull(finalRules_param, "finalRules");
            this.finalRules = finalRules_param;
            this.phonemeBuilder = phonemeBuilder_param;
            this.input = input_param;
            this.i = i_param;
            this.maxPhonemes = maxPhonemes_param;
        }

        public int getI() {
            return this.i;
        }

        public PhoneticEngine_PhonemeBuilder getPhonemeBuilder() {
            return this.phonemeBuilder;
        }

        /**
         * Invokes the rules. Loops over the rules list, stopping at the first one that has a
         * matching context and pattern. Then applies this rule to the phoneme builder to produce
         * updated phonemes. If there was no match, {@code i} is advanced one and the character is
         * silently dropped from the phonetic spelling.
         *
         * @return {@code this}
         */
        public PhoneticEngine_RulesApplication invoke() {
            this.found = false;
            int patternLength = 1;
            final List<Rule> rules = this.finalRules.get(input.subSequence(i, i + patternLength));
            if (rules != null) {
                for (final Rule rule : rules) {
                    final String pattern = rule.getPattern();
                    patternLength = pattern.length();
                    if (rule.patternAndContextMatches(this.input, this.i)) {
                        this.phonemeBuilder.apply(rule.getPhoneme(), maxPhonemes);
                        this.found = true;
                        break;
                    }
                }
            }

            if (!this.found) {
                patternLength = 1;
            }

            this.i += patternLength;
            return this;
        }

        public boolean isFound() {
            return this.found;
        }
    }

    private static final Map<NameType, Set<String>> NAME_PREFIXES = new EnumMap<>(NameType.class);

    static {
        NAME_PREFIXES.put(
                NameType.ASHKENAZI,
                Collections.unmodifiableSet(
                        new HashSet<>(Arrays.asList("bar", "ben", "da", "de", "van", "von"))));
        NAME_PREFIXES.put(
                NameType.SEPHARDIC,
                Collections.unmodifiableSet(
                        new HashSet<>(
                                Arrays.asList(
                                        "al", "el", "da", "dal", "de", "del", "dela", "de la",
                                        "della", "des", "di", "do", "dos", "du", "van", "von"))));
        NAME_PREFIXES.put(
                NameType.GENERIC,
                Collections.unmodifiableSet(
                        new HashSet<>(
                                Arrays.asList(
                                        "da", "dal", "de", "del", "dela", "de la", "della", "des",
                                        "di", "do", "dos", "du", "van", "von"))));
    }

    /**
     * Joins some strings with an internal separator.
     *
     * @param strings Strings to join
     * @param sep String to separate them with
     * @return a single String consisting of each element of {@code strings} interleaved by {@code
     *     sep}
     */
    private static String join(final Iterable<String> strings, final String sep) {
        final StringBuilder sb = new StringBuilder();
        final Iterator<String> si = strings.iterator();
        if (si.hasNext()) {
            sb.append(si.next());
        }
        while (si.hasNext()) {
            sb.append(sep).append(si.next());
        }

        return sb.toString();
    }

    private static final int DEFAULT_MAX_PHONEMES = 20;

    private final Lang lang;

    private final NameType nameType;

    private final RuleType ruleType;

    private final boolean concat;

    private final int maxPhonemes;

    /**
     * Generates a new, fully-configured phonetic engine.
     *
     * @param nameType the type of names it will use
     * @param ruleType the type of rules it will apply
     * @param concat if it will concatenate multiple encodings
     */
    public static PhoneticEngine PhoneticEngine0(
            final NameType nameType_param, final RuleType ruleType_param, final boolean concat_param) {
        return new PhoneticEngine(nameType_param, ruleType_param, concat_param, DEFAULT_MAX_PHONEMES);
    }

    /**
     * Generates a new, fully-configured phonetic engine.
     *
     * @param nameType the type of names it will use
     * @param ruleType the type of rules it will apply
     * @param concat if it will concatenate multiple encodings
     * @param maxPhonemes the maximum number of phonemes that will be handled
     * @since 1.7
     */
    public PhoneticEngine(
            final NameType nameType_param,
            final RuleType ruleType_param,
            final boolean concat_param,
            final int maxPhonemes_param) {
        if (ruleType_param == RuleType.RULES) {
            throw new IllegalArgumentException("ruleType must not be " + RuleType.RULES);
        }
        this.nameType = nameType_param;
        this.ruleType = ruleType_param;
        this.concat = concat_param;
        this.lang = Lang.instance(nameType_param);
        this.maxPhonemes = maxPhonemes_param;
    }

    /**
     * Applies the final rules to convert from a language-specific phonetic representation to a
     * language-independent representation.
     *
     * @param phonemeBuilder the current phonemes
     * @param finalRules the final rules to apply
     * @return the resulting phonemes
     */
    private PhoneticEngine_PhonemeBuilder applyFinalRules(
            final PhoneticEngine_PhonemeBuilder phonemeBuilder, final Map<String, List<Rule>> finalRules) {
        Objects.requireNonNull(finalRules, "finalRules");
        if (finalRules.isEmpty()) {
            return phonemeBuilder;
        }

        final Map<Rule.Rule_Phoneme, Rule.Rule_Phoneme> phonemes = new TreeMap<>(Rule.Rule_Phoneme.COMPARATOR);

        for (final Rule.Rule_Phoneme phoneme : phonemeBuilder.getPhonemes()) {
            PhoneticEngine_PhonemeBuilder subBuilder = PhoneticEngine_PhonemeBuilder.empty(phoneme.getLanguages());
            final String phonemeText = phoneme.getPhonemeText().toString();

            for (int i = 0; i < phonemeText.length(); ) {
                final PhoneticEngine_RulesApplication rulesApplication =
                        new PhoneticEngine_RulesApplication(finalRules, phonemeText, subBuilder, i, maxPhonemes)
                                .invoke();
                final boolean found = rulesApplication.isFound();
                subBuilder = rulesApplication.getPhonemeBuilder();

                if (!found) {
                    subBuilder.append(phonemeText.subSequence(i, i + 1));
                }

                i = rulesApplication.getI();
            }

            for (final Rule.Rule_Phoneme newPhoneme : subBuilder.getPhonemes()) {
                if (phonemes.containsKey(newPhoneme)) {
                    final Rule.Rule_Phoneme oldPhoneme = phonemes.remove(newPhoneme);
                    final Rule.Rule_Phoneme mergedPhoneme =
                            oldPhoneme.mergeWithLanguage(newPhoneme.getLanguages());
                    phonemes.put(mergedPhoneme, mergedPhoneme);
                } else {
                    phonemes.put(newPhoneme, newPhoneme);
                }
            }
        }

        return new PhoneticEngine_PhonemeBuilder(0, phonemes.keySet(), null);
    }

    /**
     * Encodes a string to its phonetic representation.
     *
     * @param input the String to encode
     * @return the encoding of the input
     */
    public String encode0(final String input) {
        final Languages.Languages_LanguageSet languageSet = this.lang.guessLanguages(input);
        return encode1(input, languageSet);
    }

    /**
     * Encodes an input string into an output phonetic representation, given a set of possible
     * origin languages.
     *
     * @param input String to phoneticise; a String with dashes or spaces separating each word
     * @param languageSet set of possible origin languages
     * @return a phonetic representation of the input; a String containing '-'-separated phonetic
     *     representations of the input
     */
    public String encode1(String input, final Languages.Languages_LanguageSet languageSet) {
        final Map<String, List<Rule>> rules =
                Rule.getInstanceMap0(this.nameType, RuleType.RULES, languageSet);
        final Map<String, List<Rule>> finalRules1 =
                Rule.getInstanceMap1(this.nameType, this.ruleType, "common");
        final Map<String, List<Rule>> finalRules2 =
                Rule.getInstanceMap0(this.nameType, this.ruleType, languageSet);

        input = input.toLowerCase(Locale.ENGLISH).replace('-', ' ').trim();

        if (this.nameType == NameType.GENERIC) {
            if (input.length() >= 2 && input.substring(0, 2).equals("d'")) { // check for d'
                final String remainder = input.substring(2);
                final String combined = "d" + remainder;
                return "(" + encode0(remainder) + ")-(" + encode0(combined) + ")";
            }
            for (final String l : NAME_PREFIXES.get(this.nameType)) {
                if (input.startsWith(l + " ")) {
                    final String remainder =
                            input.substring(l.length() + 1); // input without the prefix
                    final String combined = l + remainder; // input with prefix without space
                    return "(" + encode0(remainder) + ")-(" + encode0(combined) + ")";
                }
            }
        }

        final List<String> words = Arrays.asList(input.split("\\s+"));
        final List<String> words2 = new ArrayList<>();

        switch (this.nameType) {
            case SEPHARDIC:
                for (final String aWord : words) {
                    final String[] parts = aWord.split("'");
                    final String lastPart = parts[parts.length - 1];
                    words2.add(lastPart);
                }
                words2.removeAll(NAME_PREFIXES.get(this.nameType));
                break;
            case ASHKENAZI:
                words2.addAll(words);
                words2.removeAll(NAME_PREFIXES.get(this.nameType));
                break;
            case GENERIC:
                words2.addAll(words);
                break;
            default:
                throw new IllegalStateException("Unreachable case: " + this.nameType);
        }

        if (this.concat) {
            input = join(words2, " ");
        } else if (words2.size() == 1) {
            input = words.iterator().next();
        } else {
            final StringBuilder result = new StringBuilder();
            for (final String word : words2) {
                result.append("-").append(encode0(word));
            }
            return result.substring(1);
        }

        PhoneticEngine_PhonemeBuilder phonemeBuilder = PhoneticEngine_PhonemeBuilder.empty(languageSet);

        for (int i = 0; i < input.length(); ) {
            final PhoneticEngine_RulesApplication rulesApplication =
                    new PhoneticEngine_RulesApplication(rules, input, phonemeBuilder, i, maxPhonemes).invoke();
            i = rulesApplication.getI();
            phonemeBuilder = rulesApplication.getPhonemeBuilder();
        }

        phonemeBuilder = applyFinalRules(phonemeBuilder, finalRules1);
        phonemeBuilder = applyFinalRules(phonemeBuilder, finalRules2);

        return phonemeBuilder.makeString();
    }

    /**
     * Gets the Lang language guessing rules being used.
     *
     * @return the Lang in use
     */
    public Lang getLang() {
        return this.lang;
    }

    /**
     * Gets the NameType being used.
     *
     * @return the NameType in use
     */
    public NameType getNameType() {
        return this.nameType;
    }

    /**
     * Gets the RuleType being used.
     *
     * @return the RuleType in use
     */
    public RuleType getRuleType() {
        return this.ruleType;
    }

    /**
     * Gets if multiple phonetic encodings are concatenated or if just the first one is kept.
     *
     * @return true if multiple phonetic encodings are returned, false if just the first is
     */
    public boolean isConcat() {
        return this.concat;
    }

    /**
     * Gets the maximum number of phonemes the engine will calculate for a given input.
     *
     * @return the maximum number of phonemes
     * @since 1.7
     */
    public int getMaxPhonemes() {
        return this.maxPhonemes;
    }
}
