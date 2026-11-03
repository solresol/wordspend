"""The conditional source reader must not reroute Wordspend or run its importer."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from psycopg.conninfo import conninfo_to_dict

from scripts import import_pausanias as reader


def connection(database="pausanias", role="wordspend", host="/var/run/postgresql",
               port=5433, major=18):
    result = Mock()
    result.info = SimpleNamespace(dbname=database, user=role, host=host,
                                  port=port, server_version=major * 10000 + 6)
    return result


def test_source_defaults_ignore_pg16_environment_and_preserve_own_route(monkeypatch):
    monkeypatch.delenv("PAUSANIAS_DATABASE_URL", raising=False)
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("WORDSPEND_DATABASE_URL", "dbname=wordspend port=5432")
    conn = connection()
    driver = Mock(return_value=conn)
    own_connect = Mock(side_effect=AssertionError("Own database must not be opened"))
    monkeypatch.setattr(reader.psycopg, "connect", driver)
    monkeypatch.setattr(reader, "connect", own_connect)
    assert reader.pausanias_source_connection() is conn
    assert conninfo_to_dict(driver.call_args.args[0]) == {
        "host": "/var/run/postgresql", "port": "5433",
        "dbname": "pausanias", "user": "wordspend"}
    assert conn.read_only is True
    conn.cursor.assert_not_called()
    own_connect.assert_not_called()
    from wordspend.db import database_url
    assert database_url() == "dbname=wordspend port=5432"


def test_explicit_isolated_source_is_verified_without_processing(monkeypatch):
    monkeypatch.setenv("PAUSANIAS_DATABASE_URL", "dbname=pausanias_rehearsal_reader port=5433")
    conn = connection(database="pausanias_rehearsal_reader")
    monkeypatch.setattr(reader.psycopg, "connect", Mock(return_value=conn))
    assert reader.pausanias_source_connection() is conn
    conn.cursor.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"port": 5432}, {"major": 16}, {"database": "wordspend"},
    {"role": "postgres"}, {"host": "unexpected.example"},
])
def test_wrong_source_fails_before_queries(monkeypatch, changes):
    monkeypatch.delenv("PAUSANIAS_DATABASE_URL", raising=False)
    conn = connection(**changes)
    monkeypatch.setattr(reader.psycopg, "connect", Mock(return_value=conn))
    with pytest.raises(RuntimeError, match="Refusing Pausanias source"):
        reader.pausanias_source_connection()
    conn.close.assert_called_once()
    conn.cursor.assert_not_called()
