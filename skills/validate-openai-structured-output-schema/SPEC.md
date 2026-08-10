# validate-openai-structured-output-schema の仕様

## 目的

このスキルは、Codex CLI の `--output-schema` と OpenAI Structured Outputs に渡す JSON Schema を、API 呼び出し前にオフラインで検証する。
一般の JSON Schema として解釈できても OpenAI の対応サブセットに適合しないスキーマを、決定論的な検査で検出する。

検証後の状態は、次の条件を満たす。

- JSON 文法と UTF-8 エンコーディングが有効である。
- バージョン付きプロファイルが許可する構造とキーワードだけを使用している。
- OpenAI Structured Outputs が要求する object の規則とサイズ上限に適合している。
- ローカル参照が有効であり、再帰参照を無限展開せずに検査できている。
- 人間向けまたは機械向けの診断から、違反箇所と違反理由を特定できる。

このファイルは、`validate-openai-structured-output-schema` のスキル仕様の正本である。
実行時仕様を変更するときは、先にこのファイルを変更する。

## 適用条件

OpenAI Structured Outputs 用の JSON Schema を作成、変更、レビュー、または検証するときに、このスキルを使用する。
対象には、Codex CLI の `codex exec --output-schema` へ渡すファイルを含む。

スキル名が明示されていない場合も、対象ファイルまたは依頼が OpenAI Structured Outputs 用であると判断できる場合は適用する。

## 対象外

このスキルだけでは、次の作業を行わない。

- 一般用途の JSON Schema 全機能への適合性検証
- 生成済み JSON instance のスキーマ適合性検証
- OpenAI API または Codex CLI を呼び出すリモート互換性カナリア
- モデルごとの Structured Outputs 対応可否の判定
- fine-tuned model 固有の追加制約の検証
- OpenAI 側で将来追加される未公開または未反映のキーワードの推測

オフライン検証の成功は、リモートサービスによる受理を絶対に保証しない。

## 入力と優先順位

必須入力は、検証対象となる UTF-8 の JSON Schema ファイルである。
利用者がファイルを明示していない場合は、変更差分、`codex exec` の呼び出し、設定、テストから対象を特定する。

複数の候補がある場合は、OpenAI Structured Outputs 用であることを確認できるファイルだけを検証する。
一般用途の JSON Schema を、根拠なくこのプロファイルで拒否しない。

利用者の依頼種別を優先する。
変更を依頼された場合は違反を修正して再検証する。
レビューだけを依頼された場合は、ファイルを変更せずに診断を報告する。

## 独立性と合成

このスキルは、他のスキルがなくても、配布 CLI による対象特定、診断、許可された修正、再検証、報告を完了する。
Python、仕様、レビューに固有の別スキルを、オフライン検証の必須条件にしない。

他のスキルと同時に適用する場合も、このスキルが決定的に判定するのは、この仕様で定義したプロファイルへの適合性だけとする。
正本仕様の意味、レビュー所見、変更権限、一般的な実装品質は、それぞれに適用される規則を累積する。
配布 CLI の診断は所見の根拠に利用できるが、正本仕様を validator の実装から逆算しない。

同じ schema の検証は一回に統合する。
統合した検証でも、使用したプロファイル、全診断、終了コード、修正後の再検証を省略しない。

## プロファイル

既定かつ唯一のプロファイル名は、`openai-structured-outputs-2026-08` とする。
このプロファイルは fail-closed とする。
許可リストにないキーワードは、OpenAI が明示的に禁止していない場合もエラーにする。

プロファイルの確認日は `2026-08-10` とする。
根拠となる公式文書を次に示す。

- [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)

OpenAI 側の仕様変更へ自動追従しない。
対応範囲を変更するときは、公式文書を再確認して新しいバージョン付きプロファイルを追加する。

## スキーマ規則

### JSON 文書

入力は UTF-8 の JSON 文書とする。
重複キー、`NaN`、`Infinity`、`-Infinity` を受理しない。
JSON Schema の各ノードは JSON object とし、boolean schema を受理しない。

### ルート

ルートは、`type` が文字列の `object` である schema object とする。
ルートでは `anyOf` と nullable type を受理しない。

### 型と構成

単一型として許可する型を次に示す。

- `string`
- `number`
- `integer`
- `boolean`
- `object`
- `array`
- `null`

配列形式の `type` は nullable を表す場合だけ許可する。
配列には、`null` と一つの非 null 型を重複なく指定する。

非ルートの `anyOf` を許可する。
`anyOf` は一つ以上の schema object を持ち、各分岐が同じプロファイルに適合する必要がある。

`$defs` とローカル `$ref` を許可する。
`$ref` は `#` または `#/` で始まる JSON Pointer とする。
外部参照、存在しない参照、schema object 以外を指す参照を受理しない。
再帰参照は循環を検出し、参照先を無限に展開しない。

### 共通キーワード

型付き schema object では、必要に応じて次の共通キーワードを許可する。

- `description`
- `enum`
- `const`
- `$defs`

`description` は文字列とする。
`enum` は、一つ以上の重複しない JSON 値を持つ配列とする。
`$defs` は、定義名から schema object への object とする。

`$ref` schema object では、`$ref`、`description`、`$defs` だけを許可する。
`anyOf` schema object では、`anyOf`、`description`、`$defs` だけを許可する。

### object

`object` を含む型では、`properties`、`required`、`additionalProperties` を必須とする。
`properties` は、プロパティ名から schema object への object とする。
`required` は、重複しないプロパティ名の配列とする。

`required` の集合は、`properties` のキー集合と完全に一致させる。
不足した必須項目と、定義されていない必須項目をどちらもエラーにする。
`additionalProperties` は JSON boolean の `false` とする。

### array

`array` を含む型では、schema object の `items` を必須とする。
`minItems` と `maxItems` は、0 以上の整数とする。

### string

`string` を含む型では、文字列の `pattern` を許可する。
`pattern` は Python の標準正規表現エンジンでコンパイル可能とする。

`format` で許可する値を次に示す。

- `date-time`
- `time`
- `date`
- `duration`
- `email`
- `hostname`
- `ipv4`
- `ipv6`
- `uuid`

### number と integer

`number` または `integer` を含む型では、次のキーワードを許可する。

- `multipleOf`
- `maximum`
- `exclusiveMaximum`
- `minimum`
- `exclusiveMinimum`

各値は JSON number とする。
JSON boolean を number として扱わない。
`multipleOf` は 0 より大きい値とする。

### 非対応キーワードと未知キーワード

OpenAI が対応しない構成キーワードには、`UNSUPPORTED_KEYWORD` を報告する。
対象となるキーワードを次に示す。

- `allOf`
- `oneOf`
- `not`
- `dependentRequired`
- `dependentSchemas`
- `if`
- `then`
- `else`

許可リストにない他のキーワードには、`UNKNOWN_KEYWORD` を報告する。
同じキーワードを、警告へ緩和するオプションは設けない。

### 上限

文書内の物理的に一意な schema node を一度だけ集計する。
再帰参照による展開分を重複して数えない。

適用する上限を次に示す。

- object property の合計は 5,000 以下
- object の実効的なネストは 10 階層以下
- property 名、定義名、文字列の enum 値、文字列の const 値の文字数合計は 120,000 以下
- enum 値の合計は 1,000 以下
- 250 個を超える値を持つ一つの enum では、文字列値の文字数合計は 15,000 以下

ネスト検査では、`properties`、`items`、`anyOf`、`$ref` をたどる。
再帰中に同じ schema node へ戻った場合は、その循環を追加階層として展開しない。
未参照の定義も、定義自身を入口として検査する。

## CLI

配布するコマンドの書式を次に示す。

```bash
python3 <skill-root>/scripts/validate_schema.py \
  [--profile openai-structured-outputs-2026-08] \
  [--format text|json] \
  path/to/schema.json
```

一回の実行では一つのファイルを検証する。
既定のプロファイルは `openai-structured-outputs-2026-08` とする。
既定の出力形式は `text` とする。

終了コードの意味を次に示す。

- `0`: スキーマがプロファイルに適合した。
- `1`: UTF-8、JSON 文法、またはスキーマの違反を検出した。
- `2`: 引数、プロファイル、ファイル読み込み、または内部処理のエラーが発生した。

検出可能な違反は、最初の一件で停止せずに収集する。
診断は、`schemaPointer`、`code`、`message`、`details` の順で決定的に整列する。
ルートの `schemaPointer` は `/` とする。

JSON 出力の形式を次に示す。

```json
{
  "profile": "openai-structured-outputs-2026-08",
  "path": "path/to/schema.json",
  "valid": false,
  "errors": [
    {
      "code": "OBJECT_REQUIRED_MISMATCH",
      "schemaPointer": "/",
      "message": "Object properties and required fields must match.",
      "details": {
        "missingRequired": ["status"],
        "unexpectedRequired": []
      }
    }
  ]
}
```

`valid` が `true` の場合は、`errors` を空配列とする。
text 出力では、成功時に対象パスとプロファイルを一行で示す。
違反時は、一診断を一行で示す。

## 実行時の手順

1. OpenAI Structured Outputs 用の対象ファイルを特定する。
2. 対象ごとに配布 CLI を実行する。
3. 終了コード `1` の場合は、全診断を確認する。
4. 変更が許可されている場合は、診断に対応する最小の修正を行う。
5. 同じプロファイルで再実行し、終了コード `0` を確認する。
6. 終了コード `2` の場合は、検証済みとせずに原因を報告する。
7. 使用したプロファイル、対象ファイル、結果を最終報告へ含める。

API または Codex CLI を、このスキルの標準手順として呼び出さない。

## 検証

スキルの作業完了前に、次の条件を確認する。

- 対象となる全ファイルを検証している。
- すべての診断が JSON Pointer と安定したコードを持つ。
- JSON 出力が固定形式に適合している。
- 終了コードが定義どおりである。
- 再帰参照が停止する。
- 上限値と超過値の境界がテストされている。
- スキーマ違反を修正した場合は、同じプロファイルで再検証している。
- オフライン検証をリモート受理の絶対保証として報告していない。

一つでも満たさない場合は、完了としない。
