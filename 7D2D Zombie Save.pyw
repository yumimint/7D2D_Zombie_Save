import datetime
import functools
import locale
import os
import shutil
import subprocess
import tkinter as tk
import tkinter.ttk as ttk  # zipfile を明示的に使用するため
import zipfile
from collections import namedtuple
from pathlib import Path
from tkinter.messagebox import askyesno, showerror, showinfo
from typing import Optional

# from ttkthemes import ThemedTk  # ダークテーマのために追加


SAVEDATA = namedtuple('SAVEDATA', 'path name worldname')
SAVES = Path(os.environ['APPDATA']) / '7DaysToDie' / 'Saves'
# Backups フォルダをスクリプトと同じ階層に作成
BACKUPS = Path(__file__).parent / '7D2DBackups'
BACKUPS.mkdir(exist_ok=True)


I18N = {
    'en_US': {
        "app_title": "7D2D Zombie Save",
        "save_data_list_label": "Save Data List",
        "operations_label": "Operations",
        "backup_list_label": "Backup List",
        "backup_button": "Backup",
        "restore_button": "Restore",
        "reload_button": "Reload List",
        "open_backup_folder_button": "Open Backup Folder",
        "open_saves_folder_button": "Open Saves Folder",
        "info_title": "Info",
        "error_title": "Error",
        "overwrite_confirm_title": "Overwrite Confirmation",
        "restore_confirm_title": "Restore Confirmation",
        "backup_error_title": "Backup Error",
        "restore_error_title": "Restore Error",
        "folder_open_not_supported_msg": "Automatic folder opening is not supported.\nPath: {path}",
        "folder_open_error_msg": "Could not open the folder.\n{path}\n\nDetails: {e}",
        "select_save_for_backup_error_msg": "Please select the save data to back up.",
        "overwrite_confirm_msg": "{filename} already exists. Do you want to overwrite it?",
        "status_backing_up": "Backing up...",
        "backup_failed_error_msg": "Failed to create backup.\n\nDetails: {e}",
        "select_backup_for_restore_error_msg": "Please select the backup file to restore.",
        "backup_file_not_found_error_msg": "The specified backup file was not found: {filename}",
        "cannot_get_savename_error_msg": "Could not retrieve the save data name from the backup.",
        "restore_confirm_msg": "Do you want to restore save data \"{savename}\" from backup \"{backup_filename}\"?\n\nThe current save data will be overwritten.",
        "status_restoring": "Restoring...",
        "restore_file_not_found_error_msg": "File or directory not found during restore.\n\nDetails: {e}",
        "restore_permission_error_msg": "A permission issue occurred during restore.\n\nDetails: {e}",
        "restore_bad_zip_error_msg": "The backup file is corrupted or in an invalid format.\n\nDetails: {e}",
        "restore_unexpected_error_msg": "An unexpected error occurred during restore.\n\nDetails: {e}",
        "mtime_empty_dir_error_msg": "{path} does not contain any files."
    },
    'ja_JP': {
        "save_data_list_label": "セーブデータリスト",
        "operations_label": "操作",
        "backup_list_label": "バックアップリスト",
        "backup_button": "バックアップ",
        "restore_button": "復元",
        "reload_button": "リストを更新",
        "open_backup_folder_button": "バックアップフォルダを開く",
        "open_saves_folder_button": "Savesフォルダを開く",
        "info_title": "情報",
        "error_title": "エラー",
        "overwrite_confirm_title": "上書き確認",
        "restore_confirm_title": "復元の確認",
        "backup_error_title": "バックアップエラー",
        "restore_error_title": "復元エラー",
        "folder_open_not_supported_msg": "フォルダの自動オープンはサポートされていません。\nパス: {path}",
        "folder_open_error_msg": "フォルダを開けませんでした。\n{path}\n\n詳細: {e}",
        "select_save_for_backup_error_msg": "バックアップするセーブデータを選択してください。",
        "overwrite_confirm_msg": "{filename}は既に存在します。上書きしますか？",
        "status_backing_up": "バックアップしています...",
        "backup_failed_error_msg": "バックアップの作成に失敗しました。\n\n詳細: {e}",
        "select_backup_for_restore_error_msg": "復元するバックアップファイルを選択してください。",
        "backup_file_not_found_error_msg": "指定されたバックアップファイルが見つかりません: {filename}",
        "cannot_get_savename_error_msg": "バックアップからセーブデータ名を取得できませんでした。",
        "restore_confirm_msg": "バックアップ「{backup_filename}」からセーブデータ「{savename}」を復元しますか？\n\n現在のセーブデータは上書きされます。",
        "status_restoring": "復元しています...",
        "restore_file_not_found_error_msg": "復元中にファイルまたはディレクトリが見つかりませんでした。\n\n詳細: {e}",
        "restore_permission_error_msg": "復元中にアクセス許可の問題が発生しました。\n\n詳細: {e}",
        "restore_bad_zip_error_msg": "バックアップファイルが破損しているか、不正な形式です。\n\n詳細: {e}",
        "restore_unexpected_error_msg": "復元中に予期せぬエラーが発生しました。\n\n詳細: {e}",
        "mtime_empty_dir_error_msg": "{path} にはファイルが含まれていません。"
    },
}


class Application(tk.Frame):
    STRINGS = {}

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

        lang = locale.getdefaultlocale()[0]
        # lang = "en_US"

        if lang in I18N:
            self.STRINGS = I18N[lang].copy()
            for key, text in I18N["en_US"].items():
                if key not in self.STRINGS:
                    self.STRINGS[key] = text
        else:
            self.STRINGS = self.I18N['en_US']

        # アプリケーションのタイトルを設定
        self.master.title(self.STRINGS["app_title"])
        self.master.resizable(False, False)  # ウィンドウのリサイズを禁止
        self.pack()
        self.create_widgets()
        self.load_save_data()
        self.load_backup_data()

    def create_widgets(self):
        """ウィジェットを作成する
        """
        # 3つのフレームを作成
        self.column1 = tk.Frame(self)
        self.column2 = tk.Frame(self)
        self.column3 = tk.Frame(self)

        self.column1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.column2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.column3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 各列にラベルを追加（仮のウィジェット）
        tk.Label(self.column1,
                 text=self.STRINGS["save_data_list_label"]).pack()
        tk.Label(self.column2, text=self.STRINGS["operations_label"]).pack()
        tk.Label(self.column3, text=self.STRINGS["backup_list_label"]).pack()

        # ttk.Button のスタイルを設定
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 12))

        # リストボックス (左の列に配置)
        self.save_listbox = tk.Listbox(
            self.column1, width=40, exportselection=False)
        self.save_listbox.pack(pady=10, fill=tk.BOTH, expand=True)
        self.save_listbox.bind('<<ListboxSelect>>', self.on_save_select)

        # バックアップリストボックス (右の列に配置)
        self.backup_listbox = tk.Listbox(
            self.column3, width=40, exportselection=False)
        self.backup_listbox.pack(pady=10, fill=tk.BOTH, expand=True)
        self.backup_listbox.bind('<<ListboxSelect>>', self.on_backup_select)

        # ボタン (中央の列に配置)
        self.button_frame = tk.Frame(self.column2)
        self.button_frame.pack(pady=10)

        self.backup_button = ttk.Button(self.button_frame,
                                        text=self.STRINGS["backup_button"],
                                        command=self.do_backup,
                                        style='TButton', state=tk.DISABLED)
        self.backup_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        self.restore_button = ttk.Button(self.button_frame,
                                         text=self.STRINGS["restore_button"],
                                         command=self.do_restore,
                                         style='TButton', state=tk.DISABLED)
        self.restore_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        self.reload_button = ttk.Button(self.button_frame,
                                        text=self.STRINGS["reload_button"],
                                        command=self.reload, style='TButton')
        self.reload_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        ttk.Button(self.button_frame,
                   text=self.STRINGS["open_backup_folder_button"],
                   command=lambda: self._startfile(BACKUPS),
                   style='TButton').pack(side=tk.TOP, padx=5, pady=5,
                                         fill=tk.X)

        ttk.Button(self.button_frame,
                   text=self.STRINGS["open_saves_folder_button"],
                   command=lambda: self._startfile(SAVES),
                   style='TButton').pack(side=tk.TOP, padx=5, pady=5,
                                         fill=tk.X)

        # ステータス表示用のラベル (中央の列に配置)
        self.status_label = tk.Label(self.column2, text="")
        self.status_label.pack(pady=5)

    def _startfile(self, path):
        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['open', str(path)])  # macOS
            else:
                showinfo(
                    self.STRINGS["info_title"],
                    self.STRINGS["folder_open_not_supported_msg"].format(path=path))
        except Exception as e:
            showerror(
                self.STRINGS["error_title"],
                self.STRINGS["folder_open_error_msg"].format(path=path, e=e))

    def reload(self):
        self.load_save_data()
        self.load_backup_data()

    def load_save_data(self):
        """セーブデータの一覧をリストボックスに表示する"""
        self.backup_button.config(state=tk.DISABLED)
        self.save_listbox.delete(0, tk.END)  # リストボックスをクリア

        self._cashed_mtime_of_dir.cache_clear()

        # セーブデータの一覧を取得
        self.save_dirs = sorted(
            self._get_saves(),
            key=lambda x: self._cashed_mtime_of_dir(x.path),
            reverse=True)  # 最新順に

        for save in self.save_dirs:
            display_name = f"{save.path.name} ({save.worldname})"
            # display_name = save.path.name
            self.save_listbox.insert(tk.END, display_name)

    def on_save_select(self, event):
        """セーブデータリストボックスで項目が選択されたときの処理"""
        widget = event.widget

        selection = widget.curselection()
        if selection:
            # index = selection[0]
            # selected_save = self.save_dirs[index]
            self.backup_button.config(state=tk.NORMAL)
        else:
            self.backup_button.config(state=tk.DISABLED)

        self.master.update_idletasks()

    def on_backup_select(self, event):
        """バックアップリストボックスで項目が選択されたときの処理"""
        widget = event.widget
        selection = widget.curselection()
        if selection:
            # index = selection[0]
            # selected_backup = self.backup_files[index]
            # print(selected_backup)
            self.restore_button.config(state=tk.NORMAL)
        else:
            self.restore_button.config(state=tk.DISABLED)

    def load_backup_data(self, selected_save: Path = None):
        """バックアップデータの一覧をリストボックスに表示する"""
        self.restore_button.config(state=tk.DISABLED)  # バックアップリスト更新時は復元ボタンを無効化

        if selected_save is None:
            self.backup_files = list(BACKUPS.glob("*.zip"))
        else:
            # selected_saveが在れば関連するzipだけリスト化
            self.backup_files = list(BACKUPS.glob(
                f"*{selected_save.name}_*.zip"))

        # 更新日時でソート
        self.backup_files = sorted(self.backup_files,
                                   key=lambda x: x.stat().st_mtime,
                                   reverse=True)

        # リストボックスに表示
        self.backup_listbox.delete(0, tk.END)
        for backup_file in self.backup_files:
            self.backup_listbox.insert(tk.END, backup_file.name)

    def do_backup(self):
        """バックアップを作成する"""
        selected_indices = self.save_listbox.curselection()
        # ボタンが無効化されているはずなので、通常ここには到達しないが念のため
        if not selected_indices:
            showerror(self.STRINGS["error_title"],
                      self.STRINGS["select_save_for_backup_error_msg"])
            return

        save: SAVEDATA = self.save_dirs[selected_indices[0]]

        # セーブフォルダの更新時刻を取得
        # mtime = save.path.stat().st_mtime
        mtime = self._mtime_of_dir(save.path)
        dt = datetime.datetime.fromtimestamp(mtime)
        y, m, d, hh, mm = dt.year, dt.month, dt.day, dt.hour, dt.minute

        suffix = f"{y}{m:02d}{d:02d}T{hh:02d}{mm:02d}"
        root = save.path.parent.parent  # == SAVES

        # アーカイブ名（.zipなし）
        # archive_name_base = BACKUPS / f"{save.worldname}_{save.name}_{suffix}"
        archive_name_base = BACKUPS / f"{save.name}_{suffix}"
        archive_file = archive_name_base.with_suffix('.zip')  # 正しいzipファイル名

        if archive_file.exists():
            if not askyesno(
                    self.STRINGS["overwrite_confirm_title"],
                    self.STRINGS["overwrite_confirm_msg"].format(filename=archive_file.name)):
                return

        try:
            self.status_label.config(text=self.STRINGS["status_backing_up"])
            self.backup_button.config(state=tk.DISABLED)
            self.master.update_idletasks()  # GUIを強制的に更新してメッセージを表示
            shutil.make_archive(str(archive_name_base), 'zip',
                                root, f"{save.worldname}/{save.name}")
            # print(f"バックアップ作成完了: {archive_file}")
            # showinfo(
            #     "バックアップ完了", f"バックアップを作成しました:\n{archive_file.name}")
            self.load_backup_data()  # バックアップリストを更新
        except Exception as e:
            showerror(
                self.STRINGS["backup_error_title"],
                self.STRINGS["backup_failed_error_msg"].format(e=e))
        finally:
            self.status_label.config(text="")  # ステータス表示をクリア
            self.backup_button.config(state=tk.NORMAL)
            self.master.update_idletasks()  # GUIを更新

    def do_restore(self):
        """セーブデータ復元処理"""
        selected_backup_indices = self.backup_listbox.curselection()

        if not selected_backup_indices:
            showerror(self.STRINGS["error_title"],
                      self.STRINGS["select_backup_for_restore_error_msg"])
            return

        backup_file: Path = self.backup_files[selected_backup_indices[0]]

        if not backup_file.exists():
            showerror(self.STRINGS["error_title"],
                      self.STRINGS["backup_file_not_found_error_msg"].format(filename=backup_file))
            # ファイル消された？リストを最新に更新しておく
            self.load_backup_data()
            return

        savename = self._get_savename_from_archive(backup_file)
        if savename is None:
            showerror(self.STRINGS["error_title"],
                      self.STRINGS["cannot_get_savename_error_msg"])
            return

        save_dir = SAVES / savename
        if save_dir.exists():
            confirm_message = (
                self.STRINGS["restore_confirm_msg"].format(
                    backup_filename=backup_file.name,
                    savename=savename
                )
            )
            if not askyesno(self.STRINGS["restore_confirm_title"], confirm_message):
                return

        self.status_label.config(text=self.STRINGS["status_restoring"])
        self.restore_button.config(state=tk.DISABLED)
        self.master.update_idletasks()

        try:
            # 既存のセーブデータディレクトリを削除
            save_dir = SAVES / savename
            if save_dir.exists():
                shutil.rmtree(save_dir)

            # バックアップファイルを指定の場所に展開 (更新日時を保持するメソッドを使用)
            self._unpack_archive_preserving_timestamp(backup_file, SAVES)
            # print(f"セーブデータ復元完了: {savename}")

            self.load_save_data()  # セーブリストを更新)
            # showinfo("復元完了", f"セーブデータ「{savename}」を復元しました。")

        except FileNotFoundError as e:
            showerror(self.STRINGS["restore_error_title"],
                      self.STRINGS["restore_file_not_found_error_msg"].format(e=e))
        except PermissionError as e:
            showerror(self.STRINGS["restore_error_title"],
                      self.STRINGS["restore_permission_error_msg"].format(e=e))
        except (shutil.ReadError, zipfile.BadZipFile) as e:
            showerror(self.STRINGS["restore_error_title"],
                      self.STRINGS["restore_bad_zip_error_msg"].format(e=e))
        except Exception as e:
            showerror(self.STRINGS["restore_error_title"],
                      self.STRINGS["restore_unexpected_error_msg"].format(e=e))
        finally:
            self.status_label.config(text="")
            self.reload()
            self.master.update_idletasks()

    def _unpack_archive_preserving_timestamp(self, archive_path: Path, extract_dir: Path):
        """
        ZIPアーカイブを展開し、ファイルの更新日時を保持する。
        """
        if not archive_path.is_file():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
        # このアプリケーションではバックアップはZIPファイルのみを想定しているため、
        # .zip 拡張子のチェックは省略または簡略化できます。

        with zipfile.ZipFile(archive_path, 'r') as zf:
            for member_info in zf.infolist():
                # メンバーを展開
                # extract() はファイルとディレクトリの両方を処理します。
                # path 引数で展開先のルートディレクトリを指定します。
                zf.extract(member_info, path=extract_dir)

                # 展開後の実際のパス
                # member_info.filename はアーカイブ内の相対パスです。
                extracted_member_path = extract_dir / member_info.filename

                # 更新日時を設定
                # ZipInfo.date_time は (year, month, day, hour, minute, second) のタプルです。
                # ZIP仕様により、year は 1980 以上である必要があります。
                if member_info.date_time[0] >= 1980:
                    dt_tuple = member_info.date_time
                    try:
                        # datetime オブジェクトを作成
                        dt = datetime.datetime(*dt_tuple[:6])
                        # タイムスタンプ (エポック秒) に変換
                        timestamp = dt.timestamp()
                        # ファイル/ディレクトリのアクセス時刻と更新時刻を設定
                        os.utime(extracted_member_path, (timestamp, timestamp))
                    except Exception:
                        # タイムスタンプの設定に失敗した場合の警告 (ログなど)
                        # print(f"Warning: Could not set timestamp for {extracted_member_path}. Error: {e}")
                        # 処理は続行します。
                        pass
                # else:
                    # 古いZIPファイル等で日時情報が無効な場合は何もしないか、警告を出すことができます。
                    # print(f"Warning: Invalid date_time for {member_info.filename} in {archive_path}")

    def _get_savename_from_archive(self, path: Path) -> Optional[str]:
        """pathが示すアーカイブからワールド名/セーブ名を取得する"""
        if not path.is_file():
            return None

        try:
            with zipfile.ZipFile(path, 'r') as zf:
                # We are looking for a path like "WorldName/SaveName/..."
                # parts[0] would be WorldName
                # parts[1] would be SaveName
                for item_path_str in zf.namelist():
                    parts = item_path_str.split('/')
                    if len(parts) >= 2 and parts[1]:
                        return "/".join(parts[:2])
                return None
        except zipfile.BadZipFile:  # Handles corrupted or invalid zip files
            return None
        except Exception:  # Catches other potential file operation errors
            return None

    @functools.cache
    def _cashed_mtime_of_dir(self, path: Path):
        return self._mtime_of_dir(path)

    def _mtime_of_dir(self, path: Path):
        mtimes = [
            file.stat().st_mtime
            for file in path.rglob('*')
            if file.is_file()
        ]
        if not mtimes:
            msg = self.STRINGS["mtime_empty_dir_error_msg"]
            raise RuntimeError(msg.format(path=path))
        return max(mtimes)

    def _get_saves(self):
        """セーブデータの一覧を取得する"""
        if not SAVES.exists():
            return

        for world in SAVES.iterdir():
            if not world.is_dir():
                continue  # ディレクトリでなければスキップ
            if world.name == 'Empty':
                continue  # 'Empty'フォルダはスキップ

            for save in world.iterdir():
                if not save.is_dir():
                    continue
                if not (save / 'power.dat').exists():
                    # "power.dat" が無ければスキップ
                    continue
                yield SAVEDATA(save, save.name, world.name)


root = tk.Tk()
# ダークテーマを適用するために ThemedTk を使用
# "equilux" や "arc", "black" など、好みのダークテーマを選択
# root = ThemedTk(theme="equilux")

app = Application(master=root)
app.mainloop()
