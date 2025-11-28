# systerd-lite

**Overview**
- **Project**: `systerd-lite` はローカルで動作する軽量な systerd の実装で、MCP（Model Context Protocol）API と Gradio ベースの UI を提供します。
- **Main entry**: 起動用スクリプトは `start-lite.sh`、メイン実行ファイルは `systerd-lite.py` です。

**Requirements**
- **Python**: `python3`（3.8 以上を推奨）
- **Shell**: `zsh` または `bash` が使えます
- **Optional**: `docker` があるとコンテナ関連機能が利用できます

**初期セットアップ**
- リポジトリルートに移動して `start-lite.sh` を実行します。スクリプトは仮想環境を自動作成し、必要な依存をインストールします。

```zsh
chmod +x start-lite.sh
./start-lite.sh
```

- バックグラウンドで起動したい場合:

```zsh
nohup ./start-lite.sh > /tmp/systerd-lite.log 2>&1 &
echo $!
```

**起動オプション**（`start-lite.sh` の引数）
- `--port PORT` : HTTP API のポート（デフォルト `8089`）
- `--gradio PORT` : Gradio UI のポート（デフォルト `7861`）
- `--no-ui` : Gradio UI を無効化してヘッドレスで起動
- `--debug` : デバッグログを有効化

例:

```zsh
./start-lite.sh --port 8089 --gradio 7861
./start-lite.sh --no-ui
./start-lite.sh --gradio 7870 --debug
```

**主要なファイル/ディレクトリ**
- `start-lite.sh` : 起動ラッパースクリプト（仮想環境作成、依存インストール、起動）
- `systerd-lite.py` : アプリ本体（HTTP サーバ、MCP、Gradio UI を含む）
- `systerd_lite/` : アプリケーションモジュール群（`mcp.py`, `ui/`, `context.py` 等）

**動作確認（簡単）**
- ヘルスチェック:

```zsh
curl -sS http://127.0.0.1:8089/health | jq .
```

- MCP ツール一覧:

```zsh
curl -sS http://127.0.0.1:8089/mcp/tools | jq .
```

- MCP ツール呼び出し（例: `calculate`）:

```zsh
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"calculate","arguments":{"expression":"1 + 1"}}' \
  http://127.0.0.1:8089/mcp/call | jq .
```

- Gradio UI の有無を確認する（HTTP ルートの取得）:

```zsh
curl -sS http://127.0.0.1:7861/ | sed -n '1,40p'
```

**代表的な検証手順**
- `get_system_info`:

```zsh
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"get_system_info","arguments":{}}' \
  http://127.0.0.1:8089/mcp/call | jq .
```

- `list_units`（systemd ユニットの一覧。出力が非常に大きくなる場合があります）:

```zsh
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"list_units","arguments":{}}' \
  http://127.0.0.1:8089/mcp/call | jq .result | sed -n '1,200p'
```

- タスク作成 / 確認:

```zsh
# タスク作成
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"create_task","arguments":{"name":"cp_test","description":"test","command":"/bin/echo test","scheduled_time":"+1m","repeat":"once"}}' \
  http://127.0.0.1:8089/mcp/call | jq .

# タスク一覧確認
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"list_tasks","arguments":{}}' \
  http://127.0.0.1:8089/mcp/call | jq .
```

**ログとトラブルシューティング**
- 起動ログ（バックグラウンド起動時にリダイレクトした場合）: ` /tmp/systerd-lite.log` を確認してください。標準起動ではコンソール出力にログが出ます。
- 仮想環境: スクリプト実行時に `./.venv` が自動作成されます。依存がインストールされない場合は手動でインストールしてください:

```zsh
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install aiohttp psutil dbus-next gradio numpy sympy requests
```

- ポートが既に使用されている場合は `--port` / `--gradio` オプションで変更してください。
- systemd 関連（`list_units`, `manage_service` 等）は root 権限や特定の環境設定が必要な場合があります。権限不足でエラーが出るときは sudo または root 環境での実行を検討してください。

**セキュリティ注意**
- HTTP API はローカルネットワークでアクセス可能です。公開環境で使用する場合はファイアウォール設定や認証を適切に追加してください。
- `mcp` の一部ツールはシステムに変更を加えるため、操作には注意してください。

**貢献方法**
- バグ修正や機能追加は PR を送ってください。簡単な変更の場合は issue を先に作成していただけると助かります。

**ライセンス**
- 特に指定がない場合はリポジトリに含まれる `LICENSE` に従ってください。

---

# systerd-lite (English)

**Overview**
- **Project**: `systerd-lite` is a lightweight implementation of systerd for local use, providing MCP (Model Context Protocol) API and a Gradio-based UI.
- **Main entry**: The main launcher script is `start-lite.sh`, and the main executable is `systerd-lite.py`.

**Requirements**
- **Python**: `python3` (recommended 3.8 or later)
- **Shell**: `zsh` or `bash`
- **Optional**: `docker` for container-related features

**Initial Setup**
- Move to the repository root and run `start-lite.sh`. The script automatically creates a virtual environment and installs required dependencies.

```zsh
chmod +x start-lite.sh
./start-lite.sh
```

- To run in the background:

```zsh
nohup ./start-lite.sh > /tmp/systerd-lite.log 2>&1 &
echo $!
```

**Startup Options** (arguments for `start-lite.sh`)
- `--port PORT` : HTTP API port (default `8089`)
- `--gradio PORT` : Gradio UI port (default `7861`)
- `--no-ui` : Disable Gradio UI (headless mode)
- `--debug` : Enable debug logging

Examples:

```zsh
./start-lite.sh --port 8089 --gradio 7861
./start-lite.sh --no-ui
./start-lite.sh --gradio 7870 --debug
```

**Main Files/Directories**
- `start-lite.sh` : Startup wrapper script (creates venv, installs dependencies, launches)
- `systerd-lite.py` : Main application (HTTP server, MCP, Gradio UI)
- `systerd_lite/` : Application modules (`mcp.py`, `ui/`, `context.py`, etc.)

**Basic Verification**
- Health check:

```zsh
curl -sS http://127.0.0.1:8089/health | jq .
```

- List MCP tools:

```zsh
curl -sS http://127.0.0.1:8089/mcp/tools | jq .
```

- Call MCP tool (example: `calculate`):

```zsh
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"calculate","arguments":{"expression":"1 + 1"}}' \
  http://127.0.0.1:8089/mcp/call | jq .
```

- Check Gradio UI (fetch HTTP root):

```zsh
curl -sS http://127.0.0.1:7861/ | sed -n '1,40p'
```

**Typical Verification Steps**
- `get_system_info`:

```zsh
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"get_system_info","arguments":{}}' \
  http://127.0.0.1:8089/mcp/call | jq .
```

- `list_units` (systemd unit list; output may be very large):

```zsh
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"list_units","arguments":{}}' \
  http://127.0.0.1:8089/mcp/call | jq .result | sed -n '1,200p'
```

- Create/Check tasks:

```zsh
# Create task
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"create_task","arguments":{"name":"cp_test","description":"test","command":"/bin/echo test","scheduled_time":"+1m","repeat":"once"}}' \
  http://127.0.0.1:8089/mcp/call | jq .

# List tasks
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"name":"list_tasks","arguments":{}}' \
  http://127.0.0.1:8089/mcp/call | jq .
```

**Logs and Troubleshooting**
- Startup logs (when redirected in background): Check `/tmp/systerd-lite.log`. For standard startup, logs are printed to the console.
- Virtual environment: `./.venv` is automatically created when running the script. If dependencies are not installed, install manually:

```zsh
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install aiohttp psutil dbus-next gradio numpy sympy requests
```

- If ports are already in use, change with `--port` / `--gradio` options.
- systemd-related tools (`list_units`, `manage_service`, etc.) may require root privileges or specific environment settings. If you get permission errors, try running as sudo or root.

**Security Notes**
- The HTTP API is accessible on the local network. For public use, configure firewall and authentication as needed.
- Some MCP tools can modify the system; use with care.

**Contributing**
- For bug fixes or feature additions, please send a PR. For simple changes, opening an issue first is helpful.

**License**
- Unless otherwise specified, follow the `LICENSE` included in the repository。
