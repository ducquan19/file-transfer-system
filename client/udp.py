from queue import Queue
import socket
from threading import Thread
import threading
import time
import sys
import os

from core.file_handler import FileHandler
from core.constants import NUM_CHUNK, PACKET_SIZE, TIMEOUT, MAX_TRIES, INPUT_SCAN_INTERVAL
from utils.checksum import calculate_checksum, is_valid_utf8


class FileClient:
    def __init__(self, host=None, port=None, output_path=None, file_input=None):
        if host is None:
            host = input("Enter Server IP address: ")
        if port is None:
            port = int(input("Enter Server port: "))
        if output_path is None:
            output_path = input("Enter folder path to save files: ")
        if file_input is None:
            file_input = input("Enter input file path: ")

        self.server_address = (host, int(port))
        self.num_chunk = NUM_CHUNK
        self.TIMEOUT = TIMEOUT
        self.lock = threading.Lock()
        self.file_size = 0
        self.file_name = 0
        self.output_path = output_path
        self.file_input = file_input
        self.MAX_TRIES = MAX_TRIES
        self.chunk_size = 0
        self.need_file = Queue()
        self.list_file = ""
        self.file_handler = None  # Will be initialized per file

        Thread(target = self.read_input_file, daemon=True).start()

    def stop(self):
        print("\n\033[1;32;40m[NOTIFICATION] Disconnected!\n\033[0m")
        os._exit(0)

    def read_input_file(self):
        start = 0

        try:
            while True:
                try:
                    with open(self.file_input, "r") as f:
                        f.seek(start)
                        new_files = [line.strip() for line in f.readlines()]
                        start = f.tell()

                    for file in new_files:
                        if file == "": continue
                        if file in new_files:
                            self.need_file.put(file)
                    f.close()
                    time.sleep(INPUT_SCAN_INTERVAL)
                except KeyboardInterrupt:
                    return
        except Exception as e:
            print(f"Error in send_request: {e}")

    def get_file_name(self):
        if not self.need_file.empty():
            return self.need_file.get()
        else:
            return None


    def recv_chunk(self, chunk_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
                client_sock.settimeout(self.TIMEOUT)
                # send PING_MSG
                PING_MSG = "23120088"
                self.send_ping_message(client_sock, PING_MSG)
                # Get chunk boundaries from FileHandler
                start, end, total_chunk = self.file_handler.chunks[chunk_id]
                # receive chunk
                ack = 0
                received_bytes = 0
                chunk_data = b""
                fl = True
                while True:
                    try:
                        # receive packet
                        packet, _ = client_sock.recvfrom(PACKET_SIZE)
                        if packet.count(b"|") >= 3:
                            seq_s, checksum, id, data = packet.split(b"|", maxsplit=3)
                            if is_valid_utf8(seq_s) and is_valid_utf8(checksum) and is_valid_utf8(id):
                                seq_s = seq_s.decode()
                                checksum = checksum.decode()
                                id = int(id.decode())
                            else:
                                response = f"{ack - 1}"
                                client_sock.sendto(response.encode(), self.server_address)
                                continue
                            if fl:
                                if chunk_id != id:
                                    chunk_id = id
                                    start, end, total_chunk = self.file_handler.chunks[chunk_id]
                                fl = False
                            # response msg
                            if calculate_checksum(data) == checksum:
                                if int(seq_s) == ack:
                                    received_bytes += len(data)
                                    # Use FileHandler's update_progress method
                                    self.file_handler.update_progress(chunk_id, received_bytes, total_chunk)
                                    # send ack back
                                    response = f"{seq_s}"
                                    client_sock.sendto(response.encode(), self.server_address)
                                    # store bytes
                                    chunk_data += data
                                    # stop when receive full chunk
                                    if received_bytes >= total_chunk:
                                        break
                                    ack += 1
                                    continue
                        # send last ack received
                        response = f"{ack - 1}"
                        client_sock.sendto(response.encode(), self.server_address)
                    except KeyboardInterrupt:
                        break
                    except socket.timeout:
                        continue
                # Use FileHandler's finish_chunk method
                self.file_handler.finish_chunk(chunk_id, chunk_data)
                client_sock.close()
        except KeyboardInterrupt:
            return
        except Exception as e:
            print(f"Error downloading chunk {chunk_id}: {e}")

    def start_client(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
                client_socket.settimeout(self.TIMEOUT)
                # PING_MSG
                try:
                    self.send_ping_message(client_socket, "23120088")
                    print("\n\033[1;32;40m[NOTIFICATION] Sent PING_MSG to Server!\n\033[0m")
                    # receive file_list
                    self.list_file = self.recv_message(client_socket)
                    if self.list_file is not None:
                        print(self.list_file, "\n")

                    while True:
                        try:
                            # send file_name
                            self.file_name = self.get_file_name()
                            if self.file_name is not None:
                                msg = f"GET {self.file_name}"
                                print(f"Client: {msg}")
                                self.send_message(client_socket, msg)
                                # receive response (exist: file_size, not exist: NOT)
                                response = self.recv_message(client_socket)
                                if response != "NOT":
                                    # receive file_size
                                    self.file_size = int(response)
                                    self.chunk_size = self.file_size // int(self.num_chunk)
                                    # Initialize FileHandler for this file
                                    self.file_handler = FileHandler(self.file_size, self.file_name, self.output_path, self.num_chunk)
                                    # receive to download
                                    server_msg = self.recv_message(client_socket)
                                    print("\033[1;31;40m" + server_msg + "\033[0m")
                                    # threading
                                    threads = []

                                    for chunk_id in range(self.num_chunk):
                                        thread = threading.Thread(target=self.recv_chunk, args=(chunk_id,))
                                        if thread is not None:
                                            threads.append(thread)
                                            thread.start()

                                    # Use FileHandler's display_progress method
                                    progress_thread = Thread(target=self.file_handler.display_progress, daemon=True)
                                    progress_thread.start()

                                    for thread in threads:
                                        thread.join()

                                    progress_thread.join()
                                    # receive successfully file
                                    server_msg = self.recv_message(client_socket)
                                    print("\033[1;31;40m" + server_msg + "\033[0m")
                                    # send cofirm msg
                                    msg = f"{self.file_name} received successfully"
                                    self.send_message(client_socket, msg)
                                    # print
                                    print(f"Client: {msg}")
                                    # Use FileHandler's merge method
                                    self.file_handler.merge()
                                else:
                                    server_msg = f"{self.file_name} does not exist!"
                                    print("\033[1;31;40m" + "Server: " + server_msg + "\033[0m")
                        except KeyboardInterrupt:
                            FIN = "EXIT"
                            self.send_message(client_socket, FIN)
                            break
                        except ConnectionResetError:
                            print(f"Server disconnected.")
                            break
                except KeyboardInterrupt:
                    return
        except ConnectionResetError:
            print(f"Server {self.server_address} is not alive.")

    def send_ping_message(self, client_socket : socket, message):
        while True:
            try:
                client_socket.sendto(message.encode(), self.server_address)
                ack, _ = client_socket.recvfrom(PACKET_SIZE)
                if ack.decode() == "OK":
                    return
            except socket.timeout:
                continue
            except ConnectionResetError:
                return
            except UnicodeDecodeError:
                continue
            except KeyboardInterrupt:
                return

    def send_message(self, client_socket : socket, message):
        cnt = 1
        message = message.encode()
        checksum = calculate_checksum(message).encode()
        packet = b"|".join([checksum, message])
        while True:
            try:
                client_socket.sendto(packet, self.server_address)
                ack, _ = client_socket.recvfrom(PACKET_SIZE)
                if ack.decode() == "OK":
                    return
            except socket.timeout:
                # cnt = cnt + 1
                # if cnt >= self.MAX_TRIES:
                #     print("Can't send msg to server")
                #     break
                continue
            except ConnectionResetError:
                return
            except UnicodeDecodeError:
                continue
            except KeyboardInterrupt:
                return

    def recv_message(self, client_socket : socket):
        while True:
            try:
                packet, _ = client_socket.recvfrom(PACKET_SIZE)
                checksum, message = packet.split(b"|")
                checksum = checksum.decode()
                if calculate_checksum(message) == checksum:
                    response = "OK"
                    client_socket.sendto(response.encode(), self.server_address)
                    return message.decode()
                response = "NOK"
                client_socket.sendto(response.encode(), self.server_address)
            except socket.timeout:
                continue
            except UnicodeDecodeError:
                continue
            except KeyboardInterrupt:
                return None

if __name__ == "__main__":
    client = FileClient()
    client.start_client()
    client.stop()
    sys.exit(0)
