# Browser-Use 插件系统

Browser-Use 插件系统允许在不修改核心代码的情况下扩展功能。本目录包含各种插件，可以根据需要进行集成。

## 可用插件

### 截图插件 (Screenshot Plugin)

截图插件允许自动保存浏览器状态的截图和计划信息，对于调试和分析 agent 执行流程非常有用。

#### 功能

- 为每个执行步骤保存浏览器截图
- 保存每个步骤的计划信息（JSON格式）
- 保存执行结果信息
- 支持自定义目录结构和命名规则

#### 使用方法

基本用法：

```python
from browser_use.agent.service import Agent
from browser_use.plugins.screenshot.integration import setup_agent_with_screenshot_plugin

# 创建 Agent
agent = Agent(...)

# 设置截图插件
screenshot_plugin = setup_agent_with_screenshot_plugin(
    agent, 
    screenshot_dir="screenshots",
    save_plans=True
)

# 运行 Agent
await agent.run()
```

高级用法 - 创建自定义截图插件：

```python
from browser_use.plugins.screenshot.service import ScreenshotPlugin
from browser_use.plugins.screenshot.integration import create_screenshot_callbacks, wrap_multi_act

# 创建自定义截图插件类
class CustomScreenshotPlugin(ScreenshotPlugin):
    # 自定义实现...

# 创建插件实例
plugin = CustomScreenshotPlugin(...)

# 设置回调函数
step_callback, done_callback = create_screenshot_callbacks(plugin)
agent.register_new_step_callback = step_callback
agent.register_done_callback = done_callback

# 包装multi_act方法
original_multi_act = agent.multi_act
agent.multi_act = wrap_multi_act(original_multi_act, plugin)

# 将插件添加到agent对象
agent.screenshot_plugin = plugin

# 运行 Agent
await agent.run()
```

#### 输出结构

基本插件输出目录结构：
```
screenshots/
├── execute_001_YYYYMMDD_HHMMSS/
│   ├── screenshot_0.png        # 步骤初始截图
│   ├── screenshot_1.png        # 第一个结果的截图
│   ├── screenshot_2.png        # 第二个结果的截图
│   ├── plan.json
│   └── results.json
├── execute_002_YYYYMMDD_HHMMSS/
│   ├── screenshot_0.png
│   ├── screenshot_1.png
│   ├── plan.json
│   └── results.json
...
└── all_plans_YYYYMMDD_HHMMSS.json
```

## 创建新插件

要创建新插件，请遵循以下步骤：

1. 在 `plugins` 目录中创建新的子目录
2. 实现插件的核心功能（service.py）
3. 创建与 Browser-Use 集成的接口（integration.py）
4. 添加 `__init__.py` 文件，导出公共 API
5. 更新本 README 文件，添加新插件的文档

## 设计原则

插件应遵循以下设计原则：

1. **非侵入性**：插件不应修改 Browser-Use 的核心代码
2. **可配置**：插件应提供配置选项，以适应不同的使用场景
3. **健壮性**：插件应优雅地处理错误，不影响主要功能
4. **文档完整**：每个插件应有完整的文档，包括功能、用法和示例 