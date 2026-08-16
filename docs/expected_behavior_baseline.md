# Expected Behavior Baseline

## 1. 文档目的

本文档用于补充项目《Requirement-to-Test Multi-Agent Workflow》的评估基线。

在项目早期，Prompt 收敛主要依赖人工观察输出结果，例如：

* 是否出现常识补全；
* 是否生成通用风险；
* 是否在信息不足时强行生成完整测试用例；
* 汇总阶段是否新增问题。

这种方式能够帮助发现问题，但存在一个明显缺口：

> 如果没有预先定义期望行为，就很难稳定判断某次输出到底是正确、遗漏、越界还是过度收敛。

因此，本文档用于建立一组轻量级的 Expected Behavior Baseline，用于说明：

* 每个需求 case 中，系统必须识别哪些已知信息；
* 哪些信息缺口必须暴露；
* 哪些内容禁止模型补全；
* 哪些输出只能作为草案；
* 哪些情况必须进入人工复核。

Expected Behavior Baseline 不是标准答案，而是判断输出边界的参考基线。

---

## 2. 为什么不是标准答案

需求分析和测试设计不是数学题，通常不存在唯一标准答案。

同一段需求可以产生不同表达形式的 open_questions、risk items 和 test_case_drafts。

因此，本项目不要求模型输出与基线逐字一致，而是要求输出符合以下原则：

* 必须覆盖关键需求动作；
* 必须暴露关键缺失信息；
* 不得补全原需求未出现的业务规则；
* 不得将推测内容当作已知事实；
* 信息不足时不得生成完整测试用例；
* 汇总阶段不得新增上游未出现的问题。

换句话说，Expected Behavior Baseline 关注的是：

```text
输出行为是否符合预期
```

而不是：

```text
输出文本是否完全一致
```

---

## 3. Baseline 结构

每个 case 使用以下结构描述：

```json
{
  "case_id": "",
  "requirement_type": "",
  "requirement_text": "",
  "expected_known_information": [],
  "expected_actions": [],
  "expected_gap_types": [],
  "expected_open_question_intents": [],
  "forbidden_assumptions": [],
  "expected_risk_behavior": {
    "allowed_strict_risks": [],
    "forbidden_risks": []
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

---

## 4. 字段说明

### case_id

用于标识测试样本。

示例：

```text
case_00_login_register
```

---

### requirement_type

需求类型。

示例：

* 注册登录类
* CRUD 类
* 流程状态类
* AI 能力类
* 工具处理类
* 数据导出类

---

### requirement_text

原始需求文本。

---

### expected_known_information

原始需求中已经明确给出的信息。

用于判断 Agent1 是否正确提取已知信息。

---

### expected_actions

原始需求中必须识别出的核心动作。

例如：

```text
注册账号
登录系统
创建笔记
删除笔记
审核内容
展示内容
生成摘要
上传图片
识别图片
导出报表
```

---

### expected_gap_types

当前需求必须识别出的信息缺口类型。

常见 gap 类型包括：

* action_flow_gap：动作流程不明确
* rule_gap：业务规则不明确
* condition_gap：前置条件不明确
* result_state_gap：结果状态不明确
* ui_gap：页面 / 交互信息不明确
* exception_gap：异常处理不明确
* role_scope_gap：角色或权限边界不明确
* data_scope_gap：数据范围不明确
* quality_standard_gap：质量标准不明确

---

### expected_open_question_intents

open_questions 应覆盖的问题意图。

不要求逐字一致，只要求覆盖对应问题意图。

---

### forbidden_assumptions

模型禁止补全的内容。

这些内容可能符合常识，但原需求未出现，因此不得作为已知事实进入下游链路。

---

### expected_risk_behavior

用于约束 Agent2。

重点判断：

* 风险是否基于原始需求和 open_questions；
* 是否出现通用 checklist；
* 是否引入当前需求未出现的系统能力。

---

### expected_test_design_behavior

用于约束 Agent3。

重点判断：

* 是否允许输出测试点；
* 是否只能输出 test_case_drafts；
* 是否禁止生成完整 test_cases；
* 是否保留信息缺口。

---

### expected_summary_behavior

用于约束 Agent4。

重点判断：

* 是否只复用上游问题；
* 是否禁止新增问题；
* 是否禁止新增风险；
* 是否保持结果可追溯。

---

# 5. Case Baselines

---

## Case 00：注册登录类需求

### requirement_text

```text
用户可以通过手机号注册账号，注册后可以登录系统。
```

### baseline

```json
{
  "case_id": "case_00_login_register",
  "requirement_type": "注册登录类",
  "requirement_text": "用户可以通过手机号注册账号，注册后可以登录系统。",
  "expected_known_information": [
    "用户可以通过手机号注册账号",
    "注册后可以登录系统"
  ],
  "expected_actions": [
    "通过手机号注册账号",
    "登录系统"
  ],
  "expected_gap_types": [
    "action_flow_gap",
    "rule_gap",
    "ui_gap",
    "result_state_gap"
  ],
  "expected_open_question_intents": [
    "需要确认手机号是否为唯一注册方式",
    "需要确认手机号是否为唯一登录方式",
    "需要确认注册流程、规则和结果状态",
    "需要确认登录流程、规则和结果状态",
    "需要确认注册与登录是否涉及相同页面或流程",
    "需要补充页面或交互信息"
  ],
  "forbidden_assumptions": [
    "验证码",
    "密码",
    "邮箱",
    "短信校验",
    "第三方登录",
    "注册按钮",
    "登录按钮",
    "页面布局",
    "具体输入框",
    "错误提示文案",
    "手机号格式规则",
    "登录失败锁定规则"
  ],
  "expected_risk_behavior": {
    "allowed_strict_risks": [
      "注册流程规则未明确",
      "登录流程规则未明确",
      "注册与登录关系未明确",
      "页面或交互信息缺失"
    ],
    "forbidden_risks": [
      "验证码安全风险",
      "密码复杂度风险",
      "邮箱绑定风险",
      "第三方登录风险",
      "账号锁定风险"
    ]
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

### evaluation focus

该 case 重点用于评估：

* Agent1 是否补全验证码、密码、邮箱等常见注册登录机制；
* Agent1 是否识别注册和登录两个动作；
* Agent1 是否暴露流程、规则、页面信息缺口；
* Agent2 是否生成注册登录类通用安全风险；
* Agent3 是否在规则不足时仍生成完整测试用例；
* Agent4 是否新增上游未出现的问题。

---

## Case 01：CRUD 类需求

### requirement_text

```text
用户可以创建和删除自己的笔记。
```

### baseline

```json
{
  "case_id": "case_01_notes_crud",
  "requirement_type": "CRUD 类",
  "requirement_text": "用户可以创建和删除自己的笔记。",
  "expected_known_information": [
    "用户可以创建自己的笔记",
    "用户可以删除自己的笔记"
  ],
  "expected_actions": [
    "创建笔记",
    "删除笔记"
  ],
  "expected_gap_types": [
    "action_flow_gap",
    "rule_gap",
    "result_state_gap",
    "ui_gap"
  ],
  "expected_open_question_intents": [
    "需要确认创建笔记的具体流程、规则和结果状态",
    "需要确认删除笔记的具体流程、规则和结果状态",
    "需要确认笔记相关页面或交互信息"
  ],
  "forbidden_assumptions": [
    "笔记标题",
    "笔记正文",
    "保存按钮",
    "删除确认弹窗",
    "回收站",
    "草稿状态",
    "字符长度限制",
    "非法字符规则",
    "富文本编辑器",
    "分类标签"
  ],
  "expected_risk_behavior": {
    "allowed_strict_risks": [
      "创建流程规则未明确",
      "删除流程规则未明确",
      "删除后的结果状态未明确",
      "页面或交互信息缺失"
    ],
    "forbidden_risks": [
      "富文本安全风险",
      "大文件上传风险",
      "多人协作冲突风险",
      "回收站恢复风险",
      "标签分类错误风险"
    ]
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

### evaluation focus

该 case 重点用于评估：

* Agent1 是否同时识别“创建”和“删除”两个动作；
* Agent1 是否将“删除确认弹窗”等设计选项作为缺口问题；
* Agent2 是否放大 CRUD 通用风险；
* Agent3 是否直接生成完整创建 / 删除测试用例；
* Agent4 是否将抽象问题具体化为输入长度、非法字符等细节。

---

## Case 02：流程状态类需求

### requirement_text

```text
管理员可以审核用户提交的内容，审核通过后内容对外展示。
```

### baseline

```json
{
  "case_id": "case_02_review_flow",
  "requirement_type": "流程状态类",
  "requirement_text": "管理员可以审核用户提交的内容，审核通过后内容对外展示。",
  "expected_known_information": [
    "管理员可以审核用户提交的内容",
    "审核通过后内容对外展示"
  ],
  "expected_actions": [
    "审核用户提交的内容",
    "内容对外展示"
  ],
  "expected_gap_types": [
    "role_scope_gap",
    "action_flow_gap",
    "rule_gap",
    "result_state_gap",
    "exception_gap"
  ],
  "expected_open_question_intents": [
    "需要确认管理员审核的具体流程和规则",
    "需要确认审核通过后的内容展示规则",
    "需要确认审核不通过或异常情况的处理方式",
    "需要确认用户提交内容的状态流转"
  ],
  "forbidden_assumptions": [
    "审核驳回",
    "审核备注",
    "审核列表",
    "内容分类",
    "通知用户",
    "二级审核",
    "自动审核",
    "敏感词检测",
    "内容置顶",
    "展示排序"
  ],
  "expected_risk_behavior": {
    "allowed_strict_risks": [
      "审核流程规则未明确",
      "审核通过后的展示规则未明确",
      "审核不通过或异常状态未明确",
      "用户提交内容状态流转未明确"
    ],
    "forbidden_risks": [
      "敏感词审核风险",
      "自动审核误判风险",
      "内容推荐排序风险",
      "通知失败风险",
      "多级审批风险"
    ]
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

### evaluation focus

该 case 重点用于评估：

* Agent1 是否识别审核与展示之间的状态关系；
* Agent1 是否暴露审核规则和状态流转缺口；
* Agent2 是否引入敏感词、自动审核等未出现机制；
* Agent3 是否在审核规则不完整时生成完整流程测试用例；
* Agent4 是否新增审核不通过以外的复杂流程。

---

## Case 03：AI 能力类需求

### requirement_text

```text
系统可以对用户输入的文本生成摘要。
```

### baseline

```json
{
  "case_id": "case_03_text_summary",
  "requirement_type": "AI 能力类",
  "requirement_text": "系统可以对用户输入的文本生成摘要。",
  "expected_known_information": [
    "系统可以对用户输入的文本生成摘要"
  ],
  "expected_actions": [
    "输入文本",
    "生成摘要"
  ],
  "expected_gap_types": [
    "action_flow_gap",
    "rule_gap",
    "quality_standard_gap",
    "exception_gap",
    "ui_gap"
  ],
  "expected_open_question_intents": [
    "需要确认文本输入和摘要生成的具体流程",
    "需要确认摘要生成规则或质量标准",
    "需要确认输入异常或生成失败时的处理方式",
    "需要确认页面或交互信息"
  ],
  "forbidden_assumptions": [
    "摘要长度",
    "摘要格式",
    "摘要语言",
    "支持长文本",
    "支持多语言",
    "关键词提取",
    "模型选择",
    "生成速度要求",
    "重新生成",
    "复制摘要",
    "摘要评分"
  ],
  "expected_risk_behavior": {
    "allowed_strict_risks": [
      "摘要生成流程未明确",
      "摘要质量标准未明确",
      "输入异常处理未明确",
      "生成失败处理未明确"
    ],
    "forbidden_risks": [
      "多语言生成风险",
      "摘要长度控制风险",
      "模型幻觉风险",
      "关键词提取风险",
      "生成速度性能风险"
    ]
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

### evaluation focus

该 case 重点用于评估：

* Agent1 是否把“输入文本”和“生成摘要”识别为核心动作；
* Agent1 是否引入摘要长度、格式、语言等默认规则；
* Agent2 是否生成 AI 场景通用风险；
* Agent3 是否在缺少质量标准时生成完整测试用例；
* Agent4 是否在汇总阶段新增摘要标准问题。

---

## Case 04：工具处理类需求

### requirement_text

```text
用户可以上传图片并进行识别。
```

### baseline

```json
{
  "case_id": "case_04_image_recognition",
  "requirement_type": "工具处理类",
  "requirement_text": "用户可以上传图片并进行识别。",
  "expected_known_information": [
    "用户可以上传图片",
    "系统可以进行识别"
  ],
  "expected_actions": [
    "上传图片",
    "识别图片"
  ],
  "expected_gap_types": [
    "action_flow_gap",
    "rule_gap",
    "result_state_gap",
    "exception_gap",
    "ui_gap"
  ],
  "expected_open_question_intents": [
    "需要确认图片上传与识别的具体流程",
    "需要确认图片上传规则",
    "需要确认识别结果的输出规则",
    "需要确认上传或识别异常时的处理方式",
    "需要确认页面或交互信息"
  ],
  "forbidden_assumptions": [
    "图片格式限制",
    "图片大小限制",
    "支持批量上传",
    "识别类型",
    "识别准确率",
    "识别结果列表",
    "上传进度条",
    "重新上传",
    "识别失败重试",
    "OCR",
    "人脸识别",
    "物体识别"
  ],
  "expected_risk_behavior": {
    "allowed_strict_risks": [
      "图片上传流程未明确",
      "图片上传规则未明确",
      "识别结果输出规则未明确",
      "上传或识别异常处理未明确"
    ],
    "forbidden_risks": [
      "OCR 识别风险",
      "人脸识别隐私风险",
      "大文件上传性能风险",
      "批量上传并发风险",
      "识别准确率风险"
    ]
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

### evaluation focus

该 case 重点用于评估：

* Agent1 是否识别“上传”和“识别”两个动作；
* Agent1 是否把图片格式、大小、识别类型作为已知规则；
* Agent2 是否生成大文件、OCR、人脸识别等泛化风险；
* Agent3 是否在缺少上传规则和识别标准时生成完整测试用例；
* Agent4 是否新增识别结果类型或具体异常场景。

---

## Case 05：数据导出类需求

### requirement_text

```text
系统支持导出数据报表。
```

### baseline

```json
{
  "case_id": "case_05_export_report",
  "requirement_type": "数据导出类",
  "requirement_text": "系统支持导出数据报表。",
  "expected_known_information": [
    "系统支持导出数据报表"
  ],
  "expected_actions": [
    "导出数据报表"
  ],
  "expected_gap_types": [
    "action_flow_gap",
    "rule_gap",
    "data_scope_gap",
    "result_state_gap",
    "exception_gap"
  ],
  "expected_open_question_intents": [
    "需要确认数据报表导出的具体流程",
    "需要确认导出数据范围",
    "需要确认导出格式或结果规则",
    "需要确认导出异常时的处理方式"
  ],
  "forbidden_assumptions": [
    "Excel",
    "CSV",
    "PDF",
    "导出按钮",
    "导出进度",
    "下载链接",
    "导出权限",
    "按时间筛选",
    "字段选择",
    "导出失败重试",
    "批量导出"
  ],
  "expected_risk_behavior": {
    "allowed_strict_risks": [
      "导出流程未明确",
      "导出数据范围未明确",
      "导出结果规则未明确",
      "导出异常处理未明确"
    ],
    "forbidden_risks": [
      "Excel 格式兼容风险",
      "大数据量导出性能风险",
      "导出权限风险",
      "字段权限风险",
      "批量导出风险"
    ]
  },
  "expected_test_design_behavior": {
    "allow_test_points": true,
    "allow_test_case_drafts": true,
    "forbid_complete_test_cases": true,
    "must_expose_missing_info": true
  },
  "expected_summary_behavior": {
    "must_reuse_upstream_questions": true,
    "forbid_new_questions": true,
    "forbid_new_risks": true
  },
  "human_review_required": true
}
```

### evaluation focus

该 case 重点用于评估：

* Agent1 是否识别“导出数据报表”作为核心动作；
* Agent1 是否补全导出格式、按钮、权限等规则；
* Agent2 是否生成大数据量导出、字段权限等泛化风险；
* Agent3 是否在缺少导出规则时生成完整测试用例；
* Agent4 是否新增导出格式或权限问题。

---

# 6. Evaluation Rules

## 6.1 PASS

输出满足以下条件：

* 识别出 expected_actions 中的核心动作；
* 覆盖主要 expected_open_question_intents；
* 未出现 forbidden_assumptions；
* 风险与当前需求和 open_questions 相关；
* 信息不足时未生成完整 test_cases；
* Agent4 未新增上游未出现的问题或风险。

---

## 6.2 PARTIAL

输出存在轻微问题，但未破坏主链路。

例如：

* 核心动作识别完整，但 open_questions 表达偏抽象；
* 风险表达略泛，但未引入具体未确认机制；
* test_case_drafts 偏简略，但没有生成完整测试用例；
* Agent4 表达略有总结扩展，但未新增实质问题。

---

## 6.3 FAIL

输出出现以下任一情况：

* 遗漏核心动作；
* 将 forbidden_assumptions 当作已知信息；
* 生成与当前需求无关的通用风险；
* 在信息不足时生成完整 test_cases；
* Agent4 新增上游未出现的问题或风险；
* 下游明显承接了上游补全信息继续扩展。

---

# 7. How to Use This Baseline

每次调整 Prompt、Schema 或 Agent 结构后，应选择至少 3 个 case 进行复测：

推荐最小组合：

* case_00_login_register
* case_01_notes_crud
* case_03_text_summary

如果涉及工具类或数据类需求，可补充：

* case_04_image_recognition
* case_05_export_report

评估流程：

```text
运行 Pipeline
↓
对照 Expected Behavior Baseline
↓
标记 PASS / PARTIAL / FAIL
↓
记录失败发生在哪个 Agent
↓
判断是否需要继续修改
```

如果同一 Agent 围绕同类问题连续修改多次仍无法稳定，应停止继续微调 Prompt，转入结构调整或保留为当前版本限制。

---

# 8. Current Limitations

当前 Baseline 仍属于轻量评测集，存在以下限制：

* case 数量较少；
* 主要覆盖极简需求文本；
* 不包含真实项目背景；
* 不包含行业上下文；
* 不包含页面原型或系统规则；
* 主要依赖人工判断；
* 不作为自动评分系统。

因此，该 Baseline 主要用于判断：

* 是否越界补全；
* 是否风险泛化；
* 是否伪完整生成；
* 是否汇总扩写；
* 是否遵守生成边界。

它不用于判断完整测试设计质量。

如果后续要评估真实测试设计准确性，需要引入 Context Layer，包括：

* 项目背景；
* 业务规则；
* 页面信息；
* 系统上下文；
* 行业背景；
* 历史缺陷；
* 已有功能约束。

---

# 9. Conclusion

Expected Behavior Baseline 的作用不是提供唯一标准答案，而是为需求到测试设计 Workflow 提供可复核的行为边界。

它用于回答：

```text
这次输出是否符合当前需求边界？
```

而不是回答：

```text
这次输出是否生成了最完整的测试结果？
```

通过该 Baseline，项目可以从“人工观察输出是否合理”进一步转向“基于预设行为边界判断输出是否越界”。

这也是项目从 Prompt 收敛实验走向可复核 AI Workflow 的关键补充。
