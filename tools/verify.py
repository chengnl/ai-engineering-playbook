#!/usr/bin/env python3
"""Run explicitly configured local checks without shell interpolation; no implied environment safety."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def run_checks(project, group):
    project = Path(project).resolve()
    config = json.loads((project / '.engineering/project.json').read_text())
    if not isinstance(config, dict):
        raise ValueError('project configuration must be an object')
    if config.get('status') != 'ready':
        raise ValueError('project needs adaptation; configure and review checks before setting ready')
    groups = config.get('checks')
    if not isinstance(groups, dict):
        raise ValueError('checks must be an object')
    selected = list(groups) if group == 'all' else [group]
    commands = []
    # Validate ALL selected commands before executing the first one.
    for name in selected:
        items = groups.get(name)
        if not isinstance(items, list) or not items:
            raise ValueError(f'{name}: checks are not configured')
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f'{name}: check must be object')
            argv = item.get('argv')
            timeout = item.get('timeout_seconds')
            purpose = item.get('purpose')
            if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a and '\0' not in a for a in argv):
                raise ValueError(f'{name}: argv must be a non-empty string array')
            if type(timeout) is not int or not 1 <= timeout <= 7200:
                raise ValueError(f'{name}: timeout_seconds must be 1..7200')
            if not isinstance(purpose, str) or not purpose.strip():
                raise ValueError(f'{name}: purpose required')
            commands.append((name, argv, timeout))
    if not commands:
        raise ValueError('no selected checks')
    for index, (name, argv, timeout) in enumerate(commands, 1):
        print(f'RUN {index}/{len(commands)} group={name}', flush=True)
        # Dedicated process group lets timeout clean descendants on POSIX.
        process = subprocess.Popen(argv, cwd=project, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            import os
            import signal
            if sys.platform == 'win32':
                process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait()
            print('FAIL: check timed out or interrupted; external side effects may still need review', file=sys.stderr)
            return 124
        if code:
            print(f'FAIL: group={name}, exit={code}', file=sys.stderr)
            return 1
    print(f'PASS: {len(commands)} configured commands exited zero; no broader guarantee')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--group', required=True)
    args = parser.parse_args()
    try:
        return run_checks(args.project, args.group)
    except (OSError, ValueError, TypeError) as error:
        print(f'Checks unavailable: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
