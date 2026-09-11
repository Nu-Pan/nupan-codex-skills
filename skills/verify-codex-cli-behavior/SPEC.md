# Codex CLI 挙動を検証するスキルの仕様

## 目的と適用場面

Codex CLI へ依存するアプリの判断を、対象版のソース根拠と安全な実測へ結び付ける。
CLI を直接または SDK・wrapper を介してローカル process として使うアプリの設計、実装、変更、レビューに適用する。
CLI を開発道具として使うだけの作業や、ローカル CLI を起動しない API 統合には適用しない。
配布設定では暗黙の適用を有効にする。

## 依存する挙動と対象版を確かめる

誤認するとアプリの設計や制御、互換性の判断が変わる挙動を対象とする。
アプリの要求と integration code から依存をたどり、必要な挙動を確認する。
入出力や終了処理などの項目を、網羅するためだけに調査しない。

対象 revision は、アプリが宣言する commit または exact version を優先する。
特定できなければ、アプリが実際に起動する CLI の版を確認する。
version range だけの場合は、lock file や実行環境から exact version を調べる。
version から `openai/codex` の `rust-v<version>` release tag が指す commit を解決する。

tag は commit object まで解決し、annotated tag の tag object SHA を使わない。
`^{commit}` または remote の peeled reference を利用できる。
対象を特定できない場合は最新 stable release を調査用に代用し、理由と対象環境の未確認を示す。
prerelease は利用者やアプリが対象として指定した場合に使う。

## Production source に根拠付ける

重要な挙動を、対象 revision の `openai/codex` production implementation で確認する。
判断に必要な呼び出し元と実装先をたどり、実在する commit・path・行範囲を確認する。
根拠には、次の形式の immutable permalink を使う。

```text
https://github.com/openai/codex/blob/<full-40-character-commit-sha>/<path>#L<start>-L<end>
```

行範囲は、判断を支える範囲に絞る。
公式文書やテストは解釈の補強に使えるが、production source の確認を置き換えない。
CLI の実装を理由に、対象アプリの正本仕様や利用者の要求を書き換えない。
現在の内部実装から、将来の互換性や公開契約を保証しない。

ソースと文書や実測が異なる場合は、revision と実行条件を調べる。
不一致が残る場合は、確認した事実を分けて示し、実際の挙動を断定しない。
公開されていない server-side の意味は、CLI 側で確認できる境界までを根拠化する。

## 実測と互換性を確認する

安全に実行できる場合は、ソースと同じ version・platform・設定で重要な挙動を絞って観測する。
条件差を追える確認を選び、一時 workspace と非機密の入力を使う。
認証や外部作用が必要な操作は、既存の権限とリポジトリの規則に従う。
実測できない場合は、その理由と判断への影響を示す。
ソース確認と実測は区別する。

ソースに根拠付けた重要な依存には、対応版の pin、起動時の version check、または安全側の capability fallback を設ける。
fallback は、失敗条件と利用者への通知を読み取れるようにする。
一つの対策が複数の依存を守る場合は共用する。

## 根拠を残して報告する

変更を依頼された場合は、既存の設計文書など一箇所へ根拠の詳細を集約する。
適切な文書がなければ `docs/codex-cli-behavior-evidence.md` を作る。
挙動とその依存理由、revision、実行条件、production permalink、実測結果、残る不確実性を追跡できるようにする。
integration code の必要な箇所から、その根拠へたどれる参照を置く。
同じ詳細や URL を各コメントへ複製する義務は設けない。

レビューだけの依頼ではファイルを変更しない。
重要な依存の根拠や互換性対策を追えない場合は、その影響を報告する。
特定の文書名や近接コメントの欠落だけを、挙動上の不整合と断定しない。

最終報告では、確認した挙動と判断に必要な条件、検証結果、根拠への参照を簡潔に示す。
文書へ詳細を記録した場合は、その参照を使える。
参照先がない場合は、報告自体へ production permalink と必要な根拠を記載する。
未確認の重要挙動は、未確認として理由と影響を明記する。

## 評価

各重要挙動が対象版のソースへ結び付き、実測との区別と互換性対策を追えることを確認する。
同じ調査や検証は共用する。
production source を確認できない重要挙動が残る場合は、検証完了としない。
