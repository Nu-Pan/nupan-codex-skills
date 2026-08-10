# `validate_schema.py`

## Summary
- OpenAI Structured Outputs 用 JSON Schema 検証 CLI の実装。厳格な UTF-8/JSON パース、スキーマ構造・キーワード・型・参照・正規表現・数値制約・上限値を検査し、決定的な診断結果をテキストまたは JSON で出力する。検証プロファイルの挙動や診断コードを変更・確認するときの実装入口。

## Read this when
- OpenAI Structured Outputs プロファイルに対する JSON Schema の受け入れ条件を調査するとき
- 検証診断、ローカル参照解決、深さ・プロパティ数・文字列長・enum 数の制限を変更またはデバッグするとき
- CLI の引数、終了コード、出力形式、ファイル読み込み処理を確認するとき

## Do not read this when
- リポジトリ共通のスキル構造や保守手順を確認したいとき
- この検証器の実行時仕様そのものを確認したいときは、まず対応する正本仕様を読むとき
- JSON Schema の具体的な入力例やテストケースだけを確認したいときは、対応するテストを直接読むとき

## hash
- 38d599f3a97ead50fbcde7b55bd06d8bdbe5dfb23a4d3df1e34127d017b2a34c
