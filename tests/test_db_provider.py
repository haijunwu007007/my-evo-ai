"""Test database provider abstraction layer"""
import os, sys, json, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.db_provider import SqliteEngine, create_engine

class TestSqliteEngine:
    def test_engine_type(self):
        e = SqliteEngine()
        assert e.engine_type == 'sqlite'

    def test_connect_and_query(self):
        e = SqliteEngine()
        e.connect()
        cur = e.execute('SELECT 1 as val')
        row = cur.fetchone()
        assert row[0] == 1
        e.close()

    def test_create_table(self):
        e = SqliteEngine()
        e.connect()
        e.execute('CREATE TABLE IF NOT EXISTS _test (id INTEGER PRIMARY KEY, name TEXT)')
        e.execute('INSERT INTO _test (name) VALUES (?)', ('hello',))
        e.commit()
        cur = e.execute('SELECT name FROM _test WHERE id=1')
        assert cur.fetchone()[0] == 'hello'
        e.execute('DROP TABLE _test')
        e.commit()
        e.close()
