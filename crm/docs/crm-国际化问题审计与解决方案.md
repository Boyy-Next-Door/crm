# CRM 国际化问题审计与解决方案

## 1. 结论先说

当前系统“语言已切中文，但界面仍残留大量英文”的问题，不是单点缺陷，而是由下面四类问题叠加造成的：

1. `zh.po` 词条覆盖不足，存在大量 `msgstr ""` 的未翻译项。
2. 前端很多可见文案没有走 `__()` 翻译链路，语言包再完整也不会生效。
3. 一部分“状态/枚举/主数据”存在数据库中，必须依赖 `translated_doctype` 或前端显式 `__(value)` 才会被翻译。
4. 部分词条写法不一致，尤其是大小写不一致，导致明明词库里有中文，运行时仍命不中。

这意味着：

- 只补 `zh.po` 不够；
- 只改前端 `__()` 也不够；
- 需要做一次“国际化机制梳理 + 文案治理 + 枚举主数据治理”的系统性修复。

## 2. 现状审计结果

### 2.1 语言资源层

中文语言包位于：

- `crm/locale/zh.po`

审计结果：

- 当前 `zh.po` 中仍有 **658** 条未翻译词条。

这说明项目虽然接入了国际化框架，但中文资源远未闭合。

### 2.2 当前国际化机制

前端翻译入口：

- `frontend/src/translation.js`

它的机制是：

- 所有界面文案必须通过 `__(...)` 进入翻译；
- 运行时从 boot 数据里的 `translated_messages` 读取翻译映射。

boot 注入发生在：

- `crm/www/crm.py`

其中同时注入了：

- `translated_messages`
- `translated_doctypes`

这说明系统本来就同时支持两类翻译：

1. 普通静态文案翻译
2. 数据型文案翻译（例如状态、来源、行业、Territory 这类主数据）

### 2.3 当前已支持翻译的“数据型 Doctype”

以下 Doctype 已启用 `translated_doctype`：

- `CRM Lead Status`
- `CRM Deal Status`
- `CRM Lead Source`
- `CRM Lost Reason`
- `CRM Territory`
- `CRM Industry`
- `CRM Sales Hierarchy`
- `CRM Product`

这类数据在理论上可以做到“数据库值是英文、界面显示中文”，前提是前端展示时要调用翻译。

### 2.4 当前未纳入翻译体系的重要数据型 Doctype

以下 Doctype 当前 **没有** 启用 `translated_doctype`：

- `CRM Communication Status`

文件：

- `crm/fcrm/doctype/crm_communication_status/crm_communication_status.json`

这会直接导致下面这些值长期显示英文：

- `Open`
- `Replied`

而这两个值又直接参与：

- Lead / Deal 的沟通状态
- SLA 区块
- 自动响应状态更新

所以这是一个核心漏点。

## 3. 问题分层梳理

## 3.1 第一类：语言包缺失

表现：

- 代码里已经用了 `__()`，但中文仍不显示；
- 原因是 `zh.po` 没有对应翻译，或翻译为空。

证据：

- `crm/locale/zh.po` 中存在大量 `msgstr ""`

这一类问题修复方式相对直接：

- 完善 `main.pot`
- 回填 `zh.po`
- 编译并发布语言包

但这只解决一部分问题。

## 3.2 第二类：前端文案没有包 `__()`

这是当前最主要的问题来源之一。

### 典型文件

- `frontend/src/utils/model.js`
- `frontend/src/utils/index.js`
- `frontend/src/pages/DataImport.vue`
- `frontend/src/components/Activities/WhatsAppArea.vue`
- `frontend/src/components/Settings/Sla/WorkDayModal.vue`
- `frontend/src/components/ConditionsFilter/CFCondition.vue`
- `frontend/src/components/Settings/AssignmentRules/AssignmentRuleView.vue`

### 典型现象

#### 1. 标准字段标签英文直出

文件：

- `frontend/src/utils/model.js`

典型文案：

- `Name`
- `Created On`
- `Last Modified`
- `Modified By`
- `Assigned To`
- `Owner`
- `Like`

这些字段被作为通用元数据标签使用，但当前没有 `__()`。

#### 2. 任务状态/优先级下拉显示英文

文件：

- `frontend/src/utils/index.js`

函数：

- `taskStatusOptions`
- `taskPriorityOptions`

虽然 `CRM Task` 的 Select 选项本身已经在 DocType JSON 中定义了：

- `Backlog`
- `Todo`
- `In Progress`
- `Done`
- `Canceled`
- `Low`
- `Medium`
- `High`

但前端生成下拉时直接把原值作为 label 返回，没有翻译。

#### 3. WhatsApp 操作项英文

文件：

- `frontend/src/components/Activities/WhatsAppArea.vue`

典型文案：

- `Reply`

当前未包 `__()`。

#### 4. SLA 工作日英文

文件：

- `frontend/src/components/Settings/Sla/WorkDayModal.vue`

典型文案：

- `Monday`
- `Tuesday`
- `Wednesday`
- `Thursday`
- `Friday`
- `Saturday`
- `Sunday`

虽然 `zh.po` 里已有这类词条，但此处 label 没走 `__()`，所以仍显示英文。

#### 5. 条件构造器操作符英文

文件：

- `frontend/src/components/ConditionsFilter/CFCondition.vue`

典型文案：

- `Equals`
- `Not Equals`
- `Like`
- `Not Like`
- `In`
- `Not In`
- `Is`
- `Between`
- `Set`
- `Not Set`
- `Yes`

这些是高频管理界面文案，当前大量未做翻译包装。

#### 6. 数据导入页业务标题英文

文件：

- `frontend/src/pages/DataImport.vue`

典型文案：

- `Leads`
- `Deals`
- `Contacts`
- `Tasks`
- `Organizations`
- `Call Log`

这些标题会直接出现在客户操作界面。

## 3.3 第三类：动态数据值未翻译

这类问题最容易被忽略，因为它们看起来像“界面文案”，实际上是“数据库里的值”。

### 1. 沟通状态未纳入 translated doctype

文件：

- `crm/fcrm/doctype/crm_communication_status/crm_communication_status.json`
- `frontend/src/components/SLASection.vue`
- `frontend/src/stores/statuses.js`

当前 `SLASection.vue` 中：

- `communicationStatuses.data?.map((status) => ({ label: status.name, ... }))`

这里直接把数据库值 `status.name` 作为 label 输出，没有翻译。

且 `CRM Communication Status` 又没有 `translated_doctype`，所以即使补词库也不稳定。

### 2. 任务状态/优先级属于“DocType Select 选项”，但前端没有翻译 label

这类值虽然能进入语言提取，但在前端展示时如果直接输出原值，仍会看到英文。

### 3. 动态 Link / Select 选项没有统一翻译策略

在 `stores/meta.js` 里，Select 字段会被转成：

- `{ label: option, value: option }`

当前没有统一做：

- `label: __(option)`

这意味着很多 Select 字段只要不是页面模板里显式调用 `__()`，就会原样显示英文。

## 3.4 第四类：词条写法不一致导致翻译命不中

这是现在很明显的一类“隐蔽问题”。

### 典型案例

文件：

- `frontend/src/components/Telephony/ExotelCallUI.vue`

代码中返回的状态值包括：

- `In progress`
- `No answer`
- `Call ended`

而语言包里现有词条至少存在：

- `In Progress`
- `No Answer`

也就是说：

- 同一个词，代码和 `zh.po` 的大小写不一致；
- `__()` 是精确匹配；
- 最终导致运行时明明已有词条，界面还是英文。

这类问题不修“文案规范”，后面还会重复出现。

## 4. 根因总结

从架构角度看，当前国际化问题的真正根因有 5 个：

1. **缺少统一国际化规范**
   - 没有规定“任何用户可见字符串都必须进 `__()`”
   - 没有规定“动态枚举 label 必须翻译”

2. **缺少动态值翻译中间层**
   - Select / Link / Status / Priority / Weekday 没有统一 `getTranslatedLabel()` 封装

3. **数据型翻译对象定义不完整**
   - 如 `CRM Communication Status` 未声明为 `translated_doctype`

4. **词条治理缺失**
   - 大小写不统一
   - 同义不同写法并存
   - 新增功能时没有同步补全语言包

5. **缺少国际化验收机制**
   - 没有扫描规则
   - 没有 CI 校验
   - 没有“中文模式冒烟清单”

## 5. 推荐解决方案

建议按“三层修复 + 一层治理”来做。

## 5.1 第一层：先修机制

目标：让以后新增代码不再继续制造英文残留。

### 方案 A：建立统一翻译辅助函数

建议新增统一方法，例如：

- `translateOptionLabel(value, doctype?)`
- `translateDynamicValue(value, { doctype, fieldname })`

适用范围：

- Select 下拉项
- Status 菜单
- Priority 菜单
- Weekday 菜单
- Filter operator 菜单
- DataImport 页面标题

原则：

- 所有用户看得到的 label，都不要直接使用原始字符串
- 一律走统一翻译函数

### 方案 B：补齐 translated doctype

至少先补：

- `CRM Communication Status`

必要时继续评估：

- 其他会显示给客户看的主数据 Doctype 是否都已开启 `translated_doctype`

### 方案 C：统一文案 canonical form

必须建立一套“源英文规范写法”，例如：

- `In Progress`
- `No Answer`
- `Call Ended`

然后：

- 代码中只允许使用 canonical 写法
- `zh.po` 只维护 canonical 写法
- 禁止再出现 `In progress` / `No answer` 这种变体

## 5.2 第二层：做一次前端全面清扫

目标：把所有用户可见硬编码文案纳入翻译。

优先级建议如下。

### P0：客户高频主流程页面

- Leads / Deals / Lead / Deal
- Tasks
- Calendar
- Data Import
- Settings 首页
- SLA 相关页面
- Assignment Rule 相关页面

### P1：高频组件

- `frontend/src/utils/model.js`
- `frontend/src/utils/index.js`
- `frontend/src/stores/meta.js`
- `frontend/src/stores/statuses.js`
- `frontend/src/components/Filter.vue`
- `frontend/src/components/ConditionsFilter/*`
- `frontend/src/components/Activities/*`
- `frontend/src/components/Telephony/*`

### P2：长尾页面

- Forms Builder
- ERPNext Settings
- Theme / Dashboard / Email / Integrations 细节页

## 5.3 第三层：补齐语言资源

在代码完成翻译接入后，再补语言包。

步骤建议：

1. 提取最新 `main.pot`
2. 合并到 `zh.po`
3. 完成中文翻译
4. 清理重复/变体词条
5. 发布并刷新缓存验证

这里要注意一个顺序：

- **先修代码入口，再补词条**

否则会出现：

- 词条已经翻了，但界面依旧不走翻译

## 5.4 第四层：建立治理与验收

这是避免问题反复出现的关键。

### 建议加入静态扫描规则

建议在 CI 或本地检查中加入：

1. 扫描 Vue/JS 中可见字符串未包 `__()`
2. 扫描常见状态词变体
3. 扫描新增 `msgid` 但 `zh.po` 未翻译

### 建议建立中文冒烟清单

至少覆盖：

1. Leads 列表 + 详情
2. Deals 列表 + 详情
3. Task 创建与状态切换
4. SLA 状态修改
5. 条件过滤器
6. Assignment Rule 页面
7. Data Import 页面
8. Form Builder 页面
9. Telephony / WhatsApp

验收标准：

- 中文模式下不出现英文主操作词
- 不出现英文状态词
- 不出现英文工作日/操作符/优先级
- 允许保留品牌名、第三方服务名、API 专有名词

## 6. 推荐实施顺序

建议分四个迭代做，不要一次性大爆改。

### 第一阶段：止血

1. 修 `translated_doctype` 缺口
2. 修状态/优先级/工作日/操作符/DataImport 标题
3. 修大小写不一致词条

目标：

- 客户最常见的英文残留先清掉 70% 以上

### 第二阶段：界面清扫

1. 扫描所有 Vue 页面硬编码文案
2. 统一包 `__()`
3. 补语言包

目标：

- 主流程页面基本中文化

### 第三阶段：动态值治理

1. Select/Link/options 建统一翻译策略
2. 时间线、下拉、Badge、过滤器全部走同一套 label 翻译

目标：

- 解决“不是页面文案，而是数据值”的英文残留

### 第四阶段：长期治理

1. 增加扫描脚本
2. 增加中文冒烟测试
3. 新增功能开发规范落地

目标：

- 防止回归

## 7. 最终建议的技术方案

如果你要真正把这件事做扎实，我建议按下面方案落地：

### 方案主线

1. **补全翻译对象定义**
   - 先把 `CRM Communication Status` 纳入 `translated_doctype`

2. **新增统一翻译工具层**
   - 专门处理动态 label / option / status / priority / weekday

3. **全局替换高频裸字符串**
   - 先 P0、再 P1、最后 P2

4. **回填并清洗 `zh.po`**
   - 包括大小写统一、重复词条清理、空翻译补全

5. **建立自动化验收**
   - 静态扫描 + 中文冒烟

## 8. 我对这个项目的判断

如果只做“补翻译文件”，最多解决 30% 到 40%。

如果按这份方案做完整：

- 可以把客户界面的英文残留压到很低；
- 后续新增模块也能沿用同一套国际化规则；
- 客户培训和交付体验会明显改善。

## 9. 下一步最值得直接执行的事项

我建议下一步直接进入实施，而不是继续停留在分析层。

最优先的第一批改动应该是：

1. `CRM Communication Status` 开启 `translated_doctype`
2. `statuses.js` / `SLASection.vue` 补动态状态翻译
3. `taskStatusOptions` / `taskPriorityOptions` 补翻译
4. `WorkDayModal.vue` 工作日补翻译
5. `CFCondition.vue` / `Filter.vue` 操作符补翻译
6. `DataImport.vue` 标题补翻译
7. `model.js` 标准字段标签补翻译
8. `ExotelCallUI.vue` 状态文案统一 canonical 写法

这批改完，客户感知会立刻提升。
