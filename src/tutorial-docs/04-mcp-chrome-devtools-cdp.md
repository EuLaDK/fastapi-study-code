# 04｜MCP、Chrome DevTools 与 CDP：连接标准、工具服务和浏览器控制

> 面向有 Python、HTTP/API 基础的 Agent 初学者。资料核查日期：2026-09-15。本文根据目录主题独立编写，不代表截图中原文件的内容。

## 1. 从“页面点了没反应”开始

工单前端的“生成草稿”按钮没有反应。你让助手查看页面，得到一张截图：按钮看起来正常。截图不能告诉你请求是否发出、接口是否返回 401、JavaScript 是否抛异常。

想定位原因，需要浏览器能提供可检查的信息；想让 Agent 使用这些能力，还要把浏览器动作包装成工具。**MCP 负责应用与工具服务怎样交换消息，Chrome DevTools MCP 提供具体浏览器工具，CDP 负责更底层的浏览器检查与控制。** 三者不在同一层。[1][3][4]

## 2. 先拆开这几个名字

| 概念 | 本质 | 工单案例里的对应物 |
| --- | --- | --- |
| MCP Host | 管理模型交互及工具连接的应用 | 运行工单助手的应用 |
| MCP Client | Host 中与某个 Server 交互的组件 | 应用内部的浏览器工具客户端 |
| MCP Server | 按协议暴露能力的程序，可本地或远程运行 | Chrome DevTools MCP 进程 |
| Chrome DevTools | 浏览器开发者工具体系，包括面板与调试能力 | Network、Console、Performance |
| CDP | 检查、调试、分析浏览器的命令与事件协议 | Network、DOM、Debugger 等协议域 |

MCP Server 不一定是一台云服务器。本地子进程同样可以是 Server。Host 通常为连接的各个 Server 建立各自的 Client；Host、Client 和 Server 是职责划分，不表示每个角色必须占一台机器。[1]

可把 MCP 理解为工具接入的共同约定，但“统一插座”类比有边界：**接得上不代表功能一样，更不代表权限、安全性和数据质量自动一致。**

## 3. 一次浏览器调用经过哪些层

```mermaid
flowchart LR
    A[模型提出浏览器动作] --> B[Host 检查权限]
    B --> C[MCP Client]
    C -->|MCP 消息| D[Chrome DevTools MCP Server]
    D --> E[Puppeteer / DevTools 能力]
    E -->|包含 CDP 等浏览器控制机制| F[Chrome]
    F --> G[页面状态、请求、异常、性能数据]
    G --> D
    D --> C
```

官方仓库说明，Chrome DevTools MCP 提供网络检查、截图、控制台信息、性能分析，并使用 Puppeteer 完成浏览器自动化。[3] 不能把每个高层 MCP 工具理解成“一对一转发某条 CDP 指令”：一个工具可能等待页面稳定、组合多个操作、整理结果后才返回。

CDP 按 DOM、Network、Debugger 等域组织命令和事件。[4] 例如浏览器发生网络请求会产生可观察事件；Agent 不需要凭截图推测 HTTP 状态码，而可以读取请求详情。这是增加可观测性，不是让模型突然拥有浏览器内部知识。

## 4. MCP 标准化了什么，没有标准化什么

MCP 规定消息和能力表达方式。常见服务端能力有：

- **Tools**：可调用的动作，如查询工单、检查网络请求。
- **Resources**：可读取的上下文数据，如接口说明、数据库结构。
- **Prompts**：可复用的交互模板。

它并不规定模型必须用 ReAct，是否使用 RAG，或者数据库应如何分表。这些仍属于应用设计。[1]

传输也不是“只有 HTTP”。常见方式包括本地进程的 **stdio**，以及适合远程连接的 **Streamable HTTP**。前者通过标准输入输出交换协议消息；普通调试日志不应混进协议输出。后者通过 HTTP 传送消息，可结合 SSE 流式返回；授权仍需正确实现。

**版本提醒：截至核查日，官网当前版本显示为 `2026-07-28`。** 当前架构文档描述按请求携带协议版本与能力元数据的无状态交换，并提供 `server/discover`；该版本还将 sampling 和协议 logging 标为 deprecated。旧教程里的初始化握手和能力细节需要对照版本，不能机械拼接。[1][2]

这里的“无状态”指协议处理不依赖先前消息建立的隐含会话状态，**不表示浏览器没有登录态，也不表示业务服务不能保存工单**。实际接入必须核对 Host、SDK、Server 共同支持的版本；官网更新不代表已安装客户端已经支持。

## 5. 用同一个案例走完诊断过程

场景：测试环境中，工单 42 的“生成草稿”按钮无响应。

1. **明确环境和对象。** 使用受控测试账号，确认页面 URL 与工单编号，避免把生产操作当测试。
2. **观察页面结构。** 从当前页面快照找到按钮。工具快照中的元素标识可能随重新渲染变化，不能拿旧标识盲点。
3. **复现一次。** 触发生成草稿，检查 Console 错误和对应网络请求。
4. **按证据缩小范围。** 没有请求，先查事件绑定和前端异常；返回 401，查身份传递与会话；返回 422，核对请求字段与接口结构；返回成功但页面没更新，查响应解析和状态更新。
5. **修复后复验。** 再执行相同条件，核对实际草稿内容和页面状态，不把“这次没有报错”当作业务正确。

这些状态码只能提供线索，不能单独证明根因。例如 401 可能来自网关或应用，需要结合请求 URL、响应来源和服务端日志。

浏览器工具适合验证真实页面行为。若只是批量查询工单且已有稳定 API，直接用 HTTP 接口通常步骤更少、返回更结构化。若要覆盖页面交互、登录流程、布局或浏览器端故障，再使用浏览器自动化。这是按问题选工具，不是 MCP 和 HTTP 二选一。

## 6. 浏览器权限和版本的实际代价

浏览器实例可能带有 Cookie、登录态和个人资料。官方 README 明确说明 MCP 客户端可以检查、调试和修改浏览器中的数据。[3] 因此“仅开一个浏览器工具”也可能具备代表用户提交表单的能力。测试时采用隔离浏览器上下文或专用配置；向真实客户发送回复仍遵守[第 03 篇的授权规则](03-tool-call-hitl-security.md)。

截至核查日，仓库还说明默认启用使用统计，性能工具可能查询 CrUX；生产或敏感环境应核对当前开关与数据流。这些是该工具的实现细节，不是 MCP 协议的统一行为。[3]

CDP 官网提示 tip-of-tree 协议变化频繁且不保证向后兼容。[4] 把依赖固定到经过验证的组合有利于复现；直接追随 `latest` 方便试用，但升级后应重新验证工具参数、浏览器兼容性和授权配置。

## 7. 面试与练习

**题：有 function calling，为什么还需要 MCP？**

function calling 让模型输出可由程序执行的结构化调用；MCP 让应用与外部能力提供者以共同协议发现和调用工具。它们可以衔接使用。只有几个内部函数时，不一定要加 MCP；当多个客户端需要复用同一服务、统一接入时，协议化的价值更明显。

**练习：浏览器 MCP 工具能成功列出，为什么点击仍失败？**

答案：列工具只证明工具服务能够提供能力描述；浏览器可能没启动、目标页面不存在、元素标识已过期，或者执行被权限拒绝。按“Host 与 Server 连接 → 工具执行环境 → 页面状态 → 业务接口”逐层查，不能直接归因于模型不够聪明。

继续阅读：[运行时与快照](06-tui-lsp-snapshot-runtime.md)、[面试题与解析](10-interview-questions-and-answers.md)。

## 依据与查阅入口

以下来源均于 **2026-09-15** 实际读取。页面故障的排查顺序是本文工程建议，具体工具名和参数以所安装版本为准。

1. [MCP Architecture overview](https://modelcontextprotocol.io/docs/learn/architecture)：Host、Client、Server、能力、传输及当前无状态交换说明。
2. [MCP 当前架构文档的 Markdown 版本](https://modelcontextprotocol.io/docs/learn/architecture.md)：本次核对的 `2026-07-28` 版本引用、`server/discover`、sampling/logging 弃用说明。
3. [Chrome DevTools MCP 官方仓库](https://github.com/ChromeDevTools/chrome-devtools-mcp)：能力、Puppeteer、浏览器数据可见性、兼容性与数据收集说明；[工具参考](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md)记录当前参数。
4. [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)：协议域、命令与事件、tip-of-tree 兼容性边界。

[返回导航](README.md) · [下一章：Prompt 与 Skill](05-prompt-skill-prompt-engineering.md)
