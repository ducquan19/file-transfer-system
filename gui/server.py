#!/usr/bin/env python3
"""
GUI Server for TCP/UDP File Transfer
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logic modules (separated from CLI)
from core.tcp_logic import TCPServerLogic
from core.udp_logic import UDPServerLogic


class FileTransferServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transfer Server")
        self.root.geometry("800x600")

        self.server = None
        self.running = False
        self.resource_folder = str(Path.home())

        self.create_widgets()

    def create_widgets(self):
        # Server Settings Frame
        settings_frame = ttk.LabelFrame(self.root, text="Server Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)

        # Protocol selection
        ttk.Label(settings_frame, text="Protocol:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="TCP")
        protocol_frame = ttk.Frame(settings_frame)
        protocol_frame.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Radiobutton(protocol_frame, text="TCP", variable=self.protocol_var,
                       value="TCP", command=self.update_default_port).pack(side="left", padx=5)
        ttk.Radiobutton(protocol_frame, text="UDP", variable=self.protocol_var,
                       value="UDP", command=self.update_default_port).pack(side="left", padx=5)

        # Host
        ttk.Label(settings_frame, text="Host:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.host_entry = ttk.Entry(settings_frame, width=30)
        self.host_entry.insert(0, "0.0.0.0")
        self.host_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Port
        ttk.Label(settings_frame, text="Port:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.port_entry = ttk.Entry(settings_frame, width=30)
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Resource folder
        ttk.Label(settings_frame, text="Resource Folder:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        folder_frame = ttk.Frame(settings_frame)
        folder_frame.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.folder_entry = ttk.Entry(folder_frame, width=40)
        self.folder_entry.insert(0, self.resource_folder)
        self.folder_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side="left", padx=(5, 0))

        # Control buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        self.start_btn = ttk.Button(button_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(button_frame, text="Stop Server", command=self.stop_server, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # File List Frame
        file_frame = ttk.LabelFrame(self.root, text="Shared Files", padding=10)
        file_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # File listbox with scrollbar
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_listbox.yview)

        # Refresh button
        ttk.Button(file_frame, text="Refresh File List", command=self.refresh_file_list).pack(pady=5)

        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="Server Log", padding=10)
        status_frame.pack(fill="both", padx=10, pady=5)

        self.status_text = scrolledtext.ScrolledText(status_frame, height=10, state="disabled")
        self.status_text.pack(fill="both", expand=True)

        # Initial file list refresh
        self.refresh_file_list()

    def update_default_port(self):
        if not self.running:
            protocol = self.protocol_var.get()
            self.port_entry.delete(0, tk.END)
            if protocol == "TCP":
                self.port_entry.insert(0, "5000")
            else:
                self.port_entry.insert(0, "6000")

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.resource_folder)
        if folder:
            self.resource_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.refresh_file_list()

    def refresh_file_list(self):
        folder = self.folder_entry.get().strip()
        self.file_listbox.delete(0, tk.END)

        if not os.path.exists(folder):
            self.file_listbox.insert(tk.END, "Folder does not exist")
            return

        try:
            files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            if not files:
                self.file_listbox.insert(tk.END, "No files in folder")
            else:
                for f in files:
                    size = os.path.getsize(os.path.join(folder, f))
                    self.file_listbox.insert(tk.END, f"{f} ({size} bytes)")
        except Exception as e:
            self.file_listbox.insert(tk.END, f"Error: {e}")

    def log_status(self, message):
        self.status_text.config(state="normal")
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state="disabled")

    def start_server(self):
        if self.running:
            messagebox.showinfo("Info", "Server is already running")
            return

        protocol = self.protocol_var.get()
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        folder = self.folder_entry.get().strip()

        if not host or not port:
            messagebox.showerror("Error", "Please enter host and port")
            return

        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid resource folder")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        self.resource_folder = folder

        # Disable settings
        self.start_btn.config(state="disabled")
        self.host_entry.config(state="disabled")
        self.port_entry.config(state="disabled")
        self.folder_entry.config(state="disabled")
        for child in self.root.winfo_children():
            if isinstance(child, ttk.LabelFrame) and child.cget("text") == "Server Settings":
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.Frame):
                        for rb in widget.winfo_children():
                            if isinstance(rb, ttk.Radiobutton):
                                rb.config(state="disabled")

        self.stop_btn.config(state="normal")
        self.running = True

        self.log_status(f"Starting {protocol} server on {host}:{port}...")
        self.log_status(f"Resource folder: {folder}")

        # Start server in separate thread
        thread = threading.Thread(target=self._start_server_thread, args=(protocol, host, port, folder))
        thread.daemon = True
        thread.start()

    def _start_server_thread(self, protocol, host, port, folder):
        try:
            if protocol == "TCP":
                # Use TCP logic layer
                self.server = TCPServerLogic(host, port, folder, on_log=self.log_status)
                success = self.server.start()
                if not success:
                    raise Exception("Failed to start TCP server")
            else:
                # Use UDP logic layer
                self.server = UDPServerLogic(host, port, folder, on_log=self.log_status)
                success = self.server.start()
                if not success:
                    raise Exception("Failed to start UDP server")

        except Exception as e:
            self.root.after(0, lambda: self.log_status(f"Server error: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Server Error", str(e)))
            self.root.after(0, self._reset_server_state)

    def stop_server(self):
        if not self.running:
            return

        self.log_status("Stopping server...")

        try:
            if self.server:
                self.server.stop()
        except Exception as e:
            self.log_status(f"Error stopping server: {e}")

        self._reset_server_state()
        self.log_status("Server stopped")
        messagebox.showinfo("Info", "Server stopped successfully")

    def _reset_server_state(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.host_entry.config(state="normal")
        self.port_entry.config(state="normal")
        self.folder_entry.config(state="normal")

        # Re-enable protocol radio buttons
        for child in self.root.winfo_children():
            if isinstance(child, ttk.LabelFrame) and child.cget("text") == "Server Settings":
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.Frame):
                        for rb in widget.winfo_children():
                            if isinstance(rb, ttk.Radiobutton):
                                rb.config(state="normal")


def main():
    root = tk.Tk()
    app = FileTransferServerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
