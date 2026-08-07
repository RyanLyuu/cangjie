package com.example.minimal;

public class AddDependency {
    public static String normalizeLabel(String label) {
        return "tag:" + label;
    }

    public static int computeDelta(int currentValue, int auditSize) {
        return auditSize + 2;
    }

    public static String formatScore(String name, int value) {
        return name + ":" + value;
    }
}
