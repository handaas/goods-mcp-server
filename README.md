# 零售商品动态

[该 MCP 服务提供企业关键词搜索、商品搜索、企业商品、海外店铺商品、品牌和电商渠道查询能力，帮助用户开展选品、竞品研究、商品资质核验与渠道分析。](https://www.handaas.com/)

## 主要功能

- 🏢 企业简称与关键词搜索
- 🔍 零售商品与海外网店搜索
- 🧾 企业零售商品和电商商品查询
- 🌍 海外店铺商品目录查询
- 🏷️ 美业企业品牌与产品功效分析
- 🛒 国内及全球网店渠道分析

## 服务设计说明

- 服务按实际使用对象提供 6 个 Tool，不按上游 API 数量平铺工具。
- 用户只提供企业简称时，先用 `goods_enterprise_search` 获取企业全称或稳定 ID。
- 企业商品与海外店铺商品分别提供独立 Tool，避免同一个参数在不同来源中表达不同对象。
- `goods_enterprise_products` 可选择零售商品或电商商品，但单次调用只访问一个 Product ID。
- 企业零售商品每页最多 10 条；其他翻页查询每页最多 50 条。
- 翻页结果的业务外层统一为 `total` 与 `resultList`。
- 已移除依赖第三方商品的店铺热销、月销售和累计销售能力，不再注册价格或销售趋势 Tool。
- Tool 成功时返回 HandaaS Integrator Gateway 提取后的业务 `data`。

## 环境要求

- Python 3.10+
- 依赖包：python-dotenv、requests、mcp

## 本地快速启动

### 1. 进入项目目录

```bash
cd goods-mcp-server
```

### 2. 创建虚拟环境并安装依赖

```bash
python3 -m venv mcp_env
source mcp_env/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
HANDAAS_REQUEST_TIMEOUT=30
```

`HANDAAS_REQUEST_TIMEOUT` 为可选配置，单位为秒，默认值为 30。

### 4. 启动服务

```bash
python server/mcp_server.py streamable-http
```

服务默认地址为 `http://localhost:8000/mcp`。

也可以使用：

```bash
./start_mcp_server.sh streamable-http
```

支持 `stdio`、`sse` 和 `streamable-http` 三种启动方式。

### 5. Cursor / Cherry Studio 配置

```json
{
  "mcpServers": {
    "goods-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## STDIO 版安装部署

将 `{workdir}` 替换为项目绝对路径：

```json
{
  "mcpServers": {
    "goods-mcp-server": {
      "command": "{workdir}/mcp_env/bin/python",
      "args": [
        "{workdir}/server/mcp_server.py",
        "stdio"
      ]
    }
  }
}
```

`INTEGRATOR_ID`、`SECRET_ID` 和 `SECRET_KEY` 需要登录 [HandaaS](https://www.handaas.com/) 注册并开通对接器后获取。真实凭据只应保存在本地 `.env` 或部署密钥中。

## 可用工具与 Product ID

| MCP Tool | 场景或选项 | Product ID |
|---|---|---|
| `goods_enterprise_search` | 企业简称、品牌或产品关键词查询企业 | `675cea1f0e009a9ea37edaa1` |
| `goods_search` | `source=retail` 零售商品搜索 | `6a609f509d30d4fcc00ccff5` |
| `goods_search` | `source=overseas` 海外网店搜索 | `66c9a954268e9d7292c1a9ab` |
| `goods_enterprise_products` | `productType=retail` 企业零售商品信息 | `6a62157cb050fd2d69e9f7ff` |
| `goods_enterprise_products` | `productType=ecommerce` 企业电商商品明细 | `66c33eff3c0917a9a02feb9d` |
| `goods_overseas_store_products` | 海外网店商品 | `66d5b7e0537c3f61d646c496` |
| `goods_brand` | `view=brand_detail` 美业企业品牌明细 | `66c702b725f04ab44cd24d5e` |
| `goods_brand` | `view=product_overview` 美业品牌产品功效概况 | `66d5b7e1537c3f61d646c573` |
| `goods_channel` | `source=domestic_store` 企业电商店铺信息 | `66c702b725f04ab44cd24c83` |
| `goods_channel` | `source=global_store` 企业国内外网店明细 | `672b3125338beb3ec2f5dc43` |

### 1. goods_enterprise_search

**功能**：按企业简称、品牌、产品或其他关键词搜索候选企业。

**主要参数**：

- `matchKeyword`（必需）：企业简称或相关关键词。
- `pageIndex`（可选）：页码，从 1 开始。
- `pageSize`（可选）：默认 10，最大 50。

**返回**：候选企业 `total/resultList`。确认企业后，优先把企业全称、企业 ID 或统一社会信用代码传给企业商品、品牌和渠道 Tool。

### 2. goods_search

**功能**：搜索零售商品或海外网店，用于选品、商品发现和跨境渠道筛选。

**主要参数**：

- `matchKeyword`（可选）：商品名、网店名或商品关键词。
- `source`（可选）：`retail` 零售商品；`overseas` 海外网店。默认 `retail`。
- `pageIndex`（可选）：页码，从 1 开始。
- `pageSize`（可选）：最大 50；零售搜索默认 10，海外搜索默认 50。
- `eshopSource`、`eshopCategories`、`eshopSalesLevel`（可选）：仅海外网店搜索使用。
- `operationStatus`、`hasAssociateEnterprise`（可选）：海外网店状态和关联企业筛选。

**返回**：`total` 与 `resultList`。

### 3. goods_enterprise_products

**功能**：按企业查询零售商品或电商商品，适合商品资质核验、企业商品盘点和竞品研究。

**主要参数**：

- `matchKeyword`（必需）：企业名称、企业 ID、注册号或统一社会信用代码。
- `productType`（可选）：`retail` 企业零售商品；`ecommerce` 企业电商商品。默认 `retail`。
- `keywordType`（可选）：`name`、`nameId`、`regNumber` 或 `socialCreditCode`。
- `pageIndex`（可选）：页码，从 1 开始。
- `pageSize`（可选）：零售商品最大 10、默认 10；电商商品最大 50、默认 50。

**零售商品返回字段**：

- 商品名称、商品条码、上架日期
- 企业名称、企业 ID
- 品牌名称、GPC 分类

**电商商品返回字段**：

- 商品名称、图片链接、价格、商品来源

### 4. goods_overseas_store_products

**功能**：按海外网店 ID 查询店铺商品目录。

**主要参数**：

- `storeId`（必需）：由 `goods_search(source=overseas)` 返回的网店 `_id`。
- `pageIndex`、`pageSize`（可选）：MCP 本地分页，`pageSize` 最大 50。

**返回**：商品数量、评论、BSR、类目、商品名称和链接等信息，并统一为 `total/resultList`。

### 5. goods_brand

**功能**：查询美业企业品牌明细或品牌产品功效概况。

**主要参数**：

- `matchKeyword`（必需）：企业标识。
- `view`（可选）：`brand_detail` 品牌明细；`product_overview` 产品功效概况。
- `keywordType`（可选）：企业标识类型。

### 6. goods_channel

**功能**：查询企业国内电商店铺列表或国内外网店全局明细。

**主要参数**：

- `matchKeyword`（必需）：企业标识。
- `source`（可选）：`domestic_store` 国内电商店铺；`global_store` 国内外网店。
- `keywordType`（可选）：企业标识类型。
- `pageIndex`、`pageSize`（可选）：仅国内店铺使用，`pageSize` 最大 50。

## 使用场景

1. **企业定位**：用简称、品牌或产品关键词找到候选企业和稳定标识。
2. **商品发现**：按商品关键词发现零售商品，或按商品和平台筛选海外网店。
3. **企业商品盘点**：查询企业的零售商品条码、品牌、GPC 分类及电商商品价格。
4. **商品资质核验**：使用企业标识定位商品主体，核对商品名称、条码和上架信息。
5. **跨境竞品研究**：从海外网店搜索进入指定店铺商品目录，分析类目和 BSR。
6. **品牌分析**：了解美业企业品牌、主营产品和产品功效布局。
7. **渠道分析**：比较企业国内电商店铺和国内外网店布局。

## 使用注意事项

1. **单数据源调用**：一次调用只访问 `source`、`productType` 或 `view` 选中的一个 Product ID。
2. **分页限制**：企业零售商品 `pageSize` 最大 10；其他翻页工具最大 50。
3. **简称处理**：企业简称无法直接查询时，先调用 `goods_enterprise_search`。
4. **标识优先级**：确认候选后，优先使用企业 ID 或统一社会信用代码。
5. **海外店铺 ID**：`storeId` 必须来自海外网店搜索结果，不能使用企业名称代替。
6. **空结果**：`total=0`、`resultList=[]` 是合法业务结果。
7. **能力边界**：本服务不再提供店铺热销、月销售额、累计销量或销售趋势查询。

## 使用提问示例

### goods_enterprise_search

1. “小米”对应哪些企业？
2. 帮我通过“格力”找到准确企业名称和企业 ID。

### goods_search

1. 帮我查找零售市场里的咖啡商品，先看 10 条。
2. 搜索销售 coffee 的亚马逊海外网店。

### goods_enterprise_products

1. 查询小米科技有限责任公司的零售商品名称、条码和品牌。
2. 查看某企业在电商平台发布的商品名称、价格和来源。

### goods_overseas_store_products

1. 查看这个海外网店的商品目录和 BSR。
2. 分页列出指定海外店铺的商品与评论数量。

### goods_brand

1. 查询上海家化联合股份有限公司的品牌明细。
2. 分析欧莱雅（中国）有限公司的品牌产品功效概况。

### goods_channel

1. 珠海格力电器股份有限公司有哪些国内电商店铺？
2. 北京京东世纪贸易有限公司在国内外有哪些网店渠道？

## 测试验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests -v
```

单元测试使用 Mock HTTP 响应，不调用真实 HandaaS 商品接口。
