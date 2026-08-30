# verify-codex-cli-behavior の仕様

## 目的

このスキルは、Codex CLI を使用するアプリの設計、実装、レビューで、依存する CLI 挙動を対象版の GitHub 上の実装本体へ結び付ける。
記憶や利用者向け文書だけに依存せず、バージョンを固定したソース根拠と安全な実測結果を成果物へ残す。

完了時には、次の状態を満たす。

- アプリが依存する重要な Codex CLI 挙動を特定している。
- 各重要挙動に、対象 revision の `openai/codex` production implementation を示す固定 permalink がある。
- 対象 version、platform、設定条件、実測結果、確認できない範囲を追跡できる。
- 根拠を設計文書、integration code の近接コメント、最終報告へ残している。
- version-sensitive な依存に、version pin、起動時検査、または capability fallback がある。

このファイルは、`verify-codex-cli-behavior` のスキル仕様の正本である。
実行時仕様を変更するときは、先にこのファイルを変更する。

## 適用条件

Codex CLI をローカル process として直接起動するアプリを設計、実装、変更、またはレビューするときに、このスキルを使用する。
SDK、library、wrapper、subprocess helper を介してローカルの Codex CLI を起動する場合も対象とする。

スキル名が明示されていない場合も、アプリが Codex CLI の挙動へ依存すると判断できる場合は適用する。
新規 integration と、既存 integration の変更またはレビューをどちらも対象とする。

## 対象外

このスキルだけでは、次の作業を対象にしない。

- Codex CLI を開発作業の道具として使うだけの作業
- ローカルの Codex CLI process を起動しない OpenAI API または cloud service integration
- Codex CLI との関係がない一般的な CLI application の開発
- 公開 source から確認できない server-side semantics の断定
- 利用者が依頼していない変更、外部操作、または互換性範囲の拡張

## 入力と優先順位

調査では、次の入力を使用する。

- 対象アプリの正本仕様、設計文書、設定、lock file、実装、テスト
- 対象とする Codex CLI の version または commit
- 対象 platform と、挙動へ影響する設定
- アプリが前提とする引数、入出力、終了、認証、安全制御の挙動
- 利用者が変更またはレビューのどちらを依頼したか

対象 revision は、次の順で特定する。

1. アプリが宣言する Codex CLI の commit または exact version を確認する。
2. 宣言から特定できない場合は、アプリが実際に起動する CLI の commit または version を確認する。
3. version だけが判明した場合は、`openai/codex` の対応する `rust-v<version>` release tag が指す commit を解決する。
4. いずれからも特定できない場合は、GitHub Releases の最新 stable release が指す commit を代用する。

release tag が annotated tag の場合は、tag object を `^{commit}` または remote の peeled `^{}` reference で commit まで dereference する。
permalink には、annotated tag object の SHA ではなく、dereference 後の commit SHA を使用する。
lightweight tag の場合も、tag が指す object が commit であることを確認する。
明示された prerelease を対象とする場合だけ、対応する prerelease revision を使用する。
version range だけが宣言されている場合は、lock file または実行環境から exact version を特定する。
代用した revision は、その理由とともに明記する。
代用した revision と対象環境が一致すると断定しない。

Codex CLI の挙動を判断するときは、対象 revision の production implementation を利用者向け文書、release notes、テスト、記憶、実測より優先する。
対象アプリの正本仕様や利用者の要求を、Codex CLI の source を理由に上書きしない。

## 独立性と合成

このスキルは、他のスキルがなくても、対象 revision の特定、source 調査、根拠の記録、focused verification、報告を完了する。
OpenAI、仕様、実装、テスト、レビューに固有の別スキルを必須条件にしない。

他のスキルと同時に適用する場合は、同じ source 調査、文書変更、コメント追加、実測、報告を一回に統合する。
統合した作業でも、このスキルが要求する revision、permalink、記録場所、実測状態を省略しない。
レビューだけの依頼に変更権限を追加しない。

## 重要挙動の特定

重要挙動は、誤認した場合にアプリの設計、制御、互換性、またはテスト結果が変わる Codex CLI の挙動とする。
対象アプリの仕様、integration code、設定、テストから重要挙動を列挙する。

確認対象の例を次に示す。

- command と argument の解釈
- 設定の読み込みと優先順位
- stdin、stdout、stderr、JSONL event の扱い
- 終了コードと error の伝播
- authentication と credential の探索
- approval と sandbox の適用
- signal、child process、timeout、終了処理の lifecycle

対象アプリが依存しない挙動を網羅目的で調査しない。
一つの挙動が複数の production path に依存する場合は、その判断に必要な path をすべて確認する。

## ソース根拠

各重要挙動には、`openai/codex` の production implementation を直接示す permalink を一つ以上付ける。
permalink を記録する前に、使用する SHA が commit object であり、示した path と行範囲がその commit に存在することを確認する。
permalink は、次の形式を満たす。

```text
https://github.com/openai/codex/blob/<full-40-character-commit-sha>/<path>#L<start>-L<end>
```

行範囲は、挙動の判断に必要な最小範囲とする。
呼び出し元と実装先の両方が判断に必要な場合は、それぞれの permalink を記録する。

次の情報だけでは、production source の根拠要件を満たさない。

- `main` などの可変 branch を含む URL
- tag 名だけを含む URL
- repository root、directory、検索結果だけを指す URL
- issue、pull request、discussion、利用者向け文書、release notes だけの参照
- test code、fixture、snapshot だけの参照

対応する test code、公式文書、release notes は、production implementation の解釈を補強する根拠として使用できる。
補強根拠を production implementation の代わりにしない。

source と文書または実測が異なる場合は、対象 revision と実行条件の一致を再確認する。
不一致が残る場合は、production source を実装判断の優先根拠とする。
不一致、条件差、残る不確実性は成果物へ記録する。
production source から、将来 version の互換性や公開契約を断定しない。

GitHub 上の対象 revision の production implementation を確認できない重要挙動は、根拠確認済みとして扱わない。
その状態では、このスキルの作業を完了扱いにしない。
公開 source に含まれない server-side semantics は、CLI 側で確認できる request、response、error handling の境界までを根拠化する。
確認できない server-side の範囲と、それに依存する判断を明記する。

## 根拠の記録

変更が許可されている場合は、確認した根拠を文書と integration code の両方へ残す。

1. 対象リポジトリの規約に従い、既存の正本仕様または設計文書へ挙動、条件、permalink を記録する。
2. 適切な既存文書がない場合は、`docs/codex-cli-behavior-evidence.md` を文書の記録先として作成する。
3. 各挙動へ依存する integration code の直前または直近に、文書と同じ immutable permalink を含むコメントを置く。

文書には、挙動ごとに次の情報を記録する。

- 挙動の要約と、アプリが依存する理由
- 対象 Codex CLI version、full commit SHA、platform、関連設定
- production implementation の permalink
- focused verification の方法と結果、または実施できない理由
- 文書、実測、source の不一致と残る不確実性
- version pin、起動時検査、または capability fallback

同じ挙動を複数箇所で利用する場合は、設計文書を正本として重複説明を抑えてよい。
各 integration point の近接コメントから、正本と同じ immutable permalink を追跡できる状態は維持する。

レビューだけを依頼された場合は、ファイルを変更しない。
レビューでは、欠けている source 根拠、設計文書、近接コメント、互換性対策、実測を所見として報告する。

## Focused verification

安全かつ実行可能な場合は、source で確認した重要挙動を focused verification で観測する。
対象 source と同じ Codex CLI version、platform、設定を使用する。
一つの確認で複数条件を変えない。

version 表示、help、引数検査など、外部作用を必要としない確認を優先する。
一時 workspace と非機密の入力を使用する。
認証、network access、課金、外部変更、広い filesystem access が必要な確認は、既存の権限と対象リポジトリの規則に従う。

実測結果には、command または手順、version、platform、設定条件、終了結果、観測内容を記録する。
安全に実施できない場合は、未実施の理由と判断への影響を記録する。
source の確認を、実測済みとして扱わない。
実測の成功を、異なる version、platform、設定での互換性保証として扱わない。

## 実装時の規則

source で確認した挙動だけを integration の前提にする。
対象 revision の source に根拠付ける重要挙動は、version-sensitive として扱う。
各重要挙動への依存には、次のいずれかを実装する。

- 対応する Codex CLI version または commit の pin
- 起動前または起動時の version check
- 未対応 version で安全側へ移行する capability fallback

source の内部構造を公開 API とみなさない。
将来 version の挙動を、現在の source から推測して実装しない。
根拠と異なる挙動を許容する fallback は、失敗条件と利用者への通知を明確にする。

## 出力

最終報告では、重要挙動ごとに次の情報を要約する。

- 対象 Codex CLI version、platform、full commit SHA
- 確認した挙動
- production implementation の permalink
- focused verification の結果、または未実施理由
- 不一致、代用 revision、確認不能範囲
- 更新した設計文書、近接コメント、互換性対策

production implementation の permalink URL 自体を最終報告へ記載する。
設計文書やコードへのリンクだけを、最終報告の production source permalink の代わりにしない。
最終報告を送信する直前に、source 確認済みの各重要挙動について `https://github.com/openai/codex/blob/<full-40-character-commit-sha>/<path>#L<start>-L<end>` 形式の検証済み URL が応答本文に一つ以上あることを確認する。
検証済み URL が応答本文から漏れている場合だけ、追加してから送信する。
source 未確認の挙動には URL を作らず、未確認の理由を報告する。
利用者が別形式を指定していない場合は、挙動と根拠の対応を表または短い一覧で示す。
確認できなかった重要挙動がある場合は、未確認であることと完了できない理由を明示する。

## 検証

完了前に、次の条件を確認する。

- 対象アプリが依存する重要挙動を列挙している。
- 対象 revision の選択と代用の有無を記録している。
- 各重要挙動に full 40-character commit SHA と最小行範囲を含む production source permalink がある。
- test code、文書、release notes だけを source 根拠にしていない。
- 変更時は、設計文書と integration code の近接コメントに同じ permalink がある。
- version-sensitive な依存に version pin、version check、または capability fallback がある。
- 安全な focused verification を実施したか、未実施理由と影響を記録している。
- source 確認と実測を区別している。
- 不一致と確認不能範囲を隠していない。
- レビューだけの依頼でファイルを変更していない。
- 最終報告に version、platform、commit、挙動、permalink、実測結果がある。

GitHub 上の production source を確認できない重要挙動が一つでも残る場合は、完了としない。

## 重視する価値

Codex CLI の挙動へ依存する判断を、対象 revision まで追跡できる状態にする。
source から確認できる事実と、文書、実測、推測、将来互換性を混同しない。
