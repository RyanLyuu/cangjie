/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.commons.codec.language.bm;

public class Rule1 extends Rule {
    private final String pat;
    private final String lCon;
    private final String rCon;
    private final Rule_PhonemeExpr ph;
    private final int myLine;
    private final String loc;

    public Rule1(String pat_param, String lCon_param, String rCon_param, Rule_PhonemeExpr ph_param, int cLine, String location) {
        super(pat_param, lCon_param, rCon_param, ph_param);
        this.pat = pat_param;
        this.lCon = lCon_param;
        this.rCon = rCon_param;
        this.ph = ph_param;
        this.myLine = cLine;
        this.loc = location;
    }

    @Override
    public String toString() {
        final StringBuilder sb = new StringBuilder();
        sb.append("Rule");
        sb.append("{line=").append(myLine);
        sb.append(", loc='").append(loc).append('\'');
        sb.append(", pat='").append(pat).append('\'');
        sb.append(", lcon='").append(lCon).append('\'');
        sb.append(", rcon='").append(rCon).append('\'');
        sb.append('}');
        return sb.toString();
    }
}
