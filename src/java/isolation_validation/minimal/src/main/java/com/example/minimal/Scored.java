package com.example.minimal;

public class Scored {
    private String name;
    private int value;
    private boolean active;

    public Scored(String name, int value, boolean active) {
        this.name = name;
        this.value = value;
        this.active = active;
    }

    public String getName() { return name; }
    public int getValue() { return value; }
    public boolean isActive() { return active; }
}
