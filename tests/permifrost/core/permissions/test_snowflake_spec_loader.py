import pytest
import os

from permifrost.core.permissions import SpecLoadingError
from permifrost.core.permissions.snowflake_spec_loader import SnowflakeSpecLoader
from permifrost.core.permissions.utils.snowflake_connector import SnowflakeConnector
from permifrost_test_utils.snowflake_schema_builder import SnowflakeSchemaBuilder
from permifrost_test_utils.snowflake_connector import MockSnowflakeConnector


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_FILE_DIR = os.path.join(THIS_DIR, "specs")
SCHEMA_FILE_DIR = os.path.join(THIS_DIR, "schemas")


def get_spec_from_file(file_name):
    with open(os.path.join(SPEC_FILE_DIR, file_name), "r") as fd:
        spec_data = fd.read()
    return spec_data


@pytest.fixture
def test_dir(request):
    return request.fspath.dirname


@pytest.fixture
def mock_connector():
    return MockSnowflakeConnector()


@pytest.fixture
def test_roles_spec_file():
    """Semi-robust spec file for testing role filtering."""
    spec_file_data = (
        SnowflakeSchemaBuilder()
        .add_user()
        .add_user(name="testuser")
        .add_db(owner="primary", name="primarydb")
        .add_db(owner="secondary", name="secondarydb")
        .add_warehouse(owner="primary", name="primarywarehouse")
        .add_warehouse(owner="secondary", name="secondarywarehouse")
        .add_role()
        .add_role(name="securityadmin")
        .add_role(name="primary")
        .add_role(name="secondary")
        .build()
    )
    yield spec_file_data


@pytest.fixture
def test_grants_roles_mock_connection(mocker, mock_method, return_value):
    mocker.patch("sqlalchemy.create_engine")
    mock_connector = MockSnowflakeConnector()
    mocker.patch.object(
        mock_connector, "get_current_role", return_value="securityadmin"
    )
    mocker.patch.object(mock_connector, "get_current_user", return_value="testuser")
    mocker.patch.object(
        mock_connector,
        "show_warehouses",
        return_value=["primarywarehouse", "secondarywarehouse"],
    )
    mocker.patch.object(
        mock_connector, "show_databases", return_value=["primarydb", "secondarydb"]
    )
    mocker.patch.object(
        mock_connector, "show_roles", return_value=["testrole", "securityadmin"]
    )
    mocker.patch.object(
        mock_connector, "show_users", return_value=["testuser", "testusername"]
    )
    mocker.patch.object(mock_connector, mock_method, return_value=return_value)
    yield mock_connector


@pytest.fixture()
def test_roles_mock_connector(mocker):
    """Mock connector for use in testing role filtering."""

    mock_connector = MockSnowflakeConnector()
    # Connector Mock Madness
    mocker.patch("sqlalchemy.create_engine")
    mocker.patch.object(
        mock_connector, "get_current_role", return_value="securityadmin"
    )
    mocker.patch.object(mock_connector, "get_current_user", return_value="testuser")
    mocker.patch.object(
        mock_connector,
        "show_warehouses",
        return_value=["primarywarehouse", "secondarywarehouse"],
    )
    mocker.patch.object(
        mock_connector, "show_databases", return_value=["primarydb", "secondarydb"]
    )
    mocker.patch.object(
        mock_connector,
        "show_roles",
        return_value=["primary", "secondary", "testrole", "securityadmin"],
    )
    mocker.patch.object(
        mock_connector, "show_users", return_value=["testuser", "testusername"]
    )
    yield mock_connector


class TestSnowflakeSpecLoader:
    # test_check_entities_on_snowflake_server_checks_role_owner
    def enforce_owner_role():
        """
        SnowflakeSchemaBuilder loads correctly with only role and owner attr
        """
        spec_file_data = SnowflakeSchemaBuilder().add_role(owner="user").build()
        method = "show_roles"
        return_value = {"testrole": "user"}

        return [spec_file_data, method, return_value]

    # test_check_entities_on_snowflake_server_checks_role_owner
    def empty_spec_file():
        """
        SnowflakeSchemaBuilder loads correctly with empty spec file
        """
        spec_file_data = SnowflakeSchemaBuilder().set_version("1.0").build()
        method = "show_roles"
        return_value = {"testrole": "none"}

        return [spec_file_data, method, return_value]

    @pytest.mark.parametrize(
        "config",
        [
            enforce_owner_role,
            empty_spec_file,
        ],
    )
    def test_check_entities_on_snowflake_server_checks_role_owner(
        self, config, mocker, mock_connector
    ):
        spec_file_data, method, return_value = config()
        print("Spec file is: ")
        print(spec_file_data)
        mocker.patch("builtins.open", mocker.mock_open(read_data=spec_file_data))
        mocker.patch.object(mock_connector, method, return_value=return_value)
        SnowflakeSpecLoader("", mock_connector)

    # test_check_entities_on_snowflake_server_errors_if_role_owner_does_not_match
    def require_owner_error_handling_case_one():
        """
        Raise error when role owner on Snowflake is different than
        role owner in spec
        """
        spec_file_data = SnowflakeSchemaBuilder().add_role(owner="user").build()
        method = "show_roles"
        return_value = {"testrole": "testuser"}
        expected_error = "Role testrole has owner testuser on snowflake, but has owner user defined in the spec file"

        return [spec_file_data, method, return_value, expected_error]

    def require_owner_error_handling_case_two():
        """
        Role in spec missing on Snowflake
        """
        spec_file_data = SnowflakeSchemaBuilder().add_role(owner="user").build()
        method = "show_roles"
        return_value = {"some-other-role": "none"}
        expected_error = (
            "Missing Entity Error: Role testrole was not found on Snowflake Server"
        )

        return [spec_file_data, method, return_value, expected_error]

    def require_owner_error_handling_case_three():
        """
        Role in spec missing on Snowflake
        """
        spec_file_data = SnowflakeSchemaBuilder().add_role().build()
        method = "show_roles"
        return_value = {}
        expected_error = (
            "Missing Entity Error: Role testrole was not found on Snowflake Server"
        )

        return [spec_file_data, method, return_value, expected_error]

    def require_owner_error_handling_case_four():
        """
        Role in spec missing on Snowflake
        """
        spec_file_data = SnowflakeSchemaBuilder().add_role(owner="user").build()
        method = "show_roles"
        return_value = {}
        expected_error = (
            "Missing Entity Error: Role testrole was not found on Snowflake Server"
        )

        return [spec_file_data, method, return_value, expected_error]

    @pytest.mark.parametrize(
        "config",
        [
            require_owner_error_handling_case_one,
            require_owner_error_handling_case_two,
            require_owner_error_handling_case_three,
            require_owner_error_handling_case_four,
        ],
    )
    def test_check_entities_on_snowflake_server_errors_if_role_owner_does_not_match(
        self,
        config,
        mocker,
        mock_connector,
    ):
        spec_file_data, method, return_value, expected_error = config()
        """
        Error handling for owner functionality:
        """
        print("Spec file is: ")
        print(spec_file_data)
        mocker.patch("builtins.open", mocker.mock_open(read_data=spec_file_data))
        mocker.patch.object(mock_connector, method, return_value=return_value)
        with pytest.raises(SpecLoadingError) as context:
            SnowflakeSpecLoader("", mock_connector)

        assert expected_error in str(context.value)

    # test_check_entities_on_snowflake_server_filters_grants_to_role_to_items_defined_in_config
    def generate_grants_for_spec_roles_case_one():
        """
        Shows FUTURE GRANTS to be applied to the testrole found in the
        tests/permifrost/core/permissions/specs folder which should
        filter out secondarydb grant references as only primarydb is
        cited in the spec file
        """
        mock_method = "show_future_grants"
        spec_file_data = get_spec_from_file(
            "snowflake_server_filters_grants_to_role_to_items_defined_in_config.yml"
        )
        return_value = SnowflakeSchemaBuilder().build_from_file(
            SCHEMA_FILE_DIR,
            "snowflake_server_filters_grants_to_role_to_items_defined_in_config_future_grants.json",
        )
        expected_value = SnowflakeSchemaBuilder().build_from_file(
            SCHEMA_FILE_DIR,
            "snowflake_server_filters_grants_to_role_to_items_defined_in_config_future_grants_expected_values.json",
        )
        return [mock_method, return_value, [spec_file_data, expected_value]]

    # test_check_entities_on_snowflake_server_filters_grants_to_role_to_items_defined_in_config
    def generate_grants_for_spec_roles_case_two():
        """
        Shows GRANTS to be applied to the testrole found in the
        tests/permifrost/core/permissions/specs folder which should
        filter out secondarydb grant references as only primarydb is
        cited in the spec file
        """

        mock_method = "show_grants_to_role"
        spec_file_data = get_spec_from_file(
            "snowflake_server_filters_grants_to_role_to_items_defined_in_config.yml"
        )
        return_value = SnowflakeSchemaBuilder().build_from_file(
            SCHEMA_FILE_DIR,
            "snowflake_server_filters_grants_to_role_to_items_defined_in_config_grants_to_role.json",
        )
        expected_value = SnowflakeSchemaBuilder().build_from_file(
            SCHEMA_FILE_DIR,
            "snowflake_server_filters_grants_to_role_to_items_defined_in_config_grants_to_role_expected_values.json",
        )
        return [mock_method, return_value, [spec_file_data, expected_value]]

    @pytest.mark.parametrize(
        "mock_method,return_value,config",
        [
            generate_grants_for_spec_roles_case_one(),
            generate_grants_for_spec_roles_case_two(),
        ],
    )
    def test_check_entities_on_snowflake_server_filters_grants_to_role_to_items_defined_in_config(
        self, test_grants_roles_mock_connection, mocker, mock_method, config
    ):
        spec_file_data, expected_value = config
        mocker.patch("builtins.open", mocker.mock_open(read_data=spec_file_data))
        spec_loader = SnowflakeSpecLoader(
            spec_path="", conn=test_grants_roles_mock_connection
        )

        assert expected_value == spec_loader.grants_to_role

    @pytest.mark.parametrize(
        "database_refs,warehouse_refs,grant_on,filter_set,expected_value",
        [
            # database filter matches config
            (
                ["db1", "db2", "db3"],
                ["warehouse_doesnt_matter"],
                "database",
                ["db1", "db2", "db3"],
                ["db1", "db2", "db3"],
            ),
            # database filter less objects than config
            (
                ["db1", "db2", "db3"],
                ["warehouse_doesnt_matter"],
                "database",
                ["db1"],
                ["db1"],
            ),
            # database filter more objects than config
            (
                ["db1"],
                ["warehouse_doesnt_matter"],
                "database",
                ["db1", "db2", "db3"],
                ["db1"],
            ),
            # account return passed filter set
            (
                ["database_doesnt_matter"],
                ["warehouse_doesnt_matter"],
                "account",
                ["account1", "account2"],
                ["account1", "account2"],
            ),
            # warehouse filter matches config
            (
                ["database_doesnt_matter"],
                ["warehouse1", "warehouse2", "warehouse3"],
                "warehouse",
                ["warehouse1", "warehouse2", "warehouse3"],
                ["warehouse1", "warehouse2", "warehouse3"],
            ),
            # warehouse filter less than config
            (
                ["database_doesnt_matter"],
                ["warehouse1", "warehouse2", "warehouse3"],
                "warehouse",
                ["warehouse1"],
                ["warehouse1"],
            ),
            # warehouse filter more than config
            (
                ["database_doesnt_matter"],
                ["warehouse1"],
                "warehouse",
                ["warehouse1", "warehouse2", "warehouse3"],
                ["warehouse1"],
            ),
            ###
            # everything else with single config db
            ###
            # filter set without dots
            (
                ["db1"],
                ["warehouse_doesnt_matter"],
                "not_really_relevant",
                ["item1", "item2", "item3"],
                ["item1", "item2", "item3"],
            ),
            # filter set with one level dots
            (
                ["db1"],
                ["warehouse_doesnt_matter"],
                "not_really_relevant",
                ["db1.some_item", "db1.some_item2", "db2.some_item"],
                ["db1.some_item", "db1.some_item2"],
            ),
            # filter set with 3 levels of dots
            (
                ["db1"],
                ["warehouse_doesnt_matter"],
                "not_really_relevant",
                [
                    "db1.some_item.sub_item.sub_sub_item",
                    "db1.some_item.sub_item.sub_sub_item",
                    "db2.some_item.sub_item.sub_sub_item",
                ],
                [
                    "db1.some_item.sub_item.sub_sub_item",
                    "db1.some_item.sub_item.sub_sub_item",
                ],
            ),
            # filter set with 3 levels of dots no matching db
            (
                ["db1"],
                ["warehouse_doesnt_matter"],
                "not_really_relevant",
                [
                    "db2.some_item.sub_item.sub_sub_item",
                    "db2.some_item.sub_item.sub_sub_item",
                    "db2.some_item.sub_item.sub_sub_item",
                ],
                [],
            ),
        ],
    )
    def test_filter_to_database_refs(
        self,
        mocker,
        database_refs,
        warehouse_refs,
        grant_on,
        filter_set,
        expected_value,
    ):
        mocker.patch.object(SnowflakeSpecLoader, "__init__", lambda *args: None)
        spec_loader = SnowflakeSpecLoader("", None)
        spec_loader.entities = {
            "database_refs": database_refs,
            "warehouse_refs": warehouse_refs,
        }
        spec_loader.filter_to_database_refs(grant_on=grant_on, filter_set=filter_set)

    def test_load_spec_loads_file(self, mocker, mock_connector):
        mock_open = mocker.patch(
            "builtins.open", mocker.mock_open(read_data="""version: "1.0" """)
        )
        filepath = "filepath to open"
        SnowflakeSpecLoader(filepath, mock_connector)

        mock_open.assert_called_once_with(filepath, "r")

    def load_spec_with_owner_case_one():
        """
        SnowflakeSpecLoader loads without error for database with owner
        """
        spec_file_data = SnowflakeSchemaBuilder().add_db(owner="user").build()
        method = "show_databases"
        return_value = ["testdb"]

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_two():
        """
        SnowflakeSpecLoader loads without error for role with owner
        """
        spec_file_data = SnowflakeSchemaBuilder().add_role(owner="user").build()
        method = "show_roles"
        return_value = {"testrole": "user"}

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_three():
        """
        SnowflakeSpecLoader loads without error for user with owner
        """
        spec_file_data = SnowflakeSchemaBuilder().add_user(owner="user").build()
        method = "show_users"
        return_value = ["testusername"]

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_four():
        """
        SnowflakeSpecLoader loads without error for warehouse with owner
        """
        spec_file_data = SnowflakeSchemaBuilder().add_warehouse(owner="user").build()
        method = "show_warehouses"
        return_value = ["testwarehouse"]

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_five():
        """
        SnowflakeSpecLoader loads without error for database with owner
        and require-owner: True
        """
        spec_file_data = (
            SnowflakeSchemaBuilder().require_owner().add_db(owner="user").build()
        )
        method = "show_databases"
        return_value = ["testdb"]

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_six():
        """
        SnowflakeSpecLoader loads without error for role with owner
        and require-owner: True
        """
        spec_file_data = (
            SnowflakeSchemaBuilder().require_owner().add_role(owner="user").build()
        )
        method = "show_roles"
        return_value = {"testrole": "user"}

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_seven():
        """
        SnowflakeSpecLoader loads without error for user with owner
        and require-owner: True
        """
        spec_file_data = (
            SnowflakeSchemaBuilder().require_owner().add_user(owner="user").build()
        )
        method = "show_users"
        return_value = ["testusername"]

        return [spec_file_data, method, return_value]

    def load_spec_with_owner_case_eight():
        """
        SnowflakeSpecLoader loads without error for warehouse with owner
        and require-owner: True
        """
        spec_file_data = (
            SnowflakeSchemaBuilder().require_owner().add_warehouse(owner="user").build()
        )
        method = "show_warehouses"
        return_value = ["testwarehouse"]

        return [spec_file_data, method, return_value]

    @pytest.mark.parametrize(
        "config",
        [
            load_spec_with_owner_case_one,
            load_spec_with_owner_case_two,
            load_spec_with_owner_case_three,
            load_spec_with_owner_case_four,
            load_spec_with_owner_case_five,
            load_spec_with_owner_case_six,
            load_spec_with_owner_case_seven,
            load_spec_with_owner_case_eight,
        ],
    )
    def test_load_spec_with_owner(
        self,
        config,
        mocker,
        mock_connector,
    ):
        spec_file_data, method, return_value = config()
        print("Spec file is: ")
        print(spec_file_data)
        mocker.patch("builtins.open", mocker.mock_open(read_data=spec_file_data))
        mocker.patch.object(mock_connector, method, return_value=return_value)
        SnowflakeSpecLoader("", mock_connector)

    # test_load_spec_owner_required_with_no_owner
    def load_spec_file_error_case_one():
        """
        Raise 'Owner not defined' error on show_databases
        with no owner and require-owner = True
        """
        spec_file_data = SnowflakeSchemaBuilder().require_owner().add_db().build()
        method = "show_databases"
        return_value = ["testdb"]
        return [spec_file_data, method, return_value]

    # test_load_spec_owner_required_with_no_owner
    def load_spec_file_error_case_two():
        """
        Raise 'Owner not defined' error on show_roles
        with no owner and require-owner = True
        """
        spec_file_data = SnowflakeSchemaBuilder().require_owner().add_role().build()
        method = "show_roles"
        return_value = ["testrole"]
        return [spec_file_data, method, return_value]

    # test_load_spec_owner_required_with_no_owner
    def load_spec_file_error_case_three():
        """
        Raise 'Owner not defined' error on show_users
        with no owner and require-owner = True
        """
        spec_file_data = SnowflakeSchemaBuilder().require_owner().add_user().build()
        method = "show_users"
        return_value = ["testusername"]
        return [spec_file_data, method, return_value]

    # test_load_spec_owner_required_with_no_owner
    def load_spec_file_error_case_four():
        """
        Raise 'Owner not defined' error on show_warehouses
        with no owner and require-owner = True
        """
        spec_file_data = (
            SnowflakeSchemaBuilder().require_owner().add_warehouse().build()
        )
        method = "show_warehouses"
        return_value = ["testwarehouse"]
        return [spec_file_data, method, return_value]

    @pytest.mark.parametrize(
        "config",
        [
            load_spec_file_error_case_one,
            load_spec_file_error_case_two,
            load_spec_file_error_case_three,
            load_spec_file_error_case_four,
        ],
    )
    def test_load_spec_owner_required_with_no_owner(
        self,
        config,
        mocker,
        mock_connector,
    ):
        spec_file_data, method, return_value = config()
        print("Spec file is: ")
        print(spec_file_data)
        mocker.patch("builtins.open", mocker.mock_open(read_data=spec_file_data))
        mocker.patch.object(mock_connector, method, return_value=return_value)
        with pytest.raises(SpecLoadingError) as context:
            SnowflakeSpecLoader("", mock_connector)

        assert "Spec Error: Owner not defined" in str(context.value)

    def test_generate_permission_queries_with_requires_owner(
        self, mocker, mock_connector
    ):
        """
        Generate no permissions for empty spec with require-owner: True
        """
        spec_file_data = (
            SnowflakeSchemaBuilder().set_version("1.0").require_owner().build()
        )
        print("Spec file is: ")
        print(spec_file_data)
        mocker.patch("builtins.open", mocker.mock_open(read_data=spec_file_data))
        spec_loader = SnowflakeSpecLoader("", mock_connector)
        queries = spec_loader.generate_permission_queries()

        assert [] == queries

    def test_role_filter(self, mocker, test_roles_mock_connector, test_roles_spec_file):
        """GRANT queries list filtered by role."""

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)
        results = spec_loader.generate_permission_queries(
            roles=["primary"], run_list=["roles"]
        )
        expected = [
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role primary"}
        ]
        assert results == expected

    def test_role_filter_multiple(
        self, mocker, test_roles_mock_connector, test_roles_spec_file
    ):
        """Make sure that the GRANT queries list can be filtered by multiple roles."""

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)
        results = spec_loader.generate_permission_queries(
            roles=["primary", "secondary"], run_list=["roles"]
        )
        expected_results = [
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role primary"},
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role secondary"},
        ]
        assert results == expected_results

    def test_role_filter_and_user_filter(
        self, mocker, test_roles_mock_connector, test_roles_spec_file
    ):
        """
        Make sure that the grant queries list can be filtered by
        multiple roles and a single user ignores the user
        """

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)
        results = spec_loader.generate_permission_queries(
            roles=["primary", "secondary"],
            users=["testusername"],
            run_list=["roles", "users"],
        )
        expected_results = [
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role primary"},
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role secondary"},
            {
                "already_granted": False,
                "sql": "ALTER USER testusername SET DISABLED = FALSE",
            },
        ]
        assert results == expected_results

    def test_no_role_or_user_filter(
        self, mocker, test_roles_mock_connector, test_roles_spec_file
    ):
        """Test that the generate_permissions_query does no filtering on when users and roles are not defined."""

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)

        expected_sql_queries = [
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role testrole"},
            {
                "already_granted": False,
                "sql": "GRANT ROLE testrole TO role securityadmin",
            },
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role primary"},
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role secondary"},
            {
                "already_granted": False,
                "sql": "ALTER USER testusername SET DISABLED = FALSE",
            },
            {
                "already_granted": False,
                "sql": "ALTER USER testuser SET DISABLED = FALSE",
            },
        ]

        assert spec_loader.generate_permission_queries() == expected_sql_queries

    def test_user_filter(self, mocker, test_roles_mock_connector, test_roles_spec_file):
        """Make sure that the grant queries list can be filtered by user."""

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)
        assert spec_loader.generate_permission_queries(
            users=["testusername"], run_list=["users"]
        ) == [
            {
                "already_granted": False,
                "sql": "ALTER USER testusername SET DISABLED = FALSE",
            }
        ]

    def test_user_filter_multiple(
        self, mocker, test_roles_mock_connector, test_roles_spec_file
    ):
        """Make sure that the grant queries list can be filtered by multiple users."""

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)
        results = spec_loader.generate_permission_queries(
            users=["testusername", "testuser"], run_list=["users"]
        )
        expected_results = [
            {
                "already_granted": False,
                "sql": "ALTER USER testusername SET DISABLED = FALSE",
            },
            {
                "already_granted": False,
                "sql": "ALTER USER testuser SET DISABLED = FALSE",
            },
        ]
        assert results == expected_results

    def test_user_filter_and_roles_filter(
        self, mocker, test_roles_mock_connector, test_roles_spec_file
    ):
        """Make sure that the grant queries list can be filtered by multiple users and a single role ignores the role"""

        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        spec_loader = SnowflakeSpecLoader(spec_path="", conn=test_roles_mock_connector)
        results = spec_loader.generate_permission_queries(
            users=["testusername", "testuser"],
            roles=["primary"],
            run_list=["roles", "users"],
        )
        expected_results = [
            {"already_granted": False, "sql": "GRANT ROLE testrole TO role primary"},
            {
                "already_granted": False,
                "sql": "ALTER USER testusername SET DISABLED = FALSE",
            },
            {
                "already_granted": False,
                "sql": "ALTER USER testuser SET DISABLED = FALSE",
            },
        ]
        assert results == expected_results

    def test_remove_duplicate_queries(self):

        sql_command_1 = {"sql": "GRANT OWNERSHIP ON SCHEMA PIZZA TO ROLE LIZZY"}
        sql_command_2 = sql_command_1.copy()
        sql_command_3 = {"sql": "REVOKE ALL PRIVILEGES ON SCHEMA PIZZA FROM ROLE LIZZY"}
        sql_command_4 = sql_command_3.copy()

        result = SnowflakeSpecLoader.remove_duplicate_queries(
            [sql_command_1, sql_command_2, sql_command_3, sql_command_4]
        )
        assert result == [sql_command_1, sql_command_3]


class TestGetPrivilegesFromSnowflakeServer:
    def users_with_users_roles_run_list():
        """Only users with full run_list"""
        users = ["testusername", "testuser"]
        roles = []
        run_list = ["roles", "users"]
        expected_calls = [
            ("get_role_privileges_from_snowflake_server", 1, {}),
            (
                "get_user_privileges_from_snowflake_server",
                1,
                {"users": ["testusername", "testuser"]},
            ),
        ]
        return [users, roles, run_list, expected_calls]

    def roles_with_users_roles_run_list():
        """Only Roles passed with full run_list"""
        users = []
        roles = ["primary"]
        run_list = ["roles", "users"]
        expected_calls = [
            (
                "get_role_privileges_from_snowflake_server",
                1,
                {"roles": ["primary"], "ignore_memberships": False},
            ),
            ("get_user_privileges_from_snowflake_server", 1, {"users": []}),
        ]
        return [users, roles, run_list, expected_calls]

    def users_roles_with_users_run_list():
        """Users and roles passed but roles not in run_list"""
        users = ["testusername", "testuser"]
        roles = ["primary"]
        run_list = ["users"]
        expected_calls = [
            ("get_role_privileges_from_snowflake_server", 0, {}),
            (
                "get_user_privileges_from_snowflake_server",
                1,
                {"users": ["testusername", "testuser"]},
            ),
        ]
        return [users, roles, run_list, expected_calls]

    def users_roles_with_roles_run_list():
        """Users and roles passed but users not in run_list"""
        users = ["testusername", "testuser"]
        roles = ["primary"]
        run_list = ["roles"]
        expected_calls = [
            (
                "get_role_privileges_from_snowflake_server",
                1,
                {"roles": ["primary"], "ignore_memberships": False},
            ),
            ("get_user_privileges_from_snowflake_server", 0, {}),
        ]
        return [users, roles, run_list, expected_calls]

    def users_with_users_run_list():
        """Only Users passed with only users in run_list"""
        users = ["testusername", "testuser"]
        roles = []
        run_list = ["users"]
        expected_calls = [
            ("get_role_privileges_from_snowflake_server", 0, {}),
            (
                "get_user_privileges_from_snowflake_server",
                1,
                {"users": ["testusername", "testuser"]},
            ),
        ]
        return [users, roles, run_list, expected_calls]

    def roles_with_roles_run_list():
        """Only Roles passed with only roles in run_list"""
        users = []
        roles = ["primary"]
        run_list = ["roles"]
        expected_calls = [
            (
                "get_role_privileges_from_snowflake_server",
                1,
                {"roles": ["primary"], "ignore_memberships": False},
            ),
            ("get_user_privileges_from_snowflake_server", 0, {}),
        ]
        return [users, roles, run_list, expected_calls]

    def users_roles_with_users_roles_run_list():
        """Users and Roles passed with users and roles in run_list"""
        users = ["testusername", "testuser"]
        roles = ["primary"]
        run_list = ["roles", "users"]
        expected_calls = [
            (
                "get_role_privileges_from_snowflake_server",
                1,
                {"roles": ["primary"], "ignore_memberships": False},
            ),
            (
                "get_user_privileges_from_snowflake_server",
                1,
                {"users": ["testusername", "testuser"]},
            ),
        ]
        return [users, roles, run_list, expected_calls]

    def users_roles_with_empty_run_list():
        """Users and Roles passed with empty list run_list"""
        users = ["testusername", "testuser"]
        roles = ["primary"]
        run_list = []
        expected_calls = [
            (
                "get_role_privileges_from_snowflake_server",
                1,
                {"roles": ["primary"], "ignore_memberships": False},
            ),
            (
                "get_user_privileges_from_snowflake_server",
                1,
                {"users": ["testusername", "testuser"]},
            ),
        ]
        return [users, roles, run_list, expected_calls]

    def users_and_roles_with_none_run_list():
        """Users and Roles passed and run_list == None"""
        users = ["testusername", "testuser"]
        roles = ["primary"]
        run_list = None
        expected_calls = [
            (
                "get_role_privileges_from_snowflake_server",
                1,
                {"roles": ["primary"], "ignore_memberships": False},
            ),
            (
                "get_user_privileges_from_snowflake_server",
                1,
                {"users": ["testusername", "testuser"]},
            ),
        ]
        return [users, roles, run_list, expected_calls]

    @pytest.mark.parametrize(
        "config",
        [
            users_with_users_roles_run_list,
            roles_with_users_roles_run_list,
            users_roles_with_users_run_list,
            users_roles_with_roles_run_list,
            users_with_users_run_list,
            roles_with_roles_run_list,
            users_roles_with_users_roles_run_list,
            users_roles_with_empty_run_list,
            users_and_roles_with_none_run_list,
        ],
    )
    def test_get_privileges_from_snowflake_server(
        self,
        mocker,
        test_roles_mock_connector,
        test_roles_spec_file,
        config,
    ):
        """Verify correct calls when getting privs from server:"""
        users, roles, run_list, expected_calls = config()
        print(f"Spec File Data is:\n{test_roles_spec_file}")
        mocker.patch("builtins.open", mocker.mock_open(read_data=test_roles_spec_file))
        mock_get_role_privileges_from_snowflake_server = mocker.patch.object(
            SnowflakeSpecLoader,
            "get_role_privileges_from_snowflake_server",
            return_value=None,
        )
        mock_get_user_privileges_from_snowflake_server = mocker.patch.object(
            SnowflakeSpecLoader,
            "get_user_privileges_from_snowflake_server",
            return_value=None,
        )
        SnowflakeSpecLoader(
            spec_path="",
            conn=test_roles_mock_connector,
            users=users,
            roles=roles,
            run_list=run_list,
        )
        for method, call_count, arguments in expected_calls:
            if method == "get_role_privileges_from_snowflake_server":
                assert (
                    mock_get_role_privileges_from_snowflake_server.call_count
                    == call_count
                )
                if arguments:
                    mock_get_role_privileges_from_snowflake_server.assert_called_with(
                        conn=test_roles_mock_connector, **arguments
                    )
            if method == "get_user_privileges_from_snowflake_server":
                assert (
                    mock_get_user_privileges_from_snowflake_server.call_count
                    == call_count
                )
                if arguments:
                    mock_get_user_privileges_from_snowflake_server.assert_called_with(
                        conn=test_roles_mock_connector, **arguments
                    )


class TestSpecFileLoading:
    def test_check_entities_on_snowflake_server_no_warehouses(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "show_warehouses")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.show_warehouses.assert_not_called()

    def test_check_entities_on_snowflake_server_no_databases(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "show_databases")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.show_databases.assert_not_called()

    def test_check_entities_on_snowflake_server_no_schemas(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "show_schemas")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.show_schemas.assert_not_called()

    def test_check_entities_on_snowflake_server_no_tables(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "show_tables")
        mocker.patch.object(mock_connector, "show_views")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.show_tables.assert_not_called()
        mock_connector.show_views.assert_not_called()

    def test_check_entities_on_snowflake_server_no_roles(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "show_roles")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.show_roles.assert_not_called()

    def test_check_entities_on_snowflake_server_no_users(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "show_users")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.show_users.assert_not_called()

    def test_check_permissions_on_snowflake_server_as_securityadmin(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(
            MockSnowflakeConnector, "get_current_role", return_value="securityadmin"
        )
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.get_current_role.assert_called()

    def test_check_permissions_on_snowflake_server_not_as_securityadmin(
        self, test_dir, mocker, mock_connector
    ):
        """
        Validates that an error is raised if not using SECURITYADMIN
        """
        mocker.patch.object(
            MockSnowflakeConnector, "get_current_role", return_value="notsecurityadmin"
        )
        with pytest.raises(SpecLoadingError):
            SnowflakeSpecLoader(
                os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"),
                mock_connector,
            )
            mock_connector.get_current_role.assert_called()

    def test_check_permissions_on_snowflake_server_gets_current_user_info(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(mock_connector, "get_current_user")
        SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_blank.yml"), mock_connector
        )
        mock_connector.get_current_user.assert_called()

    def test_edge_case_entities_generate_correct_statements(
        self, test_dir, mocker, mock_connector
    ):
        mocker.patch.object(
            SnowflakeSpecLoader, "check_entities_on_snowflake_server", return_value=None
        )
        mocker.patch(
            "permifrost.core.permissions.utils.snowflake_connector.SnowflakeConnector",
            MockSnowflakeConnector,
        )
        mocker.patch.object(SnowflakeConnector, "__init__", lambda x: None)
        spec_loader = SnowflakeSpecLoader(
            os.path.join(test_dir, "specs", "snowflake_spec_edge_cases.yml"),
            mock_connector,
        )
        mocker.patch.object(
            SnowflakeConnector,
            "show_tables",
            return_value=[],
        )
        mocker.patch.object(
            SnowflakeConnector,
            "show_views",
            return_value=[],
        )

        expected = [
            "ALTER USER first.last SET DISABLED = FALSE",
            "GRANT OWNERSHIP ON database database_1 TO ROLE test_role COPY CURRENT GRANTS",
            "GRANT OWNERSHIP ON database shared_database_1 TO ROLE test_role COPY CURRENT GRANTS",
            "GRANT OWNERSHIP ON schema database_1.schema_1 TO ROLE test_role COPY CURRENT GRANTS",
            "GRANT OWNERSHIP ON table database_1.schema_1.table_1 TO ROLE test_role COPY CURRENT GRANTS",
            "GRANT ROLE test_role TO user first.last",
            "GRANT monitor ON warehouse warehouse_1 TO ROLE test_role",
            "GRANT operate ON warehouse warehouse_1 TO ROLE test_role",
            "GRANT usage ON database database_1 TO ROLE test_role",
            "GRANT usage ON schema database_1.read_only_schema TO ROLE test_role",
            "GRANT usage ON schema database_1.write_schema TO ROLE test_role",
            "GRANT usage ON warehouse warehouse_1 TO ROLE test_role",
            "GRANT usage, monitor, create schema ON database database_1 TO ROLE test_role",
            "GRANT usage, monitor, create table, create view, create stage, create file format, create sequence, create function, create pipe ON schema database_1.write_schema TO ROLE test_role",
        ]

        mocker.patch.object(SnowflakeConnector, "show_views", return_value=[])
        sql_queries = spec_loader.generate_permission_queries()
        results = [cmd.get("sql", "") for cmd in sql_queries]
        results.sort()

        assert results == expected
