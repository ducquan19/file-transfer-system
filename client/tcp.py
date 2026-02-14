import socket
from threading import Thread
from queue import Queue
import threading
import time
import signal
import os
import sys

from core.file_handler import FileHandler
from core.constants import NUM_SOCKET, NUM_CHUNK, BUFFER_SIZE, INPUT_SCAN_INTERVAL


class Client:

    def __init__(self, HOST, PORT, folder_path, input_path, use_signals=True):
        self.socket = [] * NUM_SOCKET
        for i in range(NUM_SOCKET):
            self.socket.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            self.socket[i].connect((HOST, PORT))

        print("\n\033[1;32;40m[NOTIFICATION] Connected to Server.\n\033[0m")

        self.use_signals = use_signals
        if use_signals:
            signal.signal(signal.SIGINT, self.stop)

        self.need_file = Queue()
        self.running = True
        self.file_list = []
        self.folder_path = folder_path
        self.input_path = input_path

        try:
            self.rcv_file_list()

            input_thread = Thread(target = self.read_input_file, daemon = True)
            send_request_thread = Thread(target = self.send_request, daemon = True)

            input_thread.start()
            send_request_thread.start()

            if use_signals:
                while self.running:
                    input("")

                input_thread.join()
                send_request_thread.join()

        except (KeyboardInterrupt, ConnectionAbortedError, BrokenPipeError):
            self.stop()
        except Exception as e:
            print(f"Error in main: {e}")

    def get_file_size(self, filename):
        return int(next((size for name, size in self.file_list if name == filename), None))

    def read_input_file(self):
        start = 0

        try:
            while self.running:
                with open(self.input_path, "r") as f:
                    f.seek(start)
                    new_files = [line.strip() for line in f.readlines()]
                    start = f.tell()

                for file in new_files:
                    if file == "": continue
                    self.need_file.put(file)

                f.close()
                time.sleep(INPUT_SCAN_INTERVAL)
        except (KeyboardInterrupt, ConnectionAbortedError, BrokenPipeError):
            self.stop()
        except Exception as e:
            print(f"Error in send_request: {e}")

    def send_request(self):
        try:
            while self.running:
                if not self.need_file.empty():
                    filename = self.need_file.get()
                    msg = f"GET {filename}"
                    print(f"Client: {msg}")
                    self.socket[4].send(msg.encode())

                    # response file exist or not
                    server_response = self.socket[4].recv(1024).decode()
                    print("\033[1;31;40m" + "Server: " + server_response + "\033[0m")
                    if "not exist" not in server_response:
                        file_size = self.get_file_size(filename)
                        FileClient(filename, file_size, self, self.folder_path).rcv_file()

        except (KeyboardInterrupt, ConnectionAbortedError, BrokenPipeError):
            self.stop()
        except Exception as e:
            print(f"Error in send request: {e}")

    def rcv_file_list(self):
        try:
            server_msg = self.socket[4].recv(1024).decode()
            print(server_msg, end = '\n\n')

            for line in server_msg.splitlines():
                if line.startswith("List of files:"):
                    continue
                if " - " in line:
                    name, size = line.split(" - ")
                    self.file_list.append((name, float(size.replace("B", "").strip())))

        except (KeyboardInterrupt, ConnectionAbortedError, BrokenPipeError):
            self.stop()
        except Exception as e:
            print(f"Error in rcv_msg: {e}")

    def stop(self, *args, **kwargs):
        self.running = False
        print("\n\033[1;32;40m[NOTIFICATION] Disconnected!\n\033[0m")
        if self.use_signals:
            os._exit(0)

class FileClient:
    def __init__(self, filename, file_size, Client, folder_path):
        self.filename = filename
        self.socket = Client.socket
        self.client_instance = Client
        self.num_chunk = NUM_CHUNK
        self.running = True

        # Use FileHandler for chunk management and progress tracking
        self.file_handler = FileHandler(file_size, filename, folder_path, self.num_chunk)
        self.chunks = self.file_handler.chunks

    def rcv_file(self):
        try:
            threads = []

            for chunk_id in range(self.num_chunk):
                thread = Thread(target = self.rcv_chunk, args = (chunk_id, ), daemon = True)
                threads.append(thread)
                thread.start()

            # Use FileHandler's display_progress method
            progress_thread = Thread(target=self.file_handler.display_progress, daemon=True)
            progress_thread.start()

            for thread in threads:
                thread.join()

            progress_thread.join()

            # Use FileHandler's merge method
            self.file_handler.merge()
            server_msg = self.socket[4].recv(1024).decode()
            print("\033[1;31;40m" + "Server: " + server_msg + "\033[0m")
            client_msg = f"{self.filename} received successfully"
            self.socket[4].send(client_msg.encode())
            print(f"Client: {client_msg}")
        except (KeyboardInterrupt, ConnectionAbortedError, BrokenPipeError):
            self.stop()
        except Exception as e:
            print(f"Error in rcv_file: {e}")
        finally:
            self.running = False

    def rcv_chunk(self, chunk_id):
        start, end, size = self.chunks[chunk_id]
        rcv_size = 0
        try:
            data = b""
            while start < end:
                packet = self.socket[chunk_id].recv(min(BUFFER_SIZE, end - start))
                if not packet: break
                data += packet
                start += len(packet)
                rcv_size += len(packet)
                # Use FileHandler's update_progress method
                self.file_handler.update_progress(chunk_id, rcv_size, size)

            # Use FileHandler's finish_chunk method
            self.file_handler.finish_chunk(chunk_id, data)

        except (KeyboardInterrupt, ConnectionAbortedError, BrokenPipeError):
            self.stop()
        except Exception as e:
            print(f"Error in rcv_chunk {chunk_id + 1}: {e}")


    def stop(self, *args, **kwargs):
        self.running = False
        print("\n\033[1;32;40m[NOTIFICATION] Disconnected!\n\033[0m")
        if hasattr(self.client_instance, 'use_signals') and self.client_instance.use_signals:
            os._exit(0)

if __name__ == "__main__":
    def handle_signal(signal, frame):
        Client.stop()

    signal.signal(signal.SIGINT, handle_signal)

    try:
        HOST = input("Enter Server IP address: ")
        PORT = int(input("Enter Server port: "))
        folder_path = input("Enter folder path to save files: ")
        input_path = input("Enter input file path: ")

        Client(HOST, PORT, folder_path, input_path)
    except KeyboardInterrupt:
        Client.stop()
    except:
        print("\033[1;32;40m[NOTIFICATION] Cannot connect to Server!\033[0m")
