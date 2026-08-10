# `README.md`

## Summary
- Codex CLI と OpenAI Structured Outputs 用の JSON Schema を、バージョン付き fail-closed プロファイルでオフライン検証するスキルの概要と配布物への入口を示す。詳細な仕様は仕様書で確認する。

## Read this when
- Codex CLI または OpenAI Structured Outputs 用 JSON Schema のオフライン検証について、スキルの目的や配布物の入口を確認したいとき。
- このスキルの実行時仕様を確認する必要があるとき。

## Do not read this when
- 検証仕様の詳細な挙動を直接確認したいときは、仕様書を読む。
- 配布物の具体的な内容を確認したいときは、配布物のディレクトリへ直接進む。

## hash
- e70e4ccdf9e129af4c042d1d83e37665f82cdda7dbcf1bd49a55222213b8e994

# `SPEC.md`

## Summary
- OpenAI Structured Outputs 用 JSON Schema のオフライン検証仕様を定義する正本文書。適用条件、対象外、スキーマ規則、プロファイル、上限、CLI、診断形式、実行手順、検証完了条件を確認する入口。

## Read this when
- OpenAI Structured Outputs または Codex CLI の --output-schema 用スキーマの検証・レビュー・変更を行うとき
- このスキルの許可キーワード、参照、object 規則、上限、診断コード、CLI 終了コードを確認するとき
- 検証処理やテストの実行時仕様を変更するとき

## Do not read this when
- 一般用途の JSON Schema の全機能や生成済み JSON instance の適合性だけを扱うとき
- OpenAI API のリモート互換性、モデル対応可否、fine-tuned model 固有制約だけを調べるとき
- この仕様の個別実装やテスト結果を直接確認する必要があるときは、対応する実装・テストへ進む

## hash
- f78d17eeac323b3501d71f0d117f8e985a105fb94a398c34a8dce23407eb3251

# `dist`

## Summary
- OpenAI Structured Outputs 用 JSON Schema を、固定プロファイルへの適合性という観点でオフライン検証するスキル一式を収録する。スキルの適用条件、検証手順、診断対応、結果報告に加え、エージェント設定と検証 CLI の実装へ進む入口となる。

## Read this when
- Codex CLI の --output-schema または OpenAI Structured Outputs 用 schema の作成、変更、レビュー、検証を行うとき。
- このスキルの適用条件、実行手順、診断の扱い、エージェント向け設定、検証処理の全体像を確認するとき。

## Do not read this when
- 一般用途の JSON Schema や生成済み JSON instance の検証だけが目的のとき。
- OpenAI API や Codex CLI のリモート実行自体が必要なとき。
- 検証 CLI の具体的な実装やエージェント設定だけを確認したい場合は、それぞれの下位要素へ直接進むとき。

## hash
- 85f6fcb972da1690d8821f258dfcd8e92a9e2fadeee9494b422a3a3e5c538645

# `tests`

## Summary
- OpenAI Structured Outputs 用 JSON Schema 検証スクリプトの pytest テスト。対応構文、参照・再帰、JSON 入力、診断出力、終了コード、エラー順序、各種上限値を検証する。検証実装やテスト仕様を確認・変更する際の具体的なテスト入口。

## Read this when
- validate_schema.py の挙動を変更またはレビューするとき
- JSON Schema の対応キーワード、参照解決、入力エラー、診断形式、制限値に関するテスト結果を確認するとき
- validate-openai-structured-output-schema スキルの検証を実行するとき

## Do not read this when
- ルーティング文書やスキル共通仕様だけを確認するとき
- テスト対象の実装詳細を直接調べるとき
- このテストファイルが扱わないドキュメントや配布設定だけを確認するとき

## hash
- 15297d87476d8b0fd91b1a5fdf8d84915372990f75f4d3e60e946811e19f4643
