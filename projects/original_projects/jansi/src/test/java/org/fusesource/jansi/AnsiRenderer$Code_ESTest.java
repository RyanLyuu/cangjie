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

public class AnsiRenderer$Code_ESTest  {

    @Test
    public void test0() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.NEGATIVE_OFF;
        // Undeclared exception!
        try {
            ansiRenderer_Code0.getColor();
            fail("Expecting exception: ClassCastException");

        } catch (ClassCastException e) {
            //
            // class org.fusesource.jansi.Ansi$Attribute cannot be cast to class org.fusesource.jansi.Ansi$Color
            // (org.fusesource.jansi.Ansi$Attribute and org.fusesource.jansi.Ansi$Color are in unnamed module of loader
            // org.evosuite.instrumentation.InstrumentingClassLoader @469c1d23)
            //
}
    }

    @Test
    public void test1() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.BG_GREEN;
        boolean boolean0 = ansiRenderer_Code0.isBackground();
        assertTrue(boolean0);
    }

    @Test
    public void test2() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.DEFAULT;
        boolean boolean0 = ansiRenderer_Code0.isAttribute();
        assertFalse(boolean0);
    }

    @Test
    public void test3() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.BG_GREEN;
        boolean boolean0 = ansiRenderer_Code0.isColor();
        assertTrue(boolean0);
    }

    @Test
    public void test4() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.CYAN;
        // Undeclared exception!
        try {
            ansiRenderer_Code0.getAttribute();
            fail("Expecting exception: ClassCastException");

        } catch (ClassCastException e) {
            //
            // class org.fusesource.jansi.Ansi$Color cannot be cast to class org.fusesource.jansi.Ansi$Attribute
            // (org.fusesource.jansi.Ansi$Color and org.fusesource.jansi.Ansi$Attribute are in unnamed module of loader
            // org.evosuite.instrumentation.InstrumentingClassLoader @469c1d23)
            //
}
    }
}
