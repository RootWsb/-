# Skill Router Evaluation Report

## Summary

| Run | Rows | Score | Waste | Exact | Avg selected | Avg ideal | Precision | Recall | Micro F1 | Extra/request | Missing/request |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Prod_ML | 10 | 80.9% | 6.7% | 40.0% | 5.70 | 7.80 | 93.0% | 67.9% | 78.5% | 0.40 | 2.50 |

## Prod_ML

### Top Extra Skills

- `nocobase-ui-builder`: 1
- `writing-plans`: 1
- `nocobase-plugin-development`: 1
- `oa-wanxiang-plugin-api`: 1

### Top Missing Skills

- `test-driven-development`: 4
- `systematic-debugging`: 4
- `nocobase-acl-manage`: 2
- `nocobase-workflow-manage`: 2
- `oa-wanxiang-page-api`: 2
- `writing-plans`: 2
- `nocobase-plugin-development`: 2
- `oa-wanxiang-plugin-api`: 2
- `oa-wanxiang-workflow-api`: 1
- `nocobase-data-modeling`: 1

### Worst 10 Rows

- row 6, score=0.500, waste=0.667, missing=None, extra=nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-plugin-api, writing-plans: 你直接根据我的需求文档进行  已上传文件： - 研服部需求_3.18.docx: ~/workspace/uploads/files/20260520-021010-52ad/研服部需求_3.18.docx
- row 3, score=0.571, waste=0.000, missing=nocobase-acl-manage, nocobase-data-analysis, nocobase-plugin-development, nocobase-ui-builder, oa-wanxiang-page-api, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, writing-plans, extra=None: RD-001 产品需求全生命周期管理 1.1 需求描述 基于公司现有 OA / 万象协同平台，使用建设“产品需求”全生命周期管理模块，实现销售、售前、研发三方围绕同一需求单进行协同。 目标如下： ● 建立统一需求入口，避免需求分散在 IM、Excel、邮件中。 ● 实现需求信息标准化录入与协同补充。 ● 实现需求全过程留痕、可追溯、可审计。 ● 为后续统计分
- row 1, score=0.706, waste=0.000, missing=nocobase-acl-manage, nocobase-data-modeling, nocobase-workflow-manage, oa-wanxiang-workflow-api, test-driven-development, extra=None: 请帮我自检 evolution 插件为什么没有向 UguardAgent 上报事件。  要求： 1. 不要输出任何 token、API key、Authorization、密码或完整 snapshot。 2. 只返回脱敏摘要。 3. 如果你没有权限访问文件或执行命令，请明确说明“无权限”。  请检查以下内容：  A. evolution 插件是否已启用。 B
- row 7, score=0.706, waste=0.000, missing=brainstorming, nocobase-workflow-manage, systematic-debugging, test-driven-development, writing-plans, extra=None: 需求-合作商功能搭建 需求描述       搭建一个合作商管理页面，支持添加分类、按照分类查看合作商、支持新增、编辑、删除合作商。   1. 搭建分类体系（树表） 表名：合作商分类，标题：合作商分类 ●表类型：分类 ●核心字段： ○名称：合作商分类表 ○编码：partner_Category  2. 搭建合作商数据表 ●表名：合作商，标题：合作商 ●表类型：
- row 10, score=0.750, waste=0.000, missing=nocobase-plugin-development, oa-wanxiang-plugin-api, systematic-debugging, test-driven-development, extra=None: 在此仓库地址创建一个新分支，开发历史记录插件要求如下：1.启用历史记录 添加数据表和字段 首先进入历史记录插件配置页面，添加需要记录操作历史的数据表和字段。为了提高记录效率，避免数据冗余，建议仅配置必要的数据表和字段，如唯一 ID, 创建日期、更新日期，创建人、更新人等字段，通常不需要记录。 2.同步历史数据快照 在启用历史记录前创建的数据，只有在第一次更新
- row 2, score=0.857, waste=0.000, missing=oa-wanxiang-page-api, systematic-debugging, extra=None: 在分支agent-kingbasees中，加入kingbase插件，要求最终效果和官网一致且功能完整；插件开发流程： 1.实现插件开关功能 2.完成插件在菜单栏的展示配置 3.内容翻译，确保翻译内容与官网保持一致 4.实现内容新增可用，功能完整；开发中要解决的问题：不要功能实现单一，仅完成插件开关开发，其余功能未完成。 不要新增内容未进行中文翻译，翻译文案与
- row 4, score=1.000, waste=0.000, missing=None, extra=None: 拉取最新分支agent-shujuyuan-waibu-oracle，参考Oracle官网内容进行修改，先翻译成中文，在服务器地址、端口、数据库、用户名、密码、表前缀，增加变量和密钥功能  已上传文件： - Oracle官网.png: ~/workspace/uploads/files/20260514-063416-e7b1/Oracle官网.png - 
- row 5, score=1.000, waste=0.000, missing=None, extra=None: 在分支agent-import-pro中，实现导入自检，是否支持异步导入操作，独立线程执行，支持大量数据导入。支持高级导入选项。 在执行导入之后，导入的流程将在独立的后台线程中执行，无需用户手动配置。在用户界面中，执行导入操作后，右上方会显示当前正在执行的导入任务，并且实时展示任务进度。 导入结束后，可在导入任务中查看导入结果。参考https://docs.
- row 8, score=1.000, waste=0.000, missing=None, extra=None: 在此分支修改agent-import-pro，求功能全部要与官方插件一致全方面更改优化，最终要实现分支插件导入pro插件功能与https://docs.nocobase.com/cn/interface-builder/actions/types/import-pro文档描述的一模一样，要求在导入pro插件开启后实现文档中的所有功能
- row 9, score=1.000, waste=0.000, missing=None, extra=None: git@e.coding.net:uguardsec/aiyuangong/agent-console.git v2分支 拉取项目，准备开发功能，添加全局的项目功能，管理员创建项目，所有用户都能看到和使用。
