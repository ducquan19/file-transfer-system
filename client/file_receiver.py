import threading
import sys
import os
from threading import Thread
from core.constants import NUM_CHUNK, BUFFER_SIZE

class FileReceiver:

    def __init__(self, filename, file_size, client, folder_path):
        self.filename = filename
        self.socket = client.socket
        self.output_file = folder_path + "/" + filename

        self.num_chunk = NUM_CHUNK
        self.chunks_data = [None] * self.num_chunk
        self.lock = threading.Lock()
        self.chunk_progress = [0.0] * self.num_chunk
        self.done_chunk = [False] * self.num_chunk

        self.chunks = []
        for chunk_id in range(self.num_chunk):
            chunk_start = chunk_id * (file_size // self.num_chunk)
            chunk_end = (chunk_id + 1) * (file_size // self.num_chunk) \
                if chunk_id < self.num_chunk - 1 else file_size
            self.chunks.append((chunk_start, chunk_end, chunk_end - chunk_start))

    def rcv_chunk(self, chunk_id):
        start, end, size = self.chunks[chunk_id]
        rcv_size = 0
        data = b""

        while start < end:
            packet = self.socket[chunk_id].recv(min(BUFFER_SIZE, end - start))
            if not packet:
                break

            data += packet
            start += len(packet)
            rcv_size += len(packet)

            with self.lock:
                self.chunk_progress[chunk_id] = rcv_size * 100 / size

        self.chunks_data[chunk_id] = data
        self.done_chunk[chunk_id] = True

    def merge_chunks(self):
        with open(self.output_file, "wb") as f:
            for chunk in self.chunks_data:
                f.write(chunk)

    def display_progress(self):
        while any(done == False for done in self.done_chunk):
            progress_msg = ""
            for i in range(self.num_chunk):
                if self.chunk_progress[i] != 100:
                    progress_msg += f"Downloading {self.filename} part {i+1}: {self.chunk_progress[i]:.2f}%"
                else:
                    progress_msg += f"{self.filename} part {i+1} downloaded successfully"

                if i < self.num_chunk - 1:
                    progress_msg += "\n"

            print(progress_msg)
            sys.stdout.write(f"\033[{self.num_chunk}A\033[0G\033[J")

        print("\n".join(
            [f"{self.filename} part {i+1} downloaded successfully" for i in range(self.num_chunk)]
        ))

    def receive(self):
        threads = []
        for chunk_id in range(self.num_chunk):
            t = Thread(target=self.rcv_chunk, args=(chunk_id,), daemon=True)
            threads.append(t)
            t.start()

        self.display_progress()

        for t in threads:
            t.join()

        self.merge_chunks()
