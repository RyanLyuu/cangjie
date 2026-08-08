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

import java.io.File;
import java.io.FileOutputStream;
import java.lang.Throwable;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.io.OutputStream;
import java.io.PipedOutputStream;
import java.nio.charset.Charset;

import org.fusesource.jansi.AnsiColors;
import org.fusesource.jansi.AnsiMode;
import org.fusesource.jansi.AnsiType;
import org.junit.Test;

import static org.junit.Assert.*;

public class AnsiOutputStream_ESTest  {


    @Test
    public void test01() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        int int0 = ansiOutputStream_ZeroWidthSupplier0.getTerminalWidth();
        assertEquals(0, int0);
    }

    @Test
    public void test02() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                byteArrayOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(5);
        assertEquals(3, byteArrayOutputStream0.size());
        assertEquals("\u001B]\u0005", byteArrayOutputStream0.toString());
    }

    @Test
    public void test03() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(89);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }


    @Test
    public void test05() throws Throwable {
        FileOutputStream mockFileOutputStream0 = new FileOutputStream("9R5/3");
        BufferedOutputStream bufferedOutputStream0 = new BufferedOutputStream(mockFileOutputStream0);
        ObjectOutputStream objectOutputStream0 = new ObjectOutputStream(bufferedOutputStream0);
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(bufferedOutputStream0);
        AnsiType ansiType0 = AnsiType.Redirected;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        Charset charset0 = Charset.defaultCharset();
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                objectOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.close();
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test06() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        FileOutputStream mockFileOutputStream0 = new FileOutputStream("}]!P");
        ObjectOutputStream objectOutputStream0 = new ObjectOutputStream(mockFileOutputStream0);
        BufferedOutputStream bufferedOutputStream0 = new BufferedOutputStream(objectOutputStream0);
        DataOutputStream dataOutputStream0 = new DataOutputStream(bufferedOutputStream0);
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(mockFileOutputStream0);
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        Charset charset0 = Charset.defaultCharset();
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                dataOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        boolean boolean0 = ansiOutputStream0.isResetAtUninstall();
        assertFalse(boolean0);
    }

    @Test
    public void test07() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(34);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(65);
            fail("Expecting exception: ClassCastException");

        } catch (ClassCastException e) {
            //
            // class java.lang.String cannot be cast to class java.lang.Integer (java.lang.String and java.lang.Integer
            // are in module java.base of loader 'bootstrap')
            //
}
    }

    @Test
    public void test08() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiType ansiType0 = AnsiType.VirtualTerminal;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(pipedOutputStream0);
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                pipedOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        try {
            ansiOutputStream0.write(122);
            fail("Expecting exception: IOException");

        } catch (IOException e) {
            //
            // Pipe not connected
            //
}
    }

    @Test
    public void test09() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        Charset charset0 = Charset.defaultCharset();
        PipedOutputStream pipedOutputStream0 = new PipedOutputStream();
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                pipedOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        try {
            ansiOutputStream0.uninstall();
            fail("Expecting exception: IOException");

        } catch (IOException e) {
            //
            // Pipe not connected
            //
}
    }

    @Test
    public void test10() throws Throwable {
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiType ansiType0 = AnsiType.Native;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                (AnsiOutputStream.WidthSupplier) null,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        // Undeclared exception!
        try {
            ansiOutputStream0.getTerminalWidth();
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }


    @Test
    public void test12() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(34);
        // Undeclared exception!
        try {
            ansiOutputStream0.write((-1828));
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }





    @Test
    public void test17() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.setMode(ansiMode0);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }


    @Test
    public void test19() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.uninstall();
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test20() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Redirected;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.uninstall();
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test21() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.uninstall();
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }


    @Test
    public void test23() throws Throwable {
        FileOutputStream mockFileOutputStream0 = new FileOutputStream("{");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Redirected;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockFileOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.install();
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test24() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        ansiOutputStream0.write(59);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(7);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test25() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(40);
        ansiOutputStream0.write(40);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test26() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        ansiOutputStream0.write(59);
        ansiOutputStream0.write(7);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test27() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Native;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(93);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test28() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Native;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(27);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test29() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        ansiOutputStream0.write(48);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test30() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(93);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test31() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(34);
        // Undeclared exception!
        try {
            ansiOutputStream0.uninstall();
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test32() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(34);
        ansiOutputStream0.write(59);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test33() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(51);
        ansiOutputStream0.write(59);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test34() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(49);
        ansiOutputStream0.write(49);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test35() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.VirtualTerminal;
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(49);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(27);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test36() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(61);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test37() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(63);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test38() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(59);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test39() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(38);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test40() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Native;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(41);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test41() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        // Undeclared exception!
        try {
            ansiOutputStream0.uninstall();
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test42() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                byteArrayOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(5);
        assertEquals(1, byteArrayOutputStream0.size());
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test43() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(40);
        // Undeclared exception!
        try {
            ansiOutputStream0.write(40);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test44() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        ansiOutputStream0.write(59);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test45() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(93);
        ansiOutputStream0.write(48);
        ansiOutputStream0.write(59);
        ansiOutputStream0.write(93);
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test46() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Native;
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.write(27);
        ansiOutputStream0.write(91);
        ansiOutputStream0.write(34);
        ansiOutputStream0.write(34);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test47() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        AnsiMode ansiMode0 = AnsiMode.Force;
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.VirtualTerminal;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.getMode();
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test48() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                byteArrayOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        int int0 = ansiOutputStream0.getTerminalWidth();
        assertEquals(0, int0);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test49() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        ByteArrayOutputStream byteArrayOutputStream0 = new ByteArrayOutputStream();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                byteArrayOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.setResetAtUninstall(true);
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test50() throws Throwable {
        FileOutputStream mockFileOutputStream0 = new FileOutputStream("9R5/3");
        BufferedOutputStream bufferedOutputStream0 = new BufferedOutputStream(mockFileOutputStream0);
        ObjectOutputStream objectOutputStream0 = new ObjectOutputStream(bufferedOutputStream0);
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiProcessor ansiProcessor0 = new AnsiProcessor(bufferedOutputStream0);
        AnsiType ansiType0 = AnsiType.Redirected;
        AnsiColors ansiColors0 = AnsiColors.Colors16;
        Charset charset0 = Charset.defaultCharset();
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                objectOutputStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        boolean boolean0 = ansiOutputStream0.isResetAtUninstall();
        assertTrue(boolean0);
    }

    @Test
    public void test51() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        AnsiMode ansiMode0 = AnsiMode.Force;
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.VirtualTerminal;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        ansiOutputStream0.getType();
        assertTrue(ansiOutputStream0.isResetAtUninstall());
    }

    @Test
    public void test52() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiMode ansiMode0 = AnsiMode.Strip;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        // Undeclared exception!
        try {
            ansiOutputStream0.close();
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // no message in exception (getMessage() returned null)
            //
}
    }

    @Test
    public void test53() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        Charset charset0 = Charset.defaultCharset();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                (OutputStream) null,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                ansiProcessor0,
                ansiType0,
                ansiColors0,
                charset0,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        ansiOutputStream0.getColors();
        assertFalse(ansiOutputStream0.isResetAtUninstall());
    }
}
