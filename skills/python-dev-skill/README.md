# python-dev-skill

Python プロジェクトの構成に合わせて、実装と品質検査を行う Codex スキルです。
プロジェクトが宣言する Python、仮想環境、依存関係管理方法、ツール設定を優先します。
調査した構成に基づいて、検査対象とコマンドを決定します。

変更中の focused check と、fresh な完了ゲートを分けて適用します。
主な検査内容を次に示します。

- pytest fixture による隔離
- install 後相当の package test
- Ruff と mypy
- pytest-timeout
- Python development mode と `ResourceWarning` 検査

実行時仕様の正本は、[`SPEC.md`](SPEC.md) です。
配布物は、[`dist`](dist) にあります。
共通の導入方法は、[ルート README のインストール手順](../../README.md#インストール)を参照してください。

## 呼び出し例

Python の実装と品質検査を依頼するときは、プロンプトで `$python-dev-skill` を指定します。

```text
$python-dev-skill を使って、このリポジトリの変更を実装し、適切な Python 品質ゲートを実行してください。
```
