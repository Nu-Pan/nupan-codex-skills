# Structured Outputs のスキーマを検証するスキルの仕様

## 目的と適用場面

OpenAI Structured Outputs 用の JSON Schema を、API 呼び出し前にオフラインで検証する。また、Codex CLI の `--output-schema` へ渡すスキーマの作成・変更・レビューにも適用する。ただし、JSON Schema 一般や、生成済みのデータがスキーマに適合するかどうかの検証には使わない。

利用者が指定したファイルを優先し、指定がなければスキーマを使うコードや設定から用途を確かめ、対象ファイルを特定する。そのうえで、このスキルに付属する検証コマンド（配布 CLI）で診断し、許可された修正を行う。

診断では、バージョンごとに固定した検証規則（プロファイル）にスキーマが適合するかを調べる。ただし、プロファイルに適合しても、リモートサービスがスキーマを受理するとは限らない。

## プロファイル

使用できるプロファイルは `openai-structured-outputs-2026-08` だけとし、指定がなければこのプロファイルを使う。このプロファイルでは、許可リストにないキーワードをエラーとして扱う。検証規則の根拠は、`2026-08-10` に確認した次の公式文書とする。

- [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)

このプロファイルの対応範囲は固定する。そのため、対応範囲を変更するときは公式文書を再確認し、新しいバージョンのプロファイルを追加する。

## スキーマ規則

### JSON 文書

入力は UTF-8 の JSON 文書とし、重複キー、`NaN`、`Infinity`、`-Infinity` を受理しない。また、スキーマの各ノードは JSON オブジェクトとし、真偽値で表すスキーマは受理しない。

ルートは、`type` の値に文字列 `"object"` を指定したスキーマとする。ルートでの `anyOf` と、`null` を許容する型指定は受理しない。

### 型と構成

`type` に単一の型を指定する場合は、`string`、`number`、`integer`、`boolean`、`object`、`array`、`null` を許可する。一方、配列形式の `type` は、`null` を許容する型（nullable）を表すために使う。この形式では、`null` と、それ以外の一つの型を重複なく指定する。

ルート以外では `anyOf` を使える。ただし、分岐には一つ以上のスキーマオブジェクトを指定し、各分岐も同じプロファイルに適合する必要がある。

`$defs` とローカルの `$ref` を許可する。`$ref` は、`#`、または `#/` で始まる JSON Pointer とし、文書内のスキーマオブジェクトを指すものとする。参照先にも同じプロファイルのスキーマ規則を適用し、違反は参照先の位置へ診断する。JSON オブジェクトであることだけではスキーマとして適合したことにならない。再帰参照では、循環を検出して展開を止める。

### 共通キーワード

型を指定したスキーマオブジェクトでは、次の共通キーワードを許可する。

| キーワード | 値 |
| --- | --- |
| `description` | 文字列 |
| `enum` | 一つ以上の重複しない JSON 値を持つ配列 |
| `const` | JSON 値 |
| `$defs` | 定義名をキー、スキーマオブジェクトを値とするオブジェクト |

一方、`$ref` を使うスキーマオブジェクトでは、`$ref`、`description`、`$defs` だけを許可する。また、`anyOf` を使うスキーマオブジェクトでは、`anyOf`、`description`、`$defs` だけを許可する。

### 型固有のキーワード

指定した型に応じて、次のキーワードと値の規則を使う。`null` を許容する型にも同じ規則を適用する。

| 型 | キーワードと値の規則 |
| --- | --- |
| `object` | `properties`、`required`、`additionalProperties` を必須とする。`properties` は、プロパティ名をキー、スキーマオブジェクトを値とするオブジェクトとする。`required` は重複のないプロパティ名の配列とし、全プロパティを過不足なく指定する。`additionalProperties` は JSON の真偽値 `false` とする。 |
| `array` | `items` を必須とし、その値はスキーマオブジェクトとする。`minItems` と `maxItems` を指定する場合は、0 以上の整数とする。 |
| `string` | 文字列の `pattern` と `format` を許可する。`pattern` は Python の標準正規表現エンジンでコンパイル可能とする。`format` は下記の値から選ぶ。 |
| `number`、`integer` | `multipleOf`、`maximum`、`exclusiveMaximum`、`minimum`、`exclusiveMinimum` を許可する。値は JSON の数値とし、真偽値を数値として扱わない。`multipleOf` は 0 より大きい値とする。 |

`format` の許可値は `date-time`、`time`、`date`、`duration`、`email`、`hostname`、`ipv4`、`ipv6`、`uuid` とする。

### 非対応キーワードと未知キーワード

許可しないキーワードは、次のエラーで区別する。警告へ緩和するオプションは設けない。

| 対象 | 診断コード |
| --- | --- |
| 非対応の構成キーワード `allOf`、`oneOf`、`not`、`dependentRequired`、`dependentSchemas`、`if`、`then`、`else` | `UNSUPPORTED_KEYWORD` |
| 許可リストにないその他のキーワード | `UNKNOWN_KEYWORD` |

### 上限

スキーマの規模は、次の上限内に収める。各項目を集計するときは、文書内の同じ位置にあるスキーマノードを一度だけ数える。

| 集計対象 | 上限 |
| --- | --- |
| オブジェクトのプロパティ数の合計 | 5,000 |
| オブジェクトの実効的なネスト | 10 階層 |
| プロパティ名、定義名、文字列の `enum` 値、文字列の `const` 値の文字数合計 | 120,000 |
| `enum` 値の個数の合計 | 1,000 |
| 250 個を超える値を持つ一つの `enum` に含まれる、文字列値の文字数合計 | 15,000 |

ネストの検査では `properties`、`items`、`anyOf`、`$ref` をたどり、同じスキーマノードへ戻る循環は追加の階層として展開しない。また、参照されていない定義も、その定義を入口として検査する。

## CLI

配布するコマンドの書式を次に示す。

```bash
python3 {{skill-root}}/scripts/validate_schema.py \
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

配布 CLI は検出可能な違反をすべて集め、診断を常に同じ順序で並べる。その順序は、各診断の `schemaPointer`、`code`、`message`、`details` をこの優先順で比較して決める。また、ルートを指す `schemaPointer` は `/` とする。

JSON 出力は `profile`、`path`、`valid`、`errors` を持つオブジェクトとし、`errors` の各診断は `code`、`schemaPointer`、`message`、`details` を持つ。次に、`properties` にある `status` が `required` から漏れている場合の出力例を示す。

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

`valid` が `true` の場合は `errors` を空配列とする。一方、`text` 形式の出力は、成功時に対象パスとプロファイルを一行で示し、違反時は一診断を一行で示す。

## 診断を解消する

対象ファイルごとに配布 CLI を実行し、全診断を確認する。この CLI はプロファイル固有の許可リストと上限を検査するため、一般の JSON Schema 検証ツールによる検査が成功しても、配布 CLI の検証を代用したことにはならない。このスキルによるプロファイルへの適合性の検査はオフラインで行い、その検査のために API や Codex CLI を呼び出さない。

修正の可否と範囲は、元の依頼とセッションで認められた作業範囲から判断する。アプリやスキーマの作成・変更を任されている場合は、その作業に必要な不整合の解消も含める。一方、レビューだけの依頼ではファイルを変更しない。

修正では、アプリの正本仕様からスキーマが満たすべき契約を確認し、診断結果からプロファイルへの適合性を確かめる。そのうえで、診断が示す箇所と関連する定義を一緒に読み、契約を保って不整合を解消し、同じプロファイルで再検証する。テスト用のスキーマでは、正常入力か拒否を確認する入力かを契約から判断し、意図した違反を消さない。

## 結果と検証

報告では、検証したファイルとプロファイルを示し、適合・違反・検証不能のどの結果になったかを伝える。違反が残る場合は、診断コードと JSON Pointer を示し、違反の原因と箇所をたどれるようにする。

配布 CLI のテストでは、入力、プロファイル規則、診断形式、終了コードを検証する。また、上限値と超過値の境界、および再帰参照の展開が停止することを確認する。複数の規則が同じスキーマの検証を求める場合は、一回の結果を共用する。
