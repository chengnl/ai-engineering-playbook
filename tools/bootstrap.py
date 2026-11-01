#!/usr/bin/env python3
"""Copy an offline, pinned governance pack; never run project commands or overwrite files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parents[1]


def ensure_no_links(path):
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError(f"symbolic-link destination is not allowed: {part}")


def bootstrap(destination, name, no_agent_entry=False):
    if not isinstance(name, str) or not name.strip() or any(c in name for c in '\r\n\0'):
        raise ValueError("project name must be a non-empty single line")
    dest = Path(os.path.abspath(destination))
    ensure_no_links(dest)
    if dest.exists() and not dest.is_dir():
        raise ValueError("destination is not a directory")
    version = (SOURCE / 'VERSION').read_text().strip()
    payload = {}
    for folder in ['standards', 'workflows', 'templates']:
        for src in (SOURCE / folder).rglob('*'):
            if src.is_symlink():
                raise ValueError("source template contains a symbolic link")
            if src.is_file():
                payload[Path('.engineering') / src.relative_to(SOURCE)] = src.read_bytes()
    for script in ['check.py', 'verify.py']:
        payload[Path('.engineering/tools') / script] = (SOURCE / 'tools' / script).read_bytes()
    profile = json.loads((SOURCE / 'templates/project.json').read_text())
    profile.update(project_name=name.strip(), playbook_version=version)
    payload[Path('.engineering/project.json')] = (json.dumps(profile, ensure_ascii=False, indent=2) + '\n').encode()
    readme = (SOURCE / 'templates/adoption-readme.md').read_text().replace('(../standards/', '(standards/').replace('(../workflows/', '(workflows/')
    payload[Path('.engineering/README.md')] = readme.encode()
    agent = (SOURCE / 'templates/AGENTS.md.template').read_bytes()
    payload[Path('.engineering/AGENTS.snippet.md') if no_agent_entry else Path('AGENTS.md')] = agent
    # Existing project README/knowledge entry remain byte-for-byte intact.
    if not (dest / 'README.md').exists():
        payload[Path('README.md')] = f"# {name.strip()}\n\n研发治理骨架已接入，尚未建立业务应用。先读[研发规范入口](.engineering/README.md)，完成项目适配后再实施。\n\n[工程知识](docs/README.md)\n".encode()
    if not (dest / 'docs/README.md').exists():
        payload[Path('docs/README.md')] = b'# Project knowledge\n\nDocument architecture, business flows, API, data, permissions and operations here. No implementation is assumed yet.\n'
    manifest = {'playbook_version': version, 'files': {str(p): hashlib.sha256(data).hexdigest() for p, data in sorted(payload.items())}}
    payload[Path('.engineering/manifest.json')] = (json.dumps(manifest, indent=2) + '\n').encode()
    # Refuse any existing governance pack or destination collision before writing anything.
    if (dest / '.engineering').exists():
        raise ValueError(".engineering already exists; review a version upgrade manually")
    for rel in payload:
        ensure_no_links(dest / rel)
        if (dest / rel).exists():
            raise ValueError(f"would overwrite {rel}; use --no-agent-entry for an existing AGENTS.md")
    missing_dirs = []
    parent = dest
    while not parent.exists():
        missing_dirs.append(parent)
        parent = parent.parent
    created = []
    created_dirs = []
    lock = None
    try:
        dest.mkdir(parents=True, exist_ok=True)
        lock_path = dest / '.playbook-init.lock'
        lock = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        for rel, data in payload.items():
            target = dest / rel
            ensure_no_links(target)
            missing = []
            parent = target.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            target.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.extend(reversed(missing))
            # Exclusive creation protects against a concurrent writer after preflight.
            with target.open('xb') as stream:
                created.append(target)
                stream.write(data)
        return {'version': version, 'destination': str(dest), 'created_files': len(created), 'needs_adaptation': True, 'merge_agent_entry': no_agent_entry}
    except BaseException:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        # Only remove directories this initializer created, including on failure.
        for directory in sorted(set(created_dirs), key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    finally:
        if lock is not None:
            os.close(lock)
            (dest / '.playbook-init.lock').unlink(missing_ok=True)
        for directory in missing_dirs:
            try:
                directory.rmdir()
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--no-agent-entry', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(bootstrap(args.destination, args.name, args.no_agent_entry), ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Initialization failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
