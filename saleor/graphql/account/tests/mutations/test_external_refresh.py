import json
from unittest.mock import Mock, patch

from freezegun import freeze_time

from .....plugins.base_plugin import ExternalAccessTokens
from ....tests.utils import get_graphql_content

MUTATION_EXTERNAL_REFRESH = """
    mutation externalRefresh($pluginId: String!, $input: JSONString!){
        externalRefresh(pluginId: $pluginId, input: $input){
            token
            refreshToken
            csrfToken
            user{
                email
            }
            errors{
                field
                message
            }
        }
}
"""


def test_external_refresh_plugin_not_active(api_client, customer_user):
    variables = {"pluginId": "pluginId1", "input": json.dumps({"refreshToken": "ABCD"})}
    response = api_client.post_graphql(MUTATION_EXTERNAL_REFRESH, variables)
    content = get_graphql_content(response)
    data = content["data"]["externalRefresh"]
    assert data["token"] is None
    assert data["refreshToken"] is None
    assert data["csrfToken"] is None
    assert data["user"] is None


@freeze_time("2018-05-31 12:00:00")
@patch("saleor.core.middleware.jwt_decode_with_exception_handler")
def test_external_refresh(
    mock_refresh_token_middleware, api_client, customer_user, monkeypatch, rf
):
    expected_token = "token1"
    expected_refresh_token = "refresh2"
    expected_csrf_token = "csrf3"
    mocked_plugin_fun = Mock()
    expected_return = ExternalAccessTokens(
        token=expected_token,
        refresh_token=expected_refresh_token,
        csrf_token=expected_csrf_token,
        user=customer_user,
    )
    mocked_plugin_fun.return_value = expected_return
    monkeypatch.setattr(
        "saleor.plugins.manager.PluginsManager.external_refresh", mocked_plugin_fun
    )
    variables = {"pluginId": "pluginId1", "input": json.dumps({"refreshToken": "ABCD"})}
    response = api_client.post_graphql(MUTATION_EXTERNAL_REFRESH, variables)
    content = get_graphql_content(response)
    data = content["data"]["externalRefresh"]
    assert data["token"] == expected_token
    assert data["refreshToken"] == expected_refresh_token
    assert data["csrfToken"] == expected_csrf_token
    assert data["user"]["email"] == customer_user.email
    assert customer_user.last_login
    last_login = customer_user.last_login.strftime("%Y-%m-%d %H:%M:%S")
    assert last_login == "2018-05-31 12:00:00"
    assert mocked_plugin_fun.called
    assert mock_refresh_token_middleware.called
