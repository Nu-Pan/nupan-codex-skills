# `README.md`

## Summary
- Pythonプロジェクトの実装と品質検査を支援するスキルの概要と、優先すべきプロジェクト設定・検査方針を示す。実行時仕様と配布物への入口でもある。

## Read this when
- Pythonプロジェクトの実装、テスト、静的解析、性能計測、開発モードでの検査に関する作業を始めるとき
- このスキルの実行時仕様を確認する必要があるとき
- 配布されているスキル成果物の場所を確認するとき

## Do not read this when
- 具体的な実行時の規則や手順を確認したい場合は、直接実行時仕様を読むとき
- 配布物の内容だけを確認したい場合は、直接配布物のディレクトリへ進むとき
- Python以外のプロジェクトの実装や品質検査を扱うとき

## hash
- fb2f3b7dc88a88a27d2162306253f3ef7c72f81da55e1fa832ef5b16a3f388b8

# `SPEC.md`

## Summary
- Python プロジェクトの実装、レビュー、開発環境整備、品質ゲート、性能計測に関する実行時仕様を定める。Python の環境選択、依存関係、pytest、Ruff、mypy、性能計測、完了前の検証方針を確認するための入口である。

## Read this when
- Python code や package の開発・修正・レビューを行うとき
- Python の開発依存関係、テスト環境、品質ゲートを整備または変更するとき
- Python の benchmark、profiler、性能回帰検査を追加・変更するとき
- Python 作業の完了前に lint、型検査、full test、代表経路の実行時間計測条件を確認するとき

## Do not read this when
- Python を含まない作業を行うとき
- Python 作業でも、対象の具体的な実装やテストコードを直接確認する必要があるときは、先に対象の source または test を読むべき場合
- リポジトリ共通のスキル構造や追加手順だけを確認したいときは、共通仕様や追加手順の文書を読むべき場合

## hash
- da9e0d1f83c643e6aa48b1e5401cc66fe90f167901c38c1879b0d693b0649d3c

# `dist`

## Summary
- Python プロジェクトの開発支援スキルを配布する領域。Python の実装・パッケージ構成・pytest・品質検査・性能計測に関する作業の入口となる。

## Read this when
- Python の実装、パッケージ構成、pytest、開発依存関係、Ruff・mypy 設定、品質ゲートを変更または検証するとき
- Python の実行時間、CPU、メモリ割り当て、ベンチマーク、プロファイリングを調査するとき
- Python の変更後に lint、format、型検査、テスト、ResourceWarning 検査を実行するとき

## Do not read this when
- Python を含まない実装やテストだけを扱うとき
- 別の言語や専用開発手順が正本となる領域だけを変更するとき
- 既存の Python 実行経路、パッケージ、検査設定に影響しない文章編集を行うとき

## hash
- 30b39d1483b559692aa01e7ebf1c418e36e32a607e4f2728950f60169a4f24a2
