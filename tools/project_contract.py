"""Versioned project contract and deterministic source fingerprint (stdlib only)."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

SCHEMA = 2
CORE_STANDARDS = {'collaboration', 'testing', 'security-operations'}
PLACEHOLDER = re.compile(r'^(待补|待确认|待填写|REPLACE_|TODO\b|TBD\b|CHANGE_ID$)', re.I)
SKIP = {'.git', '__pycache__', '.venv', 'node_modules', 'target', 'output', 'var'}


def text(value):
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER.search(value.strip())


def local_path(root, value, directory=False):
    root = Path(root).resolve()
    if not isinstance(value, str) or not value or '\0' in value or Path(value).is_absolute():
        raise ValueError('expected a relative local path')
    candidate = root / value
    if any(p.is_symlink() for p in [candidate, *candidate.parents] if p != root and root in p.parents):
        raise ValueError('symbolic-link paths are not accepted')
    result = candidate.resolve()
    if not result.is_relative_to(root) or result == root:
        raise ValueError('path escapes root or selects the whole project')
    if not (result.is_dir() if directory else result.is_file()):
        raise ValueError('referenced local file/directory is missing')
    return result


def command_errors(item, hook=False):
    if not isinstance(item, dict):
        return ['command must be an object']
    errors = []
    argv = item.get('argv')
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a and '\0' not in a for a in argv):
        errors.append('argv must be a non-empty string array')
    if type(item.get('timeout_seconds')) is not int or not 1 <= item['timeout_seconds'] <= 7200:
        errors.append('timeout_seconds must be 1..7200')
    grace = item.get('grace_seconds', 3)
    if type(grace) is not int or not 0 <= grace <= 30:
        errors.append('grace_seconds must be 0..30')
    if hook:
        return errors
    if not isinstance(item.get('id'), str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', item['id']):
        errors.append('stable command id required')
    if not text(item.get('purpose')):
        errors.append('meaningful purpose required')
    resources = item.get('resources')
    if not isinstance(resources, dict):
        return errors + ['resources declaration required']
    if resources.get('mode') == 'none':
        if not text(resources.get('reason')):
            errors.append('resource-free reason required')
        if 'cleanup' in resources or 'residual_check' in resources:
            errors.append('resource-free commands cannot hide cleanup hooks')
    elif resources.get('mode') == 'isolated':
        if not text(resources.get('ownership')):
            errors.append('isolated resource ownership required')
        for key in ['cleanup', 'residual_check']:
            errors += [key + ': ' + e for e in command_errors(resources.get(key), hook=True)]
    else:
        errors.append('resources mode must be none or isolated')
    return errors


def profile_errors(config, project):
    if not isinstance(config, dict):
        return ['project configuration must be an object']
    errors = []
    if type(config.get('schema_version')) is not int or config.get('schema_version') != SCHEMA:
        errors.append('unsupported project schema_version; migrate explicitly to 2')
    if config.get('status') != 'ready':
        errors.append('project needs adaptation; status must be ready')
    for key in ['project_name', 'business_description', 'environment_policy', 'git_policy', 'ci_policy', 'test_resource_cleanup']:
        if not text(config.get(key)):
            errors.append(key + ': missing or placeholder')
    version = config.get('playbook_version')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        errors.append('playbook_version must be an explicit semantic version')
    stack = config.get('stack')
    if not isinstance(stack, dict):
        errors.append('stack must be an object')
    else:
        for key in ['backend', 'frontend', 'database']:
            area = stack.get(key)
            if not isinstance(area, dict) or not text(area.get('technology')):
                errors.append('stack.' + key + ': explicit technology or none required')
            elif area['technology'] == 'none' and not text(area.get('reason')):
                errors.append('stack.' + key + ': non-applicability reason required')
    boundary = config.get('business_boundaries')
    if not isinstance(boundary, list) or not boundary or not all(text(v) for v in boundary):
        errors.append('meaningful business boundaries required')
    try:
        knowledge = local_path(project, config.get('knowledge_entry'))
        if not knowledge.read_text().strip():
            errors.append('knowledge entry is empty')
    except (ValueError, OSError):
        errors.append('knowledge_entry must be an existing non-empty local file')
    standards = config.get('applicable_standards')
    if not isinstance(standards, list) or not standards or not all(isinstance(v, str) and re.fullmatch(r'[a-z][a-z-]*', v) for v in standards):
        errors.append('applicable_standards must explicitly select standard IDs')
    else:
        if not CORE_STANDARDS <= set(standards):
            errors.append('core collaboration/testing/security standards required')
        for standard in standards:
            try:
                local_path(project, '.engineering/standards/' + standard + '.md')
            except ValueError:
                errors.append('selected standard missing: ' + standard)
    env = config.get('environment')
    if not isinstance(env, dict) or env.get('classification') not in ['test', 'development'] or not text(env.get('label')) or env.get('production_access') != 'forbidden':
        errors.append('explicit non-production environment and forbidden production access required')
    sources = config.get('source_paths')
    if not isinstance(sources, list) or not sources or not all(isinstance(v, str) for v in sources):
        errors.append('source_paths must be an explicit non-empty list')
    else:
        for source in sources:
            try:
                candidate = Path(project) / source
                local_path(project, source, directory=candidate.is_dir())
            except ValueError:
                errors.append('source path missing/outside/symbolic: ' + source)
    exceptions = config.get('exceptions')
    if not isinstance(exceptions, list):
        errors.append('exceptions must be a list')
    else:
        for entry in exceptions:
            if not isinstance(entry, dict) or not all(text(entry.get(k)) for k in ['rule', 'reason', 'scope', 'risk', 'compensation', 'review_condition']):
                errors.append('exception must include rule/reason/scope/risk/compensation/review_condition')
    groups = config.get('checks')
    seen = set()
    if not isinstance(groups, dict) or not groups:
        errors.append('checks must contain at least one configured group')
    else:
        for group, items in groups.items():
            if not isinstance(group, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', group) or group == 'all':
                errors.append('invalid check group ID')
            if isinstance(items, dict) and set(items) == {'not_applicable_reason'} and text(items['not_applicable_reason']):
                continue
            if not isinstance(items, list) or not items:
                errors.append(str(group) + ': configure checks or explicit non-applicability')
                continue
            for item in items:
                errors += [str(group) + ': ' + e for e in command_errors(item)]
                if isinstance(item, dict) and isinstance(item.get('id'), str):
                    if item['id'] in seen:
                        errors.append('duplicate command id: ' + item['id'])
                    seen.add(item['id'])
    return errors


def load_profile(project):
    project = Path(project).resolve()
    path = local_path(project, '.engineering/project.json')
    config = json.loads(path.read_text())
    errors = profile_errors(config, project)
    if errors:
        raise ValueError('; '.join(errors))
    return config


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def source_state(project, config):
    project = Path(project).resolve()
    files = {local_path(project, '.engineering/project.json')}
    for source in config['source_paths']:
        candidate = project / source
        path = local_path(project, source, directory=candidate.is_dir())
        if path.is_file():
            files.add(path)
        else:
            for here, dirs, names in os.walk(path, followlinks=False):
                dirs[:] = [d for d in dirs if d not in SKIP]
                for name in dirs + names:
                    if (Path(here) / name).is_symlink():
                        raise ValueError('symbolic source input rejected')
                files.update(Path(here) / name for name in names)
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update((str(path.relative_to(project)) + '\0' + sha_file(path) + '\n').encode())
    try:
        revision = subprocess.check_output(['git', '-C', str(project), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(project), 'status', '--porcelain'], stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = 'unversioned', True
    return {'revision': revision, 'dirty': dirty, 'fingerprint': digest.hexdigest(), 'scope': config['source_paths']}
