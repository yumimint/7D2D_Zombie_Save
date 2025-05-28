import datetime
import functools
import os
import shutil
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
import zipfile
from collections import namedtuple
from pathlib import Path
from tkinter.messagebox import askyesno, showerror, showinfo
from typing import Optional

# from ttkthemes import ThemedTk  # ダークテーマのために追加


SAVEDATA = namedtuple('SAVEDATA', 'path name worldname')


def mtime_of_dir(path: Path):
    mtimes = [
        file.stat().st_mtime
        for file in path.rglob('*')
        if file.is_file()
    ]
    if not mtimes:
        raise RecursionError(f"{path} has not contain any files")

    return max(mtimes)


def startfile(path):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # macOS, Linux
            subprocess.Popen(['open', str(path)])  # macOS
            # Linuxの場合は
            # subprocess.Popen(['xdg-open', str(path)]) なども検討
        else:
            showinfo(
                "情報", f"フォルダの自動オープンはサポートされていません。\nパス: {path}")
    except Exception as e:
        # print(f"Error opening backup folder: {e}")
        showerror(
            "エラー", f"フォルダを開けませんでした。\n{path}\n\n詳細: {e}")


def get_savename_from_archive(path: Path) -> Optional[str]:
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


class Application(tk.Frame):
    APPDATA = Path(os.environ['APPDATA'])
    SAVES = APPDATA / '7DaysToDie' / 'Saves'
    # Backups フォルダをスクリプトと同じ階層に作成
    BACKUPS = Path(__file__).parent / '7D2DBackups'
    BACKUPS.mkdir(exist_ok=True)

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        # アプリケーションのタイトルを設定
        self.master.title("7D2D Zombie Save")
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
        tk.Label(self.column1, text="セーブデータリスト").pack()
        tk.Label(self.column2, text="操作").pack()
        tk.Label(self.column3, text="バックアップリスト").pack()

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

        self.backup_button = ttk.Button(self.button_frame, text="バックアップ",
                                        command=self.create_backup,
                                        style='TButton', state=tk.DISABLED)
        self.backup_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        self.restore_button = ttk.Button(self.button_frame, text="復元",
                                         command=self.restore_save,
                                         style='TButton', state=tk.DISABLED)
        self.restore_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        self.reload_button = ttk.Button(self.button_frame, text="リストを更新",
                                        command=self.reload, style='TButton')
        self.reload_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        ttk.Button(self.button_frame, text="バックアップフォルダを開く",
                   command=lambda: startfile(self.BACKUPS),
                   style='TButton').pack(side=tk.TOP, padx=5, pady=5,
                                         fill=tk.X)

        ttk.Button(self.button_frame, text="Savesフォルダを開く",
                   command=lambda: startfile(self.SAVES),
                   style='TButton').pack(side=tk.TOP, padx=5, pady=5,
                                         fill=tk.X)

        # ステータス表示用のラベル (中央の列に配置)
        self.status_label = tk.Label(self.column2, text="")
        self.status_label.pack(pady=5)

    def reload(self):
        self.load_save_data()
        self.load_backup_data()

    def get_saves(self):
        """セーブデータの一覧を取得する"""
        if not self.SAVES.exists():
            return

        for world in self.SAVES.iterdir():
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

    def load_save_data(self):
        """セーブデータの一覧をリストボックスに表示する"""
        self.backup_button.config(state=tk.DISABLED)
        self.save_listbox.delete(0, tk.END)  # リストボックスをクリア

        # if not self.SAVES.exists():
        #     # print(f"Savesフォルダが見つかりません: {self.SAVES}")
        #     self.save_listbox.insert(tk.END, "Savesフォルダが見つかりません")
        #     return

        cashed_mtime_of_dir = functools.cache(mtime_of_dir)

        # セーブデータの一覧を取得
        self.save_dirs = sorted(
            self.get_saves(),
            key=lambda x: cashed_mtime_of_dir(x.path),
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
            # self.load_backup_data(selected_save)
        else:
            self.backup_button.config(state=tk.DISABLED)
            # self.load_backup_data(None)  # 選択解除時はバックアップリストもクリア

        self.master.update_idletasks()

        # セーブデータ選択変更時は復元ボタンを無効化
        # self.restore_button.config(state=tk.DISABLED)

    def on_backup_select(self, event):
        """バックアップリストボックスで項目が選択されたときの処理"""
        widget = event.widget
        selection = widget.curselection()
        if selection:
            index = selection[0]
            selected_backup = self.backup_files[index]
            print(selected_backup)
            self.restore_button.config(state=tk.NORMAL)
        else:
            self.restore_button.config(state=tk.DISABLED)

    def load_backup_data(self, selected_save: Path = None):
        """バックアップデータの一覧をリストボックスに表示する
        """
        self.restore_button.config(state=tk.DISABLED)  # バックアップリスト更新時は復元ボタンを無効化

        if selected_save is None:
            self.backup_files = list(self.BACKUPS.glob("*.zip"))
        else:
            self.backup_files = list(
                self.BACKUPS.glob(f"*{selected_save.name}_*.zip"))

        self.backup_files = sorted(self.backup_files,
                                   key=lambda x: x.stat().st_mtime,
                                   reverse=True)

        self.backup_listbox.delete(0, tk.END)
        for backup_file in self.backup_files:
            self.backup_listbox.insert(tk.END, backup_file.name)

    def create_backup(self):
        """バックアップを作成する"""
        selected_indices = self.save_listbox.curselection()
        # ボタンが無効化されているはずなので、通常ここには到達しないが念のため
        if not selected_indices:
            showerror("エラー", "バックアップするセーブデータを選択してください。")
            return

        save: SAVEDATA = self.save_dirs[selected_indices[0]]

        # セーブフォルダの更新時刻を取得
        # mtime = save.path.stat().st_mtime
        mtime = mtime_of_dir(save.path)
        dt = datetime.datetime.fromtimestamp(mtime)
        y, m, d, hh, mm = dt.year, dt.month, dt.day, dt.hour, dt.minute

        suffix = f"{y}{m:02d}{d:02d}T{hh:02d}{mm:02d}"
        worldname = save.worldname
        savename = save.path.name
        root = save.path.parent.parent

        # アーカイブ名（.zipなし）
        # archive_name_base = self.BACKUPS / f"{worldname}_{savename}_{suffix}"
        archive_name_base = self.BACKUPS / f"{savename}_{suffix}"
        archive_file = archive_name_base.with_suffix('.zip')  # 正しいzipファイル名

        if archive_file.exists():
            if not askyesno("上書き確認", f"{archive_file.name}は既に存在します。上書きしますか？"):
                return

        try:
            self.status_label.config(text="バックアップしています...")
            self.backup_button.config(state=tk.DISABLED)
            self.master.update_idletasks()  # GUIを強制的に更新してメッセージを表示
            shutil.make_archive(str(archive_name_base), 'zip',
                                root, f"{worldname}/{savename}")
            # print(f"バックアップ作成完了: {archive_file}")
            showinfo(
                "バックアップ完了", f"バックアップを作成しました:\n{archive_file.name}")
            self.load_backup_data()  # バックアップリストを更新
        except Exception as e:
            showerror(
                "バックアップエラー",
                f"バックアップの作成に失敗しました。\n\n詳細: {e}")
        finally:
            self.status_label.config(text="")  # ステータス表示をクリア
            self.backup_button.config(state=tk.NORMAL)
            self.master.update_idletasks()  # GUIを更新

    def restore_save(self):
        """セーブデータ復元処理"""
        selected_backup_indices = self.backup_listbox.curselection()

        if not selected_backup_indices:
            showerror("エラー", "復元するバックアップファイルを選択してください。")
            return

        backup_file: Path = self.backup_files[selected_backup_indices[0]]

        if not backup_file.exists():
            showerror("エラー", f"指定されたバックアップファイルが見つかりません: {backup_file}")
            # ファイル消された？リストを最新に更新しておく
            self.load_backup_data()
            return

        savename = get_savename_from_archive(backup_file)
        if savename is None:
            return

        save_dir = self.SAVES / savename
        if save_dir.exists():
            confirm_message = (
                f"バックアップ「{backup_file.name}」から"
                f"セーブデータ「{savename}」を復元しますか？\n\n"
                "現在のセーブデータは上書きされます。"
            )
            if not askyesno("復元の確認", confirm_message):
                return

        self.status_label.config(text="復元しています...")
        self.restore_button.config(state=tk.DISABLED)
        self.master.update_idletasks()

        try:
            # 既存のセーブデータディレクトリを削除
            save_dir = self.SAVES / savename
            if save_dir.exists():
                shutil.rmtree(save_dir)

            # バックアップファイルを指定の場所に展開
            # save_dir.parent に展開することで、元の save_dir と同じ階層構造を復元
            shutil.unpack_archive(str(backup_file), str(self.SAVES))

            showinfo("復元完了", f"セーブデータ「{savename}」を復元しました。")

        except FileNotFoundError as e:
            showerror("復元エラー", f"復元中にファイルまたはディレクトリが見つかりませんでした。\n\n詳細: {e}")
        except PermissionError as e:
            showerror("復元エラー", f"復元中にアクセス許可の問題が発生しました。\n\n詳細: {e}")
        except (shutil.ReadError, zipfile.BadZipFile) as e:
            showerror("復元エラー", f"バックアップファイルが破損しているか、不正な形式です。\n\n詳細: {e}")
        except Exception as e:
            showerror("復元エラー", f"復元中に予期せぬエラーが発生しました。\n\n詳細: {e}")
        finally:
            self.status_label.config(text="")
            self.reload()
            self.master.update_idletasks()


root = tk.Tk()
# ダークテーマを適用するために ThemedTk を使用
# "equilux" や "arc", "black" など、好みのダークテーマを選択
# root = ThemedTk(theme="equilux")

app = Application(master=root)
app.mainloop()
