# スキルの仕様

## 概要

- Python 開発環境として有用なツールの使用を推奨する
- プロジェクトが宣言する Python のバージョン、仮想環境、依存関係管理方法、ツール設定を優先する。Python のバージョンが宣言されていない場合は Python 3.11 以上を使用する
- Ruff と mypy が未導入の場合は、既存の開発用 dependency group や requirements file へ追加する。pytest を使用するプロジェクトでは、pytest-timeout も同じ開発依存関係へ追加する。依存関係管理方法がない場合は、リポジトリ内の `.venv` に pip で導入し、グローバル環境を変更しない
- 検査対象の Python package、module、test command は、設定ファイル、package 構成、既存の開発手順を調査して決定する
- 実行可能な Python の処理を作成または変更した場合は、代表経路の実行時間を実測する

## 適用条件

Python プロジェクトの構成に従った実装と品質検査が必要な場合に、このスキルを使用する。
想定する作業には、次の内容を含む。

- Python code と package の開発または修正
- Python code のレビュー
- Python 開発環境の整備
- Python 向け品質ゲートの実行または変更

## 独立性と合成

このスキルは、他のスキルがなくても、Python の実装、テスト、品質ゲート、代表経路の計測を完了する。
汎用的な実装、テスト、性能スキルを、Python 作業の必須条件にしない。

他のスキルと同時に適用する場合は、Python の環境、runner、型検査、lint、resource 検査に関する詳細を追加する。
実装とテストの簡潔性、レビューの変更範囲、性能計測の条件は、両立する規則を累積して満たす。
同じ test、品質ゲート、代表経路の計測をスキルごとに繰り返さず、一回の実行結果を共有する。

Python 用の開発依存を追加する場合も、対象プロジェクトの依存関係管理と、必要な外部依存だけを追加する規則を同時に満たす。
同時に満たせない場合は、依存を追加して完了扱いにせず、競合する要求を報告する。

## pytest と package test

### goal

- pytest では filesystem、HOME、cwd、環境変数を `tmp_path`、fixture、monkeypatch で隔離する
- Python package、import path、公開 symbol、package data を変更した場合は、source checkout だけでなく install 後相当の layout でも import と resource 参照を検証する
- optional な外部 executable を必要とする pytest は、存在を検査し、具体的な理由を指定した `pytest.mark.skipif` で skip する
- pytest を使用するプロジェクトでは、停止、deadlock、終了しない外部 process を検出するため、pytest-timeout で全体に保守的な timeout を設定する
- timeout 値は正常時の実測時間と実行環境の揺らぎを考慮して決める。正当に長い test には、理由を残したうえで test 単位の timeout を設定する
- 変更中の focused test でも pytest-timeout を有効にする
- pytest-timeout は停止検出に使用し、処理速度の合格を示す benchmark として扱わない
- Python の実行時間を判断する場合は、project の benchmark または代表経路の wall-clock time を計測する

### non-goal

- source checkout からの import 成功だけで、install 後の package 構成を検証済みとすること
- pytest を使用していないプロジェクトへ pytest または pytest-timeout を強制すること
- timeout に到達しないことだけで、実行時間を確認済みとすること

## Ruff

### goal

- プロジェクトの設定を使用して lint、import の整理状態、format を検査し、構文上・静的解析上の明白な不具合、未使用の import、import 順序、基本的な style 違反を機械的に検出する
- 変更中は変更箇所に絞った検査を行う
- 設定がない状態で Ruff を導入する場合は、小さく説明可能な rule set から始める。`noqa` が不可避な場合は対象を最小範囲に限定して理由を近傍へ残す

### non-goal

- Ruff の全 rule、preview rule、厳格な docstring rule を最初から一律に有効化すること
- 広範な `noqa` や file-level ignore で Ruff の指摘を隠すこと

## mypy

### goal

- プロジェクトの設定と package 構成から検査対象を決め、first-party の Python code に対して型の不整合、到達不能な前提、不適切な `Any` の流出、無効になった ignore を検出する
- 変更中は変更した module とその利用側を検査する
- 設定がない状態で mypy を導入する場合は first-party code を blocking な対象とし、既存 code の型付け状況に合わせて段階的に厳格化する。型エラーは原則として実装または型注釈を修正して解消する

### non-goal

- 既存 code の状態を調査せず、最初から strict mode 全体や全関数への型注釈を強制すること
- error を隠すために、対象全体の除外、`ignore_errors`、広範な `type: ignore`、根拠のない `Any` や `cast` を追加すること
- vendored code、生成 code、仮想環境、第三者 package まで無条件に型検査の対象とすること
- mypy の成功を runtime test の代わりにすること

## 完了ゲート

### goal

- 完了前には、現在の worktree に対して first-party の Python code 全体の read-only な Ruff、プロジェクトが定める全対象の mypy、full test を、少なくとも以下に相当する command で fresh に実行する

```bash
python -m ruff check {{first-party-targets}}
python -m ruff format --check {{first-party-targets}}
python -m mypy {{first-party-targets-or-packages}}
PYTHONDEVMODE=1 PYTHONWARNINGS="error::ResourceWarning" python -m pytest {{project-full-test-arguments}}
```

- pytest を使用する場合は pytest-timeout を full test でも有効にする。project 固有の test runner を使用する場合も、その runner が起動する Python process へ development mode と `ResourceWarning` のエラー化を適用する
- 第三者 library だけが発生させる warning を除外する必要がある場合は、実際の出力を根拠に module、message、warning category を用いて最小範囲に限定し、理由を記録する
- 実行可能な処理を作成または変更した場合は、代表経路の実行時間を計測する。既存実装と比較する場合は、同じ command、入力、環境を使用する

### non-goal

- `ResourceWarning` 以外を含む全 warning を、この Skill だけを根拠として一律にエラー化すること
- project code による resource leak を warning filter、広範な pytest 設定、環境変数の解除によって隠すこと
- 第三者 library の warning を、project code に原因があるか調査せず修正対象または除外対象と決めること
- focused test の成功や過去の実行結果だけで、development mode を使用した full test が成功したと報告すること
- development mode と `ResourceWarning` 検査だけで、すべての resource leak を検出できると保証すること
- pytest-timeout の成功を、性能要件または性能改善の根拠として報告すること
