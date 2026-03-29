import json
import os

class LogManager:
    def __init__(self, log_file="wal.log"):
        self.log_file = log_file
        self.lsn = 0
        # Check if log file exists and find the last LSN
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if "lsn" in record:
                            self.lsn = max(self.lsn, record["lsn"])
                    except json.JSONDecodeError:
                        continue

    def append(self, record):
        self.lsn += 1
        record['lsn'] = self.lsn
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return self.lsn

    def read_logs(self):
        if not os.path.exists(self.log_file):
            return []
        logs = []
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return logs
