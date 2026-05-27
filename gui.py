#!/usr/bin/env python3
"""Tkinter GUI for converting Wisconsin SOA PDFs to CSV."""

import csv
import glob
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

from parse_wi_soa import HEADER, ParseError, extract_text, parse_forms
from validate import find_pairs


class ConvertTab:
    def __init__(self, parent, progress, status, eta_label):
        self.parent = parent
        self.progress = progress
        self.status = status
        self.eta_label = eta_label
        self.rows = []
        self.had_error = False

        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(btn_frame, text="Load PDFs…", command=self._pick_files).pack(
            side="left", expand=True, fill="x", padx=(0, 3)
        )
        ttk.Button(btn_frame, text="Load Folder…", command=self._pick_folder).pack(
            side="left", expand=True, fill="x", padx=(3, 0)
        )

        self.save_btn = ttk.Button(frame, text="Save as CSV…", command=self._save)
        self.save_btn.pack(fill="x", pady=(0, 5))
        self.save_btn.config(state="disabled")

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select SOA PDF files",
            filetypes=[("PDF files", "*.pdf")],
        )
        if paths:
            self._convert(list(paths))

    def _pick_folder(self):
        directory = filedialog.askdirectory(title="Select folder of SOA PDFs")
        if not directory:
            return
        paths = sorted(glob.glob(os.path.join(directory, "*.pdf")))
        if not paths:
            _clear(self.status)
            _log(self.status, f"No PDF files found in {os.path.basename(directory)}/")
            return
        self._convert(paths)

    def _convert(self, paths):
        self.rows = []
        self.had_error = False
        self.save_btn.config(state="disabled", text="Save as CSV…")
        self.progress.reset(len(paths))
        self.eta_label.config(text="")
        _clear(self.status)
        threading.Thread(target=self._do_convert, args=(paths,), daemon=True).start()

    def _do_convert(self, paths):
        t0 = time.monotonic()
        for i, path in enumerate(paths):
            name = os.path.basename(path)
            try:
                text = extract_text(path)
                rows = parse_forms(text, source=name)
                self.rows.extend(rows)
                self.parent.after(0, self._tick, True, i + 1, len(paths), t0)
                self.parent.after(0, _log, self.status, f"OK: {name} ({len(rows)} rows)")
            except Exception as e:
                self.parent.after(0, self._tick, False, i + 1, len(paths), t0)
                self.parent.after(0, _log, self.status, f"FAILED: {name} — {e}")
                self.had_error = True
                self.parent.after(0, self._convert_done, i + 1, len(paths), t0)
                return

        self.parent.after(0, self._convert_done, len(paths), len(paths), t0)

    def _tick(self, success, done, total, t0):
        self.progress.add(success)
        self.eta_label.config(text=_eta_text(done, total, t0))

    def _convert_done(self, completed, total, t0):
        elapsed = time.monotonic() - t0
        self.eta_label.config(text=f"Completed {completed}/{total} in {_fmt_duration(elapsed)}")
        if self.had_error:
            if self.rows:
                self.save_btn.config(state="normal", text="Save Partial CSV…")
                _log(self.status, f"\nStopped. {len(self.rows)} rows from {completed - 1}/{total} files.")
            else:
                _log(self.status, f"\nFailed on first file. Nothing to save.")
        else:
            self.save_btn.config(state="normal")
            _log(self.status, f"\nDone! {len(self.rows)} rows from {total} files ready to save.")

    def _save(self):
        path = filedialog.asksaveasfilename(
            title="Save CSV as",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(HEADER)
                for row in self.rows:
                    writer.writerow(row)
            _log(self.status, f"Saved {len(self.rows)} rows to {os.path.basename(path)}")
        except OSError as e:
            _log(self.status, f"Failed to write: {e}")


class ValidateTab:
    def __init__(self, parent, progress, status, eta_label):
        self.parent = parent
        self.progress = progress
        self.status = status
        self.eta_label = eta_label

        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=(
                "To verify this tool's output, manually convert a few PDFs to CSV\n"
                "by hand, then select the folder containing both files. The tool\n"
                "will parse each PDF and compare against your hand-made CSV.\n\n"
                "Filenames must match (e.g. 2025soaadams.pdf and 2025soaadams.csv)."
            ),
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        ttk.Button(
            frame, text="Select Folder of PDF/CSV Pairs…", command=self._pick_folder
        ).pack(fill="x")

    def _pick_folder(self):
        directory = filedialog.askdirectory(title="Select folder with PDF/CSV pairs")
        if not directory:
            return

        pairs = find_pairs(directory)
        if not pairs:
            _clear(self.status)
            _log(self.status, f"No PDF/CSV pairs found in {os.path.basename(directory)}/")
            return

        _clear(self.status)
        self.progress.reset(len(pairs))
        self.eta_label.config(text="")
        threading.Thread(target=self._do_validate, args=(pairs,), daemon=True).start()

    def _do_validate(self, pairs):
        t0 = time.monotonic()
        failures = 0
        for i, (name, pdf_path, csv_path) in enumerate(pairs):
            try:
                with open(csv_path) as f:
                    reader = csv.reader(f)
                    expected_header = next(reader)
                    expected_rows = list(reader)

                text = extract_text(pdf_path)
                actual_rows = parse_forms(text, source=name)

                if expected_header != HEADER:
                    self.parent.after(0, _log, self.status, f"FAIL: {name} — header mismatch")
                    failures += 1
                elif len(actual_rows) != len(expected_rows):
                    self.parent.after(
                        0, _log, self.status,
                        f"FAIL: {name} — got {len(actual_rows)} rows, "
                        f"expected {len(expected_rows)}",
                    )
                    failures += 1
                else:
                    mismatches = []
                    total = 0
                    for ri, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
                        for ci, (a, e) in enumerate(zip(actual, expected)):
                            total += 1
                            if a != e:
                                col = HEADER[ci] if ci < len(HEADER) else f"col {ci}"
                                mismatches.append(f"    row {ri+1}, {col}: {a!r} vs {e!r}")
                    if mismatches:
                        matched = total - len(mismatches)
                        detail = "\n".join(mismatches[:5])
                        if len(mismatches) > 5:
                            detail += f"\n    ... and {len(mismatches) - 5} more"
                        self.parent.after(
                            0, _log, self.status,
                            f"FAIL: {name} — {matched}/{total} cells matched\n{detail}",
                        )
                        failures += 1
                    else:
                        self.parent.after(0, self._tick, True, i + 1, len(pairs), t0)
                        self.parent.after(0, _log, self.status, f"OK: {name} ({total} cells match)")
                        continue
            except Exception as e:
                self.parent.after(0, _log, self.status, f"FAIL: {name} — {e}")

            failures += 1
            self.parent.after(0, self._tick, False, i + 1, len(pairs), t0)

        elapsed = time.monotonic() - t0
        self.parent.after(0, self.eta_label.config, {"text": f"Completed {len(pairs)}/{len(pairs)} in {_fmt_duration(elapsed)}"})
        if failures:
            self.parent.after(0, _log, self.status, f"\n{failures}/{len(pairs)} files failed.")
        else:
            self.parent.after(0, _log, self.status, f"\nAll {len(pairs)} files validated OK.")

    def _tick(self, success, done, total, t0):
        self.progress.add(success)
        self.eta_label.config(text=_eta_text(done, total, t0))


class SegmentBar:
    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, height=20, bg="#e0e0e0", highlightthickness=0)
        self.segments = []
        self.total = 0

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def reset(self, total):
        self.total = total
        self.segments = []
        self.canvas.delete("all")

    def add(self, success):
        self.segments.append(success)
        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        if not self.total:
            return
        w = self.canvas.winfo_width() or 400
        h = self.canvas.winfo_height() or 20
        seg_w = w / self.total
        for i, ok in enumerate(self.segments):
            color = "#4caf50" if ok else "#e53935"
            self.canvas.create_rectangle(
                i * seg_w, 0, (i + 1) * seg_w, h, fill=color, outline=""
            )


def _fmt_duration(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def _eta_text(done, total, t0):
    elapsed = time.monotonic() - t0
    rate = done / elapsed
    remaining = (total - done) / rate
    return f"{done}/{total} — {rate:.1f} files/sec — {_fmt_duration(remaining)} remaining"


def _log(status, msg):
    status.config(state="normal")
    status.insert("end", msg + "\n")
    status.see("end")
    status.config(state="disabled")


def _clear(status):
    status.config(state="normal")
    status.delete("1.0", "end")
    status.config(state="disabled")


def main():
    root = tk.Tk()
    root.title("WI Statement of Assessment → CSV")
    root.resizable(False, False)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    bottom = ttk.Frame(root, padding=(10, 5, 10, 10))
    bottom.pack(fill="x")

    eta_label = ttk.Label(bottom, text="")
    eta_label.pack(fill="x")

    progress = SegmentBar(bottom)
    progress.pack(fill="x", pady=(0, 5))

    status = tk.Text(bottom, height=10, width=60, state="disabled")
    status.pack(fill="x")

    convert_frame = ttk.Frame(notebook)
    validate_frame = ttk.Frame(notebook)
    notebook.add(convert_frame, text="Convert")
    notebook.add(validate_frame, text="Validate")

    ConvertTab(convert_frame, progress, status, eta_label)
    ValidateTab(validate_frame, progress, status, eta_label)

    root.mainloop()


if __name__ == "__main__":
    main()
