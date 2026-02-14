import socket
from threading import Thread
import threading
import signal
import sys
import time
import os

class Server:
    def __init__(self, HOST, PORT, folder_path, use_signals=True):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((HOST, PORT))
        self.socket.listen()

        print(f"\n\033[1;32;40mServer started on ({HOST}, {PORT})\nWaiting for Clients...\033[0m")
        self.folder_path = folder_path
        self.file_list = [
                f"{f} - {(os.path.getsize(os.path.join(self.folder_path, f)))}B"
                for f in os.listdir(self.folder_path)
                if os.path.isfile(os.path.join(self.folder_path, f))
            ]

        self.file_exist = [f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))]

        self.use_signals = use_signals
        if use_signals:
            signal.signal(signal.SIGINT, self.stop_server)
        self.running = True

        try:
            multi_thread = Thread(target = self.handle_multi_client, daemon = True)
            multi_thread.start()

            if use_signals:
                while self.running:
                    input("")

                multi_thread.join()

        except KeyboardInterrupt:
            self.stop_server()
        except ConnectionAbortedError:
            self.stop_server()

    def handle_multi_client(self):
        try:
            while self.running:
                client = []
                for i in range(4):
                    client_socket, address = self.socket.accept()
                    client.append(client_socket)

                client_socket, address = self.socket.accept()
                client.append(client_socket)

                address = f"({address[0]}, {address[1]})"
                client_thread = Thread(target = self.handle_client, args = (client, address, ), daemon = True)
                client_thread.start()
        except KeyboardInterrupt:
            self.stop_server()

    def handle_client(self, client, address):
        try:
            print(f"\n\033[1;32;40m[NOTIFICATION] Connected to Client {str(address)}\n\033[0m")

            self.send_file_list(client, address)

            rcv_thread = Thread(target = self.rcv_msg, args = (client, address, ), daemon=True)
            rcv_thread.start()
        except (ConnectionResetError, BrokenPipeError):
            self.stop_client(client, address)
        except KeyboardInterrupt:
            self.stop_server()
            self.stop_client(client, address)
        except Exception as e:
            print(f"Error in handle_client: {e}")

    def send_file_list(self, client, address):
        file_list_str = "List of files:\n" + "\n".join(self.file_list)
        print(f"[DEBUG] Sending file list to {address}: {file_list_str[:100]}")
        try:
            client[4].sendall(file_list_str.encode())
            print(f"[TO] {address}: File list has been sent to Client.")
        except Exception as e:
            print(f"[ERROR] Failed to send file list to {address}: {e}")

    def check_exist_file(self, filename):
        return filename in self.file_exist

    def rcv_msg(self, client, address):
        try:
            # Set timeout to avoid blocking forever
            client[4].settimeout(1.0)
            while self.running:
                try:
                    client_msg = client[4].recv(1024).decode()
                    if not client_msg:
                        break
                    print(f"\033[1;31;40m[FROM] {address}: {client_msg}\033[0m")

                    command, filename = client_msg.split(" ", 1)
                    if command == "GET":
                        if self.check_exist_file(filename) == False:
                            msg = f"{filename} does not exist!"
                            self.send_msg(client, msg, address)
                        else:
                            msg = f"Downloading {filename}!"
                            self.send_msg(client, msg, address)
                            FileTransfer(self, filename, client, address, self.folder_path, self.running).send_file()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error in rcv_msg loop: {e}")
                    break

        except (ConnectionResetError, BrokenPipeError):
            self.stop_client(client, address)
        except KeyboardInterrupt:
            self.stop_server()
            self.stop_client(client, address)
        except Exception as e:
            print(f"Error in rcv_msg: {e}")

    def send_msg(self, client, msg, address):
        print(f"[TO] {str(address)}: {msg}")
        client[4].send(msg.encode())

    def stop_client(self, client, address):
        try:
            for i in range(5):
                client[i].close()
            print(f"\n\033[1;32;40m[NOTIFICATION] Client {address} disconnected.\n\033[0m")
        except Exception as e:
            print(f"Error in stop_client: {e}")

    def stop_server(self, *args, **kwargs):
        self.running = False
        print("\n\033[1;32;40m[NOTIFICATION] Exited the Server!\n\033[0m")
        self.socket.close()
        os._exit(0)

class FileTransfer():
    def __init__(self, Server, filename, client, address, folder_path, run):
        self.socket = Server.socket
        self.client_socket = client
        self.address = address
        self.filename = filename
        self.file_path = f"{folder_path}\\{filename}"
        self.file_size = os.path.getsize(self.file_path)
        self.num_chunk = 4
        self.chunks = []
        self.running = run
        self.server_instance = Server

        for chunk_id in range(self.num_chunk):
            chunk_start = chunk_id * (self.file_size // self.num_chunk)

            if chunk_id < self.num_chunk - 1:
                chunk_end = (chunk_id + 1) * (self.file_size // self.num_chunk)
            else:
                chunk_end = self.file_size
            chunk_size = chunk_end - chunk_start
            self.chunks.append((chunk_start, chunk_end, chunk_size))

    def send_file(self):
        try:
            threads = []
            for chunk_id in range(self.num_chunk):
                thread = Thread(target = self.send_chunk, args = (chunk_id, ), daemon = True)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            msg = f"{self.filename} downloaded successfully"
            print(f"[TO] {self.address}: {msg}")
            self.client_socket[4].send(msg.encode())
            client_msg = self.client_socket[4].recv(1024).decode()
            print(f"\033[1;31;40m[FROM] {self.address}: {client_msg}\033[0m")

        except KeyboardInterrupt:
            self.stop_server()
        except (ConnectionResetError, BrokenPipeError):
            self.stop_client()
        except Exception as e:
            print(f"Error in send_file: {e}")

    def send_chunk(self, chunk_id):
        start, end, size = self.chunks[chunk_id]
        try:
            with open(self.file_path, "rb") as f:
                f.seek(start)
                data = f.read(size)
                self.client_socket[chunk_id].sendall(data)
        except KeyboardInterrupt:
            self.stop_server()
            self.stop_client()
        except (ConnectionResetError, BrokenPipeError):
            self.stop_client()
        except Exception as e:
            print(f"Error in send_chunk {chunk_id}: {e}")

    def stop_server(self, *args, **kwargs):
        self.running = False
        print("\n\033[1;32;40m[NOTIFICATION] Exited the Server!\n\033[0m")
        try:
            self.socket.close()
        except:
            pass
        # Only exit if server was started with signals
        if hasattr(self.server_instance, 'use_signals') and self.server_instance.use_signals:
            os._exit(0)

    def stop_client(self):
        try:
            for i in range(5):
                self.client_socket[i].close()
            print(f"\n\033[1;32;40m[NOTIFICATION] Client {self.address} disconnected.\n\033[0m")
        except Exception as e:
            print(f"Error in stop_client: {e}")

if __name__ == "__main__":
    server_instance = None

    def handle_signal(signal, frame):
        if server_instance:
            server_instance.stop_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)

    try:
        HOST = input("Enter Server IP address: ")
        PORT = int(input("Enter Server port: "))
        folder_path = input("Enter resource folder path: ")

        server_instance = Server(HOST, PORT, folder_path)
    except KeyboardInterrupt:
        if server_instance:
            server_instance.stop_server()
    except:
        print("Cannot start Server!")
