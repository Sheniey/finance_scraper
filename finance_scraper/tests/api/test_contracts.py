 
from api.main import app


def test_api_exposes_only_the_requested_endpoints() -> None:
    paths: dict[str, dict[str, object]] = app.openapi()['paths']
    expected: dict[str, set[str]] = {
        '/auth/register': {'post'},
        '/auth/login': {'post'},
        '/auth/logout': {'post'},
        '/auth/refresh': {'post'},
        '/accounts': {'get', 'post'},
        '/accounts/{uuid}': {'get', 'put', 'delete'},
        '/accounts/me': {'get', 'put', 'delete'},
        '/accounts/me/change-password': {'post'},
        '/desktop/health': {'get'},
        '/desktop/shutdown': {'post'},
        '/integrations/google/authorize': {'post'},
        '/integrations/google/callback/{flow_id}': {'get'},
        '/integrations/google/status': {'get', 'delete'},
        '/reports': {'get', 'post', 'delete'},
        '/reports/{report_id}': {'get', 'delete'},
        '/reports/{report_id}/download': {'get'},
        '/reports/run-watchlist': {'post'},
        '/reports/me': {'get', 'post'},
        '/reports/me/run-watchlist': {'post'},
        '/schedules/me': {'get', 'post'},
        '/schedules/me/{schedule_id}': {'patch', 'delete'},
        '/schedules/desktop/{schedule_id}/run': {'post'},
        '/schedules/desktop/run-due': {'post'},
        '/schedules/desktop/registry': {'get'},
    }

    assert {
        path: set(operations)
        for path, operations in paths.items()
    } == expected
    for operations in paths.values():
        for operation in operations.values():
            assert operation['summary']
            assert operation['responses']


def test_api_documents_json_login_bearer_auth_and_collection_parameters() -> None:
    schema: dict[str, object] = app.openapi()
    paths = schema['paths']
    login_operation = paths['/auth/login']['post']
    account_list_operation = paths['/accounts']['get']
    report_create_operation = paths['/reports']['post']
    account_parameters = {
        parameter['name']
        for parameter in account_list_operation['parameters']
    }

    assert 'application/json' in login_operation['requestBody']['content']
    assert schema['components']['securitySchemes']['BearerAuth'] == {
        'type': 'http',
        'scheme': 'bearer',
    }
    assert {
        'page',
        'page_size',
        'page_cursor',
        'fields',
        'sort',
        'filter',
    }.issubset(account_parameters)
    report_schema_reference: str = report_create_operation['requestBody'][
        'content'
    ]['application/json']['schema']['$ref']
    report_schema_name: str = report_schema_reference.rsplit('/', maxsplit=1)[-1]
    report_properties = schema['components']['schemas'][
        report_schema_name
    ]['properties']
    assert {'ticker', 'filename'} <= report_properties.keys()
    assert 'requested_symbol' not in report_properties
    assert 'to' not in report_properties
