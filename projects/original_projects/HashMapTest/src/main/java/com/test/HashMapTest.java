package com.test;

import java.util.HashMap;

public class HashMapTest {
    public HashMap<Object, String> map;

    public void testHashMap() {
        HashMap<Object, String> map = new HashMap<>();
        map.put("key", "value");
        String v = map.get("key");
    }
}
