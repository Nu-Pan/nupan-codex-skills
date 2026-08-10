# `test_validate_schema.py`

## Summary
- OpenAI Structured Outputs 用 JSON Schema 検証スクリプトのpytestテスト。対応するスキーマ構文、参照、再帰、JSON入力、診断出力、終了コード、決定的なエラー順序、各種上限値を検証する。検証実装やテスト仕様を確認・変更するときの具体的なテスト入口。

## Read this when
- validate_schema.py の挙動を変更・レビューするとき
- JSON Schema の対応キーワード、参照解決、入力エラー、診断形式、制限値に関するテスト結果を確認するとき
- validate-openai-structured-output-schema スキルの検証を実行するとき

## Do not read this when
- ルーティング文書やスキル共通仕様だけを確認するとき
- テスト対象の実装詳細を直接調べるときは、まず検証スクリプト本体を読むべき場合
- このテストファイルが扱わないドキュメントや配布設定だけを確認するとき

## hash
- 72a2efd21383d07cb9dbfddd4607700782e25df0860ef0ecd65e1c9629fe6f3a
