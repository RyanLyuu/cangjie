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
package org.fusesource.jansi.io;

import java.io.FileOutputStream;
import java.io.PrintStream;
import java.lang.Throwable;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PipedOutputStream;
import java.util.ArrayList;
import java.util.Iterator;

import org.junit.Test;

import static org.junit.Assert.*;

public class AnsiProcessor_ESTest  {

    @Test
    public void test000() throws Throwable {
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream(1030);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        ansiProcessor0.processCursorDownLine((-3024));
        assertEquals(0, byteArrayOutputStream0.size());
    }

    @Test
    public void test001() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        arrayList0.add((Object) null);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 75);
        assertTrue(boolean0);
    }

    @Test
    public void test002() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        arrayList0.add((Object) null);
        arrayList0.add((Object) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 72);
        assertTrue(boolean0);
    }

    @Test
    public void test003() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processCursorRight((-127));
    }

    @Test
    public void test004() throws Throwable {
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream(1030);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        ansiProcessor0.processCursorDownLine(1030);
        assertEquals(1030, byteArrayOutputStream0.size());
    }

    @Test
    public void test005() throws Throwable {
        File mockFile0 = new File((File) null, "DoB^oT");
        PrintStream mockPrintStream0 = new PrintStream(mockFile0);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockPrintStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        ansiProcessor0.processUnknownExtension(arrayList0, 912);
        assertTrue(arrayList0.isEmpty());
    }

    @Test
    public void test006() throws Throwable {
        File mockFile0 = new File((File) null, "DoB^oT");
        PrintStream mockPrintStream0 = new PrintStream(mockFile0);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockPrintStream0);
        ansiProcessor0.processScrollUp(912);
    }

    @Test
    public void test007() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processScrollDown(72);
    }

    @Test
    public void test008() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ansiProcessor0.processRestoreCursorPosition();
    }

    @Test
    public void test009() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        FilterOutputStream filterOutputStream0 = new FilterOutputStream(pipedOutputStream0);
        DataOutputStream dataOutputStream0 = new DataOutputStream(filterOutputStream0);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(dataOutputStream0);
        ansiProcessor0.processDeleteLine(2712);
    }

    @Test
    public void test010() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processCursorUp(90);
    }

    @Test
    public void test011() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processCursorTo(1630, 90);
    }

    @Test
    public void test012() throws Throwable {
        File mockFile0 = new File((File) null, "DoB^oT");
        PrintStream mockPrintStream0 = new PrintStream(mockFile0);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockPrintStream0);
        ansiProcessor0.processCursorDown(912);
    }

    @Test
    public void test013() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processChangeWindowTitle("a1T/K?@g7i%k,t");
    }

    @Test
    public void test014() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processChangeIconName("");
    }

    @Test
    public void test015() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processAttributeReset();
    }

    @Test
    public void test016() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        // Undeclared exception!
        try {
            ansiProcessor0.processOperatingSystemCommand((ArrayList<Object>) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test017() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        // Undeclared exception!
        try {
            ansiProcessor0.processEscapeCommand(arrayList0, 67);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }


    @Test
    public void test019() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        // Undeclared exception!
        try {
            ansiProcessor0.processCursorRight(2332);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test020() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        try {
            ansiProcessor0.processCursorRight(107);
            fail("Expecting exception: IOException");

        } catch (IOException e) {
            //
            // Pipe not connected
            //
}
    }

    @Test
    public void test021() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        // Undeclared exception!
        try {
            ansiProcessor0.processCursorDownLine(112);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
        }
    }

    @Test
    public void test022() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        try {
            ansiProcessor0.processCursorDownLine(95);
            fail("Expecting exception: IOException");

        } catch (IOException e) {
            //
            // Pipe not connected
            //
}
    }

    @Test
    public void test023() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        // Undeclared exception!
        try {
            ansiProcessor0.processCharsetSelect0((ArrayList<Object>) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }



    @Test
    public void test026() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        arrayList0.add((Object) ansiProcessor0);
        // Undeclared exception!
        try {
            ansiProcessor0.processEscapeCommand(arrayList0, 83);
            fail("Expecting exception: ClassCastException");

        } catch (ClassCastException e) {
            //
            // class org.fusesource.jansi.io.AnsiProcessor cannot be cast to class java.lang.Integer
            // (org.fusesource.jansi.io.AnsiProcessor is in unnamed module of loader
            // org.evosuite.instrumentation.InstrumentingClassLoader @253efd1d; java.lang.Integer is in module java.base
            // of loader 'bootstrap')
            //
}
    }

    @Test
    public void test027() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        arrayList0.add((Object) null);
        // Undeclared exception!
        try {
            ansiProcessor0.processCharsetSelect0(arrayList0);
            fail("Expecting exception: IllegalArgumentException");

        } catch (IllegalArgumentException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test028() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        Character character0 = Character.valueOf(' ');
        arrayList0.add((Object) character0);
        // Undeclared exception!
        try {
            ansiProcessor0.processOperatingSystemCommand(arrayList0);
            fail("Expecting exception: IllegalArgumentException");

        } catch (IllegalArgumentException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test029() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 0);
        assertFalse(boolean0);
    }

    @Test
    public void test030() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        arrayList0.add((Object) arrayList0);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 109);
        assertFalse(boolean0);
    }

    @Test
    public void test031() throws Throwable {
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream(1030);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 1030);
        assertFalse(boolean0);
    }

    @Test
    public void test032() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 116);
        assertTrue(boolean0);
    }

    @Test
    public void test033() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 115);
        assertTrue(boolean0);
    }

    @Test
    public void test034() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 114);
        assertTrue(boolean0);
    }

    @Test
    public void test035() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 113);
        assertTrue(boolean0);
    }

    @Test
    public void test036() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 112);
        assertTrue(boolean0);
    }

    @Test
    public void test037() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 111);
        assertTrue(boolean0);
    }

    @Test
    public void test038() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 110);
        assertTrue(boolean0);
    }

    @Test
    public void test039() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 108);
        assertTrue(boolean0);
    }

    @Test
    public void test040() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 107);
        assertTrue(boolean0);
    }

    @Test
    public void test041() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 106);
        assertTrue(boolean0);
    }

    @Test
    public void test042() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 104);
        assertTrue(boolean0);
    }


    @Test
    public void test044() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 102);
        assertTrue(boolean0);
    }

    @Test
    public void test045() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 101);
        assertTrue(boolean0);
    }

    @Test
    public void test046() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 100);
        assertTrue(boolean0);
    }

    @Test
    public void test047() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 99);
        assertTrue(boolean0);
    }

    @Test
    public void test048() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 98);
        assertTrue(boolean0);
    }

    @Test
    public void test049() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 97);
        assertTrue(boolean0);
    }

    @Test
    public void test050() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 96);
        assertFalse(boolean0);
    }

    @Test
    public void test051() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 95);
        assertFalse(boolean0);
    }

    @Test
    public void test052() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 94);
        assertFalse(boolean0);
    }

    @Test
    public void test053() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 93);
        assertFalse(boolean0);
    }

    @Test
    public void test054() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 92);
        assertFalse(boolean0);
    }

    @Test
    public void test055() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 91);
        assertFalse(boolean0);
    }

    @Test
    public void test056() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 90);
        assertTrue(boolean0);
    }

    @Test
    public void test057() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 89);
        assertTrue(boolean0);
    }

    @Test
    public void test058() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 88);
        assertTrue(boolean0);
    }

    @Test
    public void test059() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 87);
        assertTrue(boolean0);
    }

    @Test
    public void test060() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 86);
        assertTrue(boolean0);
    }

    @Test
    public void test061() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 85);
        assertTrue(boolean0);
    }

    @Test
    public void test062() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 82);
        assertTrue(boolean0);
    }

    @Test
    public void test063() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 81);
        assertTrue(boolean0);
    }

    @Test
    public void test064() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 80);
        assertTrue(boolean0);
    }

    @Test
    public void test065() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 79);
        assertTrue(boolean0);
    }

    @Test
    public void test066() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 78);
        assertTrue(boolean0);
    }

    @Test
    public void test067() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 76);
        assertTrue(boolean0);
    }

    @Test
    public void test068() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 75);
        assertTrue(boolean0);
    }

    @Test
    public void test069() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 74);
        assertTrue(boolean0);
    }

    @Test
    public void test070() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 73);
        assertTrue(boolean0);
    }

    @Test
    public void test071() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 71);
        assertFalse(boolean0);
    }

    @Test
    public void test072() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 70);
        assertTrue(boolean0);
    }

    @Test
    public void test073() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        FileOutputStream mockFileOutputStream0 = new FileOutputStream("org.fusesource.jansi.io.AnsiProcessor");
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockFileOutputStream0);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 69);
        assertTrue(boolean0);
    }

    @Test
    public void test074() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 'D');
        assertTrue(boolean0);
    }

    @Test
    public void test075() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        FileOutputStream mockFileOutputStream0 =
                new FileOutputStream("org.fusesource.jansi.io.AnsiProcessor", false);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockFileOutputStream0);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 67);
        assertTrue(boolean0);
    }


    @Test
    public void test077() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 65);
        assertTrue(boolean0);
    }

    @Test
    public void test078() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        FilterOutputStream filterOutputStream0 = new FilterOutputStream(pipedOutputStream0);
        DataOutputStream dataOutputStream0 = new DataOutputStream(filterOutputStream0);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(dataOutputStream0);
        ansiProcessor0.processSetForegroundColorExt1(0, 0, 1);
    }

    @Test
    public void test079() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processEraseLine(90);
    }

    @Test
    public void test080() throws Throwable {
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 66);
        assertTrue(boolean0);
    }

    @Test
    public void test081() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processSetForegroundColor0(90);
    }

    @Test
    public void test082() throws Throwable {
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream(1030);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        ansiProcessor0.processSetBackgroundColor0(109);
    }

    @Test
    public void test083() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processDefaultBackgroundColor();
    }

    @Test
    public void test084() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 105);
        assertTrue(boolean0);
    }

    @Test
    public void test085() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processSetBackgroundColor1(65, true);
    }

    @Test
    public void test086() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processCursorLeft(107);
    }

    @Test
    public void test087() throws Throwable {
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        ansiProcessor0.processCursorToColumn(0);
    }

    @Test
    public void test088() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processSetForegroundColorExt0(255);
    }

    @Test
    public void test089() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processInsertLine(' ');
    }

    @Test
    public void test090() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processSetBackgroundColorExt0(107);
    }

    @Test
    public void test091() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        boolean boolean0 = ansiProcessor0.processEscapeCommand((ArrayList<Object>) null, 117);
        assertTrue(boolean0);
    }

    @Test
    public void test092() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processCursorUpLine(82);
    }

    @Test
    public void test093() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processEraseScreen(0);
    }

    @Test
    public void test094() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 83);
        assertTrue(boolean0);
    }

    @Test
    public void test095() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processSetBackgroundColorExt1((-3435), (-2556), 90);
    }

    @Test
    public void test096() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processDefaultTextColor();
    }

    @Test
    public void test097() throws Throwable {
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream(1030);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        ansiProcessor0.processSetForegroundColor1(1030, false);
    }

    @Test
    public void test098() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 77);
        assertTrue(boolean0);
    }

    @Test
    public void test099() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processSaveCursorPosition();
    }

    @Test
    public void test100() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processChangeIconNameAndWindowTitle("Dv");
    }

    @Test
    public void test101() throws Throwable {
        File mockFile0 = new File("0c6loin/", "0c6loin/");
        PrintStream mockPrintStream0 = new PrintStream(mockFile0);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockPrintStream0);
        ansiProcessor0.processSetAttribute(0);
    }

    @Test
    public void test102() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ArrayList<Object> arrayList0 = new ArrayList<Object>();
        boolean boolean0 = ansiProcessor0.processEscapeCommand(arrayList0, 84);
        assertTrue(boolean0);
    }

    @Test
    public void test103() throws Throwable {
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream(1030);
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(byteArrayOutputStream0);
        ansiProcessor0.processCharsetSelect1(1030, ';');
    }

    @Test
    public void test104() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        ansiProcessor0.processUnknownOperatingSystemCommand((-885), "Dv");
    }
}
