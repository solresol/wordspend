"""Production defaults, isolated overrides and fail-closed endpoint checks."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from psycopg.conninfo import conninfo_to_dict

from wordspend import db


@pytest.fixture
def driver(monkeypatch):
    for key in ['WORDSPEND_DATABASE_URL','PGHOST','PGPORT','PGUSER','PGDATABASE']:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(db.getpass, 'getuser', lambda:'wordspend')
    conn = Mock()
    conn.info = SimpleNamespace(dbname='wordspend', user='wordspend', host='/var/run/postgresql',
                                port=5433, server_version=180006)
    connect = Mock(return_value=conn)
    monkeypatch.setattr(db.psycopg, 'connect', connect)
    return connect,conn


def test_default_and_name_only_routes_ignore_inherited_pg16_port(driver, monkeypatch):
    connect,conn = driver
    monkeypatch.setenv('PGPORT','5432')
    for dsn in [None,'dbname=wordspend']:
        assert db.connect(dsn) is conn
        assert conninfo_to_dict(connect.call_args.args[0]) == {
            'host':'/var/run/postgresql','port':'5433','dbname':'wordspend','user':'wordspend'}
    conn.execute.assert_not_called()


@pytest.mark.parametrize('field,value', [
    ('dbname','pausanias'),('user','postgres'),('host','unexpected.example'),
    ('port',5432),('server_version',160015),
])
def test_wrong_actual_identity_closed_before_sql(driver, field, value):
    _,conn = driver;setattr(conn.info,field,value)
    with pytest.raises(RuntimeError,match='Refusing Wordspend SQL'):db.connect()
    conn.close.assert_called_once();conn.execute.assert_not_called()


def test_explicit_isolated_database_and_credentials_are_preserved(driver, monkeypatch):
    connect,conn = driver
    conn.info.dbname='wordspend_test_isolated';conn.info.user='tester'
    value="dbname=wordspend_test_isolated user=tester password='test fixture only' port=5433"
    monkeypatch.setenv('WORDSPEND_DATABASE_URL',value)
    assert db.database_url()==value
    assert db.connect() is conn
    fields=conninfo_to_dict(connect.call_args.args[0])
    assert fields['dbname']=='wordspend_test_isolated' and fields['user']=='tester'
    assert fields['password']=='test fixture only' and fields['port']=='5433'


def test_wordspend_override_does_not_modify_pausanias_source(driver, monkeypatch):
    monkeypatch.setenv('WORDSPEND_DATABASE_URL','dbname=wordspend_test_destination port=5433')
    from scripts import import_pausanias as reader
    source=Mock();source.info=SimpleNamespace(dbname='pausanias',user='wordspend',
        host='/var/run/postgresql',port=5433,server_version=180006)
    monkeypatch.setattr(reader.psycopg,'connect',Mock(return_value=source))
    monkeypatch.delenv('PAUSANIAS_DATABASE_URL',raising=False)
    assert reader.pausanias_source_connection() is source
    assert source.read_only is True
