from . import Handler

from time import sleep
import threading

import configparser
import hug
from pythonosc import udp_client, osc_server, dispatcher


class EosHandler(Handler):

    def __init__(self):
        self.name = 'eos'
        super().__init__()

        self.client = udp_client.SimpleUDPClient(
            self.config['console']['ip'],
            int(self.config['console']['rx-port'])
        )

        self.groups = {}
        self.presets = {}

        def group_reply_handler(address, *args):
            '''
            Deals with all OSC addresses which concern groups. Primary 
            function is receiving the group count, then fetching group 
            information by iterating through the count. On fetching 
            group information, add this to the internal config.
            '''
            if address == '/eos/out/get/group/count':
                print('Found {0} groups'.format(args[0]))
                for i in range(0, args[0]):
                    msg = '/eos/get/group/index/'+str(i)
                    self.send_osc_message(msg, 0)
            elif address.split('/')[6] == 'list':
                num = address.split('/')[5]
                label = args[2]
                self.groups[label] = num

        def preset_reply_handler(address, *args):
            '''
            Very similar to the above group reply handler.
            '''
            if address == '/eos/out/get/preset/count':
                print('Found {0} presets'.format(args[0]))
                for i in range(0, args[0]):
                    msg = '/eos/get/preset/index/'+str(i)
                    self.send_osc_message(msg, 0)
            elif address.split('/')[6] == 'list':
                num = address.split('/')[5]
                label = args[2]
                self.presets[label] = num

        router = dispatcher.Dispatcher()
        router.map('/eos/out/get/group/*', group_reply_handler)
        router.map('/eos/out/get/preset/*', preset_reply_handler)

        server = osc_server.ThreadingOSCUDPServer((
            self.config['server']['listen-ip'],
            int(self.config['console']['tx-port'])),
            router
        )
        server_thread = threading.Thread(target=server.serve_forever)
        try:
            server_thread.start()
        except (KeyboardInterrupt, SystemExit):
            server.shutdown()
            raise

        self.generate_label_dict()

    def generate_label_dict(self):

        self.send_osc_message('/eos/get/group/count', 0)
        self.send_osc_message('/eos/get/preset/count', 0)

    def eos_sync(self):
        self.groups = {}
        self.presets = {}
        self.generate_label_dict()

    def send_osc_message(self, addr, *args):
        '''
        Send an OSC message with the specified address and arguments to the 
        client as defined in the config
        '''

        self.client.send_message(addr, *args)

    def send_eos_command(self, cmd):
        '''
        Send a complete Eos command directly to the console.
        '''
        self.send_osc_message('/eos/cmd', cmd)

    def set_preset_label(self, group, preset):
        try:
            group_n = self.groups[group.upper()]
            preset_n = self.presets[preset.upper()]
        except KeyError as e:
            return('Nothing found called '+str(e))
        self.set_preset_number(group_n, preset_n)

    def set_preset_number(self, group, preset):
        cmd = ''.join(['Group ', str(group), ' Preset ', str(preset), '#'])
        self.send_eos_command(cmd)


# Public API begins here

handler = EosHandler()

@hug.put('/set/preset/label')
def set_preset_label(loc: hug.types.text, state: hug.types.text):
    '''Set a location to a certain preset, by label.'''
    handler.set_preset_label(loc, state)

@hug.put('/set/preset/number')
def set_preset_number(group: hug.types.number, preset: hug.types.number):
    '''Apply a preset to a group by number.'''
    handler.set_preset_number(group, preset)

@hug.get('/config/sync')
def config_sync():
    '''Resync Eos information.'''
    handler.eos_sync()
