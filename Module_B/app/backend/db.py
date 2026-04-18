import os
import re
import sys

import pymysql
from pymysql.err import IntegrityError, OperationalError, ProgrammingError
from shard_router import N_SHARDS

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Module_A/database"))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from db_manager import DBManager

db_manager = DBManager("module_b_wal.log")
db_manager.create_table("Users")
db_manager.create_table("Products")
db_manager.create_table("Orders")


def get_db_manager():
    return db_manager


def _parse_shard_ports(raw_ports: str):
    ports = [p.strip() for p in raw_ports.split(",") if p.strip()]
    if len(ports) != N_SHARDS:
        raise ValueError(
            f"Expected {N_SHARDS} shard ports in SHARD_PORTS, got {len(ports)}: {raw_ports}"
        )
    return [int(p) for p in ports]


_SHARD_HOST = os.getenv("SHARD_HOST", "10.0.116.184")
_SHARD_PORTS = _parse_shard_ports(os.getenv("SHARD_PORTS", "3307,3308,3309"))
_SHARD_DATABASE = os.getenv("SHARD_DATABASE", "BottleNeck")
_SHARD_USER = os.getenv("SHARD_USER", "BottleNeck")
_SHARD_PASSWORD = os.getenv("SHARD_PASSWORD", "password@123")
_METADATA_SHARD = int(os.getenv("METADATA_SHARD", "0"))

_SHARD_TABLE_RE = re.compile(r"(?:(?:`?[A-Za-z0-9_]+`?)\.)?shard_(\d+)_([A-Za-z0-9_]+)")
_FRESHWASH_SCHEMA_RE = re.compile(r"\bfreshwash\.")
_INSERT_RETURNING_RE = re.compile(
    r"^\s*(INSERT\s+INTO\s+.+?)\s+RETURNING\s+(.+?)\s*;?\s*$",
    re.IGNORECASE | re.DOTALL,
)
_INSERT_INTO_TABLE_RE = re.compile(r"INSERT\s+INTO\s+([`A-Za-z0-9_.]+)", re.IGNORECASE)
_PG_INTERVAL_HOURS_RE = re.compile(
    r"%s::timestamp\s*\+\s*interval\s*'(\d+)\s*hours'",
    re.IGNORECASE,
)


def _open_raw_shard_connection(shard_id: int):
    return pymysql.connect(
        host=_SHARD_HOST,
        port=_SHARD_PORTS[shard_id],
        user=_SHARD_USER,
        password=_SHARD_PASSWORD,
        database=_SHARD_DATABASE,
        charset="utf8mb4",
        autocommit=False,
    )


def get_shard_connection(shard_id: int):
    return _open_raw_shard_connection(shard_id)


class RoutedConnection:
    """
    DB-API compatible connection wrapper that routes SQL to the correct physical shard.
    Existing code can continue to use logical names like shard_0_laundry_order.
    """

    def __init__(self):
        self._connections = {}
        self._touched = set()

    def _get_raw_connection(self, shard_id: int):
        if shard_id < 0 or shard_id >= N_SHARDS:
            raise ValueError(f"Invalid shard_id={shard_id}")
        conn = self._connections.get(shard_id)
        if conn is None:
            conn = _open_raw_shard_connection(shard_id)
            self._connections[shard_id] = conn
        return conn

    def cursor(self):
        return RoutedCursor(self)

    def commit(self):
        for shard_id in sorted(self._touched):
            self._connections[shard_id].commit()

    def rollback(self):
        for shard_id in sorted(self._touched):
            self._connections[shard_id].rollback()

    def close(self):
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()
        self._touched.clear()


class RoutedCursor:
    def __init__(self, routed_connection: RoutedConnection):
        self._routed_connection = routed_connection
        self._delegate = None
        self._synthetic_rows = None

    def _rewrite_postgres_syntax(self, query: str) -> str:
        query = _PG_INTERVAL_HOURS_RE.sub(
            lambda m: f"DATE_ADD(%s, INTERVAL {m.group(1)} HOUR)",
            query,
        )
        return query

    def _prepare_query(self, query: str):
        query = self._rewrite_postgres_syntax(query)
        query = _FRESHWASH_SCHEMA_RE.sub(f"`{_SHARD_DATABASE}`.", query)

        shard_ids = set()

        def _replace_shard_table(match):
            shard_id = int(match.group(1))
            base_table = match.group(2)
            shard_ids.add(shard_id)
            return f"`{_SHARD_DATABASE}`.`{base_table}`"

        query = _SHARD_TABLE_RE.sub(_replace_shard_table, query)

        if not shard_ids:
            target_shard = _METADATA_SHARD
        elif len(shard_ids) == 1:
            target_shard = next(iter(shard_ids))
        else:
            raise ValueError(
                f"Single SQL statement cannot target multiple physical shards: {sorted(shard_ids)}"
            )

        return target_shard, query

    def _split_insert_returning(self, query: str):
        m = _INSERT_RETURNING_RE.match(query)
        if not m:
            return query, None
        insert_sql = m.group(1).strip()
        returning_cols = [c.strip() for c in m.group(2).split(",")]
        return insert_sql, returning_cols

    def _capture_returning_rows(self, delegate_cursor, insert_sql: str, returning_cols):
        if not returning_cols:
            return []

        first_col = returning_cols[0].split(".")[-1].strip().strip("`")
        if len(returning_cols) == 1 and first_col.endswith("_id"):
            return [(delegate_cursor.lastrowid,)]

        table_match = _INSERT_INTO_TABLE_RE.search(insert_sql)
        if not table_match:
            raise ValueError(f"Unable to infer table for RETURNING query: {insert_sql}")
        table_name = table_match.group(1)
        select_sql = (
            f"SELECT {', '.join(returning_cols)} FROM {table_name} WHERE `{first_col}` = %s"
        )
        delegate_cursor.execute(select_sql, (delegate_cursor.lastrowid,))
        row = delegate_cursor.fetchone()
        return [row] if row is not None else []

    def execute(self, query, params=None):
        self._synthetic_rows = None
        if self._delegate is not None:
            self._delegate.close()
            self._delegate = None
        target_shard, rewritten = self._prepare_query(query)
        conn = self._routed_connection._get_raw_connection(target_shard)
        self._routed_connection._touched.add(target_shard)
        self._delegate = conn.cursor()

        insert_sql, returning_cols = self._split_insert_returning(rewritten)
        if returning_cols is not None:
            self._delegate.execute(insert_sql, params)
            self._synthetic_rows = self._capture_returning_rows(
                self._delegate, insert_sql, returning_cols
            )
            return self._delegate.rowcount

        return self._delegate.execute(rewritten, params)

    def executemany(self, query, param_seq):
        self._synthetic_rows = None
        if self._delegate is not None:
            self._delegate.close()
            self._delegate = None
        target_shard, rewritten = self._prepare_query(query)
        conn = self._routed_connection._get_raw_connection(target_shard)
        self._routed_connection._touched.add(target_shard)
        self._delegate = conn.cursor()
        return self._delegate.executemany(rewritten, param_seq)

    def fetchone(self):
        if self._synthetic_rows is not None:
            if not self._synthetic_rows:
                return None
            return self._synthetic_rows.pop(0)
        return self._delegate.fetchone()

    def fetchall(self):
        if self._synthetic_rows is not None:
            rows = self._synthetic_rows
            self._synthetic_rows = []
            return rows
        return self._delegate.fetchall()

    def close(self):
        if self._delegate is not None:
            self._delegate.close()
            self._delegate = None
        self._synthetic_rows = None

    @property
    def rowcount(self):
        return 0 if self._delegate is None else self._delegate.rowcount

    @property
    def lastrowid(self):
        return None if self._delegate is None else self._delegate.lastrowid


def get_connection():
    return RoutedConnection()


def ensure_schema():
    """
    Connectivity smoke-check for all configured shards.
    Raises on any unreachable shard so startup can surface clear errors.
    """
    conns = []
    try:
        for shard_id in range(N_SHARDS):
            conn = _open_raw_shard_connection(shard_id)
            conns.append(conn)
            cur = conn.cursor()
            cur.execute("SELECT @@hostname")
            cur.fetchone()
            cur.close()
    finally:
        for conn in conns:
            conn.close()
