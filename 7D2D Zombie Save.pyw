import datetime
import functools
import json
import locale
import logging
import os
import shutil
import subprocess
import threading
import tkinter as tk
import tkinter.ttk as ttk
import zipfile
from pathlib import Path
from tkinter.messagebox import askyesno, showerror, showinfo
from typing import Generator, List, Optional

logger = logging.getLogger(__name__)

SAVES = Path(os.environ['APPDATA']) / '7DaysToDie' / 'Saves'
# Backups フォルダをスクリプトと同じ階層に作成
BACKUPS = Path(__file__).parent / '7D2DBackups'
BACKUPS.mkdir(exist_ok=True)

STRINGS = {}


def load_i18n_strings():
    global STRINGS
    lang = locale.getlocale()[0]
    logger.info(f"lang={lang}")
    # lang = "en_US"

    i18n = Path(__file__).parent / '7D2D Zombie Save i18n.json'
    with i18n.open(encoding='utf-8') as f:
        I18N = json.load(f)

    if lang in I18N:
        STRINGS = I18N[lang]
        for key, text in I18N["en_US"].items():
            if key not in STRINGS:
                STRINGS[key] = text
    else:
        STRINGS = I18N['en_US']


def displayname(savedir: Path):
    """savedirからGUIに表示するセーブ名を取得する"""
    world = savedir.parent.name
    name = savedir.name
    return f"{name} ({world})"


class Application(tk.Frame):
    """メインウィンドウクラス"""

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

        self.saves: Optional[List[Path]] = None
        self.backups: Optional[List[Path]] = None

        # For save data monitoring
        self.monitor_var = tk.BooleanVar(value=False)
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitor_event: Optional[threading.Event] = None
        self.monitored_mtimes: dict[Path, float] = {}

        icon = Path(__file__).parent / '7D2D Zombie Save.ico'
        self.master.iconbitmap(icon)

        # アプリケーションのタイトルを設定
        self.master.title(STRINGS["app_title"])
        self.master.resizable(False, False)  # ウィンドウのリサイズを禁止

        # Handle window close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.pack()
        self.create_widgets()
        self.load_save_data()
        self.load_backup_data()

    def create_widgets(self):
        """ウィジェットを作成する"""

        # 3つのフレームを作成
        self.column1 = tk.Frame(self)
        self.column2 = tk.Frame(self)
        self.column3 = tk.Frame(self)

        self.column1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.column2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.column3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 各列にラベルを追加（仮のウィジェット）
        tk.Label(self.column1,
                 text=STRINGS["save_data_list_label"]).pack()
        tk.Label(self.column2, text=STRINGS["operations_label"]).pack()
        tk.Label(self.column3, text=STRINGS["backup_list_label"]).pack()

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
                                        text=STRINGS["backup_button"],
                                        command=self.do_backup,
                                        style='TButton', state=tk.DISABLED)
        self.backup_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        self.restore_button = ttk.Button(self.button_frame,
                                         text=STRINGS["restore_button"],
                                         command=self.do_restore,
                                         style='TButton', state=tk.DISABLED)
        self.restore_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        self.reload_button = ttk.Button(self.button_frame,
                                        text=STRINGS["reload_button"],
                                        command=self.reload, style='TButton')
        self.reload_button.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        ttk.Button(self.button_frame,
                   text=STRINGS["open_backup_folder_button"],
                   command=lambda: startfile(BACKUPS),
                   style='TButton').pack(side=tk.TOP, padx=5, pady=5,
                                         fill=tk.X)

        ttk.Button(self.button_frame,
                   text=STRINGS["open_saves_folder_button"],
                   command=lambda: startfile(SAVES),
                   style='TButton').pack(side=tk.TOP, padx=5, pady=5,
                                         fill=tk.X)

        # Monitoring Checkbutton
        self.monitor_checkbox = ttk.Checkbutton(
            self.button_frame,
            text=STRINGS.get("monitor_saves_checkbox", "Auto Backup"),
            variable=self.monitor_var,
            command=self.toggle_monitoring
        )
        self.monitor_checkbox.pack(side=tk.TOP, padx=5, pady=10, fill=tk.X)

        # ステータス表示用のラベル (中央の列に配置)
        self.status_label = tk.Label(self.column2, text="")
        self.status_label.pack(pady=5)

    def on_closing(self):
        """Handles the application window closing."""
        if self.monitor_var.get() and self.monitor_thread and self.monitor_thread.is_alive():
            logger.info("Stopping monitoring thread before closing...")
            self.stop_monitoring()
        self.master.destroy()

    def toggle_monitoring(self):
        """Starts or stops the save data monitoring thread based on the checkbox state."""
        if self.monitor_var.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        """Starts the save data monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.info("Monitoring is already active.")
            return
        self.stop_monitor_event = threading.Event()
        self.monitored_mtimes = {}  # Reset for a fresh start
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.status_label.config(text=STRINGS.get(
            "status_monitoring_started", "Monitoring started."))

    def stop_monitoring(self):
        """Stops the save data monitoring thread."""
        if self.stop_monitor_event:
            self.stop_monitor_event.set()
        # Joining the thread is handled in on_closing or if explicitly needed elsewhere.
        # For toggling off, just setting the event is enough for the daemon thread.
        self.monitor_thread = None  # Allow garbage collection
        self.status_label.config(text=STRINGS.get(
            "status_monitoring_stopped", "Monitoring stopped."))
        self.monitored_mtimes = {}  # Clear stored mtimes

    def reload(self):
        self.load_save_data()
        self.load_backup_data()

    def monitor_loop(self):
        """Periodically checks for save data changes."""
        logger.info("Monitoring thread started.")

        def get_mtime(savedir: Path):
            return (savedir / "power.dat").stat().st_mtime

        self.monitored_mtimes = {
            savedir: get_mtime(savedir)
            for savedir in iter_savedir()
        }

        # Check every 60 seconds
        while self.stop_monitor_event and not self.stop_monitor_event.wait(5):
            if self.stop_monitor_event and self.stop_monitor_event.is_set():
                break
            current_mtimes = {
                savedir: get_mtime(savedir)
                for savedir in iter_savedir()
            }
            if current_mtimes == self.monitored_mtimes:
                continue  # No changes detected

            removed = set(self.monitored_mtimes.keys()
                          ) - set(current_mtimes.keys())
            if removed:
                logger.info(f"Saves detected as removed: {removed}")

            changed = set(self.monitored_mtimes.items()
                          ) ^ set(current_mtimes.items())
            changed = set({p[0] for p in changed}) - removed

            if changed:
                logger.info(f"Saves detected as changed: {changed}")

            # Schedule UI update in main thread
            logger.info("Scheduling UI refresh due to save data changes.")
            self.master.after(0, self.refresh_ui_from_monitor)
            self.monitored_mtimes = current_mtimes.copy()

        logger.info("Monitoring thread finished.")

    def load_save_data(self):
        """セーブデータの一覧をリストボックスに表示する"""
        self.backup_button.config(state=tk.DISABLED)
        self.save_listbox.delete(0, tk.END)  # リストボックスをクリア

        cashed_mtime_of_tree.cache_clear()

        # セーブデータの一覧を取得
        self.saves = sorted(
            iter_savedir(),
            key=lambda x: cashed_mtime_of_tree(x),
            reverse=True)  # 最新順に

        for savedir in self.saves:
            self.save_listbox.insert(tk.END, displayname(savedir))

    def refresh_ui_from_monitor(self):
        """Called from the main thread to refresh UI elements after monitoring detects changes."""
        logger.info("Refreshing UI due to detected save changes.")

        # selected_save_displayname = None
        # if self.save_listbox.curselection():
        #     try:
        #         selected_save_displayname = self.save_listbox.get(
        #             self.save_listbox.curselection()[0])
        #     except tk.TclError:  # Selection might be invalid if list is about to change drastically
        #         pass

        self.load_save_data()  # This will clear and repopulate the save list

        # if selected_save_displayname:
        #     try:
        #         items = self.save_listbox.get(0, tk.END)
        #         if selected_save_displayname in items:
        #             new_index = items.index(selected_save_displayname)
        #             self.save_listbox.selection_set(new_index)
        #             self.save_listbox.see(new_index)
        #     except (ValueError, tk.TclError):  # Item no longer exists or other error
        #         pass

        # # Update button states based on new selection (or lack thereof)
        # self.on_save_select(tk.Event())

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
            index = selection[0]
            selected_backup = self.backups[index]
            logger.info(f"selected: {selected_backup.name}")
            self.restore_button.config(state=tk.NORMAL)
        else:
            self.restore_button.config(state=tk.DISABLED)

    def load_backup_data(self, selected_save: Path = None):
        """バックアップデータの一覧をリストボックスに表示する"""
        self.restore_button.config(state=tk.DISABLED)  # バックアップリスト更新時は復元ボタンを無効化

        if selected_save is None:
            self.backups = list(BACKUPS.glob("*.zip"))
        else:
            # selected_saveが在れば関連するzipだけリスト化
            self.backups = list(BACKUPS.glob(
                f"*{selected_save.name}_*.zip"))

        # 更新日時でソート
        self.backups = sorted(self.backups,
                              key=lambda x: x.stat().st_mtime,
                              reverse=True)

        # リストボックスに表示
        self.backup_listbox.delete(0, tk.END)
        for backup_file in self.backups:
            self.backup_listbox.insert(tk.END, backup_file.name)

    def do_backup(self):
        """バックアップを作成する"""
        selected_indices = self.save_listbox.curselection()
        # ボタンが無効化されているはずなので、通常ここには到達しないが念のため
        if not selected_indices:
            showerror(STRINGS["error_title"],
                      STRINGS["select_save_for_backup_error_msg"])
            return

        savedir = self.saves[selected_indices[0]]

        try:
            self.status_label.config(text=STRINGS["status_backing_up"])
            self.backup_button.config(state=tk.DISABLED)
            self.master.update_idletasks()  # GUIを強制的に更新してメッセージを表示
            create_backup(savedir, if_exists="confirm")
            self.load_backup_data()  # バックアップリストを更新
        except Exception as e:
            logger.error(f"Error during backup: {e}")
            showerror(
                STRINGS["backup_error_title"],
                STRINGS["backup_failed_error_msg"].format(e=e))
        finally:
            self.status_label.config(text="")  # ステータス表示をクリア
            self.backup_button.config(state=tk.NORMAL)
            self.master.update_idletasks()  # GUIを更新

    def do_restore(self):
        """セーブデータ復元処理"""
        selected_backup_indices = self.backup_listbox.curselection()

        if not selected_backup_indices:
            showerror(STRINGS["error_title"],
                      STRINGS["select_backup_for_restore_error_msg"])
            return

        backup_file: Path = self.backups[selected_backup_indices[0]]

        if not backup_file.exists():
            showerror(STRINGS["error_title"],
                      STRINGS["backup_file_not_found_error_msg"].format(filename=backup_file))
            # ファイル消された？リストを最新に更新しておく
            self.load_backup_data()
            return

        savename = get_savename_from_archive(backup_file)
        if savename is None:
            showerror(STRINGS["error_title"],
                      STRINGS["cannot_get_savename_error_msg"])
            return

        save_dir = SAVES / savename
        if save_dir.exists():
            confirm_message = (
                STRINGS["restore_confirm_msg"].format(
                    backup_filename=backup_file.name,
                    savename=savename
                )
            )
            if not askyesno(STRINGS["restore_confirm_title"], confirm_message):
                return

        self.status_label.config(text=STRINGS["status_restoring"])
        self.restore_button.config(state=tk.DISABLED)
        self.master.update_idletasks()

        try:
            # 既存のセーブデータディレクトリを削除
            save_dir = SAVES / savename
            if save_dir.exists():
                shutil.rmtree(save_dir)

            # バックアップファイルを指定の場所に展開 (更新日時を保持するメソッドを使用)
            unpack_archive_preserving_timestamp(backup_file, SAVES)
            logger.info(f"restore done: {savename}")

            self.load_save_data()  # セーブリストを更新)

        except FileNotFoundError as e:
            logger.error(f"Error during restore: {e}")
            showerror(STRINGS["restore_error_title"],
                      STRINGS["restore_file_not_found_error_msg"].format(e=e))
        except PermissionError as e:
            logger.error(f"Permission error during restore: {e}")
            showerror(STRINGS["restore_error_title"],
                      STRINGS["restore_permission_error_msg"].format(e=e))
        except (shutil.ReadError, zipfile.BadZipFile) as e:
            logger.error(f"Error during restore: {e}")
            showerror(STRINGS["restore_error_title"],
                      STRINGS["restore_bad_zip_error_msg"].format(e=e))
        except Exception as e:
            logger.error(f"Unexpected error during restore: {e}")
            showerror(STRINGS["restore_error_title"],
                      STRINGS["restore_unexpected_error_msg"].format(e=e))
        finally:
            self.status_label.config(text="")
            self.reload()
            self.master.update_idletasks()


def startfile(path: Path):
    try:
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # macOS, Linux
            subprocess.Popen(['open', str(path)])  # macOS
        else:
            showinfo(
                STRINGS["info_title"],
                STRINGS["folder_open_not_supported_msg"].format(path=path))
    except Exception as e:
        showerror(
            STRINGS["error_title"],
            STRINGS["folder_open_error_msg"].format(path=path, e=e))


def unpack_archive_preserving_timestamp(archive_path: Path, extract_dir: Path):
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
                except Exception as e:
                    # タイムスタンプの設定に失敗した場合の警告
                    logger.warning(
                        f"Could not set timestamp for {extracted_member_path}. Error: {e}")
                    # 処理は続行します。
                    pass
            else:
                # 古いZIPファイル等で日時情報が無効な場合は何もしないか、警告を出すことができます。
                logger.warning(
                    f"Invalid date_time for {member_info.filename} in {archive_path}")


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
                # logger.debug(item_path_str)
                parts = item_path_str.split('/')
                if len(parts) >= 2 and parts[1]:
                    return "/".join(parts[:2])
            return None
    except zipfile.BadZipFile:  # Handles corrupted or invalid zip files
        return None
    except Exception:  # Catches other potential file operation errors
        return None


@functools.cache
def cashed_mtime_of_tree(path: Path):
    return mtime_of_tree(path)


def mtime_of_tree(path: Path):
    mtimes = [
        file.stat().st_mtime
        for file in path.rglob('*')
        if file.is_file()
    ]
    if not mtimes:
        msg = STRINGS["mtime_empty_dir_error_msg"]
        raise RuntimeError(msg.format(path=path))
    return max(mtimes)


def iter_savedir() -> Generator[Path, None, None]:
    """セーブデータを走査するジェネレーター"""
    if not SAVES.exists():
        return
    for world in SAVES.iterdir():
        if not world.is_dir():
            continue  # ディレクトリでなければスキップ
        if world.name == 'Empty':
            continue  # 'Empty'フォルダはスキップ
        for savedir in world.iterdir():
            if not savedir.is_dir():
                continue
            if (savedir / 'power.dat').exists():
                yield savedir


def create_backup(savedir: Path, *, if_exists="confirm"):
    # セーブフォルダの更新時刻を取得
    # mtime = save.stat().st_mtime
    mtime = mtime_of_tree(savedir)
    dt = datetime.datetime.fromtimestamp(mtime)
    y, m, d, hh, mm = dt.year, dt.month, dt.day, dt.hour, dt.minute

    suffix = f"{y}{m:02d}{d:02d}T{hh:02d}{mm:02d}"

    # アーカイブ名（.zipなし）
    archive_name_base = BACKUPS / f"{savedir.name}_{suffix}"
    archive_file = archive_name_base.with_suffix('.zip')  # 正しいzipファイル名

    if archive_file.exists():
        if if_exists == "confirm":
            if not askyesno(
                    STRINGS["overwrite_confirm_title"],
                    STRINGS["overwrite_confirm_msg"].format(filename=archive_file.name)):
                return
        elif if_exists == "ignore":
            return
        elif if_exists == "error":
            raise FileExistsError(f"{archive_file.name} already exists.")
        elif if_exists == "overwrite":
            pass
        else:
            raise ValueError(f"invalid if_exist value: {if_exists}")

    shutil.make_archive(str(archive_name_base), 'zip',
                        SAVES, f"{savedir.parent.name}/{savedir.name}",
                        logger=logger)

    logger.info(f"backup created: {archive_file.name}")


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s:%(levelname)s:%(message)s')
    load_i18n_strings()

    root = tk.Tk()
    # ダークテーマを適用するために ThemedTk を使用
    # "equilux" や "arc", "black" など、好みのダークテーマを選択
    # root = ThemedTk(theme="equilux")

    app = Application(master=root)
    app.mainloop()


if __name__ == "__main__":
    main()
