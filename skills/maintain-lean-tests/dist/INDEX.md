# `SKILL.md`

## Summary
- テスト、fixture、sample、snapshot、test data、性能回帰テスト、benchmarkを、現行仕様の外部挙動または意味のある制御ロジックに絞って追加・変更・整理するための実行指針。類似ケースの集約、旧仕様テストや過大なfixtureの削除、テストコードとファイル責務の簡潔化、性能検証の実測根拠、focused test・full test・品質ゲートの実行と報告までを扱う。

## Read this when
- テストや関連fixture・sample・snapshot・test dataを追加、変更、削除、統合するとき。
- 現行仕様に対する回帰検出範囲、テストの重複、旧仕様テスト、fixtureの大きさを判断するとき。
- benchmarkや性能回帰テストの追加・変更、またはfocused testとfull testの実行方針を確認するとき。
- テストコードの責務分割、helper整理、コメント削減、品質ゲート後の完了確認が必要なとき。

## Do not read this when
- テストツールの導入や設定だけを行い、テストケースやfixtureの内容を変更しないとき。
- 実装コードのみを変更し、テスト・fixture・benchmarkの設計や整理に関係しないとき。
- 対象リポジトリ固有のテスト戦略、命名、配置、実行コマンドを確認する必要があるとき。その場合は対象リポジトリの正本仕様やテスト規則を先に読む。

## hash
- 17d502a5d9614f0cdf2aa5a9ae272c5279583ccace4b22ca8b19846e6d865ddd

# `agents`

## Summary
- maintain-lean-tests スキルの表示名、説明、既定プロンプトを定義するエージェント向け設定。テストや fixture の保守、実測に基づく性能回帰検証へ利用者を導く入口。

## Read this when
- maintain-lean-tests の利用者向け表示情報や既定の依頼文を確認・変更するとき
- このスキルが案内するテスト保守作業の範囲を確認するとき

## Do not read this when
- テスト保守の適用条件や実行時規則を確認するとき
- 具体的な保守手順や検証基準を確認するとき

## hash
- 18afb6198b71cb852ad176c5efc3570903fa5153b9f134e13e202ab792d7b1e5
