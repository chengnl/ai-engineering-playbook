import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]


def load(folder,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'adapters'/folder/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


class JavaAdapterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('javac') and shutil.which('jdeps'),'JDK unavailable; not counted as verified')
    def test_compiled_good_and_bad_dependencies(self):
        tool=load('java-spring','check_layers')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();src=root/'src';classes=root/'classes'
            for package,body in [('repository','public class Store {}'),('service','public class Logic { com.example.repository.Store store; }'),('controller','public class Endpoint { com.example.service.Logic logic; }')]:
                folder=src/'com/example'/package;folder.mkdir(parents=True)
                (folder/(body.split()[2]+'.java')).write_text('package com.example.'+package+'; '+body)
            subprocess.run(['javac','-d',str(classes),*map(str,src.rglob('*.java'))],check=True,capture_output=True)
            self.assertEqual([],tool.check(classes,'com.example'))
            endpoint=src/'com/example/controller/Endpoint.java';endpoint.write_text('package com.example.controller; public class Endpoint { com.example.repository.Store store; }')
            subprocess.run(['javac','-d',str(classes),*map(str,src.rglob('*.java'))],check=True,capture_output=True)
            self.assertTrue(tool.check(classes,'com.example'))

    def test_absent_classes_cannot_pass(self):
        with self.assertRaises(ValueError):load('java-spring','check_layers').check('/does/not/exist','com.example')


class FrontendAdapterTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node unavailable; not counted as verified')
    def test_actual_node_lifecycle_regressions(self):
        result=subprocess.run(['node','--test',str(ROOT/'adapters/frontend/fixtures/latest-loader.test.mjs')],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)


class PostgresAdapterTests(unittest.TestCase):
    def setUp(self):self.tool=load('postgresql','isolated_check')

    def test_dangerous_connections_and_missing_opt_in_rejected(self):
        for env in [{},{'PGDATABASE':'business','PLAYBOOK_ALLOW_TEST_DB':'1'},{'PGDATABASE':'postgresql://host/app_test','PLAYBOOK_ALLOW_TEST_DB':'1'},{'PGDATABASE':'app_test','PLAYBOOK_ALLOW_TEST_DB':'1','PGSERVICE':'hidden'}]:
            runner=Mock()
            with self.assertRaises(ValueError):self.tool.isolated_check(env,runner)
            runner.assert_not_called()

    def test_success_uses_only_owned_schema_and_verifies_drop(self):
        statements=[]
        def runner(argv,**kwargs):
            sql=argv[-1];statements.append(sql)
            return subprocess.CompletedProcess(argv,0,'0' if 'pg_namespace' in sql else '1','')
        schema=self.tool.isolated_check({'PGDATABASE':'app_test','PLAYBOOK_ALLOW_TEST_DB':'1'},runner)
        self.assertEqual(5,len(statements));self.assertTrue(all(schema in sql for sql in statements))
        self.assertIn('DROP SCHEMA IF EXISTS '+schema,statements[-2])

    def test_failure_still_drops_and_verifies(self):
        statements=[]
        def runner(argv,**kwargs):
            sql=argv[-1];statements.append(sql)
            return subprocess.CompletedProcess(argv,1 if 'CREATE TABLE' in sql else 0,'0','private stderr suppressed')
        with self.assertRaises(RuntimeError):self.tool.isolated_check({'PGDATABASE':'app_test','PLAYBOOK_ALLOW_TEST_DB':'1'},runner)
        self.assertTrue(any('DROP SCHEMA' in sql for sql in statements));self.assertIn('pg_namespace',statements[-1])

    def test_residual_failure_cannot_pass(self):
        def runner(argv,**kwargs):return subprocess.CompletedProcess(argv,0,'1','')
        with self.assertRaises(RuntimeError):self.tool.isolated_check({'PGDATABASE':'app_test','PLAYBOOK_ALLOW_TEST_DB':'1'},runner)

    @unittest.skipUnless(os.environ.get('PLAYBOOK_RUN_PG_INTEGRATION')=='1','explicit isolated PostgreSQL integration not enabled')
    def test_real_isolated_database(self):
        self.tool.isolated_check()
