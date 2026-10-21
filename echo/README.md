# Echo

> A terminal AI coding assistant with a beautiful TUI — chat, code, and explore with any AI model.

维护与安装入口见仓库根目录 [README](../README.md)。以下模型名称是原型示例，
请以服务商账号的实际可用项为准。使用 `echo-chat` 避免系统 `echo` 命令冲突。

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CLI](https://img.shields.io/badge/CLI-Textual%20TUI-orange)

---

Echo brings AI-powered coding assistance directly into your terminal. With a gorgeous Textual TUI, support for 5+ AI providers, streaming responses, and session management — it's like having Claude Code or Cursor, but in your terminal.

## Quick Start

```bash
# Install from this source directory (no PyPI release is assumed)
python -m pip install .

# Set your API key
echo config ai.api_key sk-xxx
echo config ai.provider openai
echo config ai.model gpt-4o

# Launch the TUI
echo

# One-shot query
echo chat "explain this Python code"
```

## Features

| Feature | Description |
|---------|-------------|
| **Beautiful TUI** | Catppuccin-themed terminal UI with syntax highlighting |
| **Multi-model** | OpenAI, DeepSeek, Anthropic Claude, Google Gemini, Ollama |
| **Streaming** | Real-time token streaming |
| **Session management** | Save, load, and manage conversations |
| **One-shot mode** | `echo chat "query"` for quick answers |
| **Config management** | Easy CLI-based configuration |

## Commands

```bash
# Launch the TUI
echo

# One-shot query
echo chat "explain this Python code"

# Configuration
echo config --show
echo config ai.api_key sk-xxx
echo config ai.provider deepseek
echo config ai.model deepseek-chat

# List providers
echo providers

# List sessions
echo sessions
```

## Supported Providers

| Provider | Key | Models |
|----------|-----|--------|
| OpenAI | `openai` | GPT-4o, GPT-4o-mini, GPT-4-turbo |
| DeepSeek | `deepseek` | deepseek-chat, deepseek-reasoner |
| Anthropic | `anthropic` | Claude Sonnet 4, Claude 3.5 |
| Google Gemini | `gemini` | Gemini 2.0 Flash, 1.5 Pro |
| Ollama (Local) | `ollama` | Llama 3.1, Qwen 2.5, Mistral |

## Configuration

```bash
echo config ai.api_key sk-xxx
echo config ai.provider deepseek
echo config ai.model deepseek-chat
echo config --show
```

## Development

```bash
git clone https://github.com/miaomiao-lanmiao/first-true.git
cd first-true/echo
pip install -e .
echo
```

## License

MIT
