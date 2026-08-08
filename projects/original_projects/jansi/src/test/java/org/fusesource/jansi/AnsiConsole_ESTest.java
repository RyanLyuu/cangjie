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
import java.io.PrintStream;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.junit.Test;

import static org.junit.Assert.*;

public class AnsiConsole_ESTest  {

    @Test
    public void test00() throws Throwable {
        AnsiConsole.systemUninstall();
        boolean boolean0 = AnsiConsole.isInstalled();
        assertFalse(boolean0);
    }

    @Test
    public void test01() throws Throwable {
        AnsiConsole.systemUninstall();
        AnsiConsole.systemUninstall();
        AnsiConsole.systemInstall();
    }


    @Test
    public void test03() throws Throwable {
        boolean boolean0 = AnsiConsole.getBoolean("");
        assertFalse(boolean0);
    }


    @Test
    public void test05() throws Throwable {
        boolean boolean0 = AnsiConsole.isInstalled();
        assertFalse(boolean0);
    }


    @Test
    public void test07() throws Throwable {
        boolean boolean0 = AnsiConsole.getBoolean("os.arch");
        assertFalse(boolean0);
    }


    @Test
    public void test09() throws Throwable {
        PrintStream printStream0 = AnsiConsole.sysErr();
        assertNotNull(printStream0);
    }


    @Test
    public void test11() throws Throwable {
        PrintStream printStream0 = AnsiConsole.sysOut();
        assertNotNull(printStream0);
    }
}
