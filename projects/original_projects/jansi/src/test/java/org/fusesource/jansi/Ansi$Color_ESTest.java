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

public class Ansi$Color_ESTest  {

    @Test
    public void test0() throws Throwable {
        Ansi.Color ansi_Color0 = Ansi.Color.BLUE;
        int int0 = ansi_Color0.bgBright();
        assertEquals(104, int0);
    }

    @Test
    public void test1() throws Throwable {
        Ansi.Color ansi_Color0 = Ansi.Color.RED;
        int int0 = ansi_Color0.fg();
        assertEquals(31, int0);
    }

    @Test
    public void test2() throws Throwable {
        Ansi.Color ansi_Color0 = Ansi.Color.GREEN;
        String string0 = ansi_Color0.toString();
        assertEquals("GREEN", string0);
    }

    @Test
    public void test3() throws Throwable {
        Ansi.Color ansi_Color0 = Ansi.Color.RED;
        int int0 = ansi_Color0.value();
        assertEquals(1, int0);
    }

    @Test
    public void test4() throws Throwable {
        Ansi.Color ansi_Color0 = Ansi.Color.RED;
        int int0 = ansi_Color0.bg();
        assertEquals(41, int0);
    }

    @Test
    public void test5() throws Throwable {
        Ansi.Color ansi_Color0 = Ansi.Color.BLUE;
        int int0 = ansi_Color0.fgBright();
        assertEquals(94, int0);
    }
}
