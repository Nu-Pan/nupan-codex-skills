# nupan-codex-skills

Nu-Pan が管理する Codex スキルのリポジトリです。各スキルの仕様と配布物を `skills/` 配下で管理し、単独でも組み合わせても使えるようにしています。

必要な要件と設計意図を軸に、関連する説明や実装を一体として組み直します。その際、読み手が原則を理解し、個別の場面で判断できることを重視します。

保守では [共通仕様](docs/skill-repository-spec.md) に従い、[追加手順](docs/adding-a-skill.md)と[開発環境の規約](docs/development-environment.md)を参照してください。なお、単独・組み合わせ評価の条件は、[評価台帳](skill-composition.json)に記録しています。

## 収録スキル

- [`maintain-lean-implementation`](skills/maintain-lean-implementation/README.md): 必要な要件を保ち、関連する実装を読み取りやすく変更しやすい構成へ組み直します。
- [`maintain-lean-tests`](skills/maintain-lean-tests/README.md): 回帰検出能力を保ち、検証の意図を読み取りやすいテストへ整理します。
- [`maintain-software-specifications`](skills/maintain-software-specifications/README.md): 正本仕様の作成・改訂・推敲で、要求の選別から構成と文章表現までを扱い、要件と設計意図に基づいて判断できる説明に整えます。
- [`python-dev-skill`](skills/python-dev-skill/README.md): 既存の Python 環境と品質ゲートを優先し、変更の判断に必要な検証手段を選びます。
- [`review-specification-conformance`](skills/review-specification-conformance/README.md): 仕様や実装の問題を、確認済みの根拠と判断への影響に基づいて所見として整理します。
- [`suggest-commit-message`](skills/suggest-commit-message/README.md): セッションの意図から、未コミット変更全体の主題を一行で伝えるコミットメッセージを提案します。
- [`validate-openai-structured-output-schema`](skills/validate-openai-structured-output-schema/README.md): OpenAI Structured Outputs 用の JSON Schema を、付属の検証コマンドでバージョン付きの検証規則と照合します。
- [`verify-codex-cli-behavior`](skills/verify-codex-cli-behavior/README.md): アプリが依存する Codex CLI の挙動を対象版のソースと安全な実測で調べ、根拠と互換性対策を追跡可能にします。

## インストール

このリポジトリのルートで、スキル名と導入先ディレクトリを指定します。

```bash
python3 scripts/install_skill.py {{skill-name}} {{target-repository}}
```

また、全スキルを導入する場合は、`all` を指定します。

```bash
python3 scripts/install_skill.py all {{target-repository}}
```

導入先には既存のディレクトリを相対パスまたは絶対パスで指定します。ただし、Git リポジトリである必要はありません。配布物は `{{target-repository}}/.agents/skills/{{skill-name}}/` に配置されます。

同名スキルは配布物全体を置き換えるため、導入先で加えた変更や旧版だけのファイルは残りません。また、一括インストールでは導入先とすべての配布物を変更前に検証し、このリポジトリに収録したスキルを更新します。一方、導入先にだけ存在するスキルは保ちます。

入れ替えに失敗すると、処理中のスキルを既存版へ復元して中止します。ただし、それ以前に導入したスキルは新版のまま残ります。

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
また、対象スキルに自動テストがある場合は、pytest も実行します。

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
