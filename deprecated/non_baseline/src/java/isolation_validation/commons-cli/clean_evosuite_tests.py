"""清洗 EvoSuite 生成的测试代码，移除无效内容并替换不兼容依赖。"""

import os
import re
import argparse
from pathlib import Path

evosuite_replacements = {
    "MockFile": "File",
    "MockFileOutputStream": "FileOutputStream",
    "MockFileInputStream": "FileInputStream",
    "MockFileWriter": "FileWriter",
    "MockPrintStream": "PrintStream",
    "MockRandom": "Random",
    "MockThrowable": "Throwable",
    "MockDateFormat": "DateFormat",
    "MockSimpleDateFormat": "SimpleDateFormat",
    "MockGregorianCalendar": "GregorianCalendar",
    "MockCalendar": "Calendar",
    "MockDate": "Date",
    "MockInstant": "Instant",
    "MockPrintWriter": "PrintWriter",
    "MockURI": "URI",
    "MockIOException": "IOException",
    "MockThread": "Thread",
    "MockException": "Exception",
    "MockLocalDateTime": "LocalDateTime",
    "MockZonedDateTime": "ZonedDateTime",
}

required_imports = {
    "File": "import java.io.File;\n",
    "FileOutputStream": "import java.io.FileOutputStream;\n",
    "FileInputStream": "import java.io.FileInputStream;\n",
    "FileWriter": "import java.io.FileWriter;\n",
    "PrintStream": "import java.io.PrintStream;\n",
    "Random": "import java.util.Random;\n",
    "Throwable": "import java.lang.Throwable;\n",
    "DateFormat": "import java.text.DateFormat;\n",
    "SimpleDateFormat": "import java.text.SimpleDateFormat;\n",
    "GregorianCalendar": "import java.util.GregorianCalendar;\n",
    "Calendar": "import java.util.Calendar;\n",
    "Date": "import java.util.Date;\n",
    "Instant": "import java.time.Instant;\n",
    "PrintWriter": "import java.io.PrintWriter;\n",
    "URI": "import java.net.URI;\n",
    "IOException": "import java.io.IOException;\n",
    "Thread": "import java.lang.Thread;\n",
    "LocalDateTime": "import java.time.LocalDateTime;\n",
    "ZonedDateTime": "import java.time.ZonedDateTime;\n",
}


def remove_invalid_content(content):
    lines = content.splitlines(keepends=True)
    cleaned_lines = []
    in_test_method = False
    brace_depth = 0
    method_buffer = []
    method_has_bad_content = False

    def strip_braces_outside_strings_and_comments(line):
        in_string = False
        in_block_comment = False
        escaped = False
        i = 0
        new_line = ''
        while i < len(line):
            char = line[i]
            next_char = line[i+1] if i + 1 < len(line) else ''
            if not in_string and not in_block_comment and char == '/' and next_char == '*':
                in_block_comment = True
                i += 2
                continue
            elif in_block_comment and char == '*' and next_char == '/':
                in_block_comment = False
                i += 2
                continue
            elif in_block_comment:
                i += 1
                continue
            if not in_string and not in_block_comment and char == '/' and next_char == '/':
                break
            if not in_block_comment and char == '"' and not escaped:
                in_string = not in_string
            if not in_string and not in_block_comment:
                new_line += char
            escaped = (char == '\\' and not escaped)
            i += 1
        return new_line
    
    for line in lines:
        if not in_test_method and re.match(r'\s*@Test', line):
            in_test_method = True
            brace_depth = 0
            method_buffer = [line]
            method_has_bad_content = False
        elif in_test_method:
            method_buffer.append(line)
            logical_line = strip_braces_outside_strings_and_comments(line)
            brace_depth += logical_line.count('{') - logical_line.count('}')

            method_text = ''.join(method_buffer)
            if any(bad in line for bad in (
                "ViolatedAssumptionAnswer",
                "doReturn",
                "nullInputStream",
                "nullOutputStream",
                "nullWriter",
                "nullReader",
                '"I", "I"',
                "List.of(",
                "List.copyOf(",
                "Path.of(",
                "readNBytes(",
                "BigInteger.TWO",
                'new SimpleTimeZone((-1437), "F>@")',
                '"12:00:00 AM", string0',
                '"2/14/14", string0',
                '"1/1/70", string0',
                'evosuite.runtime.mock',
                "Expecting exception: NumberFormatException",
                "|P9xdTEk,+sJA/c6YA",
                'getTimeZone("2_X9',
                '"Fri Feb 14 20:21:21 GMT 2014", date0.toString()',
                "GregorianCalendar(0, (-5932)",
                "GregorianCalendar(0, (-533)",
                "&-<8K3$.__|",
                "ItemInputStream0.readAllBytes()",
                "EvoSuiteFile",
                "FileSystemHandling",
                "URI.aFileURI",
                "upload_00000000_0100_4000_8200_000003000000_00000000.tmp",
                '"110(K?GwA9HJ=`", "zdIj.-=r"',
                'File.createTempFile("UTF8", "", file0);',
                "IsoCountryCode",
                'file0 = TypeHandler.createFile("");',
                'withArgName("t_K|")',
                '(mockPrintWriter0, 2188, " | ", options0)',
                'printHelp3(mockPrintWriter0, 1, " *eqTk-k", "usage: ", options0, 74, 1, " *eqTk-k", false)',
                "stringBuffer2, 1, options1, 63, 133",
                'printWrapped1(mockPrintWriter0, 0, "-")',
                "X0Y}$oEsk}XD",
                "9rg.apache.commons.cli.Optio#s",
                "VqU>bqb{}J/@+_nT5",
                '"Up]p^HwcDq^yH`lq"',
                'renderWrappedText(stringBuffer0, 0, 0, "org.apache.commons.cli.Options")',
                "OptionBuilder.isRequired0();",
                "CALLS_REAL_METHODS",
                "getPlatformClassLoader(",
                ".toSecondsPart(",
                "Instant.minusSeconds(instant0",
                "Instant.plusMillis(instant0",
                "ChronoUnit chronoUnit0 = ChronoUnit.MICROS;",
                "future = executor.submit",
                'File.createTempFile("Got exception while reading/writing the stream", ":WB=UH_5qOzP_2i5")',
                "setNextRandom(",
                "assertEquals(1392409281320000L, performanceLogger_Timer0.getDuration",
                "long0 = performanceLogger_Timer0.end()",
                "Expecting exception: NegativeArraySizeException",
                "skippableIntegratedComposition0.F2 = integratedIntCompressor0.codec",
                "new IntWrapper(4336)",
                "BenchmarkSkippable.main((String[]) null)",
                "BenchmarkBitPacking.main(stringArray0)",
                "Benchmark.main(stringArray0)",
                "BenchmarkOffsettedSeries.run(mockPrintWriter0, 27, 27)",
                "BenchmarkOffsettedSeries.main(stringArray0)",
                "BenchmarkOffsettedSeries.run(mockPrintWriter0, 5, 0)",
                "clusteredDataGenerator0.fillUniform((int[]) null, 10, 10, (-158), 10)",
                "clusteredDataGenerator0.fillClustered(intArray0, 2, 2, 20, 207)",
                "uniformDataGenerator0.generateUniform(1, 135)",
                "synchronizedMutableGraph0.hashCode();",
                "lvm *:l{s",
                "C43#%t)g0",
                "OSInfo.getHardwareName()"
                "WindowsAnsiProcessor((OutputStream) null, 15L)",
                "Predicate.not(",
                "setCurrentTimeMillis(",
                "UnaryOperator<InputStream>",
                "Benchmark.main((String[]) null)",
                "BenchmarkBitPacking.main((String[]) null)",
                "compressOneBlock(intArray0, 4, 4)",
                "intArray0[1] = 2463",
                "CLibrary.tcsetattr",
                'urlValidator0.countToken("", "")',
            )):
                method_has_bad_content = True

            if "Soundex soundex0 = Soundex.US_ENGLISH;" in method_text and "int int0 = soundex0.getMaxLength();" in method_text:
                method_has_bad_content = True
            elif "DomainValidator.updateTLDOverride" in method_text and not "DomainValidator.getInstance0(" in method_text:
                method_has_bad_content = True
            elif "directedMutableGraph0.addVertex(longWeightBaseOperations0)" in method_text and "DefaultMaxFlowAlgorithmSelector<OrderedMonoid<Long>, Long, Long> defaultMaxFlowAlgorithmSelector0 = new DefaultMaxFlowAlgorithmSelector<OrderedMonoid<Long>, Long, Long>(directedMutableGraph0, (Mapper<Long, Long>) null, longWeightBaseOperations0, longWeightBaseOperations0)" in method_text:
                method_has_bad_content = True

            if brace_depth <= 0:
                if not method_has_bad_content:
                    cleaned_lines.extend(method_buffer)
                in_test_method = False
        else:
            cleaned_lines.append(line)

    return ''.join(cleaned_lines)


    

def is_evosuite_test(file_name):
    return file_name.endswith(".java") and not file_name.endswith("_scaffolding.java") and "_ESTest" in file_name

def clean_content(content):
    content = re.sub(r'import\s+org\.evosuite\.runtime\..*?;\n', '', content)
    content = re.sub(r'import\s+org\.junit\.runner\.RunWith;\n', '', content)
    content = re.sub(r'import\s+static\s+org\.evosuite\.shaded\..*?;\n', '', content)
    content = re.sub(r'@RunWith\(EvoRunner\.class\)\s*', '', content)
    content = re.sub(r'@EvoRunnerParameters\([^)]*\)\s*', '', content)
    content = re.sub(r'extends\s+[\w\$]+_scaffolding\b', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'import\s+static\s+org\.evosuite\.runtime\.\w+\..*?;\n', '', content)
    content = content.replace("@Test(timeout = 4000)", "@Test")
    content = remove_invalid_content(content)

    content = re.sub(r'^\s*.*verifyException\s*\([^)]*\);\s*\n?', '', content, flags=re.MULTILINE)
    for old, new in evosuite_replacements.items():
        content = content.replace(old, new)
    package_match = re.search(r'^(package\s+[\w\.]+;\s*)', content, flags=re.MULTILINE)
    if package_match:
        insert_pos = package_match.end()
        import_block = ""
        for class_name, import_stmt in required_imports.items():
            if class_name in content and import_stmt not in content:
                import_block += import_stmt
        content = content[:insert_pos] + import_block + content[insert_pos:]
    # content = content.replace("import org.junit.Test;", "import org.junit.jupiter.api.Test;\n")
    # content = content.replace("import static org.junit.Assert.*;", "import static org.junit.jupiter.api.Assertions.*;\n")
    return content

def process_project(project_path: Path, output_root: Path):
    for dirpath, _, filenames in os.walk(project_path / "src/test/java"):
        for filename in filenames:
            if not is_evosuite_test(filename):
                continue
            input_file = Path(dirpath) / filename
            output_relative_path = input_file.relative_to(project_path)
            output_file = output_root / output_relative_path

            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()

            cleaned_content = clean_content(content)

            os.makedirs(output_file.parent, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            print(f"Cleaned: {input_file} → {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Clean EvoSuite tests to make them Java 8 compatible.")
    parser.add_argument("input_root", type=str, help="Input root directory of projects")
    parser.add_argument("output_root", type=str, help="Output root directory for cleaned tests")

    args = parser.parse_args()
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)

    if (input_root / "src/test/java").exists():
        process_project(input_root, output_root)
    else:
        for project_dir in input_root.iterdir():
            if project_dir.is_dir():
                process_project(project_dir, output_root)

if __name__ == "__main__":
    main()
