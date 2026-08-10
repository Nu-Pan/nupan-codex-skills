# `SKILL.md`

## Summary
- OpenAI Structured Outputs 用 JSON Schema を、指定プロファイルへの適合性という観点でオフライン検証するスキル。対象 schema の特定、validator 実行、診断に基づく最小修正、検証結果の報告までを扱う。

## Read this when
- Codex CLI の --output-schema または OpenAI Structured Outputs 用 schema を作成・変更・レビュー・検証するとき。
- 対応プロファイル、JSON 文法、対応サブセット、object 規則、参照、サイズ上限を機械的に確認したいとき。

## Do not read this when
- 一般用途の JSON Schema の検証が目的で、OpenAI Structured Outputs 用である根拠がないとき。
- 生成済み JSON instance の妥当性を検証するとき。
- OpenAI API や Codex CLI のリモート実行自体が必要なとき。

## hash
- d29bf4d20d6bad2a7b05ad77cbe2c81eeb74351ed6347e617b797f1efebe7932

# `agents`

## Summary
- Codex 実行前に OpenAI Structured Outputs のスキーマファイルを検証するスキルのエージェント設定を担う。変更済みスキーマの検証フローを確認する入口となる。

## Read this when
- Structured Outputs のスキーマ変更検証スキルにおけるエージェント設定や、Codex 実行前の検証フローを確認するとき。

## Do not read this when
- スキーマ検証の具体的な実装や検査規則を確認したいとき。
- Structured Outputs と無関係なスキルや一般的なエージェント設定を調べるとき。

## hash
- 9cee31d2b4853c3d480e74abae28197e776d8bba6b4572b105f4c11c3cb84717

# `scripts`

## Summary
- OpenAI Structured Outputs 用 JSON Schema 検証 CLI を実装する入口。UTF-8/JSON パース、スキーマ構造・制約・参照・正規表現・上限値の検査と、決定的な診断出力を扱う。

## Read this when
- OpenAI Structured Outputs プロファイルの JSON Schema 受け入れ条件を調査・変更・デバッグするとき
- 検証診断、ローカル参照解決、深さ・プロパティ数・文字列長・enum 数の制限を確認するとき
- CLI の引数、終了コード、出力形式、ファイル読み込み処理を確認するとき

## Do not read this when
- リポジトリ共通のスキル構造や保守手順を確認するとき
- 検証器の実行時仕様を確認するときは、対応する正本仕様を先に読むべき場合
- 具体的な JSON Schema 入力例やテストケースだけを確認するとき

## hash
- 1d7feb45ebbc81b2bbda1d7366c97d85f31ae444f8a93072fffa677ea504a1b8
