from . import Handler
import hug
import socket
import threading
from collections import Iterable
from pythonosc import udp_client, osc_server, dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder


# The included SimpleUDPClient class does not allow you to build messages 
# with no values, which X32 requires. Therefore we add a check in this class
# to pass an empty string as no values. (An empty string cannot be sent in 
# an OSC message anyway so it is fine to do this). Other than that, this is 
# a rewrite of the SimpleUDPClient class.

class ExtendedUDPClient(udp_client.UDPClient):

    def send_message(self, address, value):
        builder = OscMessageBuilder(address=address)
        if value != '':
            if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
                values = [value]
            else:
                values = value
            for val in values:
                builder.add_arg(val)
        msg = builder.build()
        self.send(msg)


class ReuseAddressServer(osc_server.ThreadingOSCUDPServer):
    allow_reuse_address = True


class X32Handler(Handler):

    def __init__(self):
        self.name = 'x32'
        super().__init__()

        self.client = ExtendedUDPClient(
            self.config['console']['ip'],
            int(self.config['console']['rx-port'])
        )

        # Because the X32 returns OSC messages to the port from which they 
        # were sent, we need to reuse the socket for both the client and 
        # server. Therefore we manually bind the socket to a port, set the 
        # socket reuse flags on the socket and UDPServer, and then bind the 
        # server to the same socket. For explanation, see this SO thread and 
        # GitHub issue: https://bit.ly/2FmvVap
        # https://github.com/attward/python-osc/issues/41

        self.client._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client._sock.bind(('0.0.0.0', int(self.config['server']['port'])))
        client_address, client_port = self.client._sock.getsockname()

        self.data = {'ch': {}, 'bus': {}}       

        def channel_handler(address, *args):
            address = address.split('/')
            ch = address[2]
            if address[4] == 'name' and args:
                self.data['ch'][args[0].upper()] = ch

        def bus_handler(address, *args):
            address = address.split('/')
            bus = address[2]
            if address[4] == 'name' and args:
                self.data['bus'][args[0].upper()] = bus

        router = dispatcher.Dispatcher()
        router.map('/ch/*', channel_handler)
        router.map('/bus/*', bus_handler)

        # Listen for OSC packets in a new thread
        server = ReuseAddressServer((
            self.config['server']['listen-ip'],
            client_port),
            router
        )
        server_thread = threading.Thread(target=server.serve_forever)
        try:
            server_thread.start()
        except (KeyboardInterrupt, SystemExit):
            server.shutdown()

        self.generate_label_dict()
        self.x32_subscribe()

    def x32_subscribe(self):
        threading.Timer(9, self.x32_subscribe).start()
        self.send_osc_message('/xremote', '')

    def generate_label_dict(self):
        for i in range(1, 33):
            address = '/ch/{0}/config/name'.format(str(i).zfill(2))
            self.send_osc_message(address, '')
        for i in range(1, 17):
            address = '/bus/{0}/config/name'.format(str(i).zfill(2))
            self.send_osc_message(address, '')

    def send_osc_message(self, addr, *args):
        """Send an OSC message with the specified address and arguments to the 
        client as defined in the config"""

        self.client.send_message(addr, *args)

    def ch_route_label(self, src, dest, switch):
        if src.upper() not in self.data['ch']:
            return 'No source called '+src
        if dest.upper() not in self.data['bus']:
            return 'No output called '+dest
        ch_n = self.data['ch'][src.upper()]
        bus_n = self.data['bus'][dest.upper()]
        self.ch_route_number(ch_n, bus_n, switch)

    def ch_route_number(self, ch_n, bus_n, switch):
        if switch == 'on':
            self.send_osc_message('/ch/{0}/mix/{1}/on'.format(ch_n, bus_n), 1)
        if switch == 'off':
            self.send_osc_message('/ch/{0}/mix/{1}/on'.format(ch_n, bus_n), 0)


handler = X32Handler()

@hug.put('/ch/on/label')
def bus_on(src, dest):
    return handler.ch_route_label(src, dest, 'on')

@hug.put('/ch/off/label')
def bus_off(src, dest):
    return handler.ch_route_label(src,dest, 'off')
