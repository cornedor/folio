"""The Nextcloud desktop client, asked over the socket it keeps for file
managers ($XDG_RUNTIME_DIR/Nextcloud/socket), as its Nautilus extension asks.
Messages are lines: "COMMAND:argument" out, and back "REGISTER_PATH:<folder>"
for each folder it syncs, sent on connecting, and "STATUS:<state>:<path>" for
a path asked about. A state is OK, SYNC, NEW, IGNORE, ERROR or NOP (not the
client's), with +SWM after it when shared.
"""
import os
import socket
import tempfile
import time


def socket_path():
    # Without XDG_RUNTIME_DIR the client falls back as Qt does.
    runtime = os.environ.get("XDG_RUNTIME_DIR") or os.path.join(
        tempfile.gettempdir(), "runtime-" + os.environ.get("USER", ""))
    return os.path.join(runtime, "Nextcloud", "socket")


class Client:
    """A connection to the client; raises OSError when it isn't running."""

    def __init__(self, seconds):
        self.deadline = time.monotonic() + seconds
        self.pending = b""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(seconds)
        self.sock.connect(socket_path())

    def send(self, command, argument=""):
        self.sock.sendall(command.encode() + b":" + os.fsencode(argument) + b"\n")

    def lines(self):
        """The lines the client sends, until the time is up or it hangs up."""
        while True:
            while b"\n" in self.pending:
                line, self.pending = self.pending.split(b"\n", 1)
                yield os.fsdecode(line)
            left = self.deadline - time.monotonic()
            if left <= 0:
                return
            self.sock.settimeout(left)
            try:
                data = self.sock.recv(65536)
            except socket.timeout:
                return
            if not data:
                return
            self.pending += data

    def roots(self):
        """The folders the client syncs. It names them before it answers
        anything, so they've all come once it has said its version."""
        self.send("VERSION")
        found = []
        for line in self.lines():
            if line.startswith("REGISTER_PATH:"):
                found.append(line.split(":", 1)[1].rstrip("/"))
            elif line.startswith("VERSION:"):
                break
        return found

    def states(self, paths):
        """The state of each path the client answers about in time."""
        for path in paths:
            self.send("RETRIEVE_FOLDER_STATUS" if os.path.isdir(path) else "RETRIEVE_FILE_STATUS", path)
        found = {}
        if not paths:
            return found
        for line in self.lines():
            # A path may hold colons of its own; a state never does.
            parts = line.split(":", 2)
            if len(parts) == 3 and parts[0] == "STATUS" and parts[2] in paths:
                found[parts[2]] = parts[1]
                if len(found) == len(paths):
                    break
        return found
