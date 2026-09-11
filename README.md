# nupan-codex-skills

Nu-Pan が管理する Codex スキルを集約したモノレポです。
各スキルの仕様、開発用文書、インストール可能な配布物を `skills/` 配下で管理します。
各スキルは単独でも組み合わせても使えるように管理します。
必要な要件と設計意図を保ち、読み手が判断しやすい説明と実装を重視します。

全スキルに共通する構造と保守方法は、[`docs/skill-repository-spec.md`](docs/skill-repository-spec.md) に定義しています。
新規スキルは、[`docs/adding-a-skill.md`](docs/adding-a-skill.md) の手順で追加します。
開発環境の構築方法とテストの実行規約は、[`docs/development-environment.md`](docs/development-environment.md) に定義しています。
単独評価と組み合わせ評価の台帳は、[`skill-composition.json`](skill-composition.json) に記録しています。

## 収録スキル

- [`japanese-writing-skill`](skills/japanese-writing-skill/README.md): 日本語の技術文書を、意図と判断基準が伝わる説明へ組み直します。
- [`maintain-lean-implementation`](skills/maintain-lean-implementation/README.md): 必要な要件を保ち、関連する実装を読み取りやすく変更しやすい構成へ組み直します。
- [`maintain-lean-tests`](skills/maintain-lean-tests/README.md): 回帰検出能力を保ち、検証の意図を読み取りやすいテストへ整理します。
- [`maintain-software-specifications`](skills/maintain-software-specifications/README.md): 利用者の要求を関連する正本仕様へ統合し、必要な要件と設計意図を判断しやすい形で保ちます。
- [`measure-runtime-performance`](skills/measure-runtime-performance/README.md): 性能の判断に必要な観測を選び、比較可能な実測値から原因と改善結果を確かめます。
- [`python-dev-skill`](skills/python-dev-skill/README.md): 既存の Python 環境と品質ゲートを優先し、変更の判断に必要な検証手段を選びます。
- [`review-specification-conformance`](skills/review-specification-conformance/README.md): 必要な判断を妨げる仕様や実装の問題を、確認済みの根拠で報告します。
- [`suggest-commit-message`](skills/suggest-commit-message/README.md): セッションの意図から、未コミット変更全体の主題を一行で伝えるコミットメッセージを提案します。
- [`validate-openai-structured-output-schema`](skills/validate-openai-structured-output-schema/README.md): OpenAI Structured Outputs 用の JSON Schema を、配布 CLI でバージョン付きプロファイルへ照合します。
- [`verify-codex-cli-behavior`](skills/verify-codex-cli-behavior/README.md): アプリが依存する Codex CLI の挙動を対象版のソースと安全な実測で調べ、根拠と互換性対策を追跡可能にします。

## インストール

スキルは、共通インストールスクリプトで個別または一括インストールできます。
このリポジトリのルートで、スキル名と導入先ディレクトリを指定します。
個別に導入する場合は、スキル名を指定します。

```bash
python3 scripts/install_skill.py {{skill-name}} {{target-repository}}
```

全スキルを導入する場合は、`all` を指定します。

```bash
python3 scripts/install_skill.py all {{target-repository}}
```

導入先には、既存のディレクトリを相対パスまたは絶対パスで指定できます。
Git リポジトリであることは必須ではありません。
配布物は、`{{target-repository}}/.agents/skills/{{skill-name}}/` に配置されます。

同名スキルがすでに存在する場合は、配布物全体を置き換えます。
導入先で加えた変更や、旧版だけに存在するファイルは残りません。
一括インストールでは、導入先にだけ存在するスキルを削除しません。

一括インストールでは、導入先とすべての配布物を変更前に検証します。
処理途中で失敗した場合は、処理中のスキルを既存版へ復元します。
それ以前にインストールしたスキルは、新しい配布物のまま残ります。

## 使用方法

インストール後に Codex のセッションを開始します。
スキルを明示的に呼び出す場合は、依頼にスキル名を含めます。

```text
${{skill-name}} を使って、依頼内容を実行してください。
```

適用場面と固有の振る舞いは、[収録スキル](#収録スキル)から各スキルの仕様を参照してください。

## 開発

初回は、プロジェクトローカルの Python 環境を作成して開発依存をインストールします。

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

新規スキルの雛形は、スキル名を指定して生成します。

```bash
python3 scripts/create_skill.py {{skill-name}}
```

編集後は、対象スキルを検証します。
対象スキルに自動テストがある場合は、pytest も実行します。

```bash
python3 -m pytest skills/{{skill-name}}/tests
python3 scripts/validate_skills.py {{skill-name}} [{{skill-name}} ...]
```

リポジトリ全体へ影響する変更では、全スキルと全テストを検証します。

```bash
python3 scripts/validate_skills.py
python3 -m pytest tests skills
```

対象スキルに `tests/` がない場合の扱いは、[スキル開発環境の規約](docs/development-environment.md)を参照してください。
