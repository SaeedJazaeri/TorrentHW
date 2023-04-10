import asyncio
import sys
import socket
import threading
from threading import Thread
import time

class TorrentTracker:
    def __init__(self):
        self.files = {}
        self.peers = {}
        self.IP, self.port = sys.argv[1].split(":")

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode().strip()

        # Check if the message is a file registration or request
        if message.startswith('register'):
            _, filename, peer_address = message.split()
            if filename not in self.files:
                self.files[filename] = []
            self.files[filename].append(peer_address)
            self.peers[peer_address] = time.time() # update last seen time
            print(f'File {filename} registered by Peer at {peer_address}')
            self.transport.sendto('ok\n'.encode(), addr)

        elif message.startswith('request'):
            _, filename = message.split()
            if filename in self.files:
                peer_list = ' '.join(self.files[filename])
                info = 'peers {}\n'.format(peer_list)
                self.transport.sendto(info.encode(), addr)
            else:
                self.transport.sendto('file not found\n'.encode(), addr)

    def connection_lost(self, exc):
        pass

    async def send_keepalive(self):
        while True:
            for peer_address in list(self.peers.keys()):
                last_seen = self.peers[peer_address]
                if time.time() - last_seen > 20:
                    print(f"Peer at {peer_address} is not responding, removing from list")
                    for filename in self.files:
                        if peer_address in self.files[filename]:
                            self.files[filename].remove(peer_address)
                    del self.peers[peer_address]
                else:
                    print(f"Sending keepalive packet to {peer_address}")
                    self.transport.sendto('keepalive\n'.encode(), (peer_address, int(self.port)))
            await asyncio.sleep(10)

async def start_tracker(tracker):
    # Create the UDP server to accept incoming connections
    IP, port = sys.argv[1].split(":")
    transport, protocol = await asyncio.get_event_loop().create_datagram_endpoint(
        lambda: tracker,
        local_addr=(IP, int(port))
    )

    # Print a message to indicate that the server is running
    print(f'Torrent tracker listening on {IP}:{port}')

    # Create a task to run the send_keepalive function
    asyncio.create_task(tracker.send_keepalive())

    # Keep the server running indefinitely
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour
    finally:
        transport.close()


if __name__ == "__main__":
    tracker = TorrentTracker()
    asyncio.run(start_tracker(tracker))