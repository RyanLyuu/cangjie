
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
import org.apache.commons.cli.Option;
import org.apache.commons.cli.OptionBuilder;

public class OptionBuilder_ESTest  {

  @Test
  public void test00()  throws Throwable  {
      OptionBuilder.withValueSeparator1(')');
      Option option0 = OptionBuilder.create2("");
      assertEquals((-1), option0.getArgs());
      assertEquals(')', option0.getValueSeparator());
  }

  @Test
  public void test01()  throws Throwable  {
      OptionBuilder.withLongOpt("");
      Option option0 = OptionBuilder.create2("");
      assertEquals((-1), option0.getArgs());
  }

  @Test
  public void test02()  throws Throwable  {
      OptionBuilder.withArgName("org.apache.commons.cli.Option$Builder");
      Option option0 = OptionBuilder.create2("");
      assertEquals((-1), option0.getArgs());
  }

  @Test
  public void test03()  throws Throwable  {
      Option option0 = OptionBuilder.create2("NO_ARGS_ALLOWED");
      assertEquals((-1), option0.getArgs());
  }

  @Test
  public void test04()  throws Throwable  {
      OptionBuilder.hasOptionalArgs1(0);
      Option option0 = OptionBuilder.create2("");
      assertEquals(0, option0.getArgs());
      assertTrue(option0.hasOptionalArg());
  }

  @Test
  public void test05()  throws Throwable  {
      OptionBuilder.hasArg0();
      Option option0 = OptionBuilder.create2("");
      assertEquals(1, option0.getArgs());
  }

  @Test
  public void test06()  throws Throwable  {
      OptionBuilder.isRequired1(true);
      Option option0 = OptionBuilder.create1('5');
      assertEquals((-1), option0.getArgs());
      assertEquals("5", option0.getOpt());
  }

  @Test
  public void test07()  throws Throwable  {
      OptionBuilder.withValueSeparator0();
      Option option0 = OptionBuilder.create1('O');
      assertEquals((-1), option0.getArgs());
      assertEquals('=', option0.getValueSeparator());
      assertEquals("O", option0.getOpt());
  }

  @Test
  public void test08()  throws Throwable  {
      OptionBuilder.withLongOpt("U?V(");
      Option option0 = OptionBuilder.create1('k');
      assertEquals((-1), option0.getArgs());
      assertEquals(107, option0.getId());
  }

  @Test
  public void test09()  throws Throwable  {
      OptionBuilder.hasOptionalArgs0();
      Option option0 = OptionBuilder.create1('l');
      assertEquals((-2), option0.getArgs());
      assertEquals(108, option0.getId());
      assertTrue(option0.hasOptionalArg());
  }

  @Test
  public void test10()  throws Throwable  {
      OptionBuilder.hasArg0();
      Option option0 = OptionBuilder.create1('5');
      assertEquals("5", option0.getOpt());
      assertEquals(1, option0.getArgs());
  }

  @Test
  public void test11()  throws Throwable  {
      OptionBuilder.isRequired1(true);
      OptionBuilder.withLongOpt("s>&Vg-MR");
      Option option0 = OptionBuilder.create0();
      assertEquals((-1), option0.getArgs());
  }

  @Test
  public void test12()  throws Throwable  {
      OptionBuilder.withLongOpt("");
      OptionBuilder.withArgName("|Yu2\"c<=3@WUEpO");
      Option option0 = OptionBuilder.create0();
      assertEquals((-1), option0.getArgs());
  }

  @Test
  public void test13()  throws Throwable  {
      OptionBuilder.withLongOpt("");
      OptionBuilder.hasOptionalArgs1(0);
      Option option0 = OptionBuilder.create0();
      assertTrue(option0.hasOptionalArg());
      assertEquals(0, option0.getArgs());
  }

  @Test
  public void test14()  throws Throwable  {
      Object object0 = new Object();
      // Undeclared exception!
      try { 
        OptionBuilder.withType1(object0);
        fail("Expecting exception: ClassCastException");
      
      } catch(ClassCastException e) {
         //
         // class java.lang.Object cannot be cast to class java.lang.Class (java.lang.Object and java.lang.Class are in module java.base of loader 'bootstrap')
         //
}
  }

  @Test
  public void test15()  throws Throwable  {
      try { 
        OptionBuilder.create2("A CloneNotSupportedException was thrown: ");
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // The option 'A CloneNotSupportedException was thrown: ' contains an illegal character : ' '
         //
}
  }

  @Test
  public void test16()  throws Throwable  {
      try { 
        OptionBuilder.create1('&');
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // Illegal option name '&'
         //
}
  }

  @Test
  public void test17()  throws Throwable  {
      OptionBuilder optionBuilder0 = OptionBuilder.hasArg1(true);
      assertNotNull(optionBuilder0);
  }

  @Test
  public void test18()  throws Throwable  {
      OptionBuilder optionBuilder0 = OptionBuilder.hasArg1(false);
      assertNotNull(optionBuilder0);
  }

  @Test
  public void test19()  throws Throwable  {
      try { 
        OptionBuilder.create0();
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // must specify longopt
         //
}
  }

  @Test
  public void test20()  throws Throwable  {
      OptionBuilder.hasArgs0();
      Option option0 = OptionBuilder.create2("");
      assertEquals((-2), option0.getArgs());
  }

  @Test
  public void test21()  throws Throwable  {
      OptionBuilder optionBuilder0 = OptionBuilder.withType1((Object) null);
      assertNotNull(optionBuilder0);
  }

  @Test
  public void test22()  throws Throwable  {
      OptionBuilder optionBuilder0 = OptionBuilder.withDescription("org.apache.commons.cli.Option");
      assertNotNull(optionBuilder0);
  }

  @Test
  public void test23()  throws Throwable  {
      OptionBuilder.withValueSeparator0();
      OptionBuilder.withLongOpt("s>&Vg-MR");
      Option option0 = OptionBuilder.create0();
      assertEquals('=', option0.getValueSeparator());
      assertEquals((-1), option0.getArgs());
  }

  @Test
  public void test24()  throws Throwable  {
      OptionBuilder.hasOptionalArgs0();
      OptionBuilder.withLongOpt("s>&Vg-MR");
      Option option0 = OptionBuilder.create0();
      assertEquals((-2), option0.getArgs());
      assertTrue(option0.hasOptionalArg());
  }

  @Test
  public void test25()  throws Throwable  {
      OptionBuilder optionBuilder0 = OptionBuilder.hasOptionalArg();
      assertNotNull(optionBuilder0);
  }



  @Test
  public void test28()  throws Throwable  {
      Class<String> class0 = String.class;
      OptionBuilder optionBuilder0 = OptionBuilder.withType0(class0);
      assertNotNull(optionBuilder0);
  }

  @Test
  public void test29()  throws Throwable  {
      OptionBuilder.hasArg0();
      OptionBuilder.withLongOpt("U?V(");
      Option option0 = OptionBuilder.create0();
      assertEquals(1, option0.getArgs());
  }

  @Test
  public void test30()  throws Throwable  {
      OptionBuilder.hasArgs1(0);
      Option option0 = OptionBuilder.create1('R');
      assertEquals(0, option0.getArgs());
      assertEquals(82, option0.getId());
  }
}
