import asyncio
import os
import sys
import random
import struct
import asyncudp
import socket
import threading



class TorrentPeer:
    def __init__(self, peer_id, share_mode, file_name, tracker_address, own_address):
        self.peer_id = peer_id
        self.share_mode = share_mode
        self.file_name = file_name
        self.tracker_address = tracker_address
        self.own_address = own_address
        self.file_size = None
        self.peers = []

    async def start(self):
        # Register with the tracker if in sharing mode
        if self.share_mode:
            await self.register_file()

        # Get file information from the tracker if in get mode
        else:
            await self.get_file_info()

        # Start the peer server to accept incoming connections
        server = await asyncio.start_server(self.handle_peer_request, *self.own_address.split(':'))
        asyncio.create_task(self.respond_keepalive())

        # Print a message to indicate that the server is running
        print('Torrent peer listening on {}:{}'.format(*self.own_address.split(':')))

        # Keep the server running indefinitely
        async with server:
            await server.serve_forever()

    async def register_file(self):


        ip, port = (self.tracker_address).split(":")
        sock = await asyncudp.create_socket(remote_addr=(ip, int(port)))
        sock.sendto(f'register {self.file_name} {self.own_address}'.encode())
        print("send the share message to tracker")
        data, addr = await sock.recvfrom()
        print(f"got {data.decode()} from {addr}")
        await asyncio.sleep(0.5)
        sock.close()


        

    async def get_file_info(self):



        ip, port = (self.tracker_address).split(":")
        sock = await asyncudp.create_socket(remote_addr=(ip, int(port)))
        sock.sendto(f'request {self.file_name}'.encode())
        print("send the get infor message to tracker")
        data, addr = await sock.recvfrom()
        print(f"got {data.decode()} from {addr[0]}:{addr[1]}")
        await asyncio.sleep(0.5)
        message = data.decode().strip()
        _, peer_list = message.split("peers ")
        self.peers = [tuple(peer.split(':')) for peer in peer_list.split()]

        # Read the file size from the first peer in the list
        self.file_size = await self.get_file_size(*self.peers[0])
        print('Received file information for {}: size={}, peers={}'.format(self.file_name, self.file_size, self.peers))
        sock.close()



    async def get_file(self):
        # Choose a random peer to download the file from
        peer = random.choice(self.peers)

        # Connect to the peer and request the file
        reader, writer = await asyncio.open_connection(*peer)
        message = 'get {}\n'.format(self.file_name)
        writer.write(message.encode())

        # Read the file data from the peer
        data = await reader.read(self.file_size)

        # Close the connection to the peer
        writer.close()

        # Save the file data to disk
        with open(self.file_name, 'wb') as f:
            f.write(data)

        # Print a message to indicate that the file has been downloaded
        print('Downloaded file {}'.format(self.file_name))

        # Change to share mode and register the file with the tracker
        self.share_mode = True
        await self.register_file()

    async def get_file_size(self, host, port):
        # Connect to the peer and request the file size
        reader, writer = await asyncio.open_connection(host, port)
        message = 'size {}\n'.format(self.file_name)
        writer.write(message.encode())

        # Read the file size from the peer
        data = await reader.read(4)
        size = struct.unpack('>I', data)[0]

        # Close the connection to the peer
        writer.close()

        return size

    async def handle_peer_request(self, reader, writer):
        # Read the message from the peer
        data = await reader.readline()
        message = data.decode().strip()

        # Check if the message is a file request
        if message.startswith('get'):
            _, filename = message.split()

            # Send the file size to the peer
            size = os.path.getsize(filename)
            writer.write(struct.pack('>I', size))

            # Send the file data to the peer
            with open(filename, 'rb') as f:
                data = f.read()
                writer.write(data)

    async def respond_keepalive(self):
        while True:
            # Only send keepalive messages if in sharing mode
            if self.share_mode:
                # Create a UDP socket and send a keepalive message to the tracker
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                message = 'keepalive {}\n'.format(self.own_address)
                print(f"send keepalive packet from {self.own_address}")
                ip, port = (self.tracker_address).split(":")
                sock.sendto(message.encode(), (ip, int(port)))
                # Wait for a short time for a response from the tracker
                await asyncio.sleep(0.1)
                # Close the UDP socket
                sock.close()
            # Wait for a longer period of time before sending the next keepalive message
            await asyncio.sleep(9)


if __name__ == '__main__':
    # Parse command line arguments
    args = sys.argv[1:]
    peer_id = args[3]
    share_mode = args[0] == 'share'
    file_name = args[1]
    tracker_address = args[2]
    own_address = args[3]

    # Create a new peer object and start the event loop
    peer = TorrentPeer(peer_id, share_mode, file_name, tracker_address, own_address)
    asyncio.run(peer.start())
