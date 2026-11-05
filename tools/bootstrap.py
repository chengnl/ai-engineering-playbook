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
    docs_directory = dest / 'docs'
    ensure_no_links(docs_directory)
    if docs_directory.exists() and not docs_directory.is_dir():
        raise ValueError("docs destination is not a directory")
    existing_docs = docs_directory.exists()
    version = (SOURCE / 'VERSION').read_text().strip()
    payload = {}
    for folder in ['standards', 'workflows', 'templates', 'adapters']:
        for src in (SOURCE / folder).rglob('*'):
            if '__pycache__' in src.parts or src.suffix in ['.pyc', '.pyo'] or src.name == '.DS_Store':
                continue
            if src.is_symlink():
                raise ValueError("source template contains a symbolic link")
            if src.is_file():
                payload[Path('.engineering') / src.relative_to(SOURCE)] = src.read_bytes()
    for script in ['check.py', 'verify.py', 'project_contract.py', 'process_runner.py', 'evidence.py']:
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
    if not existing_docs:
        docs_templates = SOURCE / 'templates/docs'
        templates = sorted(docs_templates.rglob('*.md.template'))
        if not templates or not (docs_templates / 'README.md.template').is_file():
            raise ValueError("knowledge directory templates are missing")
        for template in templates:
            if template.is_symlink():
                raise ValueError("source knowledge template contains a symbolic link")
            relative = template.relative_to(docs_templates).with_suffix('')
            payload[Path('docs') / relative] = template.read_bytes()
    elif not (docs_directory / 'README.md').exists():
        # Existing documentation is never moved or supplemented with assumed categories.
        payload[Path('docs/README.md')] = (
            '# 工程知识入口\n\n既有docs内容已保留，未自动分类或迁移。'
            '适配时确认唯一现行主题、分类索引和历史替代关系；新项目目录模板在.engineering/templates/docs。\n\n'
            '[文档维护规范](../.engineering/standards/documentation.md)\n'
        ).encode()
    manifest = {'manifest_schema': 1, 'playbook_version': version, 'files': {str(p): hashlib.sha256(data).hexdigest() for p, data in sorted(payload.items())}}
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
