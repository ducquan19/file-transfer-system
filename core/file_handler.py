import threading
import sys

class FileHandler:

    def __init__(self, file_size, file_name, output_path, num_chunk):
        self.file_size = file_size
        self.file_name = file_name
        self.output_path = output_path
        self.num_chunk = num_chunk

        self.lock = threading.Lock()

        self.chunks_data = [None] * num_chunk
        self.chunk_progress = [0.0] * num_chunk
        self.done_chunk = [False] * num_chunk

        self.chunks = self.split_chunks()

    # =========================
    # SPLIT FILE
    # =========================
    def split_chunks(self):
        chunks = []

        for chunk_id in range(self.num_chunk):
            start = chunk_id * (self.file_size // self.num_chunk)

            if chunk_id == self.num_chunk - 1:
                end = self.file_size
            else:
                end = start + (self.file_size // self.num_chunk)

            chunks.append((start, end, end - start))

        return chunks

    # =========================
    # UPDATE PROGRESS (UDP/TCP dùng chung)
    # =========================
    def update_progress(self, chunk_id, received, total):
        with self.lock:
            self.chunk_progress[chunk_id] = (received / total) * 100

    # =========================
    # MARK DONE
    # =========================
    def finish_chunk(self, chunk_id, data):
        self.done_chunk[chunk_id] = True
        self.chunks_data[chunk_id] = data

    # =========================
    # MERGE FILE
    # =========================
    def merge(self):
        output_file = self.output_path + "\\" + self.file_name

        with open(output_file, "wb") as f:
            for chunk in self.chunks_data:
                if chunk is not None:
                    f.write(chunk)

    # =========================
    # DISPLAY PROGRESS
    # =========================
    def display_progress(self):

        while any(done is False for done in self.done_chunk):

            msg = ""

            for i in range(self.num_chunk):
                if self.chunk_progress[i] != 100:
                    msg += f"Downloading {self.file_name} part {i+1}: {self.chunk_progress[i]:.2f}%"
                else:
                    msg += f"{self.file_name} part {i+1} downloaded successfully"

                if i < self.num_chunk - 1:
                    msg += "\n"

            print(msg)
            sys.stdout.write(f"\033[{self.num_chunk}A\033[0G\033[J")

        print("\n".join(
            [f"{self.file_name} part {i+1} downloaded successfully" for i in range(self.num_chunk)]
        ))
