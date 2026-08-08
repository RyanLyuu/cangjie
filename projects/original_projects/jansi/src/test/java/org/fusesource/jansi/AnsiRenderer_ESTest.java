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
import java.io.IOException;
import java.io.PipedWriter;
import java.io.StringWriter;
import java.io.Writer;
import java.nio.BufferOverflowException;
import java.nio.CharBuffer;
import java.nio.ReadOnlyBufferException;

import org.junit.Test;

import static org.junit.Assert.*;

public class AnsiRenderer_ESTest  {

    @Test
    public void test00() throws Throwable {
        String string0 = AnsiRenderer.renderCodes1(" ");
        assertEquals("", string0);
    }

    @Test
    public void test01() throws Throwable {
        String[] stringArray0 = new String[1];
        stringArray0[0] = "BG_GREEN";
        String string0 = AnsiRenderer.renderCodes0(stringArray0);
        assertEquals("\u001B[42m", string0);
    }

    @Test
    public void test02() throws Throwable {
        String[] stringArray0 = new String[0];
        String string0 = AnsiRenderer.renderCodes0(stringArray0);
        assertEquals("", string0);
    }

    @Test
    public void test03() throws Throwable {
        String[] stringArray0 = new String[4];
        stringArray0[0] = "UNDERLINE_DOUBLE";
        stringArray0[1] = "UNDERLINE_DOUBLE";
        stringArray0[2] = "UNDERLINE_DOUBLE";
        stringArray0[3] = "UNDERLINE_DOUBLE";
        String string0 = AnsiRenderer.render2("UNDERLINE_DOUBLE", stringArray0);
        assertEquals("\u001B[21;21;21;21mUNDERLINE_DOUBLE\u001B[m", string0);
    }

    @Test
    public void test04() throws Throwable {
        // Undeclared exception!
        try {
            AnsiRenderer.renderCodes1((String) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test05() throws Throwable {
        CharBuffer charBuffer0 = CharBuffer.wrap((CharSequence) "BLINK_FAST");
        // Undeclared exception!
        try {
            AnsiRenderer.render1("BLINK_FAST", charBuffer0);
            fail("Expecting exception: ReadOnlyBufferException");

        } catch (ReadOnlyBufferException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test06() throws Throwable {
        CharBuffer charBuffer0 = CharBuffer.allocate(7);
        // Undeclared exception!
        try {
            AnsiRenderer.render1("CONCEAL_OFF", charBuffer0);
            fail("Expecting exception: BufferOverflowException");

        } catch (BufferOverflowException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test07() throws Throwable {
        // Undeclared exception!
        try {
            AnsiRenderer.render1("CONCEAL_OFF", (Appendable) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test08() throws Throwable {
        PipedWriter pipedWriter0 = new PipedWriter();
        try {
            AnsiRenderer.render1("java.lang.StringBuilder@0000000001", pipedWriter0);
            fail("Expecting exception: IOException");

        } catch (IOException e) {
            //
            // Pipe not connected
            //
}
    }

    @Test
    public void test09() throws Throwable {
        // Undeclared exception!
        try {
            AnsiRenderer.render0((String) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test10() throws Throwable {
        StringWriter stringWriter0 = new StringWriter();
        AnsiRenderer.render1("Uq*Q@lN2gFLc25@|a|", stringWriter0);
        assertEquals("Uq*Q@lN2gFLc25Uq*Q@lN2gFLc25@|a|", stringWriter0.toString());
    }

    @Test
    public void test11() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.BLACK;
        Ansi.Color ansi_Color0 = ansiRenderer_Code0.getColor();
        assertEquals("BLACK", ansi_Color0.toString());
    }

    @Test
    public void test12() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.BLACK;
        boolean boolean0 = ansiRenderer_Code0.isColor();
        assertTrue(boolean0);
    }

    @Test
    public void test13() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.WHITE;
        // Undeclared exception!
        try {
            ansiRenderer_Code0.getAttribute();
            fail("Expecting exception: ClassCastException");

        } catch (ClassCastException e) {
            //
            // class org.fusesource.jansi.Ansi$Color cannot be cast to class org.fusesource.jansi.Ansi$Attribute
            // (org.fusesource.jansi.Ansi$Color and org.fusesource.jansi.Ansi$Attribute are in unnamed module of loader
            // org.evosuite.instrumentation.InstrumentingClassLoader @e4f3b6d)
            //
}
    }

    @Test
    public void test14() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.BLACK;
        boolean boolean0 = ansiRenderer_Code0.isBackground();
        assertFalse(boolean0);
    }

    @Test
    public void test15() throws Throwable {
        AnsiRenderer.Code ansiRenderer_Code0 = AnsiRenderer.Code.BLACK;
        boolean boolean0 = ansiRenderer_Code0.isAttribute();
        assertFalse(boolean0);
    }

    @Test
    public void test16() throws Throwable {
        boolean boolean0 = AnsiRenderer.test("Uq*Q@lN2gFLc <@|a|");
        assertTrue(boolean0);
    }

    @Test
    public void test17() throws Throwable {
        boolean boolean0 = AnsiRenderer.test("#w,:*29~");
        assertFalse(boolean0);
    }

    @Test
    public void test18() throws Throwable {
        boolean boolean0 = AnsiRenderer.test((String) null);
        assertFalse(boolean0);
    }

    @Test
    public void test19() throws Throwable {
        String string0 = AnsiRenderer.renderCodes1("BG_BLUE");
        assertEquals("\u001B[44m", string0);
    }


    @Test
    public void test21() throws Throwable {
        String[] stringArray0 = new String[9];
        stringArray0[0] = "BLINK_SLOW";
        // Undeclared exception!
        try {
            AnsiRenderer.renderCodes0(stringArray0);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test22() throws Throwable {
        String string0 = AnsiRenderer.renderCodes1("MAGENTA");
        assertEquals("\u001B[35m", string0);
    }

    @Test
    public void test23() throws Throwable {
        String string0 = AnsiRenderer.render0("@|");
        assertNotNull(string0);
    }

    @Test
    public void test24() throws Throwable {
        // Undeclared exception!
        try {
            AnsiRenderer.render2("a|}FTns7<)ob", (String[]) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }
}
