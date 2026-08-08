
/*
  Licensed to the Apache Software Foundation (ASF) under one or more
  contributor license agreements.  See the NOTICE file distributed with
  this work for additional information regarding copyright ownership.
  The ASF licenses this file to You under the Apache License, Version 2.0
  (the "License"); you may not use this file except in compliance with
  the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
 */

package org.apache.commons.cli;

import java.lang.Throwable;
import org.junit.Test;
import static org.junit.Assert.*;
import org.apache.commons.cli.OptionValidator;

public class OptionValidator_ESTest  {

  @Test
  public void test0()  throws Throwable  {
      try { 
        OptionValidator.validate("'");
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // Illegal option name '''
         //
}
  }

  @Test
  public void test1()  throws Throwable  {
      try { 
        OptionValidator.validate("LeOX:D)K_kF.Y\"V");
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // The option 'LeOX:D)K_kF.Y\"V' contains an illegal character : ':'
         //
}
  }

  @Test
  public void test2()  throws Throwable  {
      String string0 = OptionValidator.validate("xjr");
      assertEquals("xjr", string0);
  }

  @Test
  public void test3()  throws Throwable  {
      String string0 = OptionValidator.validate("");
      assertEquals("", string0);
  }

  @Test
  public void test4()  throws Throwable  {
      String string0 = OptionValidator.validate((String) null);
      assertNull(string0);
  }

  @Test
  public void test5()  throws Throwable  {
      String string0 = OptionValidator.validate("@");
      assertEquals("@", string0);
  }

  @Test
  public void test6()  throws Throwable  {
      String string0 = OptionValidator.validate("?");
      assertEquals("?", string0);
  }

  @Test
  public void test7()  throws Throwable  {
      String string0 = OptionValidator.validate("l");
      assertEquals("l", string0);
  }

  @Test
  public void test8()  throws Throwable  {
      OptionValidator optionValidator0 = new OptionValidator();
  }

  @Test
  public void test9()  throws Throwable  {
      try { 
        OptionValidator.validate("`");
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // Illegal option name '`'
         //
}
  }
}
