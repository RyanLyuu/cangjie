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

import java.io.PrintStream;
import java.lang.Throwable;
import java.io.OutputStream;
import java.nio.charset.Charset;

import org.fusesource.jansi.io.AnsiOutputStream;
import org.fusesource.jansi.io.AnsiProcessor;
import org.junit.Test;

import static org.junit.Assert.*;

public class AnsiPrintStream_ESTest  {








    @Test
    public void test07() throws Throwable {
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiProcessor ansiProcessor0 = new AnsiProcessor((OutputStream) null);
        AnsiType ansiType0 = AnsiType.Unsupported;
        AnsiColors ansiColors0 = AnsiColors.Colors256;
        Charset charset0 = Charset.defaultCharset();
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
        AnsiPrintStream ansiPrintStream0 = null;
        try {
            ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, false, "");
            fail("Expecting exception: UnsupportedEncodingException");

        } catch (Throwable e) {
            //
            //
            //
}
    }




    @Test
    public void test11() throws Throwable {
        Object object0 = new Object();
        AnsiPrintStream ansiPrintStream0 = null;
        try {
            ansiPrintStream0 = new AnsiPrintStream((AnsiOutputStream) null, true, object0);
            fail("Expecting exception: IllegalArgumentException");

        } catch (IllegalArgumentException e) {
            //
            // Invalid argument type
            //
}
    }

    @Test
    public void test12() throws Throwable {
        AnsiPrintStream ansiPrintStream0 = null;
        try {
            ansiPrintStream0 = new AnsiPrintStream((AnsiOutputStream) null, false, (Object) null);
            fail("Expecting exception: NullPointerException");

        } catch (NullPointerException e) {
            //
            // Null output stream
            //
}
    }

    @Test
    public void test13() throws Throwable {
        PrintStream mockPrintStream0 = new PrintStream("Default");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockPrintStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                (Charset) null,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        AnsiPrintStream ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, false, "Default");
        ansiPrintStream0.install();
        assertEquals(
                "AnsiPrintStream{type=Emulation, colors=TrueColor, mode=Force, resetAtUninstall=false}",
                ansiPrintStream0.toString());
    }



    @Test
    public void test16() throws Throwable {
        PrintStream mockPrintStream0 = new PrintStream("Default");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockPrintStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                (Charset) null,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        AnsiPrintStream ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, true, "Default");
        String string0 = ansiPrintStream0.toString();
        assertEquals("AnsiPrintStream{type=Emulation, colors=TrueColor, mode=Default, resetAtUninstall=true}", string0);
    }

    @Test
    public void test17() throws Throwable {
        PrintStream mockPrintStream0 = new PrintStream("Default");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockPrintStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                (Charset) null,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        AnsiPrintStream ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, true, "Default");
        AnsiType ansiType1 = ansiPrintStream0.getType();
        assertSame(ansiType1, ansiType0);
    }

    @Test
    public void test18() throws Throwable {
        PrintStream mockPrintStream0 = new PrintStream("Default");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockPrintStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                (Charset) null,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        AnsiPrintStream ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, true, "Default");
        int int0 = ansiPrintStream0.getTerminalWidth();
        assertEquals(0, int0);
    }

    @Test
    public void test19() throws Throwable {
        PrintStream mockPrintStream0 = new PrintStream("Default");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Force;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockPrintStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                (Charset) null,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                false);
        AnsiPrintStream ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, false, "Default");
        AnsiColors ansiColors1 = ansiPrintStream0.getColors();
        assertSame(ansiColors1, ansiColors0);
    }

    @Test
    public void test20() throws Throwable {
        PrintStream mockPrintStream0 = new PrintStream("Default");
        AnsiOutputStream.ZeroWidthSupplier ansiOutputStream_ZeroWidthSupplier0 =
                new AnsiOutputStream.ZeroWidthSupplier();
        AnsiMode ansiMode0 = AnsiMode.Default;
        AnsiType ansiType0 = AnsiType.Emulation;
        AnsiColors ansiColors0 = AnsiColors.TrueColor;
        AnsiOutputStream ansiOutputStream0 = new AnsiOutputStream(
                mockPrintStream0,
                ansiOutputStream_ZeroWidthSupplier0,
                ansiMode0,
                (AnsiProcessor) null,
                ansiType0,
                ansiColors0,
                (Charset) null,
                (AnsiOutputStream.IoRunnable) null,
                (AnsiOutputStream.IoRunnable) null,
                true);
        AnsiPrintStream ansiPrintStream0 = new AnsiPrintStream(ansiOutputStream0, true, "Default");
        AnsiMode ansiMode1 = ansiPrintStream0.getMode();
        assertSame(ansiMode1, ansiMode0);
    }
}
