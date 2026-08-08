/*
 * Copyright (C) 2009-2023 the original author(s).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.fusesource.jansi;

import java.lang.Throwable;
import org.junit.Test;

import static org.junit.Assert.*;

public class AnsiColors_ESTest  {

    @Test
    public void test0() throws Throwable {
        AnsiColors[] ansiColorsArray0 = AnsiColors.values();
        assertEquals(3, ansiColorsArray0.length);
    }

    @Test
    public void test1() throws Throwable {
        AnsiColors ansiColors0 = AnsiColors.valueOf("Colors256");
        assertEquals(AnsiColors.Colors256, ansiColors0);
    }

    @Test
    public void test2() throws Throwable {
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        String string0 = ansiColors0.getDescription();
        assertEquals("24-bit colors", string0);
    }
}
