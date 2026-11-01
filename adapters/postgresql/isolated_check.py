#!/usr/bin/env python3
"""Opt-in disposable-schema PostgreSQL smoke; never use production credentials."""
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid


def validate_environment(environment):
    database = environment.get('PGDATABASE', '')
    if environment.get('PLAYBOOK_ALLOW_TEST_DB') != '1':
        raise ValueError('explicit PLAYBOOK_ALLOW_TEST_DB=1 is required')
    if not re.fullmatch(r'[a-z][a-z0-9_]*(?:_test|_ci)', database):
        raise ValueError('PGDATABASE must be a plain explicitly isolated *_test or *_ci name')
    if environment.get('PGSERVICE') or environment.get('PGSERVICEFILE'):
        raise ValueError('service-based hidden connection overrides are not allowed')
    return database


def isolated_check(environment=None, runner=subprocess.run):
    environment = dict(os.environ if environment is None else environment)
    database = validate_environment(environment)
    schema = 'playbook_test_' + uuid.uuid4().hex
    client = environment.get('PLAYBOOK_PSQL', 'psql')
    env = dict(environment, PGAPPNAME='playbook-isolated-check', PGOPTIONS='-c statement_timeout=10000 -c lock_timeout=5000')

    def sql(statement):
        result = runner([client, '-X', '-w', '--dbname', database, '-v', 'ON_ERROR_STOP=1', '-At', '-c', statement], env=env, capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise RuntimeError('isolated PostgreSQL command failed; raw credential-bearing stderr suppressed')
        return result.stdout.strip()

    attempted = False
    try:
        attempted = True  # Network timeout may leave CREATE committed; always attempt owned cleanup.
        sql(f'CREATE SCHEMA {schema}')
        sql(f'CREATE TABLE {schema}.sample (id BIGINT PRIMARY KEY, name TEXT NOT NULL); INSERT INTO {schema}.sample VALUES (1,\'synthetic\')')
        if sql(f'SELECT count(*) FROM {schema}.sample') != '1':
            raise RuntimeError('synthetic data assertion failed')
    finally:
        if attempted:
            try:
                sql(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
                if sql(f"SELECT count(*) FROM pg_namespace WHERE nspname='{schema}'") != '0':
                    raise RuntimeError('owned schema remains after cleanup')
            except BaseException as error:
                print('Owned test schema requiring inspection: ' + schema, file=sys.stderr)
                raise RuntimeError('cleanup/residual verification failed; inspect only this owned schema') from error
    return schema


def main():
    try:
        isolated_check()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2
    print('PASS: disposable synthetic schema cleaned and residual checked; not migration/business verification')
    return 0


if __name__ == '__main__':
    sys.exit(main())
