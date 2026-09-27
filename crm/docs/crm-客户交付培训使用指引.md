# Frappe CRM 客户交付培训使用指引

## 1. 文档目的

这份文档用于客户交付时的系统培训，目标是让客户清楚理解：

- 这个 CRM 系统是做什么的
- 业务对象之间是什么关系
- 数据从哪里来、如何流转、最后沉淀到哪里
- 销售、销售主管、管理员分别怎么用
- 上线前需要完成哪些配置

本项目是一个基于 Frappe Framework 的独立 CRM 应用，访问入口为 `/crm`。

## 2. 系统定位

这个系统的核心定位是“销售线索到商机的全过程管理平台”，重点覆盖：

- 线索采集
- 客户信息沉淀
- 商机推进
- 跟进协作
- 日历与任务
- 线索分配与 SLA
- 电话、邮件、WhatsApp 等触达记录
- 与 ERPNext 的客户/报价/产品协同

它不是纯粹的 ERP，也不是单纯的通讯录。它更像是销售前端经营系统。

## 3. 主导航与功能地图

系统主导航包括：

- `Dashboard`：销售数据看板
- `Leads`：线索池
- `Deals`：商机池
- `Contacts`：联系人
- `Organizations`：客户组织/公司
- `Notes`：业务备注
- `Tasks`：待办任务
- `Call Logs`：通话记录
- `Calendar`：日历与活动
- `Data Import`：数据导入
- `Settings`：系统设置中心

其中最核心的两个页面是：

- `Leads`：管理“还在识别、培育、资格判断阶段”的潜客
- `Deals`：管理“已经具备成交可能性、需要推进阶段”的商机

## 4. 核心业务模型

### 4.1 CRM Lead 线索

线索代表一个潜在客户入口，可以是人，也可以是公司意向。

主要字段包括：

- 姓名、邮箱、手机、电话
- 所属组织名称
- 网站
- 来源 `Source`
- 状态 `Status`
- 负责人 `Lead Owner`
- 地区 `Territory`
- 行业 `Industry`
- 产品意向与金额汇总
- SLA 与响应状态
- 丢单原因

线索特征：

- 新建时默认状态一般是 `New`
- 可分配负责人并自动形成待办/共享
- 可记录邮件、评论、事件、通话、任务、备注、附件、WhatsApp
- 可通过 `Convert to Deal` 转成商机
- 转商机后会标记 `converted = 1`

### 4.2 CRM Deal 商机

商机代表明确进入销售推进阶段的机会。

主要字段包括：

- 关联组织 `Organization`
- 商机状态 `Status`
- 商机负责人 `Deal Owner`
- 成交概率 `Probability`
- 预计成交金额 `Expected Deal Value`
- 实际成交金额 `Deal Value`
- 预计成交日期 `Expected Closure Date`
- 关闭日期 `Closed Date`
- 来源、地区、行业、币种、汇率
- 关联联系人列表 `Contacts`
- 产品明细与金额汇总
- SLA 与沟通状态
- 丢单原因

商机特征：

- 新建时默认状态一般是 `Qualification`
- 可维护多个联系人，并指定一个主联系人
- 主联系人会回填主邮箱/主手机/主电话
- 若启用 Forecasting，预计金额和预计关闭日期会成为关键管理字段
- 当状态进入 `Won` 时会自动写入关闭日期

### 4.3 Contact 联系人

联系人是标准 Frappe `Contact`，在 CRM 中作为“具体的人”管理。

典型字段：

- 姓名
- 邮箱
- 手机/电话
- 公司名
- 职位

使用方式：

- 可独立维护
- 可由线索转商机时自动创建
- 可在商机中添加多个联系人
- 商机页面支持设置主联系人

### 4.4 CRM Organization 客户组织

组织代表公司/单位，是线索与商机背后的企业主体。

主要字段：

- 组织名称
- 官网
- Logo
- 行业
- 地区
- 年营收
- 员工规模
- 地址

使用方式：

- 可独立创建
- 可在线索转商机时自动创建
- 商机可直接关联组织
- 组织上的官网信息可以驱动自动信息补全

### 4.5 CRM Task 任务

任务用于销售协作与跟进控制。

主要字段：

- 标题
- 优先级
- 状态：`Backlog / Todo / In Progress / Done / Canceled`
- 开始时间、截止时间
- 指派给谁
- 引用来源文档

任务可以直接挂到：

- 线索
- 商机
- 通话记录

### 4.6 FCRM Note 备注

备注用于沉淀业务判断、会议纪要、沟通摘要等非结构化信息。

可关联到：

- 线索
- 商机
- 通话记录

### 4.7 CRM Call Log 通话记录

通话记录用于管理销售来电、去电及录音。

支持：

- 手动通话
- Twilio
- Exotel

通话记录可继续关联：

- 线索
- 商机
- 备注
- 任务

甚至可以基于陌生来电快速“从通话记录创建线索”。

## 5. 状态模型

### 5.1 线索状态

线索状态来自 `CRM Lead Status`，可配置：

- 状态名称
- 类型：`Open / Ongoing / On Hold / Won / Lost`
- 颜色
- 排序位置

培训建议：

- 把线索状态理解为“潜客成熟度”
- `Lost` 必须填写丢失原因
- 当线索被转商机时，系统会自动标记已转化

### 5.2 商机状态

商机状态来自 `CRM Deal Status`，除了名称、类型、颜色、排序外，还带：

- 概率 `Probability`

培训建议：

- 把商机状态理解为“销售推进阶段”
- 每个阶段可设置默认成交概率
- `Lost` 要求填写丢单原因
- `Won` 会触发关闭日期

## 6. 数据关系图

可以把核心关系理解为：

`Lead -> Deal -> ERPNext Customer / Quotation`

并且横向挂载：

- `Lead -> Notes / Tasks / Events / Calls / Emails / Comments / Attachments / WhatsApp`
- `Deal -> Contacts / Products / Notes / Tasks / Events / Calls / Emails / Comments / Attachments / WhatsApp`
- `Deal -> Organization`
- `Deal -> Contacts(多个，1个主联系人)`

最重要的业务事实是：

1. 线索是入口
2. 商机是推进主体
3. 联系人与组织是客户主数据
4. 任务/日历/沟通记录是过程管理

## 7. 关键数据流

### 7.1 线索进入系统的方式

系统支持多种线索进入路径：

1. 手工新建 Lead
2. 数据导入 `Data Import`
3. 公共表单 `Forms`
4. Facebook 线索同步 `Lead Syncing`
5. 通话记录反建线索

其中公共表单底层基于 Frappe `Web Form`，支持发布 CRM Lead 或 CRM Deal 表单，公开访问路径为：

- `/crm-form/<route>`

表单提交后系统会自动：

- 写入目标文档
- 应用隐藏默认值
- 给来源打上 `Web Form`
- 对 Deal 自动创建组织和主联系人

### 7.2 线索分配流

线索创建后可通过两种方式进入负责人名下：

1. 手工指定 `Lead Owner`
2. 通过 `Assignment Rules` 自动分配

当负责人变化时，系统会：

- 自动共享文档给负责人
- 自动创建/更新待办分配

### 7.3 线索跟进流

销售在 Lead 页面进行所有跟进行为，核心结构是：

- 左侧：活动时间线
- 右侧：资料侧边栏

活动时间线支持：

- Activity
- Emails
- Comments
- Data
- Events
- Calls
- Tasks
- Notes
- Attachments
- WhatsApp

这意味着线索页就是“单客作战台”，不是简单资料卡。

### 7.4 线索转商机流

当线索具备推进价值后，通过 `Convert to Deal` 转为商机。

系统会自动完成：

1. 线索状态可更新为 `Qualified`
2. `converted = 1`
3. 若启用 SLA，沟通状态可自动变为 `Replied`
4. 创建或复用联系人
5. 创建或复用组织
6. 创建商机
7. 拷贝线索的关键信息到商机
8. 继承相关负责人/协作者

这是整个 CRM 最关键的主流程。

### 7.5 商机推进流

商机创建后，销售围绕以下动作推进：

- 更新状态
- 维护主联系人与组织信息
- 记录下一步行动 `Next Step`
- 维护预计成交时间和金额
- 维护产品清单与金额汇总
- 发邮件、建任务、建日程、打电话、发 WhatsApp

商机的经营重点是：

- 阶段是否清晰
- 责任人是否明确
- 关键联系人是否完整
- 预计金额/日期是否可信
- 产品与报价是否匹配

### 7.6 沟通与活动沉淀流

系统会把多种行为统一沉淀到时间线和关联记录中：

- 评论
- 邮件
- 附件
- 事件
- 通话
- 备注
- 任务

因此培训客户时要强调：

- 不要把沟通记录留在系统外
- 尽量在 Lead/Deal 里完成跟进动作
- 时间线是复盘、交接、审计的依据

### 7.7 日历与提醒流

日历页面使用 `Event` 作为底层模型，支持：

- 日/周/月视图
- 创建事件
- 关联线索/商机
- 参与人管理
- 默认提醒
- 单事件自定义提醒

提醒既支持：

- 系统通知
- 邮件通知

未单独设置提醒的事件，可继承 CRM 设置中的全局默认提醒。

### 7.8 SLA 响应流

SLA 可作用于：

- CRM Lead
- CRM Deal

SLA 管理逻辑包括：

- 根据条件匹配适用的 SLA
- 按工作日、工作时间、节假日计算响应截止时间
- 记录首次响应时间
- 支持滚动响应 `Rolling Responses`
- 给出状态：`First Response Due / Rolling Response Due / Failed / Fulfilled`

客户培训时要重点说明：

- SLA 是“响应时效管理”，不是商机推进阶段
- `Communication Status` 是 SLA 计算的重要输入

### 7.9 销售层级权限流

启用 `Sales Hierarchy` 后：

- 销售用户默认只看自己拥有或被分配的线索/商机
- 销售经理可看自己及下属团队的数据
- 被分配的 ToDo 也会沿层级向上可见

如果不启用层级权限：

- 销售经理通常保留更宽的数据可见范围

这个配置对客户组织的权限边界非常关键，交付时必须讲清楚。

### 7.10 组织信息自动补全流

系统支持基于官网做 `Domain Enrichment`。

触发方式：

- 新建 Lead / Deal / Organization 后自动后台补全
- 在详情页点击 `Enrich From Website`

可补全信息包括：

- 公司名称
- 公司简介
- Logo
- 行业
- 主邮箱/电话
- LinkedIn / X / Facebook 等社媒信息

注意：

- 补全结果依赖公开网站
- 是“辅助填充”，不是绝对真值
- 映射规则、覆盖策略可在后台配置

### 7.11 ERPNext 协同流

启用 ERPNext 集成后，系统支持：

- 商机状态达到指定阶段时自动创建 ERPNext Customer
- 从 CRM Deal 发起 ERPNext Quotation
- CRM Product 与 ERPNext Item 双向同步
- 跨站点 ERPNext 调用

适合培训客户理解为：

- CRM 管前端销售过程
- ERPNext 管后端交易与经营数据
- 两者通过“客户、报价、产品”打通

## 8. 页面使用说明

### 8.1 Leads 列表页

支持三种视图：

- List
- Group By
- Kanban

常见操作：

- 新建线索
- 快速筛选、排序、自定义列
- 新建备注
- 新建任务
- 快速拨号
- 进入详情页

默认只展示未转化线索。

### 8.2 Deals 列表页

支持：

- List
- Group By
- Kanban

常见操作：

- 新建商机
- 按状态看推进漏斗
- 按负责人、地区、来源分析
- 从列表直接加任务/备注/电话

### 8.3 Lead / Deal 详情页

详情页是培训的重头戏。

建议按照以下顺序讲：

1. 顶部操作区：状态、指派、转商机、定制动作
2. 左侧时间线：邮件/评论/任务/通话/事件等
3. 右侧资料区：基础字段、联系人、组织、SLA、丢单信息等
4. 附件与外部沟通入口

### 8.4 Contacts / Organizations

这两个页面的培训重点不是“单独用”，而是“作为客户主数据沉淀用”。

要让客户理解：

- 联系人解决“找谁”
- 组织解决“属于哪家公司”
- 商机解决“这笔机会推进到哪一步”

### 8.5 Tasks

任务支持列表和看板。

建议培训客户统一任务规范：

- 标题写动作，不写空泛描述
- 必填负责人
- 必填截止时间
- 尽量关联线索或商机

### 8.6 Calendar

培训重点：

- 如何创建事件
- 如何关联线索/商机
- 如何给参与人发提醒
- 如何用日历做销售节奏管理

### 8.7 Dashboard

仪表盘支持按时间范围、按销售人员查看。

常见指标包括：

- 总线索数
- 进行中商机数
- 赢单数
- 平均商机金额
- 销售趋势
- 预测收入
- 转化漏斗
- 按来源/地区/销售员统计

管理员可编辑 Dashboard 布局。

## 9. 设置中心说明

设置中心建议按下面顺序培训。

### 9.1 User Configuration

- Profile：个人资料
- Preferences：个人偏好

### 9.2 System Configuration

- General：通用设置
- Dashboard：看板配置
- Defaults：默认值
- Brand：品牌名称、Logo、Favicon
- Calendar：默认日历视图和提醒

### 9.3 User Management

- Users：用户清单
- Invite User：邀请用户
- Sales Hierarchy：销售层级树

### 9.4 Email

- Accounts：邮件账户
- Templates：邮件模板

### 9.5 Automation & Rules

- Assignment Rules：自动分配规则
- SLA Policies：SLA 规则
- Forms：公开表单设计器

### 9.6 Customization

- Home Actions：主页快捷动作

### 9.7 Integrations

- Telephony：电话集成
- WhatsApp：WhatsApp 集成
- ERPNext：ERP 联动
- Lead Syncing：线索同步

## 10. 推荐培训顺序

面向客户做培训时，建议分三段讲。

### 第一段：业务用户

1. 登录与主导航
2. Leads 列表与详情
3. 新建线索、跟进、建任务、加备注
4. 线索转商机
5. 商机推进与联系人维护
6. Calendar 与 Tasks

### 第二段：销售主管

1. Dashboard
2. Group By / Kanban 管理
3. 自定义视图
4. Assignment Rules
5. Sales Hierarchy
6. SLA

### 第三段：系统管理员

1. 用户与角色
2. 品牌与默认配置
3. 表单发布
4. 数据导入
5. 电话/WhatsApp/ERPNext/Lead Syncing
6. 运营口径与治理规范

## 11. 上线前配置清单

建议交付前和客户一起确认：

- 已创建销售角色与账号
- Lead Status 已确认
- Deal Status 已确认，概率已配置
- Lead Source 已确认
- Industry、Territory 已确认
- Sales Hierarchy 已确认
- Assignment Rules 已确认
- SLA 是否启用、规则是否测试通过
- 品牌名称、Logo、Favicon 已替换
- 邮件账户可正常发送
- 日历默认提醒已配置
- 表单已发布并联通
- 数据导入模板已演示
- 如需：Telephony / WhatsApp / ERPNext / Facebook Lead Sync 已联调

## 12. 客户日常使用建议

建议给客户明确三条管理规则：

1. 新线索当天必须分配负责人
2. 跟进动作必须沉淀在系统时间线里
3. 商机必须维护阶段、预计金额、预计关闭日期

这样 Dashboard、预测收入、转化漏斗才会有管理价值。

## 13. 常见交付提醒

### 13.1 这套系统最容易被误用的点

- 把 Leads 和 Deals 混着用
- 不维护主联系人
- 沟通在系统外发生，系统里不留痕
- 只改状态，不写任务和下一步
- Forecasting 开了，但预计金额和预计日期不维护

### 13.2 培训时要特别强调的点

- 线索是入口，商机是推进主体
- 联系人和组织是主数据，不是附属信息
- 时间线是交接依据
- 任务是执行闭环，不是装饰字段
- 配置项一旦改动，会直接影响口径和权限

## 14. 一句话业务总结

如果用一句话概括这套 CRM：

它把“线索进入、客户识别、销售推进、协作执行、节奏管理、结果分析、外部系统联动”整合在了同一个销售作业平台里。
