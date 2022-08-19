import pytest
import os
import sqlalchemy

from permifrost.snowflake_connector import SnowflakeConnector


@pytest.fixture
def snowflake_connector_env():
    os.environ["PERMISSION_BOT_USER"] = "TEST"
    os.environ["PERMISSION_BOT_PASSWORD"] = "TEST"
    os.environ["PERMISSION_BOT_ACCOUNT"] = "TEST"
    os.environ["PERMISSION_BOT_DATABASE"] = "TEST"
    os.environ["PERMISSION_BOT_ROLE"] = "TEST"
    os.environ["PERMISSION_BOT_WAREHOUSE"] = "TEST"


class TestSnowflakeConnector:
    def test_snowflaky(self):

        db1 = "analytics.schema.table"
        db2 = "1234raw.schema.table"
        db3 = '"123-with-quotes".schema.table'
        db4 = "1_db-9-RANDOM.schema.table"
        db5 = "DATABASE_1.SCHEMA_1.TABLE_1"
        db6 = "DATABASE_1.SCHEMA_1.TABLE$A"
        db7 = 'DATABASE_1.SCHEMA_1."GROUP"'
        db8 = "DATABASE_1.SCHEMA_1.1_LEADING_DIGIT"
        db9 = 'DATABASE_1.SCHEMA_1."1_LEADING_DIGIT_IN_QUOTES"'
        db10 = 'DATABASE_1.SCHEMA_1."QUOTED!TABLE%WITH^SPECIAL*CHARACTERS"'
        db11 = "DATABASE_1.SCHEMA_1.TABLE%WITH^SPECIAL*CHARACTERS"
        db12 = "DATABASE_1.SCHEMA_1.Case_Sensitive_Table_Name"
        db13 = "DATABASE_1.SCHEMA_1.TABLE_1.AMBIGUOUS_IDENTIFIER"
        db14 = 'DATABASE_1.SCHEMA_1."TABLE_1.AMBIGUOUS_IDENTIFIER"'

        assert SnowflakeConnector.snowflaky(db1) == "analytics.schema.table"
        assert SnowflakeConnector.snowflaky(db2) == '"1234raw".schema.table'
        assert SnowflakeConnector.snowflaky(db3) == '"123-with-quotes".schema.table'
        assert SnowflakeConnector.snowflaky(db4) == '"1_db-9-RANDOM".schema.table'
        assert SnowflakeConnector.snowflaky(db5) == "database_1.schema_1.table_1"
        assert SnowflakeConnector.snowflaky(db6) == "database_1.schema_1.table$a"
        assert SnowflakeConnector.snowflaky(db7) == 'database_1.schema_1."GROUP"'
        assert (
            SnowflakeConnector.snowflaky(db8) == 'database_1.schema_1."1_LEADING_DIGIT"'
        )
        assert (
            SnowflakeConnector.snowflaky(db9)
            == 'database_1.schema_1."1_LEADING_DIGIT_IN_QUOTES"'
        )
        assert (
            SnowflakeConnector.snowflaky(db10)
            == 'database_1.schema_1."QUOTED!TABLE%WITH^SPECIAL*CHARACTERS"'
        )
        assert (
            SnowflakeConnector.snowflaky(db11)
            == 'database_1.schema_1."TABLE%WITH^SPECIAL*CHARACTERS"'
        )
        assert (
            SnowflakeConnector.snowflaky(db12)
            == 'database_1.schema_1."Case_Sensitive_Table_Name"'
        )

        with pytest.warns(SyntaxWarning):
            SnowflakeConnector.snowflaky(db13)
            SnowflakeConnector.snowflaky(db14)

    def test_uses_oauth_if_available(self, mocker, snowflake_connector_env):
        mocker.patch("sqlalchemy.create_engine")
        os.environ["PERMISSION_BOT_OAUTH_TOKEN"] = "TEST"
        SnowflakeConnector()
        del os.environ["PERMISSION_BOT_OAUTH_TOKEN"]
        sqlalchemy.create_engine.assert_called_with(
            "snowflake://TEST:@TEST/?authenticator=oauth&token=TEST&warehouse=TEST"
        )

    def test_uses_key_pair_if_available(self, mocker, snowflake_connector_env):
        mocker.patch("sqlalchemy.create_engine")

        test_private_key = "TEST_PK"
        mocker.patch.object(
            SnowflakeConnector, "generate_private_key", return_value=test_private_key
        )

        os.environ["PERMISSION_BOT_KEY_PATH"] = "TEST"
        os.environ["PERMISSION_BOT_KEY_PASSPHRASE"] = "TEST"

        SnowflakeConnector()

        del os.environ["PERMISSION_BOT_KEY_PATH"]
        del os.environ["PERMISSION_BOT_KEY_PASSPHRASE"]

        sqlalchemy.create_engine.assert_called_with(
            "snowflake://TEST:@TEST/TEST?role=TEST&warehouse=TEST",
            connect_args={"private_key": test_private_key},
        )

    def test_uses_authenticator_if_available(self, mocker, snowflake_connector_env):
        mocker.patch("sqlalchemy.create_engine")
        os.environ["PERMISSION_BOT_AUTHENTICATOR"] = "TEST"
        SnowflakeConnector()
        del os.environ["PERMISSION_BOT_AUTHENTICATOR"]
        sqlalchemy.create_engine.assert_called_with(
            "snowflake://TEST:@TEST/TEST?authenticator=TEST&role=TEST&warehouse=TEST"
        )

    def test_uses_username_password_by_default(self, mocker, snowflake_connector_env):
        mocker.patch("sqlalchemy.create_engine")
        SnowflakeConnector()
        sqlalchemy.create_engine.assert_called_with(
            "snowflake://TEST:TEST@TEST/TEST?role=TEST&warehouse=TEST"
        )

    def test_run_query_executes_desired_query(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        query = "MY FUN TESTING QUERY"

        conn.run_query(query)

        conn.engine.assert_has_calls([mocker.call.connect().__enter__().execute(query)])

    def test_run_query_returns_results(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        expectedResult = "MY DATABASE RESULT"
        mocker.patch.object(
            conn.engine.connect().__enter__(), "execute", return_value=expectedResult
        )

        result = conn.run_query("query")

        assert result is expectedResult

    def test_get_current_user(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        conn.run_query = mocker.MagicMock()
        mocker.patch.object(
            conn.run_query(), "fetchone", return_value={"user": "TEST_USER"}
        )

        user = conn.get_current_user()

        conn.run_query.assert_has_calls([mocker.call("SELECT CURRENT_USER() AS USER")])
        assert user == "test_user"

    def test_get_current_role(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        conn.run_query = mocker.MagicMock()
        mocker.patch.object(
            conn.run_query(), "fetchone", return_value={"role": "TEST_ROLE"}
        )

        role = conn.get_current_role()

        conn.run_query.assert_has_calls([mocker.call("SELECT CURRENT_ROLE() AS ROLE")])
        assert role == "test_role"

    def test_show_roles(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        conn.run_query = mocker.MagicMock()
        mocker.patch.object(
            conn.run_query(),
            "fetchall",
            return_value=[
                {"name": "TEST_ROLE", "owner": "SUPERADMIN"},
                {"name": "SUPERADMIN", "owner": "SUPERADMIN"},
            ],
        )

        roles = conn.show_roles()

        conn.run_query.assert_has_calls([mocker.call("SHOW ROLES")])
        assert roles["test_role"] == "superadmin"
        assert roles["superadmin"] == "superadmin"

    def test_show_grants_to_role(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        conn.run_query = mocker.MagicMock()
        mocker.patch.object(
            conn.run_query(),
            "fetchall",
            return_value=[
                {
                    "privilege": "SELECT",
                    "granted_on": "TABLE",
                    "name": "DATABASE_1.SCHEMA_1.TABLE_1",
                },
                {
                    "privilege": "SELECT",
                    "granted_on": "TABLE",
                    "name": "DATABASE_1.SCHEMA_1.TABLE_2",
                },
            ],
        )

        grants = conn.show_grants_to_role("test_role")

        conn.run_query.assert_has_calls([mocker.call("SHOW GRANTS TO ROLE test_role")])
        assert grants == {
            "select": {
                "table": ["database_1.schema_1.table_1", "database_1.schema_1.table_2"]
            }
        }

    def test_show_grants_to_role_quoted_name(self, mocker):
        mocker.patch("sqlalchemy.create_engine")
        conn = SnowflakeConnector()
        conn.run_query = mocker.MagicMock()
        mocker.patch.object(
            conn.run_query(),
            "fetchall",
            return_value=[
                {
                    "privilege": "SELECT",
                    "granted_on": "TABLE",
                    "name": 'DATABASE_1.SCHEMA_1."GROUP"',
                },
                {
                    "privilege": "SELECT",
                    "granted_on": "TABLE",
                    "name": 'DATABASE_1.SCHEMA_1."INTERSECT"',
                },
                {
                    "privilege": "SELECT",
                    "granted_on": "TABLE",
                    "name": 'DATABASE_1.SCHEMA_1."Capitalized_Name"',
                },
                {
                    "privilege": "SELECT",
                    "granted_on": "TABLE",
                    "name": 'DATABASE_1.SCHEMA_1."123_TABLE"',
                },
            ],
        )

        grants = conn.show_grants_to_role("test_role")

        conn.run_query.assert_has_calls([mocker.call("SHOW GRANTS TO ROLE test_role")])
        assert grants == {
            "select": {
                "table": [
                    'database_1.schema_1."GROUP"',
                    'database_1.schema_1."INTERSECT"',
                    'database_1.schema_1."Capitalized_Name"',
                    'database_1.schema_1."123_TABLE"',
                ]
            }
        }
