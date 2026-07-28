# 商品大数据服务

[该 MCP 服务提供商品搜索、商品画像、品牌、价格、渠道和销售趋势分析能力，帮助用户开展选品、竞品研究和电商经营分析。](https://www.handaas.com/)

## 主要功能

- 🔍 商品与海外网店搜索
- 🧾 企业及海外网店商品画像
- 🏷️ 企业品牌与产品功效分析
- 💰 店铺热销商品与企业月销售分析
- 🛒 国内及全球网店渠道分析
- 📈 店铺与企业销售趋势分析

## 服务设计说明

- 服务按实际业务场景提供 6 个 Tool，不按上游 API 数量平铺工具。
- 通过 `source` 或 `view` 显式选择数据源，单次 Tool 调用只访问一个 Product ID。
- 翻页结果的业务外层只包含 `total` 与 `resultList`，`pageSize` 最大为 50。
- 海外商品画像由 MCP 层分页，避免一次返回完整商品列表。
- 月度接口的 `statsMonth` 必须使用 `yyyyMM` 格式，例如 `202505`。
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

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
INTEGRATOR_ID=your_integrator_id
SECRET_ID=your_secret_id
SECRET_KEY=your_secret_key
HANDAAS_REQUEST_TIMEOUT=30
```

`HANDAAS_REQUEST_TIMEOUT` 为可选配置，单位为秒，默认值为 30。

### 4. 启动 Streamable HTTP 服务

```bash
python server/mcp_server.py streamable-http
```

服务默认地址为 `http://localhost:8000/mcp`。

也可以使用启动脚本：

```bash
./start_mcp_server.sh streamable-http
```

支持 `stdio`、`sse` 和 `streamable-http` 三种启动方式。

### 5. Cursor / Cherry Studio MCP 配置

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

将 `{workdir}` 替换为 `goods-mcp-server` 的绝对路径：

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
| `goods_search` | `source=retail` 零售商品搜索 | `6a609f509d30d4fcc00ccff5` |
| `goods_search` | `source=overseas` 海外网店搜索 | `66c9a954268e9d7292c1a9ab` |
| `goods_profile` | `source=domestic` 企业电商商品明细 | `66c33eff3c0917a9a02feb9d` |
| `goods_profile` | `source=overseas` 海外网店商品画像 | `66d5b7e0537c3f61d646c496` |
| `goods_brand` | `view=brand_detail` 美业企业品牌明细 | `66c702b725f04ab44cd24d5e` |
| `goods_brand` | `view=product_overview` 美业品牌产品功效概况 | `66d5b7e1537c3f61d646c573` |
| `goods_price` | `source=store_hot_items` 店铺 Top50 热销商品 | `684ad781d4819127431f9fe1` |
| `goods_price` | `source=enterprise_monthly_sales` 企业月销售情况 | `684ad781d4819127431fa026` |
| `goods_channel` | `source=domestic_store` 企业电商店铺信息 | `66c702b725f04ab44cd24c83` |
| `goods_channel` | `source=global_store` 企业国内外网店明细 | `672b3125338beb3ec2f5dc43` |
| `goods_trend` | `source=store_monthly` 店铺月销售情况 | `684ad781d4819127431f9ff8` |
| `goods_trend` | `source=enterprise_monthly` 企业月销售情况 | `684ad781d4819127431fa026` |
| `goods_trend` | `source=enterprise_cumulative` 企业累计销售情况 | `684ad781d4819127431fa016` |

### 1. goods_search

**功能**：搜索零售商品或海外网店，用于选品、竞品发现和跨境渠道筛选。

**主要参数**：

- `matchKeyword`（可选）：商品名、网店名或商品关键词。
- `source`（可选）：`retail` 零售商品搜索；`overseas` 海外网店搜索。默认 `retail`。
- `pageIndex`（可选）：页码，从 1 开始。
- `pageSize`（可选）：每页数量，最大 50；零售搜索默认 10，海外搜索默认 50。
- `eshopSource`、`eshopCategories`、`eshopSalesLevel`（可选）：海外网店平台、商品类目和销量等级，仅 `source=overseas` 时使用。
- `operationStatus`、`hasAssociateEnterprise`（可选）：海外网店经营状态和关联企业筛选。

**返回**：`total` 和 `resultList`。

### 2. goods_profile

**功能**：查询企业国内电商商品明细，或指定海外网店的商品画像。

**主要参数**：

- `matchKeyword`（必需）：国内画像使用企业标识；海外画像使用海外网店 ID。
- `source`（可选）：`domestic` 国内商品画像；`overseas` 海外网店商品画像。默认 `domestic`。
- `keywordType`（可选）：企业标识类型，支持 `name`、`nameId`、`regNumber`、`socialCreditCode`。
- `pageIndex`、`pageSize`（可选）：页码和每页数量，`pageSize` 最大为 50。

**返回**：`total` 和 `resultList`。

### 3. goods_brand

**功能**：查询美业企业品牌明细或品牌产品功效概况。

**主要参数**：

- `matchKeyword`（必需）：企业名称、企业 ID、注册号或统一社会信用代码。
- `view`（可选）：`brand_detail` 品牌明细；`product_overview` 品牌产品概况。默认 `brand_detail`。
- `keywordType`（可选）：企业标识类型。

**返回**：所选品牌视图对应的业务字段。

### 4. goods_price

**功能**：查询店铺热销商品价格表现或企业月度销售表现。

**主要参数**：

- `statsMonth`（必需）：统计月份，格式为 `yyyyMM`。
- `source`（可选）：`store_hot_items` 店铺热销商品；`enterprise_monthly_sales` 企业月销售。默认 `store_hot_items`。
- `platform`、`shopId`：选择 `store_hot_items` 时必需。
- `matchKeyword`、`keywordType`：选择 `enterprise_monthly_sales` 时使用，其中 `matchKeyword` 必需。

**返回**：店铺 Top50 热销商品或企业月销售业务字段。

### 5. goods_channel

**功能**：查询企业国内电商店铺列表或国内外网店全局明细。

**主要参数**：

- `matchKeyword`（必需）：企业名称、企业 ID、注册号或统一社会信用代码。
- `source`（可选）：`domestic_store` 国内电商店铺；`global_store` 国内外网店。默认 `domestic_store`。
- `keywordType`（可选）：企业标识类型。
- `pageIndex`、`pageSize`（可选）：仅国内店铺视图使用，`pageSize` 最大为 50。

**返回**：国内店铺视图返回 `total` 和 `resultList`；全球网店视图返回网店概况和明细。

### 6. goods_trend

**功能**：查询店铺或企业的月度、累计销售趋势。

**主要参数**：

- `statsMonth`（必需）：统计月份，格式为 `yyyyMM`。
- `source`（可选）：`store_monthly`、`enterprise_monthly` 或 `enterprise_cumulative`，默认 `store_monthly`。
- `platform`、`shopId`：选择 `store_monthly` 时必需。
- `matchKeyword`、`keywordType`：选择企业月度或累计趋势时使用，其中 `matchKeyword` 必需。

**返回**：所选维度对应的销量、销售额及趋势业务字段。

## 使用场景

1. **选品分析**：按商品关键词发现零售商品和海外网店。
2. **竞品研究**：查询目标企业商品、品牌、价格和销售表现。
3. **品牌分析**：了解企业品牌明细、产品类型和功效布局。
4. **渠道分析**：比较企业国内电商渠道和全球网店布局。
5. **店铺运营**：分析店铺热销商品、月销量和月销售额。
6. **趋势研判**：跟踪企业月度或累计销售变化。

## 使用注意事项

1. **单数据源调用**：一次调用只会访问 `source` 或 `view` 选中的一个 Product ID。
2. **分页限制**：`pageIndex` 从 1 开始，`pageSize` 必须在 1 到 50 之间。
3. **月份格式**：`statsMonth` 必须使用 `yyyyMM` 格式。
4. **条件必填**：店铺类接口必须提供 `platform` 和 `shopId`；企业类接口必须提供 `matchKeyword`。
5. **企业标识**：企业名称不是唯一标识时，建议使用企业 ID 或统一社会信用代码。
6. **结果解释**：无数据时可能返回合法空结果，不应直接视为服务异常。

## 使用提问示例

### goods_search（商品搜索）

1. 帮我查找零售市场里的咖啡商品，先看 10 条。
2. 搜索销售 coffee 的海外网店。

### goods_profile（商品画像）

1. 小米科技有限责任公司在国内电商销售哪些商品？
2. 查看指定海外网店的商品画像。

### goods_brand（商品品牌分析）

1. 查询上海家化联合股份有限公司的品牌明细。
2. 分析欧莱雅（中国）有限公司的品牌产品功效概况。

### goods_price（商品价格分析）

1. 查询某店铺 2025 年 5 月的 Top50 热销商品。
2. 查看小米科技有限责任公司 2025 年 5 月的销售表现。

### goods_channel（商品渠道分析）

1. 珠海格力电器股份有限公司有哪些国内电商店铺？
2. 北京京东世纪贸易有限公司在国内外有哪些网店渠道？

### goods_trend（商品销售趋势）

1. 查询指定店铺 2025 年 5 月的月销售情况。
2. 查看某企业截至 2025 年 5 月的累计销售情况。

## 测试验证

```bash
python -m py_compile server/mcp_server.py
python -m unittest discover -s tests -v
```

单元测试使用 Mock HTTP 响应，不调用真实 HandaaS 商品接口。
