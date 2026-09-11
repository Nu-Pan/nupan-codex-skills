# Structured Outputs schema を検証するスキルの仕様

## 目的と適用場面

OpenAI Structured Outputs 用の JSON Schema を、API 呼び出し前にオフラインで検証する。Codex CLI の `--output-schema` へ渡す schema の作成・変更・レビューにも適用する。JSON Schema 一般や生成済み instance の検証には使わない。

利用者が指定したファイルを優先し、指定がなければ呼び出し元や設定から用途を確かめて対象を特定する。配布 CLI で診断し、許可された修正を行う。結果はバージョン付きプロファイルへの適合を示すもので、リモートサービスの受理を保証しない。

## プロファイル

プロファイルは `openai-structured-outputs-2026-08` の一つとし、既定で使う。許可リストにないキーワードをエラーにする fail-closed の方式をとる。プロファイルの確認日は `2026-08-10`、根拠は次の公式文書とする。

- [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)

対応範囲はこのバージョンで固定する。変更するときは公式文書を再確認し、新しいバージョン付きプロファイルを追加する。

## スキーマ規則

### JSON 文書

入力は UTF-8 の JSON 文書とし、重複キー、`NaN`、`Infinity`、`-Infinity` を受理しない。schema の各ノードは JSON object とし、boolean schema は受理しない。

ルートは `type` が文字列の `object` である schema object とする。ルートでの `anyOf` と nullable type は受理しない。

### 型と構成

単一型として `string`、`number`、`integer`、`boolean`、`object`、`array`、`null` を許可する。配列形式の `type` は nullable を表すために使い、`null` と一つの非 null 型を重複なく指定する。

非ルートでは `anyOf` を使える。一つ以上の schema object を分岐に持ち、各分岐は同じプロファイルに適合する必要がある。

`$defs` とローカル `$ref` を許可する。`$ref` は `#` または `#/` で始まる JSON Pointer で、文書内の schema object を指すものとする。再帰参照は循環を検出して展開を止める。

### 共通キーワード

型付き schema object では、次の共通キーワードを許可する。

| キーワード | 値 |
| --- | --- |
| `description` | 文字列 |
| `enum` | 一つ以上の重複しない JSON 値を持つ配列 |
| `const` | JSON 値 |
| `$defs` | 定義名から schema object への object |

`$ref` schema object では、`$ref`、`description`、`$defs` だけを許可する。
`anyOf` schema object では、`anyOf`、`description`、`$defs` だけを許可する。

### 型固有のキーワード

nullable を含め、指定した型に対応する規則を適用する。

| 型 | キーワードと値の規則 |
| --- | --- |
| `object` | `properties`、`required`、`additionalProperties` を必須とする。`properties` はプロパティ名から schema object への object、`required` は重複のないプロパティ名の配列で、全プロパティを過不足なく指定する。`additionalProperties` は JSON boolean の `false` とする。 |
| `array` | schema object の `items` を必須とする。`minItems` と `maxItems` を指定する場合は、0 以上の整数とする。 |
| `string` | 文字列の `pattern` と `format` を許可する。`pattern` は Python の標準正規表現エンジンでコンパイル可能とする。`format` は下記の値から選ぶ。 |
| `number`、`integer` | `multipleOf`、`maximum`、`exclusiveMaximum`、`minimum`、`exclusiveMinimum` を許可する。値は JSON number とし、boolean を number として扱わない。`multipleOf` は 0 より大きい値とする。 |

`format` の許可値は `date-time`、`time`、`date`、`duration`、`email`、`hostname`、`ipv4`、`ipv6`、`uuid` とする。

### 非対応キーワードと未知キーワード

許可しないキーワードは、次のエラーで区別する。警告へ緩和するオプションは設けない。

| 対象 | 診断コード |
| --- | --- |
| 非対応の構成キーワード `allOf`、`oneOf`、`not`、`dependentRequired`、`dependentSchemas`、`if`、`then`、`else` | `UNSUPPORTED_KEYWORD` |
| 許可リストにないその他のキーワード | `UNKNOWN_KEYWORD` |

### 上限

文書内の物理的に一意な schema node を一度だけ集計する。

| 集計対象 | 上限 |
| --- | --- |
| object property の合計 | 5,000 |
| object の実効的なネスト | 10 階層 |
| property 名、定義名、文字列の enum 値、文字列の const 値の文字数合計 | 120,000 |
| enum 値の合計 | 1,000 |
| 250 個を超える値を持つ一つの enum の、文字列値の文字数合計 | 15,000 |

ネスト検査では `properties`、`items`、`anyOf`、`$ref` をたどり、同じ schema node へ戻る循環は追加階層として展開しない。未参照の定義も、定義自身を入口として検査する。

## CLI

配布するコマンドの書式を次に示す。

```bash
python3 <skill-root>/scripts/validate_schema.py \
  [--profile openai-structured-outputs-2026-08] \
  [--format text|json] \
  path/to/schema.json
```

一回の実行で一つのファイルを検証する。既定の出力形式は `text` とし、終了コードで結果を伝える。

| 終了コード | 意味 |
| --- | --- |
| `0` | スキーマがプロファイルに適合した。 |
| `1` | UTF-8、JSON 文法、またはスキーマの違反を検出した。 |
| `2` | 引数、プロファイル、ファイル読み込み、または内部処理のエラーが発生した。 |

検出可能な違反をすべて集め、`schemaPointer`、`code`、`message`、`details` の順で決定的に整列する。ルートの `schemaPointer` は `/` とする。

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

`valid` が `true` の場合は `errors` を空配列とする。text 出力は、成功時に対象パスとプロファイルを一行で示し、違反時は一診断を一行で示す。

## 診断を解消する

対象ごとに配布 CLI を実行し、全診断を確認する。配布 CLI は固有の許可リストと上限を検査するため、一般の JSON Schema validator の成功で代用しない。API や Codex CLI を呼び出さずに検証する。

修正の依頼では、診断箇所と関連する定義を一緒に読み、意図する契約を保って不整合を解消する。契約の根拠はアプリの正本に、プロファイル適合性の根拠は診断結果に求める。修正後は同じプロファイルで再検証する。レビューだけの依頼ではファイルを変更しない。

## 結果と検証

結果には、使用したプロファイル、対象ファイル、終了結果を示す。
違反が残る場合は、診断コードと JSON Pointer から原因へたどれるようにする。
読み込みや内部処理の失敗は検証成功として扱わない。

配布 CLI のテストでは、入力、プロファイル規則、診断形式、終了コードを検証する。
上限値と超過値の境界、再帰参照の停止を確認する。
複数の規則が同じ schema の検証を求める場合は、一回の結果を共用する。
