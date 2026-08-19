"""商品大数据 MCP 服务离线测试。"""

import asyncio
import importlib.util
import json
import os
from hashlib import md5
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch


SERVER_PATH = Path(__file__).parents[1] / "server" / "mcp_server.py"
SPEC = importlib.util.spec_from_file_location("goods_mcp_server", SERVER_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class GatewayTests(TestCase):
    def test_missing_credentials_prevents_http_request(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(server.requests, "post") as post,
        ):
            result = server.call_api("product", {"query": "test"})

        self.assertEqual(result, {"error": "INTEGRATOR_ID 未配置"})
        post.assert_not_called()

    def test_signature_request_and_empty_data_are_preserved(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"data": {}}
        credentials = {
            "INTEGRATOR_ID": "integrator",
            "SECRET_ID": "secret-id",
            "SECRET_KEY": "secret-key",
            "HANDAAS_REQUEST_TIMEOUT": "12",
        }

        with (
            patch.dict(os.environ, credentials, clear=True),
            patch.object(server.requests, "post", return_value=response) as post,
        ):
            result = server.call_api("product", {"query": "商品", "unused": None})

        self.assertEqual(result, {})
        params_json = json.dumps(
            {"query": "商品"},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        expected_signature = md5(
            f"{params_json}productsecret-idsecret-key".encode("utf-8")
        ).hexdigest()
        post.assert_called_once_with(
            f"{server.GATEWAY_BASE_URL}/integrator",
            data={
                "product_id": "product",
                "secret_id": "secret-id",
                "params": params_json,
                "signature": expected_signature,
            },
            timeout=12.0,
        )

    def test_http_error_does_not_expose_response_body(self) -> None:
        response = Mock(status_code=503, text="sensitive upstream response")
        credentials = {
            "INTEGRATOR_ID": "integrator",
            "SECRET_ID": "secret-id",
            "SECRET_KEY": "secret-key",
        }
        with (
            patch.dict(os.environ, credentials, clear=True),
            patch.object(server.requests, "post", return_value=response),
        ):
            result = server.call_api("product", {})

        self.assertEqual(
            result,
            {"error": "HandaaS 网关返回非成功状态", "statusCode": 503},
        )
        self.assertNotIn("sensitive", str(result))


class ToolTests(TestCase):
    REMOVED_THIRD_PARTY_PRODUCT_IDS = {
        "684ad781d4819127431f9fe1",
        "684ad781d4819127431f9ff8",
        "684ad781d4819127431fa016",
        "684ad781d4819127431fa026",
    }

    def test_registered_tool_names(self) -> None:
        tools = asyncio.run(server.mcp.list_tools())
        self.assertEqual(
            {tool.name for tool in tools},
            {
                "goods_enterprise_search",
                "goods_search",
                "goods_enterprise_products",
                "goods_overseas_store_products",
                "goods_brand",
                "goods_channel",
            },
        )
        for tool in tools:
            self.assertEqual(tool.outputSchema.get("type"), "object")
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.destructiveHint)

    def test_enterprise_search_resolves_abbreviated_company_names(self) -> None:
        with patch.object(
            server,
            "call_api",
            return_value={"total": 1, "resultList": [{"name": "企业A全称"}]},
        ) as call:
            result = server.goods_enterprise_search("企业A", pageSize=5)
        self.assertEqual(result["total"], 1)
        call.assert_called_once_with(
            server.PRODUCT_IDS["enterprise_search"],
            {"matchKeyword": "企业A", "pageIndex": 1, "pageSize": 5},
        )

        with patch.object(server, "call_api") as call:
            invalid = server.goods_enterprise_search("企业A", pageSize=51)
        self.assertEqual(invalid["parameter"], "pageSize")
        call.assert_not_called()

    def test_search_routes_one_product_per_call(self) -> None:
        with patch.object(
            server,
            "call_api",
            return_value={"dataTotal": 12, "resultList": [{"name": "咖啡"}]},
        ) as call:
            result = server.goods_search(matchKeyword="咖啡")
        self.assertEqual(
            result,
            {"total": 12, "resultList": [{"name": "咖啡"}]},
        )
        call.assert_called_once_with(
            server.PRODUCT_IDS["retail_search"],
            {"matchKeyword": "咖啡", "pageIndex": 1, "pageSize": 10},
        )

        with patch.object(
            server,
            "call_api",
            return_value={"total": 3, "resultList": []},
        ) as call:
            result = server.goods_search(
                matchKeyword="coffee",
                source="overseas",
                eshopSource="亚马逊",
            )
        self.assertEqual(result, {"total": 3, "resultList": []})
        call.assert_called_once_with(
            server.PRODUCT_IDS["overseas_search"],
            {
                "matchKeyword": "coffee",
                "eshopSource": "亚马逊",
                "eshopCategories": None,
                "eshopSalesLevel": None,
                "operationStatus": "全部",
                "hasAssociateEnterprise": "全部",
                "pageIndex": 1,
                "pageSize": 50,
            },
        )

    def test_enterprise_product_sources_route_one_product_per_call(self) -> None:
        with patch.object(
            server,
            "call_api",
            return_value={"total": 1, "resultList": [{"commodityName": "手机"}]},
        ) as call:
            result = server.goods_enterprise_products("企业A")
        self.assertEqual(
            result,
            {"total": 1, "resultList": [{"commodityName": "手机"}]},
        )
        call.assert_called_once_with(
            server.PRODUCT_IDS["enterprise_retail_products"],
            {
                "matchKeyword": "企业A",
                "keywordType": "name",
                "pageIndex": 1,
                "pageSize": 10,
            },
        )

        with patch.object(server, "call_api", return_value={}) as call:
            server.goods_enterprise_products("企业A", productType="ecommerce")
        call.assert_called_once_with(
            server.PRODUCT_IDS["enterprise_ecommerce_products"],
            {
                "matchKeyword": "企业A",
                "keywordType": "name",
                "pageIndex": 1,
                "pageSize": 50,
            },
        )

    def test_overseas_store_products_have_a_dedicated_tool(self) -> None:
        with patch.object(
            server,
            "call_api",
            return_value={
                "productCount": 3,
                "productList": [{"id": 1}, {"id": 2}, {"id": 3}],
            },
        ) as call:
            result = server.goods_overseas_store_products(
                "shop-1", pageIndex=2, pageSize=2
            )
        self.assertEqual(result, {"total": 3, "resultList": [{"id": 3}]})
        call.assert_called_once_with(
            server.PRODUCT_IDS["overseas_store_products"],
            {"matchKeyword": "shop-1"},
        )

    def test_brand_routes_one_product_per_call(self) -> None:
        with patch.object(server, "call_api", return_value={}) as call:
            server.goods_brand("企业A", view="product_overview")
        call.assert_called_once_with(
            server.PRODUCT_IDS["brand_product_overview"],
            {"matchKeyword": "企业A", "keywordType": "name"},
        )

    def test_channel_routes_one_product_per_call(self) -> None:
        with patch.object(server, "call_api", return_value={}) as call:
            server.goods_channel("企业A", source="global_store")
        call.assert_called_once_with(
            server.PRODUCT_IDS["global_store_channel"],
            {"matchKeyword": "企业A", "keywordType": "name"},
        )

    def test_pagination_validation_blocks_invalid_request(self) -> None:
        with patch.object(server, "call_api") as call:
            result = server.goods_search(pageSize=51)
        self.assertEqual(result["parameter"], "pageSize")
        call.assert_not_called()

    def test_enterprise_retail_page_size_is_limited_to_ten(self) -> None:
        with patch.object(server, "call_api") as call:
            result = server.goods_enterprise_products("企业A", pageSize=11)
        self.assertEqual(result["parameter"], "pageSize")
        self.assertIn("1 到 10", result["error"])
        call.assert_not_called()

        with patch.object(server, "call_api", return_value={}) as call:
            server.goods_enterprise_products(
                "企业A", productType="ecommerce", pageSize=50
            )
        call.assert_called_once()

    def test_removed_third_party_products_are_not_routable(self) -> None:
        self.assertTrue(
            self.REMOVED_THIRD_PARTY_PRODUCT_IDS.isdisjoint(
                server.PRODUCT_IDS.values()
            )
        )
        self.assertEqual(
            server.PRODUCT_IDS["enterprise_retail_products"],
            "6a62157cb050fd2d69e9f7ff",
        )

    def test_invalid_transport_is_rejected_without_starting_server(self) -> None:
        with patch.object(server.mcp, "run") as run:
            result = server.main(["websocket"])
        self.assertEqual(result, 2)
        run.assert_not_called()


class DocumentationTests(TestCase):
    def test_readme_matches_redesigned_tools_and_products(self) -> None:
        readme = (SERVER_PATH.parents[1] / "README.md").read_text(encoding="utf-8")
        for tool_name in (
            "goods_enterprise_search",
            "goods_search",
            "goods_enterprise_products",
            "goods_overseas_store_products",
            "goods_brand",
            "goods_channel",
        ):
            self.assertIn(f"`{tool_name}`", readme)
        self.assertIn("6a62157cb050fd2d69e9f7ff", readme)
        for product_id in ToolTests.REMOVED_THIRD_PARTY_PRODUCT_IDS:
            self.assertNotIn(product_id, readme)
        self.assertNotIn("`goods_price`", readme)
        self.assertNotIn("`goods_trend`", readme)
