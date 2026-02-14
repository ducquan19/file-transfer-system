"""
TCP Logic Layer - Separated from CLI interface
Provides core TCP functionality for GUI or other interfaces
"""

import socket
import os
from threading import Thread
import threading


class TCPServerLogic:
    """Pure TCP server logic without CLI dependencies"""

    def __init__(self, host, port, folder_path, on_log=None):
        self.host = host
        self.port = port
        self.folder_path = folder_path
        self.on_log = on_log or (lambda msg: print(msg))
        self.running = False
        self.server_socket = None
        self.clients = []

    def log(self, message):
        """Send log message to callback"""
        self.on_log(message)

    def start(self):
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            self.running = True

            self.log(f"Server started on {self.host}:{self.port}")

            # Start accepting clients in background
            accept_thread = Thread(target=self._accept_clients, daemon=True)
            accept_thread.start()

            return True
        except Exception as e:
            self.log(f"Failed to start server: {e}")
            return False

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.log("Server stopped")

    def get_file_list(self):
        """Get list of available files"""
        try:
            files = [
                f"{f} - {os.path.getsize(os.path.join(self.folder_path, f))}B"
                for f in os.listdir(self.folder_path)
                if os.path.isfile(os.path.join(self.folder_path, f))
            ]
            return files
        except Exception as e:
            self.log(f"Error getting file list: {e}")
            return []

    def _accept_clients(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                # Accept 5 connections from one client
                client_sockets = []
                for i in range(5):
                    if not self.running:
                        break
                    client_socket, address = self.server_socket.accept()
                    client_sockets.append(client_socket)

                if len(client_sockets) == 5:
                    self.log(f"Client connected from {address}")
                    # Handle this client in a separate thread
                    client_thread = Thread(
                        target=self._handle_client,
                        args=(client_sockets, address),
                        daemon=True
                    )
                    client_thread.start()

            except Exception as e:
                if self.running:
                    self.log(f"Error accepting client: {e}")

    def _handle_client(self, client_sockets, address):
        """Handle a connected client"""
        try:
            # Send file list
            file_list = self.get_file_list()
            file_list_str = "List of files:\n" + "\n".join(file_list)
            client_sockets[4].sendall(file_list_str.encode())
            self.log(f"Sent file list to {address}")

            # Listen for file requests
            client_sockets[4].settimeout(1.0)
            while self.running:
                try:
                    msg = client_sockets[4].recv(1024).decode()
                    if not msg:
                        break

                    self.log(f"Request from {address}: {msg}")

                    if msg.startswith("GET "):
                        filename = msg[4:].strip()
                        self._send_file(client_sockets, filename, address)

                except socket.timeout:
                    continue
                except Exception as e:
                    self.log(f"Error handling request: {e}")
                    break

        except Exception as e:
            self.log(f"Error with client {address}: {e}")
        finally:
            for sock in client_sockets:
                try:
                    sock.close()
                except:
                    pass
            self.log(f"Client {address} disconnected")

    def _send_file(self, client_sockets, filename, address):
        """Send a file to client"""
        try:
            file_path = os.path.join(self.folder_path, filename)
            if not os.path.exists(file_path):
                client_sockets[4].send(f"{filename} does not exist!".encode())
                return

            file_size = os.path.getsize(file_path)
            client_sockets[4].send(f"Downloading {filename}!".encode())

            # Send file in 4 chunks using first 4 sockets
            chunk_size = file_size // 4
            threads = []

            for i in range(4):
                start = i * chunk_size
                end = start + chunk_size if i < 3 else file_size

                thread = Thread(
                    target=self._send_chunk,
                    args=(client_sockets[i], file_path, start, end, i),
                    daemon=True
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Send completion message
            client_sockets[4].send(f"{filename} downloaded successfully".encode())
            self.log(f"Sent {filename} to {address}")

        except Exception as e:
            self.log(f"Error sending file: {e}")

    def _send_chunk(self, sock, file_path, start, end, chunk_id):
        """Send a chunk of file"""
        try:
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start)
                sock.sendall(data)
        except Exception as e:
            self.log(f"Error sending chunk {chunk_id}: {e}")


class TCPClientLogic:
    """Pure TCP client logic without CLI dependencies"""

    def __init__(self, host, port, download_folder, on_log=None, on_progress=None):
        self.host = host
        self.port = port
        self.download_folder = download_folder
        self.on_log = on_log or (lambda msg: print(msg))
        self.on_progress = on_progress or (lambda p: None)
        self.sockets = []
        self.connected = False
        self.file_list = []

    def log(self, message):
        """Send log message to callback"""
        self.on_log(message)

    def connect(self):
        """Connect to server and get file list"""
        try:
            # Create 5 connections
            self.sockets = []
            for i in range(5):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                self.sockets.append(sock)

            self.log("Connected to server")

            # Receive file list
            file_list_data = self.sockets[4].recv(4096).decode()
            self.file_list = []

            for line in file_list_data.splitlines():
                if line.startswith("List of files:"):
                    continue
                if " - " in line:
                    self.file_list.append(line)

            self.log(f"Received file list: {len(self.file_list)} files")
            self.connected = True
            return True

        except Exception as e:
            self.log(f"Connection failed: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Disconnect from server"""
        for sock in self.sockets:
            try:
                sock.close()
            except:
                pass
        self.sockets = []
        self.connected = False
        self.log("Disconnected")

    def download_file(self, filename):
        """Download a single file"""
        if not self.connected:
            self.log("Not connected to server")
            return False

        try:
            # Send request
            msg = f"GET {filename}"
            self.sockets[4].send(msg.encode())

            # Get response
            response = self.sockets[4].recv(1024).decode()
            self.log(f"Server: {response}")

            if "not exist" in response:
                return False

            # Get file size
            file_size = self._get_file_size(filename)
            if not file_size:
                return False

            # Receive file in chunks
            chunk_size = file_size // 4
            chunks = [b""] * 4
            threads = []

            for i in range(4):
                expected_size = chunk_size if i < 3 else (file_size - 3 * chunk_size)
                thread = Thread(
                    target=self._receive_chunk,
                    args=(i, expected_size, chunks),
                    daemon=True
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Merge chunks and save
            file_data = b"".join(chunks)
            output_path = os.path.join(self.download_folder, filename)

            with open(output_path, 'wb') as f:
                f.write(file_data)

            # Get completion message
            completion = self.sockets[4].recv(1024).decode()
            self.log(f"Server: {completion}")

            self.log(f"Downloaded {filename} successfully")
            return True

        except Exception as e:
            self.log(f"Download failed: {e}")
            return False

    def _get_file_size(self, filename):
        """Extract file size from file list"""
        for entry in self.file_list:
            if entry.startswith(filename + " - "):
                size_str = entry.split(" - ")[1].replace("B", "")
                return int(size_str)
        return None

    def _receive_chunk(self, chunk_id, expected_size, chunks):
        """Receive a chunk of file"""
        try:
            received = 0
            data = b""

            while received < expected_size:
                chunk = self.sockets[chunk_id].recv(min(8192, expected_size - received))
                if not chunk:
                    break
                data += chunk
                received += len(chunk)

                # Report progress
                progress = (received / expected_size) * 100
                self.on_progress(progress)

            chunks[chunk_id] = data
            self.log(f"Chunk {chunk_id} received: {received} bytes")

        except Exception as e:
            self.log(f"Error receiving chunk {chunk_id}: {e}")
