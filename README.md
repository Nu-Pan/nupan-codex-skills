# nupan-codex-skills

Nu-Pan が管理する Codex スキルを集約したモノレポです。
各スキルの仕様、開発用文書、インストール可能な配布物を `skills/` 配下で管理します。

全スキルに共通する構造と保守方法は、[`docs/skill-repository-spec.md`](docs/skill-repository-spec.md) に定義しています。
新規スキルは、[`docs/adding-a-skill.md`](docs/adding-a-skill.md) の手順で追加します。
開発環境の構築方法とテストの実行規約は、[`docs/development-environment.md`](docs/development-environment.md) に定義しています。

## 収録スキル

- [`japanese-writing-skill`](skills/japanese-writing-skill/README.md): 日本語の技術文書を明確に構成するスキルです。
- [`maintain-lean-implementation`](skills/maintain-lean-implementation/README.md): 現行仕様に必要な実装だけを簡潔で保守しやすい状態に保つスキルです。
- [`maintain-lean-tests`](skills/maintain-lean-tests/README.md): 意味のある挙動を検証し、重複や旧仕様のテストを整理するスキルです。
- [`maintain-software-specifications`](skills/maintain-software-specifications/README.md): 重要な人間意図と裁量範囲を明確にし、正本仕様を保守するスキルです。
- [`python-dev-skill`](skills/python-dev-skill/README.md): Python プロジェクトの構成に合わせて実装と品質検査を行うスキルです。
- [`review-specification-conformance`](skills/review-specification-conformance/README.md): 正本仕様の矛盾と仕様に対する実装の不整合をレビューするスキルです。
- [`write-repository-routing-docs`](skills/write-repository-routing-docs/README.md): 対象本文を読む前に必要なファイルを選ぶための案内を作成するスキルです。

## インストール

全スキルは、共通インストールスクリプトでインストールできます。
このリポジトリのルートで、スキル名と導入先ディレクトリを指定します。
コマンドの書式を次に示します。

```bash
python3 scripts/install_skill.py {{skill-name}} {{target-repository}}
```

`japanese-writing-skill` をインストールする例を次に示します。

```bash
python3 scripts/install_skill.py japanese-writing-skill /absolute/path/to/repository
```

導入先には、既存のディレクトリを相対パスまたは絶対パスで指定できます。
Git リポジトリであることは必須ではありません。
配布物は、`{{target-repository}}/.agents/skills/{{skill-name}}/` に配置されます。

同名スキルがすでに存在する場合は、配布物全体を置き換えます。
導入先で加えた変更や、旧版だけに存在するファイルは残りません。

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
