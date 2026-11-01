#!/usr/bin/env python3
"""Check selected direct compiled-class dependency boundaries using JDK jdeps."""
import argparse
from pathlib import Path
import re
import subprocess
import sys


def violations(source, target):
    jdbc = target.startswith(('java.sql.', 'javax.sql.', 'org.springframework.jdbc.'))
    if '.controller.' in source and ('.repository.' in target or jdbc):
        return True
    if '.service.' in source and jdbc:
        return True
    if '.repository.' in source and ('.service.' in target or target.endswith('.ModelGateway')):
        return True
    if '.policy.' in source and (jdbc or '.repository.' in target or target.endswith('.ModelGateway')):
        return True
    return False


def check(classes, base_package, executable='jdeps'):
    classes = Path(classes)
    if not classes.is_dir() or not any(classes.rglob('*.class')):
        raise ValueError('compiled classes are missing; run a clean build first')
    if not re.fullmatch(r'[A-Za-z_]\w*(\.[A-Za-z_]\w*)+', base_package):
        raise ValueError('explicit base package required')
    result = subprocess.run([executable, '--ignore-missing-deps', '-verbose:class', '-filter:none', str(classes)], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('jdeps failed; check JDK and class-file compatibility')
    edges = []
    for line in result.stdout.splitlines():
        match = re.match(r'\s+([\w.$]+)\s+->\s+([\w.$]+)', line)
        if match and match[1].startswith(base_package + '.'):
            edges.append(match.groups())
    if not edges:
        raise ValueError('no class dependencies in configured base package; do not report empty success')
    return sorted(set(f'{a} -> {b}' for a, b in edges if violations(a, b)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classes', required=True)
    parser.add_argument('--base-package', required=True)
    parser.add_argument('--jdeps', default='jdeps')
    args = parser.parse_args()
    try:
        failures = check(args.classes, args.base_package, args.jdeps)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    print('PASS: selected direct compiled-class boundaries only; not reflection/cycle/SQL-semantic validation')
    return 0


if __name__ == '__main__':
    sys.exit(main())
