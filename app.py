import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

class CTkMessage(ctk.CTkToplevel):
    def __init__(self, title, message, yes_no=False):
        super().__init__()
        self.title(title)
        self.geometry("450x250")
        self.result = False
        
        self.lbl = ctk.CTkLabel(self, text=message, wraplength=400)
        self.lbl.pack(pady=(20, 10), padx=20, expand=True)
        
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=20)
        
        if yes_no:
            self.yes_btn = ctk.CTkButton(self.btn_frame, text="Yes", width=100, command=self.on_yes)
            self.yes_btn.pack(side="left", padx=10)
            self.no_btn = ctk.CTkButton(self.btn_frame, text="No", width=100, command=self.on_no, fg_color="#C62828", hover_color="#B71C1C")
            self.no_btn.pack(side="left", padx=10)
        else:
            self.ok_btn = ctk.CTkButton(self.btn_frame, text="OK", width=100, command=self.on_yes)
            self.ok_btn.pack()
            
        self.transient(self.master)
        self.grab_set()
        
    def on_yes(self):
        self.result = True
        self.destroy()
        
    def on_no(self):
        self.result = False
        self.destroy()

def safe_showinfo(title, msg):
    d = CTkMessage(title, msg, yes_no=False)
    d.wait_window()

def safe_askyesno(title, msg):
    d = CTkMessage(title, msg, yes_no=True)
    d.wait_window()
    return d.result

from core import ComicSorterEngine, load_config, save_config

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Comic Sorter")
        self.geometry("800x600")
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header = ctk.CTkLabel(self, text="Comic Sorter", font=ctk.CTkFont(size=28, weight="bold"))
        self.header.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Controls Frame
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.controls_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Mode Selection
        self.mode_var = tk.IntVar(value=1)
        self.radio_new = ctk.CTkRadioButton(self.controls_frame, text="1. Sort New Library", variable=self.mode_var, value=1, command=self.update_ui)
        self.radio_new.grid(row=0, column=0, padx=10, pady=15, sticky="ew")
        self.radio_resort = ctk.CTkRadioButton(self.controls_frame, text="2. Resort Existing", variable=self.mode_var, value=2, command=self.update_ui)
        self.radio_resort.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        self.radio_merge = ctk.CTkRadioButton(self.controls_frame, text="3. Smart-Merge", variable=self.mode_var, value=3, command=self.update_ui)
        self.radio_merge.grid(row=0, column=2, padx=10, pady=15, sticky="ew")
        
        # Paths Frame
        self.paths_frame = ctk.CTkFrame(self.controls_frame)
        self.paths_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        self.paths_frame.grid_columnconfigure(1, weight=1)
        
        self.source_label = ctk.CTkLabel(self.paths_frame, text="Source Dir:")
        self.source_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.source_entry = ctk.CTkEntry(self.paths_frame, state="disabled")
        self.source_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.source_btn = ctk.CTkButton(self.paths_frame, text="Browse", width=80, command=self.browse_source)
        self.source_btn.grid(row=0, column=2, padx=10, pady=10)
        
        self.dest_label = ctk.CTkLabel(self.paths_frame, text="Dest Dir:")
        self.dest_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.dest_entry = ctk.CTkEntry(self.paths_frame, state="disabled")
        self.dest_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.dest_btn = ctk.CTkButton(self.paths_frame, text="Browse", width=80, command=self.browse_dest)
        self.dest_btn.grid(row=1, column=2, padx=10, pady=10)
        
        # Checkbox Frame
        self.options_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="e")
        
        self.dry_run_var = tk.BooleanVar(value=False)
        self.chk_dry = ctk.CTkCheckBox(self.options_frame, text="Simulate (Dry-Run)", variable=self.dry_run_var)
        self.chk_dry.pack()

        # Start and Cancel Buttons
        self.btn_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        self.btn_frame.grid_columnconfigure(0, weight=2)
        self.btn_frame.grid_columnconfigure(1, weight=1)
        
        self.start_btn = ctk.CTkButton(self.btn_frame, text="START SORTING", command=self.start_sorting, height=45, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="CANCEL", command=self.cancel_sorting, height=45, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#C62828", hover_color="#B71C1C", state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        
        # Console Log
        self.log_box = ctk.CTkTextbox(self, state="disabled", font=ctk.CTkFont(family="Courier", size=13))
        
        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        
        self.log_queue = queue.Queue()
        self.is_running = False
        self.engine = None
        self.last_dir = os.path.expanduser("~")
        
        self.update_ui()
        self.check_queue()
        
    def _set_entry(self, entry, text):
        entry.configure(state="normal")
        entry.delete(0, 'end')
        entry.insert(0, text)
        entry.configure(state="disabled")
        
    def update_ui(self):
        mode = self.mode_var.get()
        if mode == 1:
            self.source_label.configure(text="Unsorted Source:")
            self.dest_label.configure(text="New Library Target:")
        elif mode == 2:
            self.source_label.configure(text="(In-Place Mode):")
            self._set_entry(self.source_entry, "*Using Dest Dir As Source*")
            self.source_btn.configure(state="disabled")
            self.dest_label.configure(text="Target Library to Resort:")
        elif mode == 3:
            self.source_label.configure(text="Unsorted Source:")
            self.source_btn.configure(state="normal")
            if self.source_entry.get() == "*Using Dest Dir As Source*":
                self._set_entry(self.source_entry, "")
            self.dest_label.configure(text="Target Library to Merge Into:")
            
        if mode != 2:
            self.source_btn.configure(state="normal")
            
    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder", initialdir=self.last_dir)
        if folder:
            self.last_dir = os.path.dirname(folder)
            self._set_entry(self.source_entry, folder)
            
    def browse_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Library", initialdir=self.last_dir)
        if folder:
            self.last_dir = os.path.dirname(folder)
            self._set_entry(self.dest_entry, folder)
            
    def write_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        
    def check_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.write_log(msg)
        except queue.Empty:
            pass
        self.after(100, self.check_queue)
        
    def thread_safe_ask(self, func, *args, **kwargs):
        """ Runs a UI dialog blockingly safely from a background thread. """
        result_container = []
        event = threading.Event()
        def ui_call():
            try:
                res = func(*args, **kwargs)
                result_container.append(res)
            except Exception as e:
                result_container.append(None)
            finally:
                event.set()
        self.after(0, ui_call)
        event.wait()
        return result_container[0] if result_container else None

    def _ui_ask_api(self):
        dialog = ctk.CTkInputDialog(text="Missing semantic match. Enter ComicVine API Key\n(or leave blank to ignore):", title="Missing Metadata")
        return dialog.get_input()

    def cancel_sorting(self):
        if self.is_running and self.engine:
            self.cancel_btn.configure(state="disabled")
            self.write_log("\n[!] Cancelling sorting process... (Will stop after current file)")
            self.engine.aborted = True

    def start_sorting(self):
        if self.is_running:
            return
            
        mode = self.mode_var.get()
        dest_dir = self.dest_entry.get()
        source_dir = self.source_entry.get() if mode != 2 else dest_dir
        
        if not dest_dir or (mode != 2 and (not source_dir or source_dir == "*Using Dest Dir As Source*")):
            safe_showinfo("Error", "Please select all required directories.")
            return
            
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.log_box.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.progress_bar.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_bar.set(0)
        self.write_log(f"\n[{'='*40}]")
        self.write_log(f"--- Starting Sort Operation (Mode {mode}) ---")
        
        config = load_config()
        api_key = config.get('comicvine_api_key')
        is_move_operation = (mode == 2)
        
        callbacks = {
            'log': lambda msg: self.log_queue.put(msg),
            'on_missing_api_key': lambda: self.thread_safe_ask(self._ui_ask_api),
            'on_rate_limit': lambda: self.thread_safe_ask(lambda: safe_askyesno("Rate Limit", "ComicVine API rate limit exceeded.\n\nContinue strictly offline?")),
            'on_failure': lambda error, context: self.thread_safe_ask(lambda: safe_askyesno("Error", f"A non-fatal error occurred:\n{context}\n\n{error}\n\nContinue skipping this file?")),
            'on_trash_prompt': lambda n: True if n == -1 else self.thread_safe_ask(lambda: safe_askyesno("Cleanup", f"Do you want to move the {n} original unsorted files to the Trash?")),
            'on_progress': lambda c, t: self.after(0, lambda: self.progress_bar.set(c / t if t > 0 else 0)),
            'on_finish': self.on_finish
        }
        
        self.engine = ComicSorterEngine(callbacks)
        
        def run_thread():
            if mode in [2, 3]:
                self.log_queue.put("Scanning existing library concepts via ML...")
                import scanner
                scanner.scan_library(dest_dir)
            try:
                is_dry_run = self.dry_run_var.get()
                self.engine.process_comics(source_dir, dest_dir, api_key, is_move_operation, mode=mode, dry_run=is_dry_run)
            except Exception as e:
                self.log_queue.put(f"[!] Uncaught thread error: {e}")
            
        threading.Thread(target=run_thread, daemon=True).start()
        
    def on_finish(self):
        def _finish_ui():
            self.is_running = False
            self.start_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            msg = "Sorting process completed or cancelled!" if (self.engine and self.engine.aborted) else "Sorting process completed successfully!"
            safe_showinfo("Done", msg)
            self.write_log(f"[{'='*40}]\n")
            self.progress_bar.grid_remove()
            self.log_box.grid_remove()
            self.engine = None
        self.after(0, _finish_ui)

if __name__ == "__main__":
    app = App()
    app.mainloop()
