# 7D2D Zombie Save - 7 Days to Die セーブデータマネージャー

## 概要

7D2D Zombie Save は、Python と Tkinter で構築されたグラフィカルユーザーインターフェース (GUI) アプリケーションです。人気ゲーム「7 Days to Die」のプレイヤーがセーブデータを管理するのを支援するために設計されました。ユーザーはゲームのセーブデータを簡単に一覧表示、バックアップ、復元でき、データ損失や破損に対するセーフティネットを提供します。

## 特徴

- **セーブデータの一覧表示**: 「7 Days to Die」のセーブデータを自動的に検出し、セーブ名とワールド名を表示します。
- **バックアップの作成**: 選択したセーブデータの圧縮 ZIP バックアップを作成します。バックアップにはタイムスタンプが付与され、簡単に識別できます (例: `MySaveGame_YYYYMMDDTHHMM.zip`)。
- **バックアップの一覧表示**: 利用可能なすべてのバックアップを日付順にソートして表示します。
- **バックアップからの復元**: 選択したバックアップファイルからゲームのセーブを簡単に復元します。このツールは、既存のセーブデータ (もしあれば) の削除と、バックアップの正しい場所への展開を処理します。
- **フォルダを開く**: 以下のフォルダを素早く開くためのボタンを提供します:
  - 「7 Days to Die」のセーブフォルダ (`%APPDATA%\7DaysToDie\Saves`)。
  - アプリケーションのバックアップフォルダ (スクリプト実行場所の `7D2DBackups` サブディレクトリ内)。
- **ユーザーフレンドリーなインターフェース**: セーブとバックアップを管理するためのシンプルで直感的な GUI。

## 要件

- **オペレーティングシステム**: 主に Windows 向けに設計されています (`%APPDATA%` および `os.startfile` への依存のため)。
- **Python**: Python 3.x。_(最小 Python バージョンを指定していただけますか？ 例: Python 3.7+)_
- **標準ライブラリ**: `tkinter`、`os`、`shutil`、`datetime`、`pathlib`、`zipfile` といった一般的な Python ライブラリを使用しており、これらは通常 Python に同梱されています。基本的な機能のために外部パッケージは厳密には必要ありません。

## 使い方

1. **アプリケーションの実行**: `7D2D Zombie Save.pyw` ファイルを実行します。これにより GUI が起動するはずです。
    - Windows では、`.pyw` ファイルを実行すると通常 `pythonw.exe` で実行され、コンソールウィンドウは表示されません。
2. **メインウィンドウ**:
    - 左側のリストには、現在の「7 Days to Die」のセーブデータが表示されます。
    - 右側のリストには、利用可能なバックアップが表示されます。
    - 中央の列にはアクションボタンが含まれています。
3. **バックアップの作成**:
    - **左側のリスト** (「セーブデータリスト」) からセーブデータを選択します。
    - **「バックアップ」 (Backup)** ボタンをクリックします。
    - セーブデータのタイムスタンプ付き ZIP ファイルが `7D2DBackups` フォルダに作成されます。
4. **バックアップの復元**:
    - **右側のリスト** (「バックアップリスト」) からバックアップファイルを選択します。
    - **「復元」 (Restore)** ボタンをクリックします。
    - アクションを確認します。選択したバックアップが復元され、そのゲームの現在のセーブデータが存在する場合は上書きされます。
5. **リストの更新**:
    - **「リストを更新」 (Reload)** ボタンをクリックして、セーブデータリストとバックアップリストの両方を更新します。
6. **フォルダを開く**:
    - **「バックアップフォルダを開く」 (Open Backup Folder)** または **「Saves フォルダを開く」 (Open Saves Folder)** ボタンを使用して、素早くアクセスします。

## フォルダ構成

- **ゲームセーブの場所**: アプリケーションは、「7 Days to Die」のセーブを標準的な Windows の場所で探します: `%APPDATA%\7DaysToDie\Saves`。
- **バックアップの場所**: バックアップは `7D2DBackups` という名前のフォルダに保存されます。このフォルダは `7D2D Zombie Save.pyw` スクリプトが置かれているのと同じディレクトリに作成されます。

## ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています

- 詳細については LICENSE.md ファイルを参照してください。

## 貢献

貢献を歓迎します！バグ、機能リクエスト、提案については、プルリクエストを送信するか、イシューを開いてください。

## 既知の問題 / 制限事項

- 現在、このアプリケーションは主に Windows 向けに設計およびテストされています。一部の機能は他の OS でも動作する可能性がありますが、デフォルトのセーブパス検出は Windows 固有です。
- 「7 Days to Die」が将来のアップデートでセーブデータのフォルダ構成を大幅に変更した場合、このツールはアップデートが必要になる可能性があります。

---

Generated by Gemini Code Assist
