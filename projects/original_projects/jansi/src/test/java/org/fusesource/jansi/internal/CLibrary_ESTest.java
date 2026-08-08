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
package org.fusesource.jansi.internal;

import java.lang.Throwable;
import org.junit.Test;

import static org.junit.Assert.*;

public class CLibrary_ESTest  {

    @Test
    public void test0() throws Throwable {
        // Undeclared exception!
        try {
            CLibrary.ttyname(2);
            fail("Expecting exception: UnsatisfiedLinkError");

        } catch (UnsatisfiedLinkError e) {
            //
            // 'java.lang.String org.fusesource.jansi.internal.CLibrary.ttyname(int)'
            //
}
    }


    @Test
    public void test2() throws Throwable {
        // Undeclared exception!
        try {
            CLibrary.tcgetattr(0, (CLibrary.Termios) null);
            fail("Expecting exception: UnsatisfiedLinkError");

        } catch (UnsatisfiedLinkError e) {
            //
            // 'int org.fusesource.jansi.internal.CLibrary.tcgetattr(int,
            // org.fusesource.jansi.internal.CLibrary$Termios)'
            //
}
    }

    @Test
    public void test3() throws Throwable {
        int[] intArray0 = new int[2];
        byte[] byteArray0 = new byte[1];
        // Undeclared exception!
        try {
            CLibrary.openpty(intArray0, intArray0, byteArray0, (CLibrary.Termios) null, (CLibrary.WinSize) null);
            fail("Expecting exception: UnsatisfiedLinkError");

        } catch (UnsatisfiedLinkError e) {
            //
            // 'int org.fusesource.jansi.internal.CLibrary.openpty(int[], int[], byte[],
            // org.fusesource.jansi.internal.CLibrary$Termios, org.fusesource.jansi.internal.CLibrary$WinSize)'
            //
}
    }

    @Test
    public void test4() throws Throwable {
        // Undeclared exception!
        try {
            CLibrary.isatty(0);
            fail("Expecting exception: UnsatisfiedLinkError");

        } catch (UnsatisfiedLinkError e) {
            //
            // 'int org.fusesource.jansi.internal.CLibrary.isatty(int)'
            //
}
    }

    @Test
    public void test5() throws Throwable {
        // Undeclared exception!
        try {
            CLibrary.ioctl(0, 0, (CLibrary.WinSize) null);
            fail("Expecting exception: UnsatisfiedLinkError");

        } catch (UnsatisfiedLinkError e) {
            //
            // 'int org.fusesource.jansi.internal.CLibrary.ioctl(int, long,
            // org.fusesource.jansi.internal.CLibrary$WinSize)'
            //
}
    }

    @Test
    public void test6() throws Throwable {
        CLibrary.WinSize cLibrary_WinSize0 = null;
        try {
            cLibrary_WinSize0 = new CLibrary.WinSize((short) 0, (short) 0);
            fail("Expecting exception: NoClassDefFoundError");

        } catch (NoClassDefFoundError e) {
        }
    }

    @Test
    public void test7() throws Throwable {
        CLibrary cLibrary0 = new CLibrary();
        assertEquals(0L, CLibrary.TIOCSWINSZ);
    }

    @Test
    public void test8() throws Throwable {
        CLibrary.Termios cLibrary_Termios0 = null;
        try {
            cLibrary_Termios0 = new CLibrary.Termios();
            fail("Expecting exception: NoClassDefFoundError");

        } catch (NoClassDefFoundError e) {
        }
    }
}
