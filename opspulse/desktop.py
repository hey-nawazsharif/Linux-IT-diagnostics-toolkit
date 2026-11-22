"""Minimal local-only desktop UI for OpsPulse, using Python's Tk toolkit.

The application does not start scans until the user clicks Run health check.
It does not auto-upload files, change system settings, require admin privileges,
create startup entries, or run a network probe by default.
"""
from __future__ import annotations

import json
from pathlib import Path
import queue
import sys
import threading
import webbrowser

from .report_io import write_report


def collect_local() -> dict:
    if sys.platform == "linux":
        from .collector import collect
        return collect()
    from .portable import collect_portable
    return collect_portable()


class DesktopApp:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.root.title("OpsPulse | Local System Diagnostics")
        self.root.geometry("930x650")
        self.root.minsize(720, 470)
        self.report = None
        self.saved_page = None
        self.queue = queue.Queue()
        self.scan_in_progress = False

        self._style = ttk.Style(root)
        if "clam" in self._style.theme_names():
            self._style.theme_use("clam")
        self._style.configure("TButton", padding=(12, 9))
        self._style.configure("Treeview", rowheight=30)
        self._style.configure("Treeview.Heading", font=("TkDefaultFont", 10, "bold"))
        self._style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        self._style.configure("Status.TLabel", font=("TkDefaultFont", 10))

        outer = ttk.Frame(root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="OpsPulse", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Local system health check   •   Read-only   •   No account   •   No automatic network probes",
        ).pack(anchor="w", pady=(2, 15))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        self.run_button = ttk.Button(toolbar, text="Run health check", command=self.start_scan)
        self.run_button.pack(side="left", padx=(0, 9))
        self.save_button = ttk.Button(toolbar, text="Save HTML + JSON", command=self.save_report, state="disabled")
        self.save_button.pack(side="left", padx=(0, 9))
        self.open_button = ttk.Button(toolbar, text="Open saved HTML", command=self.open_saved, state="disabled")
        self.open_button.pack(side="left")

        self.status_var = tk.StringVar(value="Ready. No diagnostics have been run.")
        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", wraplength=850).pack(
            anchor="w", fill="x", pady=(5, 12)
        )

        columns = ("status", "value")
        tree_section = ttk.Frame(outer)
        tree_section.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_section, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Diagnostic check")
        self.tree.heading("status", text="Status")
        self.tree.heading("value", text="Result")
        self.tree.column("#0", width=325, minwidth=180, stretch=True)
        self.tree.column("status", width=125, minwidth=100, stretch=False)
        self.tree.column("value", width=205, minwidth=135, stretch=True)
        scrollbar = ttk.Scrollbar(tree_section, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.describe_selected)

        details_header = ttk.Frame(outer)
        details_header.pack(fill="x", pady=(15, 5))
        ttk.Label(details_header, text="Details and safe follow-up", style="Status.TLabel").pack(anchor="w")
        self.detail = tk.Text(outer, height=6, wrap="word", state="disabled",
                              background="#f4f6f7", foreground="#28343b", relief="flat",
                              font=("TkDefaultFont", 10), padx=11, pady=9)
        self.detail.pack(fill="x")
        self.set_detail("Click Run health check to collect a point-in-time, local-only report.")

        ttk.Label(
            outer,
            text="No repairs, changes, scanning of other computers or automatic uploads. "
                 "Reports can contain operational information; review before sharing.",
            foreground="#596975",
            wraplength=850,
        ).pack(anchor="w", pady=(12, 0))
        self.root.after(120, self.poll_queue)

    def set_detail(self, value: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", value)
        self.detail.configure(state="disabled")

    def start_scan(self) -> None:
        if self.scan_in_progress:
            return
        self.scan_in_progress = True
        self.run_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.saved_page = None
        self.report = None
        self.tree.delete(*self.tree.get_children())
        self.set_detail("Collecting system counters locally. No network probes are being made.")
        self.status_var.set("Running local diagnostics…")
        def worker():
            try:
                self.queue.put(("report", collect_local()))
            except Exception as exc:
                self.queue.put(("error", f"{type(exc).__name__}: {exc}"))
        threading.Thread(target=worker, daemon=True).start()

    def poll_queue(self) -> None:
        from tkinter import messagebox
        try:
            while True:
                kind, data = self.queue.get_nowait()
                self.scan_in_progress = False
                self.run_button.configure(state="normal")
                if kind == "error":
                    self.status_var.set("Could not collect diagnostics. See error details.")
                    self.set_detail(str(data))
                    messagebox.showerror("OpsPulse diagnostics error", str(data), parent=self.root)
                else:
                    self.report = data
                    self.save_button.configure(state="normal")
                    for index, row in enumerate(self.report["checks"]):
                        self.tree.insert("", "end", iid=str(index), text=row["label"],
                                         values=(row["status"].upper(), row["value"]))
                    summary = self.report["summary"]
                    self.status_var.set(
                        f"{self.report['mode']} • "
                        f"{summary['critical']} critical • {summary['warn']} attention • "
                        f"{summary['pass']} healthy • {summary['skip']} not verified"
                    )
                    self.set_detail(
                        "Run complete. Select a diagnostic to review findings and next steps. "
                        "Nothing was saved or uploaded."
                    )
        except queue.Empty:
            pass
        # Tk calls happen only on the GUI thread; workers never touch widgets.
        if self.root.winfo_exists():
            self.root.after(120, self.poll_queue)

    def describe_selected(self, _event=None) -> None:
        if not self.report:
            return
        selected = self.tree.selection()
        if not selected:
            return
        item = self.report["checks"][int(selected[0])]
        lines = [item["label"], item["value"], "", item["detail"]]
        for suggestion in self.report.get("action_plan", []):
            if suggestion["check_key"] == item["key"]:
                lines.extend(["", "Suggested follow-up (manual):"])
                lines.extend(f"  {i}. {step}" for i, step in enumerate(suggestion["next_steps"], 1))
                break
        self.set_detail("\n".join(lines))

    def save_report(self) -> None:
        from tkinter import filedialog, messagebox
        if not self.report:
            return
        directory = filedialog.askdirectory(
            parent=self.root, title="Choose a local folder for the report", mustexist=True
        )
        if not directory:
            return
        try:
            json_path, page = write_report(self.report, Path(directory))
        except (OSError, UnicodeError, ValueError) as exc:
            messagebox.showerror("Could not save report", str(exc), parent=self.root)
            return
        self.saved_page = page
        self.open_button.configure(state="normal")
        self.status_var.set(f"Report saved locally: {json_path.name} and {page.name}")
        messagebox.showinfo(
            "Report saved",
            "Saved report.json and index.html to your chosen folder. "
            "Review them before uploading or sharing.",
            parent=self.root,
        )

    def open_saved(self) -> None:
        if self.saved_page and self.saved_page.exists():
            webbrowser.open(self.saved_page.resolve().as_uri())


def main() -> int:
    try:
        import tkinter as tk
        root = tk.Tk()
    except (ImportError, RuntimeError, OSError) as exc:
        print(f"OpsPulse desktop UI unavailable: {exc}. Try python -m opspulse.", file=sys.stderr)
        return 2
    DesktopApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
