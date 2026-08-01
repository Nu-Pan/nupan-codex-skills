# nupan-codex-skills

Nu-Pan が管理する Codex スキルを集約したモノレポです。
各スキルの仕様、開発用文書、インストール可能な配布物を `skills/` 配下で管理します。

全スキルに共通する構造と保守方法は、[`docs/skill-repository-spec.md`](docs/skill-repository-spec.md) に定義しています。
新規スキルは、[`docs/adding-a-skill.md`](docs/adding-a-skill.md) の手順で追加します。

## 収録スキル

- [`japanese-writing-skill`](skills/japanese-writing-skill/README.md): 日本語の技術文書を明確に構成するスキルです。
- [`python-dev-skill`](skills/python-dev-skill/README.md): Python プロジェクトの構成に合わせて実装と品質検査を行うスキルです。

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

新規スキルの雛形は、スキル名を指定して生成します。

```bash
python3 scripts/create_skill.py {{skill-name}}
```

編集後は、対象スキルを検証します。
引数を省略した場合は、すべてのスキルを検証します。

```bash
python3 scripts/validate_skills.py {{skill-name}} [{{skill-name}} ...]
python3 scripts/validate_skills.py
```

共通ツールを変更した場合は、自動テストも実行します。

```bash
python3 -m unittest discover -s tests -v
```
