package com.example.minimal;

import java.io.IOException;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class App {
    private static int globalCounter = 0;

    public static void main(String[] args) {
        System.out.println(greet("world"));
    }

    public static String greet(String name) {
        return "Hello, " + name + "!";
    }

    public static int add(int a, int b) {
        return a + b;
    }

    public static int addWithDependency(MutableBox box, List<String> audit, String label) {
        String normalizedLabel = AddDependency.normalizeLabel(label);
        int delta = AddDependency.computeDelta(box.getValue(), audit.size());
        audit.add(normalizedLabel);
        box.setValue(box.getValue() + delta);
        return box.getValue();
    }

    public static int incrementGlobalCounter() {
        globalCounter += 1;
        return globalCounter;
    }

    public static int getGlobalCounter() {
        return globalCounter;
    }

    public static void resetGlobalCounter() {
        globalCounter = 0;
    }

    public static void appendTaggedValue(List<String> values, String raw) {
        values.add("tag:" + raw);
    }

    public static int bumpBox(MutableBox box, int delta) {
        box.setValue(box.getValue() + delta);
        return box.getValue();
    }

    // triggers __mockHashSetOf
    public static List<String> filterAllowed(Set<String> allowed, List<String> items) {
        List<String> result = new ArrayList<>();
        for (String item : items) {
            if (allowed.contains(item)) result.add(item);
        }
        return result;
    }

    // triggers __mockHashMapOf
    public static int scoreOf(Map<String, Integer> scores, String key) {
        return scores.getOrDefault(key, 0);
    }

    // triggers __mockByteBufferOf
    public static int sumBuffer(ByteBuffer buf) {
        int total = 0;
        while (buf.hasRemaining()) total += (buf.get() & 0xFF);
        return total;
    }

    // triggers __mockStringReaderOf + __mockReaderEquals
    public static String readAll(StringReader reader) throws IOException {
        StringBuilder sb = new StringBuilder();
        int c;
        while ((c = reader.read()) != -1) sb.append((char) c);
        return sb.toString();
    }

    // triggers __mockStringWriterOf + __mockWriterEquals (Instance Final captured)
    public static void appendLabel(StringWriter writer, String label) {
        writer.write("[" + label + "]");
    }

    // triggers multi-field reflection construction via Scored arg
    public static String describeScore(Scored scored) {
        return AddDependency.formatScore(scored.getName(), scored.getValue());
    }

    public static class MutableBox {
        private int value;

        public MutableBox(int value) {
            this.value = value;
        }

        public int getValue() {
            return value;
        }

        public void setValue(int value) {
            this.value = value;
        }
    }
}
