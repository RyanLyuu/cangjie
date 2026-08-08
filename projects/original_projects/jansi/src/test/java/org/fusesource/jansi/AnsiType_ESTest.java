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

public class AnsiType_ESTest  {

    @Test
    public void test0() throws Throwable {
        AnsiType[] ansiTypeArray0 = AnsiType.values();
        assertEquals(5, ansiTypeArray0.length);
    }

    @Test
    public void test1() throws Throwable {
        AnsiType ansiType0 = AnsiType.valueOf("Native");
        assertEquals(AnsiType.Native, ansiType0);
    }

    @Test
    public void test2() throws Throwable {
        AnsiType ansiType0 = AnsiType.VirtualTerminal;
        String string0 = ansiType0.getDescription();
        assertEquals("Supported through windows virtual terminal", string0);
    }
}
