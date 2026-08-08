package com.example.minimal;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AppTest {
    @Test
    void greetShouldReturnExpectedString() {
        assertEquals("Hello, Codex!", App.greet("Codex"));
    }

    @Test
    void addShouldSumTwoNumbers() {
        assertEquals(5, App.add(2, 3));
    }

    @Test
    void addWithDependencyShouldMutateInputsAndReturnTaggedResult() {
        App.MutableBox box = new App.MutableBox(10);
        List<String> audit = new ArrayList<>();
        audit.add("seed");

        assertEquals(13, App.addWithDependency(box, audit, "alpha"));
        assertEquals(13, box.getValue());
        assertEquals(2, audit.size());
        assertEquals("seed", audit.get(0));
        assertEquals("tag:alpha", audit.get(1));
    }

    @Test
    void counterShouldMutateStaticState() {
        App.resetGlobalCounter();
        assertEquals(1, App.incrementGlobalCounter());
        assertEquals(2, App.incrementGlobalCounter());
        assertEquals(2, App.getGlobalCounter());
    }

    @Test
    void appendTaggedValueShouldMutateInputList() {
        List<String> values = new ArrayList<>();
        App.appendTaggedValue(values, "alpha");
        App.appendTaggedValue(values, "beta");

        assertEquals(2, values.size());
        assertEquals("tag:alpha", values.get(0));
        assertEquals("tag:beta", values.get(1));
    }

    @Test
    void bumpBoxShouldMutateObjectField() {
        App.MutableBox box = new App.MutableBox(10);

        assertEquals(13, App.bumpBox(box, 3));
        assertEquals(13, box.getValue());
    }

    @Test
    void filterAllowedShouldReturnOnlyAllowedItems() {
        Set<String> allowed = new HashSet<>(Arrays.asList("a", "b"));
        List<String> items = Arrays.asList("a", "c", "b", "d");
        List<String> result = App.filterAllowed(allowed, items);
        assertEquals(2, result.size());
        assertTrue(result.contains("a"));
        assertTrue(result.contains("b"));
    }

    @Test
    void scoreOfShouldReturnMappedValue() {
        Map<String, Integer> scores = new HashMap<>();
        scores.put("alice", 42);
        scores.put("bob", 7);
        assertEquals(42, App.scoreOf(scores, "alice"));
        assertEquals(0, App.scoreOf(scores, "unknown"));
    }

    @Test
    void sumBufferShouldSumUnsignedBytes() {
        ByteBuffer buf = ByteBuffer.wrap(new byte[]{1, 2, 3, 4});
        assertEquals(10, App.sumBuffer(buf));
    }

    @Test
    void readAllShouldReturnFullContent() throws IOException {
        StringReader reader = new StringReader("hello");
        assertEquals("hello", App.readAll(reader));
    }

    @Test
    void appendLabelShouldMutateWriter() {
        StringWriter writer = new StringWriter();
        App.appendLabel(writer, "alpha");
        assertEquals("[alpha]", writer.toString());
    }

    @Test
    void describeScoreShouldFormatMultiFieldObject() {
        Scored scored = new Scored("test", 99, true);
        assertEquals("test:99", App.describeScore(scored));
    }
}
