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



        # # Connect to the tracker and register the file
        # transport, protocol = await asyncio.get_event_loop().create_datagram_endpoint(
        #     TrackerProtocol(self.file_name, self.own_address), 
        #     remote_addr=self.tracker_address
        # )

        # # Wait for the registration to complete
        # await protocol.register_file()

        # # Close the connection to the tracker
        # transport.close()

        # # Print a message to indicate that the file has been registered
        # print('File {} registered with tracker'.format(self.file_name))

        

    async def get_file_info(self):



        ip, port = (self.tracker_address).split(":")
        sock = await asyncudp.create_socket(remote_addr=(ip, int(port)))
        sock.sendto(f'request {self.file_name}'.encode())
        print("send the get infor message to tracker")
        data, addr = await sock.recvfrom()
        print(f"got {data.decode()} from {addr}")
        await asyncio.sleep(0.5)
        message = data.decode().strip()
        _, peer_list = message.split("peers ")
        self.peers = [tuple(peer.split(':')) for peer in peer_list.split()]
        print(self.peers)

        # Read the file size from the first peer in the list
        self.file_size = await self.get_file_size(*self.peers[0])
        print('Received file information for {}: size={}, peers={}'.format(self.file_name, self.file_size, self.peers))
        sock.close()


        # # Connect to the tracker and request file information
        # reader, writer = await asyncio.open_connection(*self.tracker_address.split(':'))
        # message = 'request {}\n'.format(self.file_name)
        # writer.write(message.encode())

        # # Read the file size and list of peers with the file from the tracker
        # data = await reader.readline()
        # message = data.decode().strip()
        # _, filename, peer_list = message.split()
        # self.peers = [tuple(peer.split(':')) for peer in peer_list.split()]

        # # Read the file size from the first peer in the list
        # self.file_size = await self.get_file_size(*self.peers[0])

        # # Close the connection to the tracker
        # writer.close()

        # # Print a message to indicate that the file information has been received
        # print('Received file information for {}: size={}, peers={}'.format(self.file_name, self.file_size, self.peers))

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

    async def keepalive(self):
        UDP_IP = "127.0.0.1"  # IP address to listen on
        UDP_PORT = 9999  # port number to listen on

        sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM)  # UDP
        sock.bind((UDP_IP, UDP_PORT))  # bind the socket to the IP address and port

        while True:
            data, addr = sock.recvfrom(1024)  # receive up to 1024 bytes of data
            print("Received message:", data.decode())  # print the received message



peer = TorrentPeer(
    peer_id='1',
    share_mode=sys.argv[1]=='share',
    file_name=sys.argv[2],
    tracker_address=sys.argv[3],
    own_address=sys.argv[4]
)
asyncio.run(peer.start())

thread = threading.Thread(target=asyncio.run(peer.keepalive()))
thread.start()














# Sure! The TorrentPeer class is an implementation of a Peer in a P2P file-sharing network. It allows Peers to share and download files on the network, and communicates with the Tracker server to exchange information about available files and Peers.

# Here's an overview of the TorrentPeer class and its methods:

# __init__(self, peer_id, share_mode, file_name, tracker_address, own_address): This is the constructor method for the TorrentPeer class. It initializes the Peer with its unique peer_id, its share_mode (whether it is sharing or downloading a file), the name of the file_name it is sharing or downloading, the tracker_address where the Tracker server is located, and the own_address of the Peer.

# async def start(self): This method starts the Peer server and registers or requests information about the file with the Tracker server depending on the share_mode. It also starts listening for incoming connections from other Peers on the network.

# async def register_file(self): This method registers the file with the Tracker server by sending a UDP message containing the Peer ID, file name, and own address. It then receives a list of Peers that are currently sharing the file from the Tracker server.

# async def get_file_info(self): This method requests information about the file from the Tracker server by sending a UDP message containing the file name. It receives a list of Peers that are currently sharing the file and the file size from the first Peer in the list.

# async def get_file(self): This method downloads the file from one of the Peers that are currently sharing the file. It chooses a random Peer from the list and connects to it using TCP. It then requests the file and receives the file data from the Peer. Once the file transfer is complete, the Peer can choose to continue sharing the file with other Peers by registering the file with the Tracker server.

# async def get_file_size(self, host, port): This method retrieves the file size from a Peer by sending a TCP message containing the file name and receiving the file size in bytes.

# async def handle_peer_request(self, reader, writer): This method handles incoming requests from other Peers on the network. It reads the incoming message and checks if it is a file request. If it is a file request, the Peer sends the file size and data to the requesting Peer.

# Overall, the TorrentPeer class implements the necessary functionality for a Peer in a P2P file-sharing network, including registering and requesting files from the Tracker server and exchanging file data with other Peers on the network.














# Sure! Here's an example of how to use the TorrentPeer with the TorrentTracker. In this example, we will assume that the TorrentTracker is running on the same machine as the TorrentPeer, with IP address 127.0.0.1 and port number 6771.

# import asyncio
# from torrent_peer import TorrentPeer

# async def main():
#     # Initialize a TorrentPeer with a unique peer_id and the file to download
#     peer_id = 'peer1'
#     file_name = 'example.txt'
#     share_mode = 'download'
#     tracker_address = ('127.0.0.1', 6771)
#     own_address = ('127.0.0.1', 6881)
#     peer = TorrentPeer(peer_id, share_mode, file_name, tracker_address, own_address)

#     # Start the TorrentPeer
#     await peer.start()

# asyncio.run(main())
# In this example, we first create a TorrentPeer object with a unique peer_id and the name of the file to download. We also set the share_mode to 'download', indicating that we want to download the file rather than share it.

# We then specify the address of the TorrentTracker server as a tuple (127.0.0.1, 6771) and the own address of the TorrentPeer as a tuple (127.0.0.1, 6881).

# Finally, we start the TorrentPeer by calling the start method in an asyncio event loop.

# When the TorrentPeer starts, it will register with the TorrentTracker by sending a UDP message containing its peer_id, the name of the file it wants to download, and its own address. The TorrentTracker will respond with a list of Peers that are currently sharing the file, along with their addresses.

# The TorrentPeer will then choose a random Peer from the list and connect to it using TCP to download the file. Once the file transfer is complete, the TorrentPeer can choose to continue sharing the file with other Peers on the network by registering the file with the TorrentTracker.