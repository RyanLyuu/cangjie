
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
import java.util.LinkedList;
import java.util.List;
import org.apache.commons.cli.MissingOptionException;

public class MissingOptionException_ESTest  {

  @Test
  public void test0()  throws Throwable  {
      LinkedList<Object> linkedList0 = new LinkedList<Object>();
      Integer integer0 = new Integer(1);
      linkedList0.add((Object) integer0);
      MissingOptionException missingOptionException0 = new MissingOptionException(1, linkedList0, (String) null);
      List list0 = missingOptionException0.getMissingOptions();
      assertFalse(list0.isEmpty());
  }

  @Test
  public void test1()  throws Throwable  {
      // Undeclared exception!
      try { 
        MissingOptionException.MissingOptionException1(1, (List) null, "3cF!AtCi7c4Vm\n-");
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
}
  }

  @Test
  public void test2()  throws Throwable  {
      LinkedList<Object> linkedList0 = new LinkedList<Object>();
      MissingOptionException missingOptionException0 = new MissingOptionException((-16), linkedList0, (String) null);
  }


  @Test
  public void test4()  throws Throwable  {
      LinkedList<Object> linkedList0 = new LinkedList<Object>();
      linkedList0.add((Object) "");
      MissingOptionException missingOptionException0 = MissingOptionException.MissingOptionException1(1, linkedList0, "");
      assertNotNull(missingOptionException0);
  }

  @Test
  public void test5()  throws Throwable  {
      LinkedList<Object> linkedList0 = new LinkedList<Object>();
      MissingOptionException missingOptionException0 = MissingOptionException.MissingOptionException1(1, linkedList0, ", ");
      List list0 = missingOptionException0.getMissingOptions();
      assertEquals(0, list0.size());
  }

  @Test
  public void test6()  throws Throwable  {
      LinkedList<Object> linkedList0 = new LinkedList<Object>();
      MissingOptionException missingOptionException0 = MissingOptionException.MissingOptionException1(1379, linkedList0, "X$k#k=IoA pgf9");
      List list0 = missingOptionException0.getMissingOptions();
      assertNull(list0);
  }
}
