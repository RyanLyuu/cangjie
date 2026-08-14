"""从 Maven Surefire XML 报告中提取实际执行到的测试并汇总为 JSON。"""

import os
import json
import sys
import re
import xml.etree.ElementTree as ET

def ends_with_digits_in_brackets(s: str) -> bool:
    """
    Return True if *s* ends with one or more digits enclosed in square brackets, e.g. “[123]”.
    Otherwise return False.
    """
    return bool(re.search(r"\[\d+\]$", s))

project_name = sys.argv[1]
os.makedirs(f'executed_tests', exist_ok=True)

surefire_reports = [x for x in os.listdir(f'{project_name}/target/surefire-reports') if x.endswith('.xml')]
executed_tests = {}
for report in surefire_reports:
    tree = ET.parse(f'{project_name}/target/surefire-reports/{report}')
    root = tree.getroot()
    tests = root.findall('.//testcase')
    for test in tests:
        test_name = test.get('name')
        class_name = test.get('classname')

        if '(' in test_name and ends_with_digits_in_brackets(test_name):
            print(f'Found test with parentheses: {test_name} in {class_name}')
            test_name = test_name.split('(')[0]
        elif ends_with_digits_in_brackets(test_name):
            print(f'Found test with digits in brackets: {test_name} in {class_name}')
            test_name = test_name.split('[')[0]

        executed_tests.setdefault(class_name, {})
        executed_tests[class_name].setdefault(test_name, {'mocked': False, 'mock_duration': 0, 'timeout': False})

with open(f'executed_tests/{project_name}.json', 'w') as f:
    json.dump(executed_tests, f, indent=4)
