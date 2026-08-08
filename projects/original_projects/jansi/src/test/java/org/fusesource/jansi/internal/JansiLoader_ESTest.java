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
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.junit.Test;

import static org.junit.Assert.*;

public class JansiLoader_ESTest  {






    @Test
    public void test05() throws Throwable {
        String string0 = JansiLoader.getNativeLibraryPath();
        assertNull(string0);
    }



    @Test
    public void test08() throws Throwable {
        String string0 = JansiLoader.getNativeLibrarySourceUrl();
        assertNull(string0);
    }

    @Test
    public void test09() throws Throwable {
        int int0 = JansiLoader.getMinorVersion();
        assertEquals(4, int0);
    }

    @Test
    public void test10() throws Throwable {
        String string0 = JansiLoader.getVersion();
        assertEquals("2.4.2", string0);
    }

    @Test
    public void test11() throws Throwable {
        JansiLoader jansiLoader0 = new JansiLoader();
        int int0 = JansiLoader.getMinorVersion();
        assertEquals(4, int0);
    }
}
