# systerd-lite

<div align="center">

**AI-Native OS Core for Linux Systems**

LLMがシステムを自律的に監視・制御・最適化するためのMCPサーバー

</div>

---

## 🎯 概要

`systerd-lite` は、LLM（大規模言語モデル）がLinuxシステムを「自分の体」として操作できるようにするMCPサーバーです。

### 主な特徴

- **🔧 200+ のシステム制御ツール**: プロセス管理、ネットワーク、ストレージ、セキュリティなど
- **🤖 LLM自己編集機能**: LLMが自身のコードや環境を読み書き・修正可能
- **📡 汎用MCP対応**: HTTP/SSE/stdio の3トランスポートをサポート
- **🎛️ Gradio UI**: ブラウザベースの管理インターフェース
- **🔐 柔軟な権限管理**: ツールごとの権限設定とテンプレート

---

## 📦 クイックスタート

### 起動

```bash
# リポジトリをクローン
git clone https://github.com/your/sisterd_lite.git
cd sisterd_lite

# 起動（依存関係は自動インストール）
chmod +x start-mcp.sh
./start-mcp.sh
```

### エンドポイント

| サービス | URL | 説明 |
|---------|-----|------|
| HTTP API | http://localhost:8089 | MCP JSON-RPC エンドポイント |
| Gradio UI | http://localhost:7861 | Web管理インターフェース |
| Health | http://localhost:8089/health | ヘルスチェック |

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8089/health

# システム情報取得
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_system_info","arguments":{}}}'
```

---

## 🛠️ ツールカテゴリ

### 📊 Monitoring（監視）
| ツール | 説明 |
|-------|------|
| `get_system_info` | システム全体の情報 |
| `get_cpu_info` | CPU詳細情報 |
| `get_memory_info` | メモリ使用量 |
| `get_disk_usage` | ディスク使用量 |
| `get_temperature` | 温度センサー |
| `list_processes` | プロセス一覧 |
| `get_top_processes` | リソース消費上位 |

### 🔐 Security（セキュリティ）
| ツール | 説明 |
|-------|------|
| `get_selinux_status` | SELinux状態 |
| `get_apparmor_status` | AppArmor状態 |
| `list_firewall_rules` | ファイアウォールルール |
| `scan_suid_files` | SUID/SGIDファイル検索 |
| `get_failed_logins` | 失敗ログイン試行 |
| `audit_permissions` | パーミッション監査 |

### 🖥️ System（システム）
| ツール | 説明 |
|-------|------|
| `manage_service` | systemdサービス制御 |
| `list_units` | systemdユニット一覧 |
| `get_kernel_modules` | カーネルモジュール |
| `get_hardware_info` | ハードウェア情報 |
| `get_usb_devices` | USBデバイス一覧 |

### �� Container（コンテナ）
| ツール | 説明 |
|-------|------|
| `list_containers` | コンテナ一覧 |
| `start_container` | コンテナ起動 |
| `stop_container` | コンテナ停止 |
| `run_container` | 新規コンテナ実行 |
| `get_container_logs` | ログ取得 |

### 🤖 Self（LLM自己編集）

**LLMが自分自身の環境を操作するためのツール群**

| ツール | 説明 |
|-------|------|
| `read_workspace_file` | ワークスペース内ファイル読み取り |
| `write_workspace_file` | ファイル書き込み・作成 |
| `append_to_file` | ファイル追記 |
| `list_workspace_directory` | ディレクトリ一覧 |
| `search_workspace` | ファイル/コンテンツ検索 |
| `execute_shell_command` | シェルコマンド実行 |
| `install_python_package` | Pythonパッケージインストール |
| `get_python_environment` | Python環境情報 |
| `set_environment_variable` | 環境変数設定 |
| `restart_self` | サーバー自己再起動 |
| `get_self_status` | サーバー状態取得 |
| `backup_workspace` | ワークスペースバックアップ |

### 🧮 Calculator（計算）
| ツール | 説明 |
|-------|------|
| `calculate` | 数式評価 |
| `convert_units` | 単位変換 |
| `matrix_operation` | 行列演算 |
| `statistics` | 統計計算 |
| `solve_equation` | 方程式求解 |

### ⚙️ MCP Config（設定管理）
| ツール | 説明 |
|-------|------|
| `get_mcp_config` | 現在の設定取得 |
| `list_mcp_tools` | ツール一覧 |
| `set_mcp_tool_permission` | 個別権限設定 |
| `apply_mcp_template` | テンプレート適用 |
| `get_mcp_templates` | 利用可能テンプレート |

---

## 📋 テンプレート

用途に応じてツールセットを一括設定できます：

| テンプレート | ツール数 | 用途 |
|-------------|---------|------|
| `minimal` | ~18 | 安全な監視のみ |
| `monitoring` | ~18 | システム監視 |
| `development` | ~47 | 開発用（コンテナ、自己編集含む） |
| `security` | ~31 | セキュリティ監査 |
| `full` | ~200 | 全ツール有効 |

```bash
# テンプレート適用
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"apply_mcp_template","arguments":{"template":"development"}}}'
```

---

## 🔌 クライアント設定

### VS Code

`.vscode/mcp.json`:
```json
{
  "servers": {
    "systerd": {
      "type": "http",
      "url": "http://localhost:8089"
    }
  }
}
```

### Claude Desktop

`~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "systerd": {
      "command": "python3",
      "args": ["/path/to/mcp_server_unified.py"]
    }
  }
}
```

### Ollama / HTTP クライアント

```bash
# ツール一覧取得
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# ツール呼び出し
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_uptime","arguments":{}}}'
```

---

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ VS Code  │  │  Claude  │  │  Ollama  │  │ Gradio UI│         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │             │             │             │                │
│       └─────────────┴──────┬──────┴─────────────┘                │
│                            │                                     │
│                     ┌──────▼──────┐                              │
│                     │  MCP HTTP   │  Port 8089                   │
│                     │  Endpoint   │                              │
│                     └──────┬──────┘                              │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                     systerd-lite                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     MCPHandler                               │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │  │Monitoring│ │ Security │ │ Container│ │   Self   │        │ │
│  │  │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │        │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────────┐ │
│  │               Permission Manager                             │ │
│  │    DISABLED │ READ_ONLY │ AI_ASK │ AI_AUTO                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      Linux System                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ systemd  │ │  psutil  │ │  Docker  │ │ File I/O │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 ファイル構成

```
sisterd_lite/
├── start-mcp.sh          # 推奨起動スクリプト
├── start-lite.sh         # 代替起動スクリプト
├── systerd-lite.py       # メインアプリケーション
├── mcp_server_unified.py # stdio/HTTP/SSE統合サーバー
├── README.md             # このファイル
├── .vscode/
│   └── mcp.json          # VS Code MCP設定
├── .state/
│   └── permissions.json  # ツール権限設定（自動生成）
└── systerd_lite/         # Pythonモジュール
    ├── mcp.py            # MCPハンドラー（200+ツール）
    ├── permissions.py    # 権限管理
    ├── sensors.py        # システムセンサー
    ├── tuner.py          # システムチューニング
    ├── container.py      # コンテナ管理
    ├── scheduler.py      # タスクスケジューラ
    └── ui/               # Gradio UIモジュール
```

---

## 🔧 起動オプション

```bash
# 基本起動
./start-mcp.sh

# カスタムポート
./systerd-lite.py --port 9000 --gradio 9001

# ヘッドレスモード（UIなし）
./systerd-lite.py --no-ui

# デバッグモード
./systerd-lite.py --debug
```

---

## 🔐 セキュリティ

### 権限レベル

| レベル | 説明 |
|-------|------|
| `DISABLED` | ツール無効 |
| `READ_ONLY` | 読み取りのみ |
| `AI_ASK` | 実行前に確認 |
| `AI_AUTO` | 自動実行許可 |

### 推奨事項

- 本番環境では `minimal` または `monitoring` テンプレートを使用
- `self` カテゴリのツールは信頼できる環境でのみ有効化
- HTTP APIは必要に応じてファイアウォールで保護

---

## 📜 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照

---

## 🤝 貢献

Issue や Pull Request を歓迎します。大きな変更の場合は先に Issue で議論してください。

---

# systerd-lite (English)

<div align="center">

**AI-Native OS Core for Linux Systems**

An MCP server that allows LLMs to autonomously monitor, control, and optimize Linux systems as their own body.

</div>

---

## 🎯 Overview

`systerd-lite` is an MCP server that enables LLMs (Large Language Models) to operate Linux systems as their own body.

### Key Features

- **🔧 200+ System Control Tools**: Process management, network, storage, security, and more
- **🤖 LLM Self-Editing**: LLM can read, write, and modify its own code and environment
- **📡 Universal MCP Support**: Supports HTTP/SSE/stdio transports
- **🎛️ Gradio UI**: Browser-based management interface
- **🔐 Flexible Permission Management**: Per-tool permission settings and templates

---

## 📦 Quick Start

### Launch

```bash
# Clone repository
git clone https://github.com/your/sisterd_lite.git
cd sisterd_lite

# Start (dependencies auto-installed)
chmod +x start-mcp.sh
./start-mcp.sh
```

### Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| HTTP API | http://localhost:8089 | MCP JSON-RPC endpoint |
| Gradio UI | http://localhost:7861 | Web management interface |
| Health | http://localhost:8089/health | Health check |

### Verification

```bash
# Health check
curl http://localhost:8089/health

# Get system info
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_system_info","arguments":{}}}'
```

---

## 🛠️ Tool Categories

### 📊 Monitoring
| Tool | Description |
|------|-------------|
| `get_system_info` | System overview |
| `get_cpu_info` | Detailed CPU info |
| `get_memory_info` | Memory usage |
| `get_disk_usage` | Disk usage |
| `get_temperature` | Temperature sensors |
| `list_processes` | Process list |
| `get_top_processes` | Top resource usage |

### 🔐 Security
| Tool | Description |
|------|-------------|
| `get_selinux_status` | SELinux status |
| `get_apparmor_status` | AppArmor status |
| `list_firewall_rules` | Firewall rules |
| `scan_suid_files` | SUID/SGID file scan |
| `get_failed_logins` | Failed login attempts |
| `audit_permissions` | Permission audit |

### 🖥️ System
| Tool | Description |
|------|-------------|
| `manage_service` | systemd service control |
| `list_units` | systemd unit list |
| `get_kernel_modules` | Kernel modules |
| `get_hardware_info` | Hardware info |
| `get_usb_devices` | USB device list |

### 🐳 Container
| Tool | Description |
|------|-------------|
| `list_containers` | Container list |
| `start_container` | Start container |
| `stop_container` | Stop container |
| `run_container` | Run new container |
| `get_container_logs` | Get logs |

### 🤖 Self (LLM Self-Editing)

**Tools for LLM to operate its own environment**

| Tool | Description |
|------|-------------|
| `read_workspace_file` | Read workspace file |
| `write_workspace_file` | Write/create file |
| `append_to_file` | Append to file |
| `list_workspace_directory` | List directory |
| `search_workspace` | Search files/content |
| `execute_shell_command` | Run shell command |
| `install_python_package` | Install Python package |
| `get_python_environment` | Python environment info |
| `set_environment_variable` | Set environment variable |
| `restart_self` | Restart server |
| `get_self_status` | Get server status |
| `backup_workspace` | Backup workspace |

### 🧮 Calculator
| Tool | Description |
|------|-------------|
| `calculate` | Evaluate expression |
| `convert_units` | Unit conversion |
| `matrix_operation` | Matrix operations |
| `statistics` | Statistics |
| `solve_equation` | Equation solving |

### ⚙️ MCP Config
| Tool | Description |
|------|-------------|
| `get_mcp_config` | Get current config |
| `list_mcp_tools` | List tools |
| `set_mcp_tool_permission` | Set individual permission |
| `apply_mcp_template` | Apply template |
| `get_mcp_templates` | Available templates |

---

## 📋 Templates

Set toolsets for different use cases:

| Template | Tool Count | Use Case |
|----------|------------|----------|
| `minimal` | ~18 | Safe monitoring only |
| `monitoring` | ~18 | System monitoring |
| `development` | ~47 | Development (includes container, self-edit) |
| `security` | ~31 | Security audit |
| `full` | ~200 | All tools enabled |

```bash
# Apply template
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"apply_mcp_template","arguments":{"template":"development"}}}'
```

---

## 🔌 Client Configuration

### VS Code

`.vscode/mcp.json`:
```json
{
  "servers": {
    "systerd": {
      "type": "http",
      "url": "http://localhost:8089"
    }
  }
}
```

### Claude Desktop

`~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "systerd": {
      "command": "python3",
      "args": ["/path/to/mcp_server_unified.py"]
    }
  }
}
```

### Ollama / HTTP Client

```bash
# List tools
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Call tool
curl -X POST http://localhost:8089 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_uptime","arguments":{}}}'
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ VS Code  │  │  Claude  │  │  Ollama  │  │ Gradio UI│         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │             │             │             │                │
│       └─────────────┴──────┬──────┴─────────────┘                │
│                            │                                     │
│                     ┌──────▼──────┐                              │
│                     │  MCP HTTP   │  Port 8089                   │
│                     │  Endpoint   │                              │
│                     └──────┬──────┘                              │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                     systerd-lite                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     MCPHandler                               │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │  │Monitoring│ │ Security │ │ Container│ │   Self   │        │ │
│  │  │  Tools   │ │  Tools   │ │  Tools   │ │  Tools   │        │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────────┐ │
│  │               Permission Manager                             │ │
│  │    DISABLED │ READ_ONLY │ AI_ASK │ AI_AUTO                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      Linux System                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ systemd  │ │  psutil  │ │  Docker  │ │ File I/O │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
sisterd_lite/
├── start-mcp.sh          # Recommended startup script
├── start-lite.sh         # Alternative startup script
├── systerd-lite.py       # Main application
├── mcp_server_unified.py # Unified stdio/HTTP/SSE server
├── README.md             # This file
├── .vscode/
│   └── mcp.json          # VS Code MCP config
├── .state/
│   └── permissions.json  # Tool permission config (auto-generated)
└── systerd_lite/         # Python modules
    ├── mcp.py            # MCP handler (200+ tools)
    ├── permissions.py    # Permission management
    ├── sensors.py        # System sensors
    ├── tuner.py          # System tuning
    ├── container.py      # Container management
    ├── scheduler.py      # Task scheduler
    └── ui/               # Gradio UI module
```

---

## 🔧 Startup Options

```bash
# Basic startup
./start-mcp.sh

# Custom ports
./systerd-lite.py --port 9000 --gradio 9001

# Headless mode (no UI)
./systerd-lite.py --no-ui

# Debug mode
./systerd-lite.py --debug
```

---

## 🔐 Security

### Permission Levels

| Level | Description |
|-------|-------------|
| `DISABLED` | Tool disabled |
| `READ_ONLY` | Read-only |
| `AI_ASK` | Confirm before execution |
| `AI_AUTO` | Auto-execute allowed |

### Recommendations

- Use `minimal` or `monitoring` template in production
- Enable `self` category tools only in trusted environments
- Protect HTTP API with firewall as needed

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🤝 Contributing

Issues and Pull Requests are welcome. For major changes, please discuss in an Issue first.
