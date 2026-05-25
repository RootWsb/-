# Prod Skill Review Set

Review the candidate prod labels, then edit `ideal_skills` in the JSONL file.

## 1. no003

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
RD-001 产品需求全生命周期管理
1.1 需求描述
基于公司现有 OA / 万象协同平台，使用建设“产品需求”全生命周期管理模块，实现销售、售前、研发三方围绕同一需求单进行协同。
目标如下：
● 建立统一需求入口，避免需求分散在 IM、Excel、邮件中。
● 实现需求信息标准化录入与协同补充。
● 实现需求全过程留痕、可追溯、可审计。
● 为后续统计分析、报表、工时分析提供结构化数据。
---
1.2 业务流程
业务主流程
销售/售前都可以根据实际项目情况或市场情况创建需求工单，由多方（主要是销售部/研服部/研发部）参与，共同维护需求工单信息。
流程示例：
销售人员创建需求工单：项目作为可选项
研服人员补充需求信息
研发人员查看需求信息，明确需求后，纳入产品研发计划并跟新需求状态。
研发人员完成需求，并更新需求状态

信息同步方式
需求相关参与方有多种方式同步需求信息
• 基于评论系统实现需求的沟通和澄清，评论系统需要支持@功能，当用户在评论系统中@用户时，需要产生对应的通知信息通知到用户。
• 修改需求对象的描述信息或者是附件信息。
• 修改需求的状态
状态机设计
需求的状态设计如下：待处理、澄清中、研发中、阻塞中、已完成、已关闭
1.3 功能点
• 需求工单创建/查看/编辑/删除
• 需求工单评论
• 操作日志留痕（需求动态）
• 通知提醒
• 需求工单查询与导出
• 统计报表
---
1.3 功能点1：需求工单创建/查看/修改/删除
1.3.1 功能描述
销售/售前在 OA 系统中创建“产品需求”工单。
• 创建：主要由销售或售前负责创建（具备权限即可创建）
• 查看：
    ◦ 需求创建者可查看
    ◦ 需求处理人可查看
    ◦ 销售主管/售前主管/研发主管可查看
• 修改：
    ◦ 需求创建者可修改
    ◦ 需求处理人可修改
•  删除：
    ◦ 创建者可删除
    ◦ 销售主管/售前主管/研发主管可删除
表名：产品需求主表
• 中文名：产品需求主表（custom_requirement）
字段名
字段标识
字段类型
说明

工单编号
ticket_no
string
必填，系统自动生成

需求名称
name
string
必填

项目编号
project_no
string
选填，关联销售项目

处理人
owner
relation(user)
选填，支持多选

产品型号
product_model
relation
必填，关联系统中的产品

描述
desc
text
必填

附件
attachment
file
选填，支持配置多个

优先级
priority
select
必填，高/中/低

期望完成时间
expect_date
date
选填

当前状态
current_status
select
必填

预计开发周期
estimated_days
integer
选填

计划交付时间
planned_delivery_date
date
选填

创建时间
created_at
datetime
系统自动生成

创建人
created_by
relation(user)
系统自动生成

最近修改时间
update_at
datetme
系统自动生成

最近修改人
update_by
relation(user)
系统自动生成

是否终止
is_terminated
boolean
默认否

终止原因
terminate_reason
text
终止时必填

1.4 功能点2：需求工单评论
在需求工单详情中集成需求对象评论系统，项目创建人/处理人/管理者可以通过评论系统驱动需求。
评论系统核心记录：评论人+评论时间+评论内容，以时间倒序显示评论
评论人可以删除和修改自己的评论。
 
在评论板块中可以使用@指令指定用户，可以指定多个，当用户被@时，系统自动产生对应的通知消息通知用户，通知消息包含内容：关联的需求，时间，评论人，评论内容。
快捷操作：用户在通知中可以点击快速跳转到对应的需求。
1.5 功能点：操作日志留痕
在工单详情中所有的操作都记录动态日志，便于回溯和审计。
1.6 功能点：通知提醒
通知提醒分为两个方面：
• 当前用户在评论系统中被@时，系统自动产生通知信息
• 当用户被添加到处理人中时，系统自动产生通知信息.
1.7 功能点：需求查询与导出
需求显示页面支持筛选，选择维度有：
• 需求名称：模糊搜索
• 关联项目：下拉选择匹配
• 产品型号：下拉选择匹配
• 优先级：下拉匹配
• 处理人：下拉选择，包含关系
• 状态：下拉选择
• 创建时间：时间段搜索
 
筛选时基于当前用户已有权限展示数据进行筛选，不能跨过权限限制。
支持将需求导出为xlsx文档，以筛选结果为导出依据。
 
1.8 功能点：统计报表
支持查看需求工单的统计信息，统计信息展示内容如下
• 需求各状态发布数量情况（柱状图展示）
• 需求提出人分布情况（柱状图展示）
• 已延期需求top20列表，点击可查看需求详情
    ◦ 延期定义：到达期望完成时间时，还没有完成的需求
• 即将到期需求top20列表，点击可查看修去详情
 
1.4 插件需求
评论插件：当用户使用评论插件时，支持@功能，@用户后系统自动产生系统通知
```

## 2. no003

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
RD-001 产品需求全生命周期管理 1.1 需求描述 基于公司现有 OA / 万象协同平台，使用建设“产品需求”全生命周期管理模块，实现销售、售前、研发三方围绕同一需求单进行协同。 目标如下： ● 建立统一需求入口，避免需求分散在 IM、Excel、邮件中。 ● 实现需求信息标准化录入与协同补充。 ● 实现需求全过程留痕、可追溯、可审计。 ● 为后续统计分析、报表、工时分析提供结构化数据。
1.2 业务流程 业务主流程 销售/售前都可以根据实际项目情况或市场情况创建需求工单，由多方（主要是销售部/研服部/研发部）参与，共同维护需求工单信息。 流程示例： 销售人员创建需求工单：项目作为可选项 研服人员补充需求信息 研发人员查看需求信息，明确需求后，纳入产品研发计划并跟新需求状态。 研发人员完成需求，并更新需求状态

信息同步方式 需求相关参与方有多种方式同步需求信息 • 基于评论系统实现需求的沟通和澄清，评论系统需要支持@功能，当用户在评论系统中@用户时，需要产生对应的通知信息通知到用户。 • 修改需求对象的描述信息或者是附件信息。 • 修改需求的状态 状态机设计 需求的状态设计如下：待处理、澄清中、研发中、阻塞中、已完成、已关闭 1.3 功能点 • 需求工单创建/查看/编辑/删除 • 需求工单评论 • 操作日志留痕（需求动态） • 通知提醒 • 需求工单查询与导出 • 统计报表
1.3 功能点1：需求工单创建/查看/修改/删除 1.3.1 功能描述 销售/售前在 OA 系统中创建“产品需求”工单。 • 创建：主要由销售或售前负责创建（具备权限即可创建） • 查看： ◦ 需求创建者可查看 ◦ 需求处理人可查看 ◦ 销售主管/售前主管/研发主管可查看 • 修改： ◦ 需求创建者可修改 ◦ 需求处理人可修改 • 删除： ◦ 创建者可删除 ◦ 销售主管/售前主管/研发主管可删除 表名：产品需求主表 • 中文名：产品需求主表（custom_requirement） 字段名 字段标识 字段类型 说明

工单编号 ticket_no string 必填，系统自动生成

需求名称 name string 必填

项目编号 project_no string 选填，关联销售项目

处理人 owner relation(user) 选填，支持多选

产品型号 product_model relation 必填，关联系统中的产品

描述 desc text 必填

附件 attachment file 选填，支持配置多个

优先级 priority select 必填，高/中/低

期望完成时间 expect_date date 选填

当前状态 current_status select 必填

预计开发周期 estimated_days integer 选填

计划交付时间 planned_delivery_date date 选填

创建时间 created_at datetime 系统自动生成

创建人 created_by relation(user) 系统自动生成

最近修改时间 update_at datetme 系统自动生成

最近修改人 update_by relation(user) 系统自动生成

是否终止 is_terminated boolean 默认否

终止原因 terminate_reason text 终止时必填

1.4 功能点2：需求工单评论 在需求工单详情中集成需求对象评论系统，项目创建人/处理人/管理者可以通过评论系统驱动需求。 评论系统核心记录：评论人+评论时间+评论内容，以时间倒序显示评论 评论人可以删除和修改自己的评论。

在评论板块中可以使用@指令指定用户，可以指定多个，当用户被@时，系统自动产生对应的通知消息通知用户，通知消息包含内容：关联的需求，时间，评论人，评论内容。 快捷操作：用户在通知中可以点击快速跳转到对应的需求。 1.5 功能点：操作日志留痕 在工单详情中所有的操作都记录动态日志，便于回溯和审计。 1.6 功能点：通知提醒 通知提醒分为两个方面： • 当前用户在评论系统中被@时，系统自动产生通知信息 • 当用户被添加到处理人中时，系统自动产生通知信息. 1.7 功能点：需求查询与导出 需求显示页面支持筛选，选择维度有： • 需求名称：模糊搜索 • 关联项目：下拉选择匹配 • 产品型号：下拉选择匹配 • 优先级：下拉匹配 • 处理人：下拉选择，包含关系 • 状态：下拉选择 • 创建时间：时间段搜索

筛选时基于当前用户已有权限展示数据进行筛选，不能跨过权限限制。 支持将需求导出为xlsx文档，以筛选结果为导出依据。

1.8 功能点：统计报表 支持查看需求工单的统计信息，统计信息展示内容如下 • 需求各状态发布数量情况（柱状图展示） • 需求提出人分布情况（柱状图展示） • 已延期需求top20列表，点击可查看需求详情 ◦ 延期定义：到达期望完成时间时，还没有完成的需求 • 即将到期需求top20列表，点击可查看修去详情

1.4 插件需求 评论插件：当用户使用评论插件时，支持@功能，@用户后系统自动产生系统通知
```

## 3. 测试区块1

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
1 HR-001 业务合同审核管理
1.1 需求描述
实现合同审核全流程线上化管理，规范合同信息填写、业务类型识别、印章审核、附件审核等环节，确保合同合规、信息准确、审核高效；支持合同多维度搜索筛选、在线浏览打印、自动编号及数据导出，降低合同审核误差与合规风险，提升合同管理与审核效能，保障合同签订及履行全过程可追溯、可管控。
适用用户角色：销售专员、采购专员、合同审核专员、合同审核负责人、管理层。
1.2 业务流程

 
核心功能点列表：
合同录入登记
合同审核（甲乙方信息、业务类型、条款、印章）
合同档案管理
合同附件管理
合同信息定期核查
数据看板
筛选与导出
1.3 功能实现 
1.3.1 功能点1：合同录入登记
1.3.1.1 功能描述
业务专员通过表单录入合同基础信息，系统自动生成合同编号，提交后触发审核流程。
实现方式：
使用普通数据表创建合同主表
form 区块 + 前端联动校验规则（正则匹配违规字眼）+ 编号规则 {合同类型代码}{年份}{公司编号}{月份}{序号} 备注：敏感字眼识别，自动识别“挂靠社保、代缴社保、处理社保”等违规词，当前先正则匹配，后续实现AI审核。
保存时触发审批工作流（使用审批插件）
1.3.1.2 数据定义
表名：业务合同 标识：business_contracts 
备注：系统下人事板块下已经有 员工合同 contracts表，这个是业务合同表（销售合同、采购合同等）
字段名	字段标识	字段类型	说明
合同编号	contract_no	自动编码	必填，系统自动生成，格式如XSTL2025ZWS0314904
合同类型	contract_type	下拉单选	必填，选项：销售业务合同、销售采购合同
业务类型	business_type	下拉单选	必填，选项：代理记账、年检年审、其他等
甲方名称	party_a_name	单行文本	必填
甲方通讯地址	party_a_address	多行文本	必填
甲方联系人	party_a_contact	多对一	必填，关联员工信息
甲方手机	party_a_phone	电话号码	必填
乙方名称	party_b_name	单行文本	必填
乙方通讯地址	party_b_address	多行文本	必填
乙方联系人	party_a_contact	单行文本	必填
乙方手机	party_a_phone	电话号码	必填
委托事项名称	entrustment_name	多行文本	必填
代理期限	agency_period	日期范围	必填
完成时限	deadline	日期	必填
合同金额（大写）	amount_uppercase	单行文本	必填
合同金额（小写）	amount_lowercase	数字	必填
生效条款	effective_clause	多行文本	必填
附件	attachments	附件（多文件）	可选
项目交付表、报价单等
审核状态	review_status	下拉单选	选项：待审核、审核通过、审核驳回、待修改
异常类型	exception_type	下拉多选	选项：印章异常、附件异常、信息填写异常等
 创建人	createBy	系统	 
 创建时间 	createAt	系统	 
 最后修改人	lastUpdateBy	系统	 
 最后修改时间	lastUpdateAt	系统	 
 
1.3.2 功能点2：合同审核模块
1.3.2.1 功能描述
审核专员对合同进行全维度审核（甲乙方信息/业务类型/生效条款/金额/合同内容/印章/附件），审核通过/驳回，驳回注明原因。
实现方式：
使用审批工作流插件配置多节点审批
通过自定义按钮触发审核操作（通过/驳回）
驳回时使用弹窗表单填写驳回原因
审核记录自动写入关联的审核记录表
 
1.3.2.2 数据定义
表名：合同审核记录表 标识：business_contract_reviews
字段名	字段标识	字段类型	说明
关联合同	contract_id	多对一关联	必填，关联contracts表
审核人	reviewer	关联用户	必填
审核时间	review_time	日期时间	必填，自动记录当前时间
印章清晰度	seal_clarity	下拉单选	必填，印章清晰度，选项：清晰、模糊、不完整
印章与落款公司是否一致	seal_company_match	单选	必填，选项：是、否
是否含敏感违规字眼	has_sensitive_words	单选	必填，选项：是、否
审核结论	conclusion	下拉单选	必填，选项：通过、驳回
大小写金额是否一致	amount_match	下拉单选	必填，选项：通过、驳回
驳回原因	reject_reason	多行文本	驳回时必填
异常标注	exception_marks	JSON	记录各类异常详情
审核节点	review_node	下拉单选	选项：信息审核、印章审核、业务审核
 
1.3.3 功能点3：合同附件管理
1.3.3.1 功能描述
上传附件（项目交付表/报价单），校验合规性（禁止合并盖骑缝章、禁止报价单盖合同章），在线预览/打印。
实现方式：
使用附件字段存储文件
配置文件预览插件实现在线预览PDF
通过工作流实现附件合规性校验逻辑
附件异常时更新合同的exception_type字段
1.3.4.2 数据定义
表名：合同附件 标识：business_contract_attachments 
字段名	字段标识	字段类型	说明
关联合同	contract_id	belongsTo	必填，关联contracts表
附件类型	attachment_type	下拉单选	必填
附件文件	file	belongsToMany	必填
是否合规	is_compliant	单选	必填，是、否
合规问题描述	compliance_issue	多行文本	选填
 
1.3.3.3 附件校验规则
规则	校验逻辑
合同文件格式	仅支持PDF、JPG格式
合同底色	检查PDF页面是否存在填充底色
附件分离	项目交付表与合同文件需分文件上传
报价单用章	项目报价单禁止盖合同章
 
1.3.4 功能点4：到期提醒
1.3.4.1 功能描述
合同审核时限提醒（2工作日）、代理期限到期提醒
实现方式：
使用工作流插件配置定时任务
配置站内代办、企业微信通知渠道（先不做企业微信）
 
1.3.5 功能点5：数据看板
1.3.5.1 功能描述
1）看板统计卡片 : 展示合同总数、待审核/已通过/已驳回/当日新增/印章异常/附件异常/违规合同数。
2）数据看板：合同类型占比、审核通过率、业务类型占比、异常类型占比、合同金额统计、月度新增趋势、审核时效
实现方式：
基于 business_contracts collection 的 status 字段聚合查询
支持柱状图、饼图、折线图等ECharts图表类型
配置联动筛选区块，看板图表随筛选条件更新
启用数据下钻功能，点击图表穿透查看明细
 
1.3.5.2 核心指标定义
指标名称	计算规则
合同总数	contracts表所有记录数
待审核合同数	review_status = "待审核"
已审核通过合同数	review_status = "审核通过"
已审核驳回合同数	review_status = "审核驳回"
印章异常合同数	exception_type 包含"印章异常"
附件异常合同数	exception_type 包含"附件异常"
违规合同数	exception_type 包含违规类型
 
1.3.6 功能点6：权限配置
1.3.6.1 功能描述
基于角色的权限分级，控制不同用户的操作范围。
实现方式：
使用权限控制（ACL） 插件
支持字段级权限和数据范围权限
 
1.3.6.2 角色权限矩阵
角色	合同录入	合同审核	查看所有合同	配置权限	查看分析报告
销售/采购专员	✓	✗	✗（仅自己）	✗	✗
合同审核专员	✓	✓	✓	✗	✓
合同审核负责人	✓	✓	✓	✓	✓
管理层	✗	✗	✓	✗	✓
1.3.7 功能点7：筛选与导出
1.3.7.1 功能描述
支持多维度组合筛选，并导出筛选结果为Excel。
实现方式：
使用表格区块自带的筛选功能
配置导出记录
 
1.3.7.2 筛选维度
筛选项	字段
合同编号	contract_no
甲方公司	party_a_name
乙方名称	party_b_name
合同类型	contract_type
业务类型	business_type
审核状态	review_status
异常类型	exception_type
合同金额范围	amount_lowercase
1.3.9 功能点9：操作日志留存
1.3.9.1 功能描述
所有合同相关操作自动留存日志，便于合规核查与责任追溯。
实现方式：
使用审计日志插件
系统自动记录操作人、操作时间、操作类型、操作内容
 
1.4 插件需求
插件	是否有现成插件	说明
工作流	✅ 有	审批流程配置、定时任务
数据可视化	✅ 有	看板图表展示、联动筛选
审计日志	✅ 有	操作日志留存（企业版）
自动编码字段	✅ 有	合同编号自动生成
文件预览-PDF.js	✅ 有	PDF在线预览
企业微信	✅ 有	消息通知推送（专业版）
导出记录	✅ 有	Excel数据导出
权限控制（ACL）	✅ 有	角色权限管理
附件合规校验	❌ 需要开发	需通过工作流或自定义脚本实现
合同版本对比	❌ 需要开发	建议通过审计日志实现
```

## 4. 万象1

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, execute-test-cases`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-plugin-development, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
工作流设计（NocoBase）
触发器（Trigger）
类型：数据表事件

数据表：成绩表

触发时机：创建或更新后（afterCreate 或 afterUpdate）

触发条件：分数 < 60

动作（Actions）
动作1：查询关联信息
类型：查询数据

目标表：学生表

查询条件：学号 == 成绩表.学号

获取字段：姓名、年级、班级、班主任、联系电话

动作2：查询课程与教师
类型：查询数据

目标表：课程表

查询条件：课程编号 == 成绩表.课程编号

获取字段：课程名称、授课教师（关联到教师表获取教师姓名）

动作3：创建技术工单
类型：创建数据

目标表：技术工单（editorWorkOrder）

填充字段：

技术工单字段        填充值
状态        待处理
紧急度        高（分数<50） / 中（50-59）
项目等级        学习辅导
网站业务        学业支持（可映射为固定值）
网站分类        教学服务
地区        从学生表的班级/年级推断
网站名称        学生姓名 + “补课工单”
发起人        授课教师姓名
动作4：发送通知（可选）
类型：发送消息（邮件/站内信）

接收人：班主任、授课教师

内容模板：

text
学生 {学生姓名} 的 {课程名称} 成绩为 {分数} 分（不及格），
已自动生成技术工单（编号：{工单编号}），请及时安排辅导。
数据流转示意图
text
成绩录入（分数 < 60）
       │
       ▼
触发工作流（afterCreate/afterUpdate）
       │
       ├──► 查询学生表（获取班主任、班级）
       │
       ├──► 查询课程表（获取授课教师）
       │
       └──► 创建技术工单（关联学生、课程、教师）
                │
                ▼
         发送通知给班主任/教师
验收标准（工作流部分）
验收项        预期结果
触发条件        录入成绩 < 60 时触发，≥ 60 时不触发
工单创建        技术工单表中自动新增一条记录，字段正确填充
关联关系        工单能正确关联到成绩对应的学生、课程、教师
通知发送        班主任和授课教师收到通知（如实现）
重复触发        更新成绩从不及格→及格时，不创建重复工单
幂等性        同一成绩多次触发只产生一个工单（可增加去重逻辑）
NocoBase 实现要点
在“成绩表”上配置工作流：

进入 NocoBase → 插件管理 → 工作流

新建工作流 → 选择数据表事件 → 选择“成绩表”

配置条件节点：

添加“条件判断”节点

条件：{{ $context.data.分数 }} < 60

配置查询节点：

使用“查询数据”节点获取学生、课程、教师信息

配置创建节点：

使用“创建数据”节点，目标表选择“技术工单”
```

## 5. 万象1

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, execute-test-cases`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-plugin-development, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
工作流设计（NocoBase）
触发器（Trigger）
类型：数据表事件

数据表：成绩表

触发时机：创建或更新后（afterCreate 或 afterUpdate）

触发条件：分数 < 60

动作（Actions）
动作1：查询关联信息
类型：查询数据

目标表：学生表

查询条件：学号 == 成绩表.学号

获取字段：姓名、年级、班级、班主任、联系电话

动作2：查询课程与教师
类型：查询数据

目标表：课程表

查询条件：课程编号 == 成绩表.课程编号

获取字段：课程名称、授课教师（关联到教师表获取教师姓名）

动作3：创建技术工单
类型：创建数据

目标表：技术工单（editorWorkOrder）

填充字段：

技术工单字段        填充值
状态        待处理
紧急度        高（分数<50） / 中（50-59）
项目等级        学习辅导
网站业务        学业支持（可映射为固定值）
网站分类        教学服务
地区        从学生表的班级/年级推断
网站名称        学生姓名 + “补课工单”
发起人        授课教师姓名
动作4：发送通知（可选）
类型：发送消息（邮件/站内信）

接收人：班主任、授课教师

内容模板：

text
学生 {学生姓名} 的 {课程名称} 成绩为 {分数} 分（不及格），
已自动生成技术工单（编号：{工单编号}），请及时安排辅导。
数据流转示意图
text
成绩录入（分数 < 60）
       │
       ▼
触发工作流（afterCreate/afterUpdate）
       │
       ├──► 查询学生表（获取班主任、班级）
       │
       ├──► 查询课程表（获取授课教师）
       │
       └──► 创建技术工单（关联学生、课程、教师）
                │
                ▼
         发送通知给班主任/教师
验收标准（工作流部分）
验收项        预期结果
触发条件        录入成绩 < 60 时触发，≥ 60 时不触发
工单创建        技术工单表中自动新增一条记录，字段正确填充
关联关系        工单能正确关联到成绩对应的学生、课程、教师
通知发送        班主任和授课教师收到通知（如实现）
重复触发        更新成绩从不及格→及格时，不创建重复工单
幂等性        同一成绩多次触发只产生一个工单（可增加去重逻辑）
NocoBase 实现要点
在“成绩表”上配置工作流：

进入 NocoBase → 插件管理 → 工作流

新建工作流 → 选择数据表事件 → 选择“成绩表”

配置条件节点：

添加“条件判断”节点

条件：{{ $context.data.分数 }} < 60

配置查询节点：

使用“查询数据”节点获取学生、课程、教师信息

配置创建节点：

使用“创建数据”节点，目标表选择“技术工单”
```

## 6. no003

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
RD-001 产品需求全生命周期管理
1.1 需求描述
基于公司现有 OA / 万象协同平台，使用建设“产品需求”全生命周期管理模块，实现销售、售前、研发三方围绕同一需求单进行协同。
目标如下：
● 建立统一需求入口，避免需求分散在 IM、Excel、邮件中。
● 实现需求信息标准化录入与协同补充。
● 实现需求全过程留痕、可追溯、可审计。
● 为后续统计分析、报表、工时分析提供结构化数据。
---
1.2 业务流程
业务主流程
销售/售前都可以根据实际项目情况或市场情况创建需求工单，由多方（主要是销售部/研服部/研发部）参与，共同维护需求工单信息。
流程示例：
销售人员创建需求工单：项目作为可选项
研服人员补充需求信息
研发人员查看需求信息，明确需求后，纳入产品研发计划并跟新需求状态。
研发人员完成需求，并更新需求状态

信息同步方式
需求相关参与方有多种方式同步需求信息
• 基于评论系统实现需求的沟通和澄清，评论系统需要支持@功能，当用户在评论系统中@用户时，需要产生对应的通知信息通知到用户。
• 修改需求对象的描述信息或者是附件信息。
• 修改需求的状态
状态机设计
需求的状态设计如下：待处理、澄清中、研发中、阻塞中、已完成、已关闭
1.3 功能点
• 需求工单创建/查看/编辑/删除
• 需求工单评论
• 操作日志留痕（需求动态）
• 通知提醒
• 需求工单查询与导出
• 统计报表
---
1.3 功能点1：需求工单创建/查看/修改/删除
1.3.1 功能描述
销售/售前在 OA 系统中创建“产品需求”工单。
• 创建：主要由销售或售前负责创建（具备权限即可创建）
• 查看：
    ◦ 需求创建者可查看
    ◦ 需求处理人可查看
    ◦ 销售主管/售前主管/研发主管可查看
• 修改：
    ◦ 需求创建者可修改
    ◦ 需求处理人可修改
•  删除：
    ◦ 创建者可删除
    ◦ 销售主管/售前主管/研发主管可删除
表名：产品需求主表
• 中文名：产品需求主表（custom_requirement）
字段名
字段标识
字段类型
说明

工单编号
ticket_no
string
必填，系统自动生成

需求名称
name
string
必填

项目编号
project_no
string
选填，关联销售项目

处理人
owner
relation(user)
选填，支持多选

产品型号
product_model
relation
必填，关联系统中的产品

描述
desc
text
必填

附件
attachment
file
选填，支持配置多个

优先级
priority
select
必填，高/中/低

期望完成时间
expect_date
date
选填

当前状态
current_status
select
必填

预计开发周期
estimated_days
integer
选填

计划交付时间
planned_delivery_date
date
选填

创建时间
created_at
datetime
系统自动生成

创建人
created_by
relation(user)
系统自动生成

最近修改时间
update_at
datetme
系统自动生成

最近修改人
update_by
relation(user)
系统自动生成

是否终止
is_terminated
boolean
默认否

终止原因
terminate_reason
text
终止时必填

1.4 功能点2：需求工单评论
在需求工单详情中集成需求对象评论系统，项目创建人/处理人/管理者可以通过评论系统驱动需求。
评论系统核心记录：评论人+评论时间+评论内容，以时间倒序显示评论
评论人可以删除和修改自己的评论。
 
在评论板块中可以使用@指令指定用户，可以指定多个，当用户被@时，系统自动产生对应的通知消息通知用户，通知消息包含内容：关联的需求，时间，评论人，评论内容。
快捷操作：用户在通知中可以点击快速跳转到对应的需求。
1.5 功能点：操作日志留痕
在工单详情中所有的操作都记录动态日志，便于回溯和审计。
1.6 功能点：通知提醒
通知提醒分为两个方面：
• 当前用户在评论系统中被@时，系统自动产生通知信息
• 当用户被添加到处理人中时，系统自动产生通知信息.
1.7 功能点：需求查询与导出
需求显示页面支持筛选，选择维度有：
• 需求名称：模糊搜索
• 关联项目：下拉选择匹配
• 产品型号：下拉选择匹配
• 优先级：下拉匹配
• 处理人：下拉选择，包含关系
• 状态：下拉选择
• 创建时间：时间段搜索
 
筛选时基于当前用户已有权限展示数据进行筛选，不能跨过权限限制。
支持将需求导出为xlsx文档，以筛选结果为导出依据。
 
1.8 功能点：统计报表
支持查看需求工单的统计信息，统计信息展示内容如下
• 需求各状态发布数量情况（柱状图展示）
• 需求提出人分布情况（柱状图展示）
• 已延期需求top20列表，点击可查看需求详情
    ◦ 延期定义：到达期望完成时间时，还没有完成的需求
• 即将到期需求top20列表，点击可查看修去详情
 
1.4 插件需求
评论插件：当用户使用评论插件时，支持@功能，@用户后系统自动产生系统通知
```

## 7. no003

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
RD-001 产品需求全生命周期管理 1.1 需求描述 基于公司现有 OA / 万象协同平台，使用建设“产品需求”全生命周期管理模块，实现销售、售前、研发三方围绕同一需求单进行协同。 目标如下： ● 建立统一需求入口，避免需求分散在 IM、Excel、邮件中。 ● 实现需求信息标准化录入与协同补充。 ● 实现需求全过程留痕、可追溯、可审计。 ● 为后续统计分析、报表、工时分析提供结构化数据。
1.2 业务流程 业务主流程 销售/售前都可以根据实际项目情况或市场情况创建需求工单，由多方（主要是销售部/研服部/研发部）参与，共同维护需求工单信息。 流程示例： 销售人员创建需求工单：项目作为可选项 研服人员补充需求信息 研发人员查看需求信息，明确需求后，纳入产品研发计划并跟新需求状态。 研发人员完成需求，并更新需求状态

信息同步方式 需求相关参与方有多种方式同步需求信息 • 基于评论系统实现需求的沟通和澄清，评论系统需要支持@功能，当用户在评论系统中@用户时，需要产生对应的通知信息通知到用户。 • 修改需求对象的描述信息或者是附件信息。 • 修改需求的状态 状态机设计 需求的状态设计如下：待处理、澄清中、研发中、阻塞中、已完成、已关闭 1.3 功能点 • 需求工单创建/查看/编辑/删除 • 需求工单评论 • 操作日志留痕（需求动态） • 通知提醒 • 需求工单查询与导出 • 统计报表
1.3 功能点1：需求工单创建/查看/修改/删除 1.3.1 功能描述 销售/售前在 OA 系统中创建“产品需求”工单。 • 创建：主要由销售或售前负责创建（具备权限即可创建） • 查看： ◦ 需求创建者可查看 ◦ 需求处理人可查看 ◦ 销售主管/售前主管/研发主管可查看 • 修改： ◦ 需求创建者可修改 ◦ 需求处理人可修改 • 删除： ◦ 创建者可删除 ◦ 销售主管/售前主管/研发主管可删除 表名：产品需求主表 • 中文名：产品需求主表（custom_requirement） 字段名 字段标识 字段类型 说明

工单编号 ticket_no string 必填，系统自动生成

需求名称 name string 必填

项目编号 project_no string 选填，关联销售项目

处理人 owner relation(user) 选填，支持多选

产品型号 product_model relation 必填，关联系统中的产品

描述 desc text 必填

附件 attachment file 选填，支持配置多个

优先级 priority select 必填，高/中/低

期望完成时间 expect_date date 选填

当前状态 current_status select 必填

预计开发周期 estimated_days integer 选填

计划交付时间 planned_delivery_date date 选填

创建时间 created_at datetime 系统自动生成

创建人 created_by relation(user) 系统自动生成

最近修改时间 update_at datetme 系统自动生成

最近修改人 update_by relation(user) 系统自动生成

是否终止 is_terminated boolean 默认否

终止原因 terminate_reason text 终止时必填

1.4 功能点2：需求工单评论 在需求工单详情中集成需求对象评论系统，项目创建人/处理人/管理者可以通过评论系统驱动需求。 评论系统核心记录：评论人+评论时间+评论内容，以时间倒序显示评论 评论人可以删除和修改自己的评论。

在评论板块中可以使用@指令指定用户，可以指定多个，当用户被@时，系统自动产生对应的通知消息通知用户，通知消息包含内容：关联的需求，时间，评论人，评论内容。 快捷操作：用户在通知中可以点击快速跳转到对应的需求。 1.5 功能点：操作日志留痕 在工单详情中所有的操作都记录动态日志，便于回溯和审计。 1.6 功能点：通知提醒 通知提醒分为两个方面： • 当前用户在评论系统中被@时，系统自动产生通知信息 • 当用户被添加到处理人中时，系统自动产生通知信息. 1.7 功能点：需求查询与导出 需求显示页面支持筛选，选择维度有： • 需求名称：模糊搜索 • 关联项目：下拉选择匹配 • 产品型号：下拉选择匹配 • 优先级：下拉匹配 • 处理人：下拉选择，包含关系 • 状态：下拉选择 • 创建时间：时间段搜索

筛选时基于当前用户已有权限展示数据进行筛选，不能跨过权限限制。 支持将需求导出为xlsx文档，以筛选结果为导出依据。

1.8 功能点：统计报表 支持查看需求工单的统计信息，统计信息展示内容如下 • 需求各状态发布数量情况（柱状图展示） • 需求提出人分布情况（柱状图展示） • 已延期需求top20列表，点击可查看需求详情 ◦ 延期定义：到达期望完成时间时，还没有完成的需求 • 即将到期需求top20列表，点击可查看修去详情

1.4 插件需求 评论插件：当用户使用评论插件时，支持@功能，@用户后系统自动产生系统通知
```

## 8. 测试区块1

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
1 HR-001 业务合同审核管理
1.1 需求描述
实现合同审核全流程线上化管理，规范合同信息填写、业务类型识别、印章审核、附件审核等环节，确保合同合规、信息准确、审核高效；支持合同多维度搜索筛选、在线浏览打印、自动编号及数据导出，降低合同审核误差与合规风险，提升合同管理与审核效能，保障合同签订及履行全过程可追溯、可管控。
适用用户角色：销售专员、采购专员、合同审核专员、合同审核负责人、管理层。
1.2 业务流程

 
核心功能点列表：
合同录入登记
合同审核（甲乙方信息、业务类型、条款、印章）
合同档案管理
合同附件管理
合同信息定期核查
数据看板
筛选与导出
1.3 功能实现 
1.3.1 功能点1：合同录入登记
1.3.1.1 功能描述
业务专员通过表单录入合同基础信息，系统自动生成合同编号，提交后触发审核流程。
实现方式：
使用普通数据表创建合同主表
form 区块 + 前端联动校验规则（正则匹配违规字眼）+ 编号规则 {合同类型代码}{年份}{公司编号}{月份}{序号} 备注：敏感字眼识别，自动识别“挂靠社保、代缴社保、处理社保”等违规词，当前先正则匹配，后续实现AI审核。
保存时触发审批工作流（使用审批插件）
1.3.1.2 数据定义
表名：业务合同 标识：business_contracts 
备注：系统下人事板块下已经有 员工合同 contracts表，这个是业务合同表（销售合同、采购合同等）
字段名	字段标识	字段类型	说明
合同编号	contract_no	自动编码	必填，系统自动生成，格式如XSTL2025ZWS0314904
合同类型	contract_type	下拉单选	必填，选项：销售业务合同、销售采购合同
业务类型	business_type	下拉单选	必填，选项：代理记账、年检年审、其他等
甲方名称	party_a_name	单行文本	必填
甲方通讯地址	party_a_address	多行文本	必填
甲方联系人	party_a_contact	多对一	必填，关联员工信息
甲方手机	party_a_phone	电话号码	必填
乙方名称	party_b_name	单行文本	必填
乙方通讯地址	party_b_address	多行文本	必填
乙方联系人	party_a_contact	单行文本	必填
乙方手机	party_a_phone	电话号码	必填
委托事项名称	entrustment_name	多行文本	必填
代理期限	agency_period	日期范围	必填
完成时限	deadline	日期	必填
合同金额（大写）	amount_uppercase	单行文本	必填
合同金额（小写）	amount_lowercase	数字	必填
生效条款	effective_clause	多行文本	必填
附件	attachments	附件（多文件）	可选
项目交付表、报价单等
审核状态	review_status	下拉单选	选项：待审核、审核通过、审核驳回、待修改
异常类型	exception_type	下拉多选	选项：印章异常、附件异常、信息填写异常等
 创建人	createBy	系统	 
 创建时间 	createAt	系统	 
 最后修改人	lastUpdateBy	系统	 
 最后修改时间	lastUpdateAt	系统	 
 
1.3.2 功能点2：合同审核模块
1.3.2.1 功能描述
审核专员对合同进行全维度审核（甲乙方信息/业务类型/生效条款/金额/合同内容/印章/附件），审核通过/驳回，驳回注明原因。
实现方式：
使用审批工作流插件配置多节点审批
通过自定义按钮触发审核操作（通过/驳回）
驳回时使用弹窗表单填写驳回原因
审核记录自动写入关联的审核记录表
 
1.3.2.2 数据定义
表名：合同审核记录表 标识：business_contract_reviews
字段名	字段标识	字段类型	说明
关联合同	contract_id	多对一关联	必填，关联contracts表
审核人	reviewer	关联用户	必填
审核时间	review_time	日期时间	必填，自动记录当前时间
印章清晰度	seal_clarity	下拉单选	必填，印章清晰度，选项：清晰、模糊、不完整
印章与落款公司是否一致	seal_company_match	单选	必填，选项：是、否
是否含敏感违规字眼	has_sensitive_words	单选	必填，选项：是、否
审核结论	conclusion	下拉单选	必填，选项：通过、驳回
大小写金额是否一致	amount_match	下拉单选	必填，选项：通过、驳回
驳回原因	reject_reason	多行文本	驳回时必填
异常标注	exception_marks	JSON	记录各类异常详情
审核节点	review_node	下拉单选	选项：信息审核、印章审核、业务审核
 
1.3.3 功能点3：合同附件管理
1.3.3.1 功能描述
上传附件（项目交付表/报价单），校验合规性（禁止合并盖骑缝章、禁止报价单盖合同章），在线预览/打印。
实现方式：
使用附件字段存储文件
配置文件预览插件实现在线预览PDF
通过工作流实现附件合规性校验逻辑
附件异常时更新合同的exception_type字段
1.3.4.2 数据定义
表名：合同附件 标识：business_contract_attachments 
字段名	字段标识	字段类型	说明
关联合同	contract_id	belongsTo	必填，关联contracts表
附件类型	attachment_type	下拉单选	必填
附件文件	file	belongsToMany	必填
是否合规	is_compliant	单选	必填，是、否
合规问题描述	compliance_issue	多行文本	选填
 
1.3.3.3 附件校验规则
规则	校验逻辑
合同文件格式	仅支持PDF、JPG格式
合同底色	检查PDF页面是否存在填充底色
附件分离	项目交付表与合同文件需分文件上传
报价单用章	项目报价单禁止盖合同章
 
1.3.4 功能点4：到期提醒
1.3.4.1 功能描述
合同审核时限提醒（2工作日）、代理期限到期提醒
实现方式：
使用工作流插件配置定时任务
配置站内代办、企业微信通知渠道（先不做企业微信）
 
1.3.5 功能点5：数据看板
1.3.5.1 功能描述
1）看板统计卡片 : 展示合同总数、待审核/已通过/已驳回/当日新增/印章异常/附件异常/违规合同数。
2）数据看板：合同类型占比、审核通过率、业务类型占比、异常类型占比、合同金额统计、月度新增趋势、审核时效
实现方式：
基于 business_contracts collection 的 status 字段聚合查询
支持柱状图、饼图、折线图等ECharts图表类型
配置联动筛选区块，看板图表随筛选条件更新
启用数据下钻功能，点击图表穿透查看明细
 
1.3.5.2 核心指标定义
指标名称	计算规则
合同总数	contracts表所有记录数
待审核合同数	review_status = "待审核"
已审核通过合同数	review_status = "审核通过"
已审核驳回合同数	review_status = "审核驳回"
印章异常合同数	exception_type 包含"印章异常"
附件异常合同数	exception_type 包含"附件异常"
违规合同数	exception_type 包含违规类型
 
1.3.6 功能点6：权限配置
1.3.6.1 功能描述
基于角色的权限分级，控制不同用户的操作范围。
实现方式：
使用权限控制（ACL） 插件
支持字段级权限和数据范围权限
 
1.3.6.2 角色权限矩阵
角色	合同录入	合同审核	查看所有合同	配置权限	查看分析报告
销售/采购专员	✓	✗	✗（仅自己）	✗	✗
合同审核专员	✓	✓	✓	✗	✓
合同审核负责人	✓	✓	✓	✓	✓
管理层	✗	✗	✓	✗	✓
1.3.7 功能点7：筛选与导出
1.3.7.1 功能描述
支持多维度组合筛选，并导出筛选结果为Excel。
实现方式：
使用表格区块自带的筛选功能
配置导出记录
 
1.3.7.2 筛选维度
筛选项	字段
合同编号	contract_no
甲方公司	party_a_name
乙方名称	party_b_name
合同类型	contract_type
业务类型	business_type
审核状态	review_status
异常类型	exception_type
合同金额范围	amount_lowercase
1.3.9 功能点9：操作日志留存
1.3.9.1 功能描述
所有合同相关操作自动留存日志，便于合规核查与责任追溯。
实现方式：
使用审计日志插件
系统自动记录操作人、操作时间、操作类型、操作内容
 
1.4 插件需求
插件	是否有现成插件	说明
工作流	✅ 有	审批流程配置、定时任务
数据可视化	✅ 有	看板图表展示、联动筛选
审计日志	✅ 有	操作日志留存（企业版）
自动编码字段	✅ 有	合同编号自动生成
文件预览-PDF.js	✅ 有	PDF在线预览
企业微信	✅ 有	消息通知推送（专业版）
导出记录	✅ 有	Excel数据导出
权限控制（ACL）	✅ 有	角色权限管理
附件合规校验	❌ 需要开发	需通过工作流或自定义脚本实现
合同版本对比	❌ 需要开发	建议通过审计日志实现
```

## 9. no003

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; acl keyword; debug keyword; planning keyword`

```text
请在V2页面帮我加一个导出的按钮。
需求名称： 增强导出功能，实现列表联动与大数据量导出优化
需求背景：
当前列表字段配置与导出功能的可导出字段为两套独立配置，当列表字段发生变化（增删、排序、修改取值）后，导出字段不会自动同步，需人工二次维护，导致导出内容与列表显示不一致或导出功能失效。
导出操作仅支持同步导出全量数据，在列表经过筛选后仍会导出全部数据，无法“所见即所得”导出当前视图中的筛选结果。
单次导出数据量较大时（如超过数万行），同步导出耗时过长，易触发请求超时，严重影响用户体验。
需求目标：
提供一种更加灵活、自动化的导出方案，使得导出字段、筛选条件与当前列表视图保持联动，并支持大数据量场景下的异步导出与下载通知，降低维护成本，提升导出效率和用户体验。
功能要求：
字段自动同步
导出时默认使用当前列表显示的字段（含字段名称和顺序），无需手动配置导出字段。
当列表字段发生变更时，导出内容自动匹配最新列表字段，确保表头与列表一致。
导出当前视图数据
导出内容必须严格基于用户当前在列表中的筛选、搜索和排序结果，即“所见即所得”。
若用户未设置任何筛选，则导出全量数据；若设置了过滤条件，只导出过滤后的数据。
大数据量异步导出
当导出数据量超出设定阈值（如 5000 行）或预估耗时较长时，自动切换为异步导出模式。
用户点击导出后立即收到任务已提交的提示，无需长时间等待。
后台异步生成文件，完成后通过站内信、系统通知或其他方式告知用户，并提供下载链接。
文件格式与兼容性
支持导出为 CSV、Excel 等常见格式，并允许用户选择。
文件命名应包含导出时间、模块名称等信息，便于识别。
性能与稳定性
避免因一次性查询大量数据造成服务端内存溢出或请求超时，需支持分页查询与流式生成文件。
异步导出任务应具备失败重试和状态记录能力，用户可查看导出历史及下载已生成的文件（可选）。
用户场景描述：
业务人员 A 修改了客户列表的显示列和过滤条件，通知数据分析人员 B 需要导出当前视图的数据。B 无需了解 A 具体调整了哪些字段，只需打开对应列表并点击导出，即可获得与 A 当前屏幕一致的报表。
市场人员筛选出过去半年交易金额大于 10 万的客户列表（共 20000 条），点击导出后，页面不再长时间等待，而是提示“导出任务已创建，稍后请在通知中心下载”。几分钟后，该人员收到通知，下载完整的 CSV 文件。
非功能需求：
异步导出任务应在 10 分钟内完成，超过时间需给出异常提示。
导出的文件应包含 UTF-8 BOM 头，以解决中文乱码问题。
该功能需兼容 NocoBase 现有的权限体系，仅允许有列表查看权限的用户导出对应数据。
```

## 10. docker

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, execute-test-cases`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; debug keyword; test keyword; planning keyword`

```text
需求-合作商功能搭建
需求描述
      搭建一个合作商管理页面，支持添加分类、按照分类查看合作商、支持新增、编辑、删除合作商。

 1. 搭建分类体系（树表）
表名：合作商分类，标题：合作商分类
●表类型：分类
●核心字段：
○名称：合作商分类表
○编码：partner_Category

2. 搭建合作商数据表
●表名：合作商，标题：合作商
●表类型：普通表
●字段设计：
  字段标题	字段类型	配置说明
  编码	自增整数	唯一
  名称	单行文本	设置「必填」验证规则
  分类类型表	多对一	关联到「分类类型」表
  类型	多对一	同样关联到「分类节点」表——这个字段用来绑定具体的分类节点
  统一社会信用代码	单行文本	
  状态	下拉菜单（单选）	选项：启用（绿色）、禁用（灰色）
  联系人	单行文本	
  联系人电话	电话	或单行文本，可加格式验证
  邮箱	邮箱	自动验证邮箱格式
注意：「分类类型表」和「类型」两个字段的区别：前者是关联到分类表整体，后者是关联到具体的分类节点。

3. 搭建合作商管理区块（页面）
页面布局：左右结构（经典方案）
●左侧：树筛选区块 → 展示合作商分类树
●右侧：表格区块 → 展示合作商列表，按左侧选中分类筛选
具体步骤：
1.创建新页面：命名为“合作商管理”
2.添加树筛选区块
●区块类型：筛选区块 → 树
●绑定数据表：合作商分类
●标题字段：选择「名称」
●开启「筛选子节点」（选择父分类时自动包含子分类数据）
3.添加表格区块
●区块类型：数据区块 → 表格
●绑定数据表：合作商
●连接树筛选：配置「连接数据区块」，关联到左侧的树筛选区块
●配置显示的列：编码、名称、类型、统一社会信用代码、状态、联系人、电话、邮箱
4.配置表格操作栏：
●添加「新增」按钮 → 弹出表单区块，包含所有字段
●添加「编辑」操作 → 行内编辑或弹窗编辑
●添加「删除」操作 → 确认后删除
4. 支持分类管理（增删改查）
●在「合作商分类」表中直接操作，或用另一个页面管理分类树
●支持的操作：新增根分类、新增子分类（在节点上右键或点击“添加子记录”）、编辑分类名称、删除分类（注意：删除前检查是否有合作商关联，避免数据孤儿）
```

## 11. no003

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-data-analysis, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; acl keyword; debug keyword; planning keyword`

```text
请在V2页面帮我加一个导出的按钮。
需求名称： 增强导出功能，实现列表联动与大数据量导出优化
需求背景：
当前列表字段配置与导出功能的可导出字段为两套独立配置，当列表字段发生变化（增删、排序、修改取值）后，导出字段不会自动同步，需人工二次维护，导致导出内容与列表显示不一致或导出功能失效。
导出操作仅支持同步导出全量数据，在列表经过筛选后仍会导出全部数据，无法“所见即所得”导出当前视图中的筛选结果。
单次导出数据量较大时（如超过数万行），同步导出耗时过长，易触发请求超时，严重影响用户体验。
需求目标：
提供一种更加灵活、自动化的导出方案，使得导出字段、筛选条件与当前列表视图保持联动，并支持大数据量场景下的异步导出与下载通知，降低维护成本，提升导出效率和用户体验。
功能要求：
字段自动同步
导出时默认使用当前列表显示的字段（含字段名称和顺序），无需手动配置导出字段。
当列表字段发生变更时，导出内容自动匹配最新列表字段，确保表头与列表一致。
导出当前视图数据
导出内容必须严格基于用户当前在列表中的筛选、搜索和排序结果，即“所见即所得”。
若用户未设置任何筛选，则导出全量数据；若设置了过滤条件，只导出过滤后的数据。
大数据量异步导出
当导出数据量超出设定阈值（如 5000 行）或预估耗时较长时，自动切换为异步导出模式。
用户点击导出后立即收到任务已提交的提示，无需长时间等待。
后台异步生成文件，完成后通过站内信、系统通知或其他方式告知用户，并提供下载链接。
文件格式与兼容性
支持导出为 CSV、Excel 等常见格式，并允许用户选择。
文件命名应包含导出时间、模块名称等信息，便于识别。
性能与稳定性
避免因一次性查询大量数据造成服务端内存溢出或请求超时，需支持分页查询与流式生成文件。
异步导出任务应具备失败重试和状态记录能力，用户可查看导出历史及下载已生成的文件（可选）。
用户场景描述：
业务人员 A 修改了客户列表的显示列和过滤条件，通知数据分析人员 B 需要导出当前视图的数据。B 无需了解 A 具体调整了哪些字段，只需打开对应列表并点击导出，即可获得与 A 当前屏幕一致的报表。
市场人员筛选出过去半年交易金额大于 10 万的客户列表（共 20000 条），点击导出后，页面不再长时间等待，而是提示“导出任务已创建，稍后请在通知中心下载”。几分钟后，该人员收到通知，下载完整的 CSV 文件。
非功能需求：
异步导出任务应在 10 分钟内完成，超过时间需给出异常提示。
导出的文件应包含 UTF-8 BOM 头，以解决中文乱码问题。
该功能需兼容 NocoBase 现有的权限体系，仅允许有列表查看权限的用户导出对应数据。
```

## 12. 页面搭建

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, dispatching-parallel-agents`
- prod_candidate_skills: `brainstorming, dispatching-parallel-agents, nocobase-data-analysis, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; planning keyword`

```text
资金日报可视化看板
7.1 需求描述
实现资金收支数据实时可视化，同步OA系统现有资金相关字段，支持多维度筛选与明细穿透。
7.2 业务流程

 
OA系统资金数据(回款表/到款表/费用审批表) → 自动汇总计算
 → 看板展示：收款总额/付款总额 + 分类饼图(现金/转账/汇票)
 → 周期切换(日/周/月/季/年) → 实时刷新(每15分钟)
 → 点击穿透 → 资金明细列表(对象/金额/时间/备注/操作人)
→ 导出Excel 
后期: 银企直联自动同步银行流水
7.3 功能实现 
7.3.1 数据展示
在现有回款(`order_collection_amount`)/到款(`order_receipt_amount`)数据基础上，构建出纳模块资金日报看板：实时展示收款/付款总额、分类统计、周期筛选、明细穿透、自动刷新。后期对接银企直联实现银行到款自动更新。
实时展示当日/选定周期内的收款总额、付款总额，按收款类型、付款类型分别统计金额、笔数及占比，支持周期筛选、明细穿透、数据导出。
实现方式：
NocoBase 统计区块 + 图表区块（饼图），数据源聚合查询`order_collection_amount` + `order_receipt_amount` + `approval_fee`
7.3.2 数据定义
表名：资金日报汇总（可缓存聚合表）  
标识：fund_daily_summary
汇总表是自动生成的（供看板快速读取）
字段名	字段标识	字段类型	说明
统计日期	stat_date	时间	汇总的是哪一天的数据，如2026-05-14
收款总额	total_receipt	数字	当天所有收款的金额合计
付款总额	total_payment	数字	当天所有付款的金额合计
收款笔数	receipt_count	整数	当天的收款总笔数
付款笔数	payment_count	整数	当天的付款总笔数
现金收款	receipt_cash	数字	资金类型=现金 的收款金额
转账收款	receipt_transfer	数字	资金类型=转账 的收款金额
汇票收款	receipt_draft	数字	资金类型=汇票 的收款金额
对公付款	payment_corporate	数字	资金类型=对公付款 的付款金额
个人报销	payment_reimburse	数字	资金类型=个人报销 的付款金额
税费缴纳	payment_tax	数值	资金类型=税费缴纳 的付款金额


帮我搭建页面
```

## 13. docker

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, execute-test-cases`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; debug keyword; test keyword; planning keyword`

```text
需求-合作商功能搭建
需求描述
      搭建一个合作商管理页面，支持添加分类、按照分类查看合作商、支持新增、编辑、删除合作商。

 1. 搭建分类体系（树表）
表名：合作商分类，标题：合作商分类
●表类型：分类
●核心字段：
○名称：合作商分类表
○编码：partner_Category

2. 搭建合作商数据表
●表名：合作商，标题：合作商
●表类型：普通表
●字段设计：
  字段标题	字段类型	配置说明
  编码	自增整数	唯一
  名称	单行文本	设置「必填」验证规则
  分类类型表	多对一	关联到「分类类型」表
  类型	多对一	同样关联到「分类节点」表——这个字段用来绑定具体的分类节点
  统一社会信用代码	单行文本	
  状态	下拉菜单（单选）	选项：启用（绿色）、禁用（灰色）
  联系人	单行文本	
  联系人电话	电话	或单行文本，可加格式验证
  邮箱	邮箱	自动验证邮箱格式
注意：「分类类型表」和「类型」两个字段的区别：前者是关联到分类表整体，后者是关联到具体的分类节点。

3. 搭建合作商管理区块（页面）
页面布局：左右结构（经典方案）
●左侧：树筛选区块 → 展示合作商分类树
●右侧：表格区块 → 展示合作商列表，按左侧选中分类筛选
具体步骤：
1.创建新页面：命名为“合作商管理”
2.添加树筛选区块
●区块类型：筛选区块 → 树
●绑定数据表：合作商分类
●标题字段：选择「名称」
●开启「筛选子节点」（选择父分类时自动包含子分类数据）
3.添加表格区块
●区块类型：数据区块 → 表格
●绑定数据表：合作商
●连接树筛选：配置「连接数据区块」，关联到左侧的树筛选区块
●配置显示的列：编码、名称、类型、统一社会信用代码、状态、联系人、电话、邮箱
4.配置表格操作栏：
●添加「新增」按钮 → 弹出表单区块，包含所有字段
●添加「编辑」操作 → 行内编辑或弹窗编辑
●添加「删除」操作 → 确认后删除
4. 支持分类管理（增删改查）
●在「合作商分类」表中直接操作，或用另一个页面管理分类树
●支持的操作：新增根分类、新增子分类（在节点上右键或点击“添加子记录”）、编辑分类名称、删除分类（注意：删除前检查是否有合作商关联，避免数据孤儿）
```

## 14. 历史记录测试2.0

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, systematic-debugging, dispatching-parallel-agents`
- prod_candidate_skills: `dispatching-parallel-agents, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; systematic-debugging->systematic-debugging; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
1.启用历史记录
添加数据表和字段
首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。
2.同步历史数据快照
在启用历史记录前创建的数据，只有在第一次更新时生成快照后，后续变更才能被记录；因此首次更新或删除不会留下历史。
如果需要保留既有数据的历史，可以执行一次快照同步。
单表快照的数据量 = 记录数 × 需记录字段数。
若数据量庞大，建议通过数据范围筛选，仅同步重要数据。
点击“同步历史记录快照”按钮，设置需要同步的字段和数据范围，即可开始同步。
同步任务会在后台排队进行，可以刷新列表查看任务是否完成。
3.使用历史记录区块
添加区块
选择历史记录区块，并选择数据表，可以添加对应数据表的历史记录区块。
如果是在某个数据记录弹窗中添加历史记录区块，可以选择“当前记录”，添加针对数据记录的历史记录区块。
4.编辑描述文案模板
点击区块配置上的“编辑模板”，可以对操作记录的描述文案进行配置。
目前支持对创建、更新、删除记录的描述文案分别配置；其中对于更新记录，还支持配置字段变更的描述文案，既支持统一配置，也支持对某个字段进行单独配置。
在配置文案时可以使用变量。
配置完成后，可以选择对“当前数据表的所有历史记录区块”生效或者“仅当前历史记录区块”生效。
参考https://docs.nocobase.com/cn/record-history/官网内容，最终实现功能一致且完整无报错。
(不推送）
```

## 15. 历史记录测试

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
在此仓库地址创建一个新分支，开发历史记录插件要求如下：1.启用历史记录
添加数据表和字段
首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。
2.同步历史数据快照
在启用历史记录前创建的数据，只有在第一次更新时生成快照后，后续变更才能被记录；因此首次更新或删除不会留下历史。
如果需要保留既有数据的历史，可以执行一次快照同步。
单表快照的数据量 = 记录数 × 需记录字段数。
若数据量庞大，建议通过数据范围筛选，仅同步重要数据。
点击“同步历史记录快照”按钮，设置需要同步的字段和数据范围，即可开始同步。
同步任务会在后台排队进行，可以刷新列表查看任务是否完成。
3.使用历史记录区块
添加区块
选择历史记录区块，并选择数据表，可以添加对应数据表的历史记录区块。
如果是在某个数据记录弹窗中添加历史记录区块，可以选择“当前记录”，添加针对数据记录的历史记录区块。
4.编辑描述文案模板
点击区块配置上的“编辑模板”，可以对操作记录的描述文案进行配置。
目前支持对创建、更新、删除记录的描述文案分别配置；其中对于更新记录，还支持配置字段变更的描述文案，既支持统一配置，也支持对某个字段进行单独配置。
在配置文案时可以使用变量。
配置完成后，可以选择对“当前数据表的所有历史记录区块”生效或者“仅当前历史记录区块”生效。
参考https://docs.nocobase.com/cn/record-history/官网内容，最终实现功能一致且完整无报错。
```

## 16. 历史记录测试

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
创建一个新分支，开发历史记录插件要求如下：1.启用历史记录 添加数据表和字段 首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。 2.同步历史数据快照 在启用历史记录前创建的数据，只有在第一次更新时生成快照后，后续变更才能被记录；因此首次更新或删除不会留下历史。 如果需要保留既有数据的历史，可以执行一次快照同步。 单表快照的数据量 = 记录数 × 需记录字段数。 若数据量庞大，建议通过数据范围筛选，仅同步重要数据。 点击“同步历史记录快照”按钮，设置需要同步的字段和数据范围，即可开始同步。 同步任务会在后台排队进行，可以刷新列表查看任务是否完成。 3.使用历史记录区块 添加区块 选择历史记录区块，并选择数据表，可以添加对应数据表的历史记录区块。 如果是在某个数据记录弹窗中添加历史记录区块，可以选择“当前记录”，添加针对数据记录的历史记录区块。 4.编辑描述文案模板 点击区块配置上的“编辑模板”，可以对操作记录的描述文案进行配置。 目前支持对创建、更新、删除记录的描述文案分别配置；其中对于更新记录，还支持配置字段变更的描述文案，既支持统一配置，也支持对某个字段进行单独配置。 在配置文案时可以使用变量。 配置完成后，可以选择对“当前数据表的所有历史记录区块”生效或者“仅当前历史记录区块”生效。 参考https://docs.nocobase.com/cn/record-history/官网内容，最终实现功能一致且完整无报错。
```

## 17. 测试_evo3

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, systematic-debugging, execute-test-cases, dispatching-parallel-agents`
- prod_candidate_skills: `dispatching-parallel-agents, nocobase-acl-manage, nocobase-data-modeling, nocobase-plugin-development, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; systematic-debugging->systematic-debugging; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; test keyword`

```text
请帮我自检 evolution 插件为什么没有向 UguardAgent 上报事件。

要求：
1. 不要输出任何 token、API key、Authorization、密码或完整 snapshot。
2. 只返回脱敏摘要。
3. 如果你没有权限访问文件或执行命令，请明确说明“无权限”。

请检查以下内容：

A. evolution 插件是否已启用。
B. 当前运行时是否加载了 evolution 插件的新 snapshot。
C. snapshot 中这些字段分别是什么：
   - enabled
   - upload_enabled
   - backend.events_url
   - backend.timeout
   - target_agent_ids
D. 当前 agent_id 是什么，是否被 target_agent_ids 命中。
E. evolution 插件工作目录在哪里。
F. 工作目录下是否存在：
   - state.json
   - events.jsonl
G. 如果 events.jsonl 存在，请返回行数和最后一条事件的 kind、created_at、agent_id、status，不要返回完整内容。
H. 如果 state.json 存在，请返回 last_event_at、last_event_kind、last_upload。
I. 请从当前天磊虾运行环境访问：
   http://uguard-agent.ugclaw.svc.cluster.local:8765/api/summary
   返回是否成功、HTTP 状态码、错误摘要。
J. 请判断问题属于以下哪一类：
   - 插件未启用
   - snapshot 未更新
   - 当前智能体未命中 target_agent_ids
   - on_task_end/on_session_end 没触发
   - 插件本地已写入但上传失败
   - 网络/DNS/服务不可达
   - 后端已收到但 WebUI 看的是另一个实例或目录
```

## 18. 万象-分类视图增强插件优化

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, writing-plans`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; oa-context->oa-wanxiang-api-reader; clarification/design keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; planning keyword`

```text
git@e.coding.net:uguardsec/wanxiang/vientianeAI.git 或者 https://e.coding.net/uguardsec/wanxiang/vientianeAI.git 分支为release_v2.1.0 分支 功能名称：分类视图增强插件，文件夹packages\plugins\@tlws\category-view-enhancement，  现在需要优化：需要有一个权限控制的单独配置，入口在空间tab栏的右边就叫分类视图权限控制，根据关联的分类字典和对应角色来进行控制，比如先获取角色列表和分类列表，根据选中的角色来显示分类字典的数据和里面内置的分类视图操作，比如  角色》分类字典的分类类型列表》新增节点、新增子节点、编辑、配置扩展模版、移动、禁用、删除，样式可以参考图三，然后每个角色的勾选状态都是独立的，没有配置的角色默认不勾选，按照我的理解应该是需要创建一个表去存储这些配置吧，然后在表格开启的分类视图树形里的权限控制根据对应的角色和分类类型来显示可操作的按钮

已上传文件：
- 企业微信截图_17787291047684.png: ~/workspace/uploads/files/20260514-032522-1c76/企业微信截图_17787291047684.png
- 企业微信截图_17787299941893.png: ~/workspace/uploads/files/20260514-032522-1c76/企业微信截图_17787299941893.png
- 企业微信截图_17787301927717.png: ~/workspace/uploads/files/20260514-032522-1c76/企业微信截图_17787301927717.png
```

## 19. 历史记录测试2.0

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, systematic-debugging, dispatching-parallel-agents`
- prod_candidate_skills: `dispatching-parallel-agents, nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; systematic-debugging->systematic-debugging; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
1.启用历史记录
添加数据表和字段
首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。
2.同步历史数据快照
在启用历史记录前创建的数据，只有在第一次更新时生成快照后，后续变更才能被记录；因此首次更新或删除不会留下历史。
如果需要保留既有数据的历史，可以执行一次快照同步。
单表快照的数据量 = 记录数 × 需记录字段数。
若数据量庞大，建议通过数据范围筛选，仅同步重要数据。
点击“同步历史记录快照”按钮，设置需要同步的字段和数据范围，即可开始同步。
同步任务会在后台排队进行，可以刷新列表查看任务是否完成。
3.使用历史记录区块
添加区块
选择历史记录区块，并选择数据表，可以添加对应数据表的历史记录区块。
如果是在某个数据记录弹窗中添加历史记录区块，可以选择“当前记录”，添加针对数据记录的历史记录区块。
4.编辑描述文案模板
点击区块配置上的“编辑模板”，可以对操作记录的描述文案进行配置。
目前支持对创建、更新、删除记录的描述文案分别配置；其中对于更新记录，还支持配置字段变更的描述文案，既支持统一配置，也支持对某个字段进行单独配置。
在配置文案时可以使用变量。
配置完成后，可以选择对“当前数据表的所有历史记录区块”生效或者“仅当前历史记录区块”生效。
参考https://docs.nocobase.com/cn/record-history/官网内容，最终实现功能一致且完整无报错。
(不推送）
```

## 20. 历史记录测试

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
在此仓库地址创建一个新分支，开发历史记录插件要求如下：1.启用历史记录
添加数据表和字段
首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。
2.同步历史数据快照
在启用历史记录前创建的数据，只有在第一次更新时生成快照后，后续变更才能被记录；因此首次更新或删除不会留下历史。
如果需要保留既有数据的历史，可以执行一次快照同步。
单表快照的数据量 = 记录数 × 需记录字段数。
若数据量庞大，建议通过数据范围筛选，仅同步重要数据。
点击“同步历史记录快照”按钮，设置需要同步的字段和数据范围，即可开始同步。
同步任务会在后台排队进行，可以刷新列表查看任务是否完成。
3.使用历史记录区块
添加区块
选择历史记录区块，并选择数据表，可以添加对应数据表的历史记录区块。
如果是在某个数据记录弹窗中添加历史记录区块，可以选择“当前记录”，添加针对数据记录的历史记录区块。
4.编辑描述文案模板
点击区块配置上的“编辑模板”，可以对操作记录的描述文案进行配置。
目前支持对创建、更新、删除记录的描述文案分别配置；其中对于更新记录，还支持配置字段变更的描述文案，既支持统一配置，也支持对某个字段进行单独配置。
在配置文案时可以使用变量。
配置完成后，可以选择对“当前数据表的所有历史记录区块”生效或者“仅当前历史记录区块”生效。
参考https://docs.nocobase.com/cn/record-history/官网内容，最终实现功能一致且完整无报错。
```

## 21. 历史记录测试

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-data-modeling, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
创建一个新分支，开发历史记录插件要求如下：1.启用历史记录 添加数据表和字段 首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。 2.同步历史数据快照 在启用历史记录前创建的数据，只有在第一次更新时生成快照后，后续变更才能被记录；因此首次更新或删除不会留下历史。 如果需要保留既有数据的历史，可以执行一次快照同步。 单表快照的数据量 = 记录数 × 需记录字段数。 若数据量庞大，建议通过数据范围筛选，仅同步重要数据。 点击“同步历史记录快照”按钮，设置需要同步的字段和数据范围，即可开始同步。 同步任务会在后台排队进行，可以刷新列表查看任务是否完成。 3.使用历史记录区块 添加区块 选择历史记录区块，并选择数据表，可以添加对应数据表的历史记录区块。 如果是在某个数据记录弹窗中添加历史记录区块，可以选择“当前记录”，添加针对数据记录的历史记录区块。 4.编辑描述文案模板 点击区块配置上的“编辑模板”，可以对操作记录的描述文案进行配置。 目前支持对创建、更新、删除记录的描述文案分别配置；其中对于更新记录，还支持配置字段变更的描述文案，既支持统一配置，也支持对某个字段进行单独配置。 在配置文案时可以使用变量。 配置完成后，可以选择对“当前数据表的所有历史记录区块”生效或者“仅当前历史记录区块”生效。 参考https://docs.nocobase.com/cn/record-history/官网内容，最终实现功能一致且完整无报错。
```

## 22. 万象-分类视图增强插件优化

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, writing-plans`
- prod_candidate_skills: `brainstorming, nocobase-acl-manage, nocobase-plugin-development, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; oa-context->oa-wanxiang-api-reader; clarification/design keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; planning keyword`

```text
git@e.coding.net:uguardsec/wanxiang/vientianeAI.git 或者 https://e.coding.net/uguardsec/wanxiang/vientianeAI.git 分支为release_v2.1.0 分支 功能名称：分类视图增强插件，文件夹packages\plugins\@tlws\category-view-enhancement，  现在需要优化：需要有一个权限控制的单独配置，入口在空间tab栏的右边就叫分类视图权限控制，根据关联的分类字典和对应角色来进行控制，比如先获取角色列表和分类列表，根据选中的角色来显示分类字典的数据和里面内置的分类视图操作，比如  角色》分类字典的分类类型列表》新增节点、新增子节点、编辑、配置扩展模版、移动、禁用、删除，样式可以参考图三，然后每个角色的勾选状态都是独立的，没有配置的角色默认不勾选，按照我的理解应该是需要创建一个表去存储这些配置吧，然后在表格开启的分类视图树形里的权限控制根据对应的角色和分类类型来显示可操作的按钮

已上传文件：
- 企业微信截图_17787291047684.png: ~/workspace/uploads/files/20260514-032522-1c76/企业微信截图_17787291047684.png
- 企业微信截图_17787299941893.png: ~/workspace/uploads/files/20260514-032522-1c76/企业微信截图_17787299941893.png
- 企业微信截图_17787301927717.png: ~/workspace/uploads/files/20260514-032522-1c76/企业微信截图_17787301927717.png
```

## 23. 测试_evo3

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, systematic-debugging, execute-test-cases, dispatching-parallel-agents`
- prod_candidate_skills: `dispatching-parallel-agents, nocobase-acl-manage, nocobase-data-modeling, nocobase-plugin-development, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-plugin-api, oa-wanxiang-workflow-api, systematic-debugging, test-driven-development`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; systematic-debugging->systematic-debugging; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; test keyword`

```text
请帮我自检 evolution 插件为什么没有向 UguardAgent 上报事件。

要求：
1. 不要输出任何 token、API key、Authorization、密码或完整 snapshot。
2. 只返回脱敏摘要。
3. 如果你没有权限访问文件或执行命令，请明确说明“无权限”。

请检查以下内容：

A. evolution 插件是否已启用。
B. 当前运行时是否加载了 evolution 插件的新 snapshot。
C. snapshot 中这些字段分别是什么：
   - enabled
   - upload_enabled
   - backend.events_url
   - backend.timeout
   - target_agent_ids
D. 当前 agent_id 是什么，是否被 target_agent_ids 命中。
E. evolution 插件工作目录在哪里。
F. 工作目录下是否存在：
   - state.json
   - events.jsonl
G. 如果 events.jsonl 存在，请返回行数和最后一条事件的 kind、created_at、agent_id、status，不要返回完整内容。
H. 如果 state.json 存在，请返回 last_event_at、last_event_kind、last_upload。
I. 请从当前天磊虾运行环境访问：
   http://uguard-agent.ugclaw.svc.cluster.local:8765/api/summary
   返回是否成功、HTTP 状态码、错误摘要。
J. 请判断问题属于以下哪一类：
   - 插件未启用
   - snapshot 未更新
   - 当前智能体未命中 target_agent_ids
   - on_task_end/on_session_end 没触发
   - 插件本地已写入但上传失败
   - 网络/DNS/服务不可达
   - 后端已收到但 WebUI 看的是另一个实例或目录
```

## 24. 导入pro

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, writing-plans, test-driven-development, execute-test-cases`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-data-modeling, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-workflow-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; acl keyword; test keyword`

```text
测试是否满足1.功能增强：支持异步导入操作，独立线程执行，支持大量数据导入。支持高级导入选项。2.异步导入：在执行导入之后，导入的流程将在独立的后台线程中执行，无需用户手动配置。在用户界面中，执行导入操作后，右上方会显示当前正在执行的导入任务，并且实时展示任务进度。导入结束后，可在导入任务中查看导入结果。3.导入配置：导入选项-是否触发工作流在导入时可选择是否触发工作流。如勾选此选项且该数据表绑定了工作流（数据表事件），导入将逐行触发工作流执行。4.导入选项-识别重复记录：勾选此选项，选择对应模式，则导入时会识别重复记录，并进行处理。导入配置中的选项将作为默认值应用，管理员可以控制是否允许上传者修改这些选项（除了触发工作流选项外）。5.上传者权限设置：允许上传者修改导入选项，禁用上传者修改导入选项
```

## 25. kingbase

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
在分支agent-kingbasees中，加入kingbase插件，要求最终效果和官网一致且功能完整；插件开发流程：
1.实现插件开关功能
2.完成插件在菜单栏的展示配置
3.内容翻译，确保翻译内容与官网保持一致
4.实现内容新增可用，功能完整；开发中要解决的问题：不要功能实现单一，仅完成插件开关开发，其余功能未完成。
不要新增内容未进行中文翻译，翻译文案与官网规范不一致。已按官网规范完成中文翻译，但不能插件开启后10秒内即出现报错，无法稳定运行
最后不要新增行仅为页面摆设，无实际功能，无法正常添加内容

已上传文件：
- kingbase官网.png: ~/workspace/uploads/files/20260515-032838-d89e/kingbase官网.png
```

## 26. 测试19

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, requirements-to-test-cases`
- prod_candidate_skills: `brainstorming, nocobase-data-analysis, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, test-driven-development`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; test keyword`

```text
你现在根据这个工作流的测试用例，给出这个测试用例的前置条件需求，就是需要什么数据表和区块等等：
1. 需求描述
搭建工作流，统计销售业绩表里面汕尾-必胜队上个月销售的个人本次到款总和，并更新到表 “测试-汕尾-必胜队上月销售业绩表”

提示：涉及节点如下：1）节点1：查询，需要过滤团队名称（汕尾-必胜队）、时间（上个月）  2）节点2：聚合计算节点1中查询到的上个月个人本次到款总和  3）节点3：循环更新数据，判断条目存在则更新、不存在则插入
涉及到：查询、聚合计算、循环、判断、更新、写入    
2. 验收标准
工作流被正确的搭建出来，可运行，你可在测试-汕尾-必胜队上月销售业绩表看到数据。
```

## 27. 导入pro

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, writing-plans, test-driven-development, execute-test-cases`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-data-modeling, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-workflow-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; acl keyword; test keyword`

```text
测试是否满足1.功能增强：支持异步导入操作，独立线程执行，支持大量数据导入。支持高级导入选项。2.异步导入：在执行导入之后，导入的流程将在独立的后台线程中执行，无需用户手动配置。在用户界面中，执行导入操作后，右上方会显示当前正在执行的导入任务，并且实时展示任务进度。导入结束后，可在导入任务中查看导入结果。3.导入配置：导入选项-是否触发工作流在导入时可选择是否触发工作流。如勾选此选项且该数据表绑定了工作流（数据表事件），导入将逐行触发工作流执行。4.导入选项-识别重复记录：勾选此选项，选择对应模式，则导入时会识别重复记录，并进行处理。导入配置中的选项将作为默认值应用，管理员可以控制是否允许上传者修改这些选项（除了触发工作流选项外）。5.上传者权限设置：允许上传者修改导入选项，禁用上传者修改导入选项
```

## 28. 万象2.0 页面搭建智能体测试

- label_confidence: `high`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword`

```text
需求：搭建页面
页面名称：技术工单
页面功能：技术工单以及关联表所有字段的展示、增删改查和导入导出

数据表：技术工单（editorWorkOrder）、继承工单表（work_order）、关联数据表：项目申请（orderProject）多对一、业务省份（businessProvince）多对一、网站分类（websiteCategory） 多对一、网站业务（websiteBusiness）多对一、项目等级（projectLevelNode）多对一、编辑工单（editorWorkOrder）多对一

提示：技术工单列表展示字段有 状态、紧急度、项目等级、项目编号、网站业务、网站分类、地区、网站名称、发起人
```

## 29. 万象2.0 页面搭建智能体测试

- label_confidence: `high`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword`

```text
需求：搭建页面 页面名称：技术工单 页面功能：技术工单以及关联表所有字段的展示、增删改查和导入导出

数据表：技术工单（editorWorkOrder）、继承工单表（work_order）、关联数据表：项目申请（orderProject）多对一、业务省份（businessProvince）多对一、网站分类（websiteCategory） 多对一、网站业务（websiteBusiness）多对一、项目等级（projectLevelNode）多对一、编辑工单（editorWorkOrder）多对一

提示：技术工单列表展示字段有 状态、紧急度、项目等级、项目编号、网站业务、网站分类、地区、网站名称、发起人
```

## 30. kingbase

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
在分支agent-kingbasees中，加入kingbase插件，要求最终效果和官网一致且功能完整；插件开发流程：
1.实现插件开关功能
2.完成插件在菜单栏的展示配置
3.内容翻译，确保翻译内容与官网保持一致
4.实现内容新增可用，功能完整；开发中要解决的问题：不要功能实现单一，仅完成插件开关开发，其余功能未完成。
不要新增内容未进行中文翻译，翻译文案与官网规范不一致。已按官网规范完成中文翻译，但不能插件开启后10秒内即出现报错，无法稳定运行
最后不要新增行仅为页面摆设，无实际功能，无法正常添加内容

已上传文件：
- kingbase官网.png: ~/workspace/uploads/files/20260515-032838-d89e/kingbase官网.png
```

## 31. docker

- label_confidence: `high`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api`
- prod_candidate_skills: `brainstorming, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword`

```text
需求2：搭建页面
页面名称：技术工单
页面功能：技术工单以及关联表所有字段的展示、增删改查和导入导出

数据表：技术工单（editorWorkOrder）、继承工单表（work_order）、关联数据表：项目申请（orderProject）多对一、业务省份（businessProvince）多对一、网站分类（websiteCategory） 多对一、网站业务（websiteBusiness）多对一、项目等级（projectLevelNode）多对一、编辑工单（editorWorkOrder）多对一

提示：技术工单列表展示字段有 状态、紧急度、项目等级、项目编号、网站业务、网站分类、地区、网站名称、发起人
```

## 32. 测试19

- label_confidence: `medium`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, requirements-to-test-cases`
- prod_candidate_skills: `brainstorming, nocobase-data-analysis, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, test-driven-development`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; test keyword`

```text
你现在根据这个工作流的测试用例，给出这个测试用例的前置条件需求，就是需要什么数据表和区块等等：
1. 需求描述
搭建工作流，统计销售业绩表里面汕尾-必胜队上个月销售的个人本次到款总和，并更新到表 “测试-汕尾-必胜队上月销售业绩表”

提示：涉及节点如下：1）节点1：查询，需要过滤团队名称（汕尾-必胜队）、时间（上个月）  2）节点2：聚合计算节点1中查询到的上个月个人本次到款总和  3）节点3：循环更新数据，判断条目存在则更新、不存在则插入
涉及到：查询、聚合计算、循环、判断、更新、写入    
2. 验收标准
工作流被正确的搭建出来，可运行，你可在测试-汕尾-必胜队上月销售业绩表看到数据。
```

## 33. mssql

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, writing-plans, test-driven-development, systematic-debugging`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; systematic-debugging->systematic-debugging; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
开发mssql插件在已有的agent-external-mssql-datasource分支上继续补充功能，目前已有一个问题插件可以打开但是数据源下拉菜单不显示，并且补充mssql功能，并且要先在有表单翻译，先翻译，支持中文

已上传文件：
- mssql插件不显示.png: ~/workspace/uploads/files/20260514-013220-3846/mssql插件不显示.png
- 插件已打开.png: ~/workspace/uploads/files/20260514-013220-3846/插件已打开.png
```

## 34. Oracle

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; acl keyword; planning keyword`

```text
在最新分支agent-shujuyuan-waibu-oracle，参照官网内容更改，把英文全部翻译成中文，参照官网在下拉菜单中的添加-Oracle制作，最终实现和官网功能一致

已上传文件：
- Oracle官网.png: ~/workspace/uploads/files/20260514-090031-b427/Oracle官网.png
```

## 35. Oracle

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
在最新的分支上agent-shujuyuan-waibu-oracle更改要求功能要与官网一致，且翻译为中文。不要出现以下开发问题，1.功能实现单一，仅完成插件开关开发，其余功能未完成
2.新增内容未进行中文翻译，翻译文案与官网规范不一致
3.已按官网规范完成中文翻译，但插件开启后10秒内即出现报错，无法稳定运行
4.新增行仅为页面摆设，无实际功能，无法正常添加内容

已上传文件：
- Oracle官网.png: ~/workspace/uploads/files/20260515-013957-ca0f/Oracle官网.png
```

## 36. 审批docker

- label_confidence: `medium`
- old_ideal_skills: `materials-to-problems, wanxiangoa-api, writing-plans`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; acl keyword`

```text
推荐：现有协议增强 保留现有接口和数据表，补齐官方文档中的关键体验：数据区块/待办中心发起、草稿/提交/撤回、审批人处理、退回、转签、加签、卡片配置、快照/最新显示、权限校验。风险最低，适合当前分支。
```

## 37. mssql

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, wanxiangoa-api, writing-plans, test-driven-development, systematic-debugging`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; systematic-debugging->systematic-debugging; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; debug keyword; planning keyword`

```text
开发mssql插件在已有的agent-external-mssql-datasource分支上继续补充功能，目前已有一个问题插件可以打开但是数据源下拉菜单不显示，并且补充mssql功能，并且要先在有表单翻译，先翻译，支持中文

已上传文件：
- mssql插件不显示.png: ~/workspace/uploads/files/20260514-013220-3846/mssql插件不显示.png
- 插件已打开.png: ~/workspace/uploads/files/20260514-013220-3846/插件已打开.png
```

## 38. Oracle

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; acl keyword; planning keyword`

```text
在最新分支agent-shujuyuan-waibu-oracle，参照官网内容更改，把英文全部翻译成中文，参照官网在下拉菜单中的添加-Oracle制作，最终实现和官网功能一致

已上传文件：
- Oracle官网.png: ~/workspace/uploads/files/20260514-090031-b427/Oracle官网.png
```

## 39. Oracle

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; acl keyword; debug keyword; planning keyword`

```text
在最新的分支上agent-shujuyuan-waibu-oracle更改要求功能要与官网一致，且翻译为中文。不要出现以下开发问题，1.功能实现单一，仅完成插件开关开发，其余功能未完成
2.新增内容未进行中文翻译，翻译文案与官网规范不一致
3.已按官网规范完成中文翻译，但插件开启后10秒内即出现报错，无法稳定运行
4.新增行仅为页面摆设，无实际功能，无法正常添加内容

已上传文件：
- Oracle官网.png: ~/workspace/uploads/files/20260515-013957-ca0f/Oracle官网.png
```

## 40. 审批docker

- label_confidence: `medium`
- old_ideal_skills: `materials-to-problems, wanxiangoa-api, writing-plans`
- prod_candidate_skills: `nocobase-acl-manage, nocobase-data-modeling, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-page-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; oa-context->oa-wanxiang-api-reader; data-modeling keyword; nocobase data-modeling keyword; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; acl keyword`

```text
推荐：现有协议增强 保留现有接口和数据表，补齐官方文档中的关键体验：数据区块/待办中心发起、草稿/提交/撤回、审批人处理、退回、转签、加签、卡片配置、快照/最新显示、权限校验。风险最低，适合当前分支。
```

## 41. 导入pro

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-data-analysis, nocobase-plugin-development, oa-wanxiang-api-reader, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
分析我们的插件与官网有什么 不一致，对我们分支中插件内容进行修改，要求功能全部要与官方插件一致全方面更改优化，最终要实现分支插件导出pro插件功能与https://docs.nocobase.com/cn/interface-builder/actions/types/export-pro文档描述的一模一样
```

## 42. 导入（pro)import-pro

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
参考https://docs.nocobase.com/cn/interface-builder/actions/types/import-pro文档，完成“导入pro"插件开发，1.插件是否显示在插件管理器中显示，并且开关功能正常，2.是否在“导入pro”按钮上可以配置导出模式，并且把更改计划详细写出来。
```

## 43. kingbase

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
拉取最新分支agent-kingbasees，https://docs.nocobase.com/cn/data-sources/data-source-kingbase/参考官网介绍，最终实现与官网功能一致。把当中的数据源 - 人大金仓（KingbaseES）插件放到此分支中。把REST API 数据源插件另外建一个分支，功能开发要求：1.插件开关 2.菜单栏下显示 3.添加内容翻译且与官网一致 4.添加内容可用 5.最终实现与官网功能一致
```

## 44. 导入pro

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `brainstorming, nocobase-data-analysis, nocobase-plugin-development, oa-wanxiang-api-reader, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; clarification/design keyword; analysis keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
分析我们的插件与官网有什么 不一致，对我们分支中插件内容进行修改，要求功能全部要与官方插件一致全方面更改优化，最终要实现分支插件导出pro插件功能与https://docs.nocobase.com/cn/interface-builder/actions/types/export-pro文档描述的一模一样
```

## 45. 万象2.0 页面搭建智能体测试

- label_confidence: `medium`
- old_ideal_skills: `wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-workflow-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword`

```text
1. 新建页面，不用管原来的，新建页面名称为  技术工单管理   2.继承了 work_order   3.需修改为 中文名称
```

## 46. 测试1831docker

- label_confidence: `high`
- old_ideal_skills: `wanxiangoa-api, dispatching-parallel-agents`
- prod_candidate_skills: `dispatching-parallel-agents, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-workflow-api, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; planning keyword`

```text
查看当前整个系统，理解整个系统的业务数据和页面数据和工作流数据，理解业务逻辑、交互链路等等。可以分多个上下文搜索器去搜索，并生产文件，然后将这些文件写入记忆，作为项目初始化记忆，以树形架构的方式去探索，启动多个探索智能体去并发执行，每个探索任务制定好完整的计划，这是一个OA
```

## 47. 测试万象17

- label_confidence: `high`
- old_ideal_skills: `wanxiangoa-api, dispatching-parallel-agents`
- prod_candidate_skills: `dispatching-parallel-agents, nocobase-acl-manage, nocobase-ui-builder, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-workflow-api`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; dispatching-parallel-agents->dispatching-parallel-agents; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; workflow keyword; nocobase workflow keyword; acl keyword`

```text
1、成绩表只存 学生 + 课程 + 授课教师 + 分数，年级、班级、班主任通过学生关联链路获取
2、需要后续搭建成绩录入页面、查询页面，以及成绩审核工作流
3、教师表一张表同时承载“授课老师”和“班主任”，不额外区分角色，同一教师可同时是班主任和授课老师。
```

## 48. 导入（pro)import-pro

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
参考https://docs.nocobase.com/cn/interface-builder/actions/types/import-pro文档，完成“导入pro"插件开发，1.插件是否显示在插件管理器中显示，并且开关功能正常，2.是否在“导入pro”按钮上可以配置导出模式，并且把更改计划详细写出来。
```

## 49. kingbase

- label_confidence: `low`
- old_ideal_skills: `requirements-clarifier, materials-to-problems, wanxiangoa-api, writing-plans, test-driven-development`
- prod_candidate_skills: `nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-api-reader, oa-wanxiang-page-api, oa-wanxiang-plugin-api, test-driven-development, writing-plans`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; writing-plans->writing-plans; test-driven-development->test-driven-development; oa-context->oa-wanxiang-api-reader; page/ui keyword; nocobase ui keyword; plugin keyword; nocobase plugin keyword; planning keyword`

```text
拉取最新分支agent-kingbasees，https://docs.nocobase.com/cn/data-sources/data-source-kingbase/参考官网介绍，最终实现与官网功能一致。把当中的数据源 - 人大金仓（KingbaseES）插件放到此分支中。把REST API 数据源插件另外建一个分支，功能开发要求：1.插件开关 2.菜单栏下显示 3.添加内容翻译且与官网一致 4.添加内容可用 5.最终实现与官网功能一致
```

## 50. test

- label_confidence: `high`
- old_ideal_skills: `wanxiangoa-api, systematic-debugging`
- prod_candidate_skills: `nocobase-data-analysis, nocobase-data-modeling, nocobase-workflow-manage, oa-wanxiang-api-reader, oa-wanxiang-modeling-api, oa-wanxiang-workflow-api, systematic-debugging`
- mapping_reasons: `wanxiangoa-api->oa-wanxiang-api-reader; systematic-debugging->systematic-debugging; oa-context->oa-wanxiang-api-reader; analysis keyword; data-modeling keyword; nocobase data-modeling keyword; workflow keyword; nocobase workflow keyword; debug keyword`

```text
新建出差申请表单，包含出差人、所属部门、出差目的地、出差开始结束时间、出差事由、预估费用、同行人员、交通方式这些字段
设置字段校验，出行时间不能早于当前时间，结束时间必须晚于开始时间，预估费用为正数必填项
配置审批流程：员工提交后先直属领导审核，再部门经理审批，金额超 2000 元再加一层财务审核
审批通过自动发送站内消息通知申请人，驳回时备注驳回原因
搭建出差数据列表页，支持按部门、时间、审批状态筛选查询
新增出差统计仪表盘，统计各部门月度出差次数与费用汇总
```
