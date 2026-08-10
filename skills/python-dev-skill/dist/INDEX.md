# `SKILL.md`

## Summary
- Python プロジェクトの開発・修正・レビュー・環境整備に適用する品質ゲートの実行仕様。Python 環境、依存関係、pytest の隔離と timeout、package 構成、Ruff、mypy、ResourceWarning 検査、および目的に応じた性能計測ツールの選定を扱う。Python code・package・pytest 設定・品質検査・性能計測を変更または検証する際の入口となる。

## Read this when
- Python の実装、package 構成、pytest、開発依存関係、Ruff・mypy 設定、品質ゲートを変更または検証するとき
- Python の代表経路の実行時間、CPU、memory allocation、benchmark、profiler を調査するとき
- 開発完了前に、project の設定に従った lint、format、型検査、full test、ResourceWarning 検査を実行するとき

## Do not read this when
- Python を含まない実装やテストだけを扱うとき
- Python の品質検査や性能計測ではなく、別の言語・別の専用開発手順が正本となる領域だけを変更するとき
- 単なる文章編集や、既存の Python 実行経路・package・検査設定に影響しない作業をするとき

## hash
- deeaa4b01dc70677c8ea714f4164fb17921cf4066b5498dc6428e066f8aa7251

# `agents`

## Summary
- Python 開発支援スキルのエージェント向けインターフェース定義を収め、Python の変更に適した性能計測手段の選択、影響範囲の計測、品質ゲートの実行へ導く入口。

## Read this when
- Python の変更を実装し、性能計測と品質ゲートの実行が必要なとき。

## Do not read this when
- Python 以外の開発作業を行うとき。
- スキル固有の詳細手順を確認したいとき。

## hash
- 9bca544e930d910f9cb736e6f3d001a19f7b0ce53e585c3d40de159ee70a8fb8
