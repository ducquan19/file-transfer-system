#!/usr/bin/env python3
"""
GUI Client for TCP/UDP File Transfer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logic modules (separated from CLI)
from core.tcp_logic import TCPClientLogic
from core.udp_logic import UDPClientLogic


class FileTransferClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transfer Client")
        self.root.geometry("800x600")

        self.connected = False
        self.client = None
        self.download_folder = str(Path.home() / "Downloads")
        self.file_list = []
        self.selected_files = []

        self.create_widgets()

    def create_widgets(self):
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection Settings", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        # Protocol selection
        ttk.Label(conn_frame, text="Protocol:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="TCP")
        protocol_frame = ttk.Frame(conn_frame)
        protocol_frame.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Radiobutton(protocol_frame, text="TCP", variable=self.protocol_var, value="TCP").pack(side="left", padx=5)
        ttk.Radiobutton(protocol_frame, text="UDP", variable=self.protocol_var, value="UDP").pack(side="left", padx=5)

        # Host
        ttk.Label(conn_frame, text="Server Host:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.host_entry = ttk.Entry(conn_frame, width=30)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Port
        ttk.Label(conn_frame, text="Server Port:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.port_entry = ttk.Entry(conn_frame, width=30)
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Download folder
        ttk.Label(conn_frame, text="Download Folder:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        folder_frame = ttk.Frame(conn_frame)
        folder_frame.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.folder_entry = ttk.Entry(folder_frame, width=40)
        self.folder_entry.insert(0, self.download_folder)
        self.folder_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side="left", padx=(5, 0))

        # Connect button
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.grid(row=4, column=0, columnspan=2, pady=10)

        # File List Frame
        file_frame = ttk.LabelFrame(self.root, text="Available Files", padding=10)
        file_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # File listbox with scrollbar
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_listbox.yview)

        # Download button
        self.download_btn = ttk.Button(file_frame, text="Download Selected Files",
                                       command=self.download_selected, state="disabled")
        self.download_btn.pack(pady=5)

        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill="both", padx=10, pady=5)

        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, state="disabled")
        self.status_text.pack(fill="both", expand=True)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder)
        if folder:
            self.download_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)

    def log_status(self, message):
        self.status_text.config(state="normal")
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state="disabled")

    def connect_to_server(self):
        if self.connected:
            messagebox.showinfo("Info", "Already connected to server")
            return

        protocol = self.protocol_var.get()
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()

        if not host or not port:
            messagebox.showerror("Error", "Please enter host and port")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        self.download_folder = self.folder_entry.get().strip()
        if not os.path.exists(self.download_folder):
            try:
                os.makedirs(self.download_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create download folder: {e}")
                return

        self.log_status(f"Connecting to {protocol} server at {host}:{port}...")

        # Disable connection controls
        self.connect_btn.config(state="disabled")
        self.host_entry.config(state="disabled")
        self.port_entry.config(state="disabled")
        self.protocol_var.set(protocol)  # Lock protocol

        # Connect in separate thread
        thread = threading.Thread(target=self._connect_thread, args=(protocol, host, port))
        thread.daemon = True
        thread.start()

    def _connect_thread(self, protocol, host, port):
        try:
            if protocol == "TCP":
                self._connect_tcp(host, port)
            else:
                self._connect_udp(host, port)
        except Exception as e:
            self.root.after(0, lambda: self.log_status(f"Connection error: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Connection Error", str(e)))
            self.root.after(0, self._reset_connection)

    def _connect_tcp(self, host, port):
        try:
            print("DEBUG: Starting TCP connection...")
            self.root.after(0, lambda: self.log_status("Connecting to TCP server..."))

            # Use TCP logic layer
            self.client = TCPClientLogic(
                host, port, self.download_folder,
                on_log=lambda msg: self.root.after(0, lambda: self.log_status(msg))
            )

            success = self.client.connect()
            if not success:
                raise Exception("Failed to connect to server")

            # Get file list
            files = []
            for entry in self.client.file_list:
                if " - " in entry:
                    name, size = entry.split(" - ", 1)
                    files.append((name.strip(), size.strip()))

            print(f"DEBUG: Parsed {len(files)} files")
            self.file_list = files
            self.root.after(0, self._update_file_list)
            self.root.after(0, lambda: self.log_status(f"Connected to TCP server. {len(files)} files available."))
            self.connected = True
            print("DEBUG: Connection successful!")

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"DEBUG ERROR: {error_detail}")
            self.root.after(0, lambda: self.log_status(f"Error: {e}"))
            raise Exception(f"TCP connection failed: {e}")

    def _connect_udp(self, host, port):
        try:
            # Use UDP logic layer
            client = UDPClientLogic(
                host, port, self.download_folder,
                on_log=lambda msg: self.root.after(0, lambda: self.log_status(msg))
            )

            success = client.connect()
            if not success:
                raise Exception("Failed to connect to server")

            # Parse file list
            files = []
            for entry in client.file_list:
                if " - " in entry:
                    name, size = entry.split(" - ", 1)
                    files.append((name.strip(), size.strip()))

            self.file_list = files
            self.root.after(0, self._update_file_list)
            self.root.after(0, lambda: self.log_status(f"Connected to UDP server. {len(files)} files available."))
            self.connected = True

        except Exception as e:
            raise Exception(f"UDP connection failed: {e}")

    def _update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for name, size in self.file_list:
            self.file_listbox.insert(tk.END, f"{name} ({size})")

        self.download_btn.config(state="normal")

    def _reset_connection(self):
        self.connect_btn.config(state="normal")
        self.host_entry.config(state="normal")
        self.port_entry.config(state="normal")

    def download_selected(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select files to download")
            return

        selected_files = [self.file_list[i][0] for i in selection]

        protocol = self.protocol_var.get()
        host = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip())

        self.log_status(f"Starting download of {len(selected_files)} file(s)...")
        self.download_btn.config(state="disabled")

        # Download in separate thread
        thread = threading.Thread(target=self._download_thread,
                                 args=(protocol, host, port, selected_files))
        thread.daemon = True
        thread.start()

    def _download_thread(self, protocol, host, port, files):
        try:
            if protocol == "TCP":
                self._download_tcp(host, port, files)
            else:
                self._download_udp(host, port, files)

            self.root.after(0, lambda: self.log_status(f"Download completed successfully!"))
            self.root.after(0, lambda: messagebox.showinfo("Success",
                f"Downloaded {len(files)} file(s) to {self.download_folder}"))
        except Exception as e:
            self.root.after(0, lambda: self.log_status(f"Download error: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Download Error", str(e)))
        finally:
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

    def _download_tcp(self, host, port, files):
        # Use TCP logic layer
        client = TCPClientLogic(
            host, port, self.download_folder,
            on_log=lambda msg: self.root.after(0, lambda: self.log_status(msg))
        )

        success = client.connect()
        if not success:
            raise Exception("Failed to connect for download")

        for filename in files:
            client.download_file(filename)

        client.disconnect()

    def _download_udp(self, host, port, files):
        # Use UDP logic layer
        client = UDPClientLogic(
            host, port, self.download_folder,
            on_log=lambda msg: self.root.after(0, lambda: self.log_status(msg))
        )

        success = client.connect()
        if not success:
            raise Exception("Failed to connect for download")

        for filename in files:
            client.download_file(filename)


def main():
    root = tk.Tk()
    app = FileTransferClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
