"""
UDP Logic Layer - Separated from CLI interface
Provides core UDP functionality for GUI or other interfaces
"""

import socket
import os
import hashlib
from threading import Thread
import threading


class UDPServerLogic:
    """Pure UDP server logic without CLI dependencies"""

    def __init__(self, host, port, folder_path, on_log=None):
        self.host = host
        self.port = port
        self.folder_path = folder_path
        self.on_log = on_log or (lambda msg: print(msg))
        self.running = False
        self.server_socket = None
        self.PACKET_SIZE = 8192
        self.DATA_SIZE = self.PACKET_SIZE - 100
        self.TIMEOUT = 0.1
        self.MAX_TRIES = 100

    def log(self, message):
        """Send log message to callback"""
        self.on_log(message)

    def start(self):
        """Start the UDP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.settimeout(self.TIMEOUT)
            self.running = True

            self.log(f"UDP Server started on {self.host}:{self.port}")

            # Start handling clients
            handle_thread = Thread(target=self._handle_clients, daemon=True)
            handle_thread.start()

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
        self.log("UDP Server stopped")

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

    def _handle_clients(self):
        """Handle incoming UDP requests"""
        while self.running:
            try:
                data, client_address = self.server_socket.recvfrom(self.PACKET_SIZE)

                # Handle message in separate thread
                thread = Thread(
                    target=self._process_message,
                    args=(data, client_address),
                    daemon=True
                )
                thread.start()

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log(f"Error receiving data: {e}")

    def _process_message(self, data, client_address):
        """Process a message from client"""
        try:
            message = data.decode()

            # PING message - send file list
            if message == "23120088":
                self.log(f"PING from {client_address}")
                file_list = self.get_file_list()
                file_list_str = "List of files:\n" + "\n".join(file_list)
                self._send_message(file_list_str, client_address)

            # File request
            elif "|" in message:
                parts = message.split("|")
                if len(parts) >= 3:
                    filename = parts[0]
                    chunk_id = int(parts[1])
                    self.log(f"File request from {client_address}: {filename} chunk {chunk_id}")
                    self._send_file_chunk(filename, chunk_id, client_address)

        except Exception as e:
            self.log(f"Error processing message: {e}")

    def _send_message(self, message, client_address):
        """Send a message to client"""
        try:
            self.server_socket.sendto(message.encode(), client_address)
        except Exception as e:
            self.log(f"Error sending message: {e}")

    def _send_file_chunk(self, filename, chunk_id, client_address):
        """Send a file chunk to client"""
        try:
            file_path = os.path.join(self.folder_path, filename)
            if not os.path.exists(file_path):
                self.log(f"File not found: {filename}")
                return

            file_size = os.path.getsize(file_path)
            chunk_size = file_size // 4

            start = chunk_id * chunk_size
            end = start + chunk_size if chunk_id < 3 else file_size

            with open(file_path, 'rb') as f:
                f.seek(start)
                sequence = 0

                while start < end:
                    data = f.read(min(self.DATA_SIZE, end - start))
                    if not data:
                        break

                    # Package with checksum
                    packet = self._create_packet(data, sequence, chunk_id)

                    # Send with retry logic
                    tries = 0
                    while tries < self.MAX_TRIES and self.running:
                        self.server_socket.sendto(packet, client_address)

                        # Wait for ACK
                        try:
                            self.server_socket.settimeout(self.TIMEOUT)
                            ack_data, _ = self.server_socket.recvfrom(1024)
                            ack = int(ack_data.decode())

                            if ack == sequence:
                                break
                        except socket.timeout:
                            tries += 1
                        except:
                            break

                    start += len(data)
                    sequence += 1

            self.log(f"Sent chunk {chunk_id} of {filename} to {client_address}")

        except Exception as e:
            self.log(f"Error sending chunk: {e}")

    def _create_packet(self, data, sequence, chunk_id):
        """Create a packet with checksum"""
        checksum = hashlib.md5(data).hexdigest().encode()
        seq_bytes = str(sequence).encode()
        chunk_bytes = str(chunk_id).encode()
        return b"|".join([seq_bytes, checksum, chunk_bytes, data])

    def _calculate_checksum(self, data):
        """Calculate MD5 checksum"""
        return hashlib.md5(data).hexdigest()


class UDPClientLogic:
    """Pure UDP client logic without CLI dependencies"""

    def __init__(self, host, port, download_folder, on_log=None, on_progress=None):
        self.host = host
        self.port = port
        self.download_folder = download_folder
        self.on_log = on_log or (lambda msg: print(msg))
        self.on_progress = on_progress or (lambda p: None)
        self.server_address = (host, port)
        self.PACKET_SIZE = 8192
        self.TIMEOUT = 0.2
        self.MAX_TRIES = 100
        self.file_list = []

    def log(self, message):
        """Send log message to callback"""
        self.on_log(message)

    def connect(self):
        """Connect to server and get file list"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            # Send PING
            sock.sendto("23120088".encode(), self.server_address)
            self.log("Sent PING to server")

            # Receive file list
            data, _ = sock.recvfrom(self.PACKET_SIZE)
            file_list_data = data.decode()

            self.file_list = []
            for line in file_list_data.splitlines():
                if line.startswith("List of files:"):
                    continue
                if " - " in line:
                    self.file_list.append(line)

            sock.close()
            self.log(f"Received file list: {len(self.file_list)} files")
            return True

        except Exception as e:
            self.log(f"Connection failed: {e}")
            return False

    def download_file(self, filename):
        """Download a file from server"""
        try:
            # Get file size
            file_size = self._get_file_size(filename)
            if not file_size:
                self.log(f"File size not found: {filename}")
                return False

            self.log(f"Downloading {filename} ({file_size} bytes)")

            # Download 4 chunks in parallel
            chunks = [b""] * 4
            threads = []

            for chunk_id in range(4):
                thread = Thread(
                    target=self._download_chunk,
                    args=(filename, chunk_id, file_size, chunks),
                    daemon=True
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Merge and save
            file_data = b"".join(chunks)
            output_path = os.path.join(self.download_folder, filename)

            with open(output_path, 'wb') as f:
                f.write(file_data)

            self.log(f"Downloaded {filename} successfully")
            return True

        except Exception as e:
            self.log(f"Download failed: {e}")
            return False

    def _get_file_size(self, filename):
        """Get file size from file list"""
        for entry in self.file_list:
            if entry.startswith(filename + " - "):
                size_str = entry.split(" - ")[1].replace("B", "")
                return int(size_str)
        return None

    def _download_chunk(self, filename, chunk_id, file_size, chunks):
        """Download a single chunk"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.TIMEOUT)

            # Send request for this chunk
            request = f"{filename}|{chunk_id}|REQUEST"
            sock.sendto(request.encode(), self.server_address)

            # Calculate chunk size
            chunk_size = file_size // 4
            start = chunk_id * chunk_size
            end = start + chunk_size if chunk_id < 3 else file_size
            expected_size = end - start

            # Receive packets
            received_bytes = 0
            chunk_data = b""
            ack = 0

            while received_bytes < expected_size:
                try:
                    packet, _ = sock.recvfrom(self.PACKET_SIZE)

                    if packet.count(b"|") >= 3:
                        parts = packet.split(b"|", maxsplit=3)
                        seq_str = parts[0].decode()
                        checksum = parts[1].decode()
                        data = parts[3]

                        # Verify checksum
                        if self._verify_checksum(data, checksum):
                            if int(seq_str) == ack:
                                chunk_data += data
                                received_bytes += len(data)

                                # Send ACK
                                sock.sendto(str(ack).encode(), self.server_address)
                                ack += 1

                                # Update progress
                                progress = (received_bytes / expected_size) * 100
                                self.on_progress(progress)
                            else:
                                # Send previous ACK
                                sock.sendto(str(ack - 1).encode(), self.server_address)
                        else:
                            # Bad checksum, request resend
                            sock.sendto(str(ack - 1).encode(), self.server_address)

                except socket.timeout:
                    continue

            chunks[chunk_id] = chunk_data
            sock.close()
            self.log(f"Chunk {chunk_id} received: {received_bytes} bytes")

        except Exception as e:
            self.log(f"Error downloading chunk {chunk_id}: {e}")

    def _verify_checksum(self, data, checksum):
        """Verify data checksum"""
        calculated = hashlib.md5(data).hexdigest()
        return calculated == checksum
