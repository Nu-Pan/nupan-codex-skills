# nupan-codex-skills

Nu-Pan が管理する Codex スキルを集約したモノレポです。
各スキルの仕様、開発用文書、インストール可能な配布物を `skills/` 配下で管理します。
各スキルは単独で成立し、任意の複数スキルを同時に導入した場合も、適用される規則を累積して実行できるように管理します。

全スキルに共通する構造と保守方法は、[`docs/skill-repository-spec.md`](docs/skill-repository-spec.md) に定義しています。
新規スキルは、[`docs/adding-a-skill.md`](docs/adding-a-skill.md) の手順で追加します。
開発環境の構築方法とテストの実行規約は、[`docs/development-environment.md`](docs/development-environment.md) に定義しています。
単独評価と組み合わせ評価の台帳は、[`skill-composition.json`](skill-composition.json) に記録しています。

## 収録スキル

- [`japanese-writing-skill`](skills/japanese-writing-skill/README.md): 日本語の技術文書を明確に構成するスキルです。
- [`maintain-lean-implementation`](skills/maintain-lean-implementation/README.md): 代表経路を実測し、現行仕様に必要な実装だけを簡潔で保守しやすい状態に保つスキルです。
- [`maintain-lean-tests`](skills/maintain-lean-tests/README.md): 意味のある挙動と実測済みの性能回帰を検証し、重複や旧仕様のテストを整理するスキルです。
- [`maintain-software-specifications`](skills/maintain-software-specifications/README.md): 重要な人間意図と裁量範囲を明確にし、正本仕様を保守するスキルです。
- [`measure-runtime-performance`](skills/measure-runtime-performance/README.md): 必要な計測 tool を選び、代表経路の実測で確認したボトルネックだけを改善するスキルです。
- [`python-dev-skill`](skills/python-dev-skill/README.md): Python プロジェクトの構成と用途に合わせて benchmark・profiler を選び、実装と品質検査を行うスキルです。
- [`review-specification-conformance`](skills/review-specification-conformance/README.md): 正本仕様の矛盾と仕様に対する実装の不整合をレビューするスキルです。
- [`suggest-commit-message`](skills/suggest-commit-message/README.md): セッションの目的と判断から、変更全体の高レベルな意味を表すコミットメッセージを提案するスキルです。
- [`validate-openai-structured-output-schema`](skills/validate-openai-structured-output-schema/README.md): Codex CLI と OpenAI Structured Outputs 向けの JSON Schema をオフライン検証するスキルです。

## インストール

スキルは、共通インストールスクリプトで個別または一括インストールできます。
このリポジトリのルートで、スキル名と導入先ディレクトリを指定します。
1 つのスキルをインストールするコマンドの書式を次に示します。

```bash
python3 scripts/install_skill.py {{skill-name}} {{target-repository}}
```

`japanese-writing-skill` をインストールする例を次に示します。

```bash
python3 scripts/install_skill.py japanese-writing-skill /absolute/path/to/repository
```

全スキルを一括インストールするコマンドの書式を次に示します。

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

各スキルの概要と仕様へのリンクは、[収録スキル](#収録スキル)から各スキルの `README.md` を参照してください。
固有の保守規則があるスキルでは、そのスキルの `AGENTS.md` も参照します。

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
