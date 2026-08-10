---
name: python-dev-skill
description: Python プロジェクトの開発、修正、レビュー、開発環境整備で、プロジェクトが宣言する Python・仮想環境・依存関係管理・ツール設定を優先し、pytest の隔離と package test を扱い、Ruff、mypy、pytest-timeout、Python development mode、ResourceWarning 検査を適用する。実行可能な Python の処理では代表経路を実測し、benchmark、CPU profiler、memory profiler を目的に応じて選ぶ。Python code、Python package、pytest、Python 向け品質ゲート、性能計測を変更または検証するときに使用する。
---

# Python 固有の品質ゲートを適用する

対象 project の Python 構成を優先し、Python code と package に適した test と検査ツールを適用する。

## 1. Python 環境と検査対象を特定する

- `pyproject.toml`、lockfile、requirements file、`setup.cfg`、`tox.ini` などから、Python のバージョン、仮想環境、依存関係管理方法、Ruff・mypy・test runner・性能計測 tool の設定を特定する。
- 検査対象の first-party Python package・module と、focused test・full test の command を package 構成と既存の開発手順から決める。
- 宣言済みの Python、仮想環境、dependency manager、設定、project script を優先する。Python のバージョンが宣言されていない場合だけ Python 3.11 以上を使用する。
- Ruff と mypy が未導入なら、既存の開発用 dependency group または requirements file へ追加する。pytest を使用する project では、pytest-timeout も同じ開発依存関係へ追加する。
- 対象リポジトリの規則が依存追加を禁止する場合は追加せず、実行できない品質ゲートと理由を報告する。
- 依存関係管理方法がない場合は repository 内の `.venv` に pip で導入し、global environment を変更しない。
- 選択した interpreter から `python -m ruff`、`python -m mypy`、test runner を起動する。

## 2. pytest と Python package を検証する

- pytest では filesystem、HOME、cwd、環境変数を `tmp_path`、fixture、monkeypatch で隔離する。
- Python package、import path、公開 symbol、package data を変更した場合は、source checkout だけでなく install 後相当の layout でも import と resource 参照を検証する。
- optional な外部 executable を必要とする pytest は存在を検査し、具体的な理由を指定した `pytest.mark.skipif` で skip する。
- source checkout からの import 成功だけで、install 後の package 構成を検証済みとしない。
- pytest を使用する project では、停止、deadlock、終了しない外部 process を検出するため、pytest-timeout で保守的な global timeout を設定する。
- timeout 値は正常時の実測時間と実行環境の揺らぎを考慮して決める。正当に長い test には、理由を残して test 単位の timeout を設定する。
- 変更中の focused test でも pytest-timeout を有効にする。
- pytest-timeout を停止検出に使用し、処理速度の合格を示す benchmark として扱わない。
- Python の実行時間を判断する場合は、project の benchmark または代表経路の wall-clock time を計測する。
- pytest を使用していない project へ pytest または pytest-timeout を導入しない。

## 3. パフォーマンス計測 tool を選ぶ

- project が管理する benchmark、profiler、計測 command、設定を最初に使用する。
- 代表経路は既存 benchmark または `time.perf_counter_ns()` などの monotonic clock で計測する。
- 小さく独立した処理には `timeit` を使用する。setup、I/O、garbage collection、process startup を含む待ち時間は、end-to-end の経路で別に計測する。
- process を分離した反復、warm-up、結果の保存と比較が必要なら `pyperf` を使用する。
- pytest で、定量的な性能要件、安定して再現できる回帰、または既存の性能品質ゲートを継続検証する場合は、test 構成と両立する `pytest-benchmark` を使用し、機能上の正しさも検証する。
- 再現可能な短い処理の関数別 call 数と時間には `cProfile` と `pstats` を使用する。
- 長時間実行、thread、multiprocess、実行中 process、または code 変更を避ける CPU 調査には `py-spy` を使用する。
- Python allocation と snapshot 差分には `tracemalloc` を使用する。native extension、interpreter、peak、一時 allocation まで必要なら Memray を使用する。
- memory tool は、memory 要件、allocation の症状、または実測上の根拠がある場合だけ使用する。候補 tool を一律に実行または導入しない。
- `pyperf`、`pytest-benchmark`、`py-spy`、Memray の選定条件を満たす場合は、独自 benchmark または profiler helper を追加して第三者 tool の開発依存を回避しない。
- profiler の実行時間を benchmark 結果にしない。原因特定後は profiler なしで代表経路を同じ条件で再計測する。
- 既存 tool と標準ライブラリでは必要な観測ができない場合は、選択した第三者 tool だけを既存の開発依存へ追加し、lockfile を更新する。runtime dependency へ追加しない。
- 依存追加が禁止されている場合は追加せず、代替した方法または未計測の範囲を報告する。依存関係管理方法がない場合は repository 内の `.venv` を使用する。
- 再生成可能な profile、trace、benchmark 出力は、project が正本として管理する場合だけ repository へ追加する。
- `py-spy` の attach など追加権限を必要とする操作では、権限を回避または拡大しない。許可された方法へ切り替えるか未計測として報告する。

## 4. Ruff を実行する

- project の Ruff 設定を使い、lint、未使用 import、import 順序、format を検査する。
- 変更中は変更した first-party path を中心に検査する。
- 設定なしで Ruff を導入する場合は、小さく説明可能な rule set から始める。全 rule、preview rule、厳格な docstring rule を一律に有効化しない。
- `noqa` が不可避なら対象を最小範囲に限定し、理由を近傍へ残す。広範な `noqa` や file-level ignore で指摘を隠さない。

## 5. mypy を実行する

- project の mypy 設定と package 構成から検査対象を決め、型の不整合、到達不能な前提、不適切な `Any` の流出、無効になった ignore を検出する。
- 変更中は変更した module とその利用側を検査する。
- 設定なしで導入する場合は first-party code を blocking な対象とし、既存 code の型付け状況に合わせて段階的に厳格化する。最初から strict mode 全体や全関数への型注釈を強制しない。
- 型エラーは実装または正確な型注釈で解消する。対象全体の除外、`ignore_errors`、広範な `type: ignore`、根拠のない `Any` や `cast` で隠さない。
- vendored code、生成 code、仮想環境、第三者 package を無条件に検査対象へ含めない。
- mypy の成功を runtime test の代わりにしない。

## 6. 完了ゲートを実行する

完了前には、現在の worktree に対して first-party Python code 全体の書き換えなしの Ruff、project が定める全対象の mypy、full test を、次に相当する command で fresh に実行する。

```bash
python -m ruff check {{first-party-targets}}
python -m ruff format --check {{first-party-targets}}
python -m mypy {{first-party-targets-or-packages}}
PYTHONDEVMODE=1 PYTHONWARNINGS="error::ResourceWarning" python -m pytest {{project-full-test-arguments}}
```

- pytest を使用する場合は pytest-timeout を full test でも有効にする。project 固有の test runner を使用する場合も、その runner が起動する Python process へ development mode と `ResourceWarning` のエラー化を適用する。
- 実行可能な処理を作成または変更した場合は、代表経路の実行時間を計測する。既存実装と比較する場合は、同じ command、入力、環境を使用する。
- profiler を使用した場合は、profiler なしの代表経路を再計測する。第三者の計測 tool を追加した場合は、選定理由と追加した開発依存を報告する。
- 第三者 library だけが発生させる warning を除外する場合は、実際の出力を根拠に category、module、message で最小範囲に限定し、理由を記録する。
- `ResourceWarning` 以外の全 warning を、この skill だけを根拠として一律にエラー化しない。
- project code の resource leak を warning filter、広範な pytest 設定、環境変数の解除で隠さない。
- 第三者 library の warning を、project code に原因があるか調査せず修正対象または除外対象と決めない。
- focused test や過去の実行結果だけで、development mode を使用した full test が成功したと報告しない。
- development mode と `ResourceWarning` 検査だけですべての resource leak を検出できると保証しない。
- pytest-timeout の成功を、性能要件または性能改善の根拠として報告しない。
