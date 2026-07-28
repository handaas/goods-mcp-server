"""HandaaS 商品大数据 MCP 服务。"""

import json
import os
import sys
from hashlib import md5
from typing import Any, Literal
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


load_dotenv()

mcp = FastMCP(
    "商品大数据",
    instructions=(
        "面向选品、竞品、品牌、价格、渠道和销售趋势分析。"
        "组合场景通过 source 参数选择一个上游数据源，单次工具调用不会默认触发多个计费接口。"
    ),
    dependencies=["python-dotenv", "requests"],
)

GATEWAY_BASE_URL = "https://console.handaas.com/api/v1/integrator/call_api"
DEFAULT_TIMEOUT_SECONDS = 30.0

PRODUCT_IDS = {
    "retail_search": "6a609f509d30d4fcc00ccff5",
    "overseas_search": "66c9a954268e9d7292c1a9ab",
    "domestic_product_profile": "66c33eff3c0917a9a02feb9d",
    "overseas_product_profile": "66d5b7e0537c3f61d646c496",
    "brand_detail": "66c702b725f04ab44cd24d5e",
    "brand_product_overview": "66d5b7e1537c3f61d646c573",
    "store_top_items": "684ad781d4819127431f9fe1",
    "enterprise_monthly_sales": "684ad781d4819127431fa026",
    "domestic_store_channel": "66c702b725f04ab44cd24c83",
    "global_store_channel": "672b3125338beb3ec2f5dc43",
    "store_monthly_sales": "684ad781d4819127431f9ff8",
    "enterprise_cumulative_sales": "684ad781d4819127431fa016",
}

KeywordType = Literal["name", "nameId", "regNumber", "socialCreditCode"]
READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _request_timeout() -> float:
    """读取请求超时配置，非法值回退为默认值。"""
    raw_value = os.environ.get("HANDAAS_REQUEST_TIMEOUT", "")
    try:
        value = float(raw_value) if raw_value else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def _credential(name: str) -> str | None:
    """读取并清理认证配置。"""
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("your_"):
        return None
    return value


def _build_signature(call_params: dict[str, str], secret_key: str) -> str:
    """按 HandaaS Integrator Gateway 规则生成 MD5 签名。"""
    plain_text = "".join(str(call_params[key]) for key in sorted(call_params))
    return md5(f"{plain_text}{secret_key}".encode("utf-8")).hexdigest()


def _compact_params(params: dict[str, Any]) -> dict[str, Any]:
    """移除未提供的可选参数，保留 0、False 和空字符串等有效值。"""
    return {key: value for key, value in params.items() if value is not None}


def _pagination_error(page_index: int, page_size: int) -> dict[str, Any] | None:
    """校验 HandaaS 分页公共约束。"""
    if page_index < 1:
        return {"error": "pageIndex 必须大于等于 1", "parameter": "pageIndex"}
    if page_size < 1 or page_size > 50:
        return {
            "error": "pageSize 必须在 1 到 50 之间",
            "parameter": "pageSize",
        }
    return None


def _normalize_paged_result(result: Any) -> Any:
    """将上游翻页结果统一收口为 total 与 resultList。"""
    if not isinstance(result, dict) or "error" in result:
        return result
    result_list = result.get("resultList")
    if not isinstance(result_list, list):
        return result
    total = result.get("total", result.get("dataTotal", len(result_list)))
    return {"total": total, "resultList": result_list}


def _normalize_product_page(
    result: Any,
    page_index: int,
    page_size: int,
) -> Any:
    """将海外商品列表转换为统一分页结构。"""
    if not isinstance(result, dict) or "error" in result:
        return result
    product_list = result.get("productList")
    if not isinstance(product_list, list):
        return result
    total = result.get("productCount", len(product_list))
    start = (page_index - 1) * page_size
    return {
        "total": total,
        "resultList": product_list[start : start + page_size],
    }


def _stats_month_error(stats_month: str) -> dict[str, Any] | None:
    """校验 yyyyMM 统计月份。"""
    if (
        len(stats_month) != 6
        or not stats_month.isdigit()
        or not 1 <= int(stats_month[4:]) <= 12
    ):
        return {
            "error": "statsMonth 必须使用 yyyyMM 格式，例如 202505",
            "parameter": "statsMonth",
        }
    return None


def _missing_parameter(name: str, source: str) -> dict[str, Any]:
    """生成可操作的条件必填参数错误。"""
    return {
        "error": f"选择 {source} 数据源时必须提供 {name}",
        "parameter": name,
        "source": source,
    }


def call_api(product_id: str, params: dict[str, Any]) -> Any:
    """
    调用 HandaaS Integrator Gateway，并返回响应中的 data。

    不向调用方泄露密钥、签名、网关响应正文或底层网络异常详情。
    """
    integrator_id = _credential("INTEGRATOR_ID")
    secret_id = _credential("SECRET_ID")
    secret_key = _credential("SECRET_KEY")

    if not integrator_id:
        return {"error": "INTEGRATOR_ID 未配置"}
    if not secret_id:
        return {"error": "SECRET_ID 未配置"}
    if not secret_key:
        return {"error": "SECRET_KEY 未配置"}
    if not product_id:
        return {"error": "Product ID 不能为空"}

    call_params = {
        "product_id": product_id,
        "secret_id": secret_id,
        "params": json.dumps(
            _compact_params(params),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    call_params["signature"] = _build_signature(call_params, secret_key)
    url = f"{GATEWAY_BASE_URL}/{quote(integrator_id, safe='')}"

    try:
        response = requests.post(
            url,
            data=call_params,
            timeout=_request_timeout(),
        )
    except requests.RequestException:
        return {"error": "HandaaS 网关请求失败，请稍后重试"}

    if response.status_code != 200:
        return {
            "error": "HandaaS 网关返回非成功状态",
            "statusCode": response.status_code,
        }

    try:
        payload = response.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return {"error": "HandaaS 网关返回了无法解析的响应"}

    if not isinstance(payload, dict):
        return {"error": "HandaaS 网关返回格式异常"}
    if "data" in payload:
        return payload["data"]

    message = payload.get("msgCN") or payload.get("message") or "HandaaS 网关未返回 data"
    error = {"error": message}
    if payload.get("code") is not None:
        error["code"] = payload["code"]
    return error


@mcp.tool(title="商品搜索", annotations=READ_ONLY_TOOL)
def goods_search(
    matchKeyword: str | None = None,
    source: Literal["retail", "overseas"] = "retail",
    pageIndex: int = 1,
    pageSize: int | None = None,
    eshopSource: str | None = None,
    eshopCategories: str | None = None,
    eshopSalesLevel: str | None = None,
    operationStatus: str = "全部",
    hasAssociateEnterprise: str = "全部",
) -> dict[str, Any]:
    """
    搜索零售商品或海外网店，用于选品、竞品发现和跨境渠道筛选。

    参数:
    - matchKeyword: 商品名、网店名或商品关键词。
    - source: retail=零售商品搜索；overseas=海外网店搜索。
    - pageIndex: 页码，从 1 开始。
    - pageSize: 每页数量，最大 50；retail 默认 10，overseas 默认 50。
    - eshopSource: 海外网店平台，仅 source=overseas 时使用。
    - eshopCategories: 海外商品类目，多个值用英文逗号分隔。
    - eshopSalesLevel: 海外网店销量等级。
    - operationStatus: 海外网店状态。
    - hasAssociateEnterprise: 是否有关联企业。

    返回:
    - 翻页结果仅包含 total 与 resultList 业务内容。
    """
    resolved_page_size = pageSize if pageSize is not None else (10 if source == "retail" else 50)
    if error := _pagination_error(pageIndex, resolved_page_size):
        return error

    if source == "retail":
        return _normalize_paged_result(
            call_api(
                PRODUCT_IDS["retail_search"],
                {
                    "matchKeyword": matchKeyword,
                    "pageIndex": pageIndex,
                    "pageSize": resolved_page_size,
                },
            )
        )

    return _normalize_paged_result(
        call_api(
            PRODUCT_IDS["overseas_search"],
            {
                "matchKeyword": matchKeyword,
                "eshopSource": eshopSource,
                "eshopCategories": eshopCategories,
                "eshopSalesLevel": eshopSalesLevel,
                "operationStatus": operationStatus,
                "hasAssociateEnterprise": hasAssociateEnterprise,
                "pageIndex": pageIndex,
                "pageSize": resolved_page_size,
            },
        )
    )


@mcp.tool(title="商品画像", annotations=READ_ONLY_TOOL)
def goods_profile(
    matchKeyword: str,
    source: Literal["domestic", "overseas"] = "domestic",
    keywordType: KeywordType = "name",
    pageIndex: int = 1,
    pageSize: int = 50,
) -> dict[str, Any]:
    """
    查询企业国内电商商品明细或指定海外网店的商品画像。

    参数:
    - matchKeyword: domestic 时为企业标识；overseas 时为海外网店 ID。
    - source: domestic=企业电商商品明细；overseas=海外网店商品。
    - keywordType: domestic 企业标识类型。
    - pageIndex/pageSize: 两种数据源共用的 MCP 分页参数，pageSize 最大 50。
    """
    if error := _pagination_error(pageIndex, pageSize):
        return error
    if source == "overseas":
        return _normalize_product_page(
            call_api(
                PRODUCT_IDS["overseas_product_profile"],
                {"matchKeyword": matchKeyword},
            ),
            pageIndex,
            pageSize,
        )

    return call_api(
        PRODUCT_IDS["domestic_product_profile"],
        {
            "matchKeyword": matchKeyword,
            "keywordType": keywordType,
            "pageIndex": pageIndex,
            "pageSize": pageSize,
        },
    )


@mcp.tool(title="商品品牌分析", annotations=READ_ONLY_TOOL)
def goods_brand(
    matchKeyword: str,
    view: Literal["brand_detail", "product_overview"] = "brand_detail",
    keywordType: KeywordType = "name",
) -> dict[str, Any]:
    """
    查询美业企业品牌明细或品牌产品功效概况。

    参数:
    - matchKeyword: 企业名称、企业 ID、注册号或统一社会信用代码。
    - view: brand_detail=品牌明细；product_overview=品牌产品概况。
    - keywordType: matchKeyword 的主体类型。
    """
    route = "brand_detail" if view == "brand_detail" else "brand_product_overview"
    return call_api(
        PRODUCT_IDS[route],
        {"matchKeyword": matchKeyword, "keywordType": keywordType},
    )


@mcp.tool(title="商品价格分析", annotations=READ_ONLY_TOOL)
def goods_price(
    statsMonth: str,
    source: Literal["store_hot_items", "enterprise_monthly_sales"] = "store_hot_items",
    platform: str | None = None,
    shopId: str | None = None,
    matchKeyword: str | None = None,
    keywordType: KeywordType = "name",
) -> dict[str, Any]:
    """
    查询店铺热销商品价格表现或企业月度销售表现。

    参数:
    - statsMonth: 统计月份，格式 yyyyMM，例如 202505。
    - source: store_hot_items=店铺 Top50 热销商品；enterprise_monthly_sales=企业月销售。
    - platform/shopId: 店铺热销商品数据源必填。
    - matchKeyword/keywordType: 企业月销售数据源使用的企业标识。
    """
    if error := _stats_month_error(statsMonth):
        return error
    if source == "store_hot_items":
        if not platform:
            return _missing_parameter("platform", source)
        if not shopId:
            return _missing_parameter("shopId", source)
        return call_api(
            PRODUCT_IDS["store_top_items"],
            {"platform": platform, "shopId": shopId, "statsMonth": statsMonth},
        )

    if not matchKeyword:
        return _missing_parameter("matchKeyword", source)
    return call_api(
        PRODUCT_IDS["enterprise_monthly_sales"],
        {
            "matchKeyword": matchKeyword,
            "keywordType": keywordType,
            "statsMonth": statsMonth,
        },
    )


@mcp.tool(title="商品渠道分析", annotations=READ_ONLY_TOOL)
def goods_channel(
    matchKeyword: str,
    source: Literal["domestic_store", "global_store"] = "domestic_store",
    keywordType: KeywordType = "name",
    pageIndex: int = 1,
    pageSize: int = 50,
) -> dict[str, Any]:
    """
    查询企业国内电商店铺列表或国内外网店全局明细。

    参数:
    - matchKeyword: 企业名称、企业 ID、注册号或统一社会信用代码。
    - source: domestic_store=国内电商店铺列表；global_store=国内外网店明细。
    - keywordType: matchKeyword 的主体类型。
    - pageIndex/pageSize: domestic_store 分页参数，pageSize 最大 50。
    """
    if source == "global_store":
        return call_api(
            PRODUCT_IDS["global_store_channel"],
            {"matchKeyword": matchKeyword, "keywordType": keywordType},
        )

    if error := _pagination_error(pageIndex, pageSize):
        return error
    return call_api(
        PRODUCT_IDS["domestic_store_channel"],
        {
            "matchKeyword": matchKeyword,
            "keywordType": keywordType,
            "pageIndex": pageIndex,
            "pageSize": pageSize,
        },
    )


@mcp.tool(title="商品销售趋势", annotations=READ_ONLY_TOOL)
def goods_trend(
    statsMonth: str,
    source: Literal[
        "store_monthly",
        "enterprise_monthly",
        "enterprise_cumulative",
    ] = "store_monthly",
    platform: str | None = None,
    shopId: str | None = None,
    matchKeyword: str | None = None,
    keywordType: KeywordType = "name",
) -> dict[str, Any]:
    """
    查询店铺或企业的月度、累计销售趋势。

    参数:
    - statsMonth: 统计月份，格式 yyyyMM。
    - source: store_monthly、enterprise_monthly 或 enterprise_cumulative。
    - platform/shopId: store_monthly 数据源必填。
    - matchKeyword/keywordType: 企业月度或累计趋势数据源使用的企业标识。
    """
    if error := _stats_month_error(statsMonth):
        return error
    if source == "store_monthly":
        if not platform:
            return _missing_parameter("platform", source)
        if not shopId:
            return _missing_parameter("shopId", source)
        return call_api(
            PRODUCT_IDS["store_monthly_sales"],
            {"platform": platform, "shopId": shopId, "statsMonth": statsMonth},
        )

    if not matchKeyword:
        return _missing_parameter("matchKeyword", source)
    route = (
        "enterprise_monthly_sales"
        if source == "enterprise_monthly"
        else "enterprise_cumulative_sales"
    )
    return call_api(
        PRODUCT_IDS[route],
        {
            "matchKeyword": matchKeyword,
            "keywordType": keywordType,
            "statsMonth": statsMonth,
        },
    )


def main(argv: list[str] | None = None) -> int:
    """启动 MCP 服务。"""
    arguments = sys.argv[1:] if argv is None else argv
    transport = arguments[0] if arguments else "stdio"
    if transport not in {"stdio", "sse", "streamable-http"}:
        print(
            "启动方式必须是 stdio、sse 或 streamable-http",
            file=sys.stderr,
        )
        return 2
    mcp.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
