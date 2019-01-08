from . import Handler
import hug
import threading
from pythonosc import udp_client, osc_server, dispatcher


class EosHandler(Handler):

    def __init__(self):
        self.name = 'eos'
        super().__init__()

        self.client = udp_client.SimpleUDPClient(
            self.config['console']['ip'],
            int(self.config['console']['rx-port'])
        )

        self.data = {'group': {}, 'preset': {}}

        self.set_eos_user(int(self.config['console']['user']))

        def data_reply_handler(address, *args):
            """Deals with groups and presets messages.
            These can include counts, data dumps, and empty returns 
            indicating the group or preset has been deleted.

            /eos/out/get/group/count=3
            /eos/out/get/group/1/list/0/3=74738347 3829383 LABEL
            """

            def delete_num_from_data(eos_type, num):
                """Delete a given Eos item from the internal data dict."""
                for k, v in self.data[eos_type].items():
                    if v == num:
                        del self.data[eos_type][k]
                        break
            
            address = address.split('/')
            eos_type = address[4]

            # Empty arguments and an address length of 6 indicates that the 
            # request address has been returned empty, so we can assume it 
            # has been deleted on the console and therefore remove it from 
            # our internal dict.

            if len(address) == 6 and not args:
                num = address[5]
                delete_num_from_data(eos_type, num)

            # Keyword 5 being count indicates we are receiving the count 
            # number for a data type in the arguments. We then request all 
            # data in the list by sending OSC requests for every index.

            elif address[5] == 'count':
                print('Found {0} {1}'.format(args[0], eos_type))
                for i in range(0, args[0]):
                    msg = '/eos/get/{0}/index/{1}'.format(eos_type, str(i))
                    self.send_osc_message(msg, 0)

            # Keyword 6 being list indicates we have received an information 
            # dump in the arguments, in this case containing the label.

            elif address[6] == 'list':
                num = address[5]
                label = args[2].upper()
                # We don't know whether this is a new group/preset or a 
                # change of name of an existing one, so we need to check if 
                # there is already a group/preset with this number in the 
                # dictionary, and if there is, delete it and add this one.
                if num in self.data[eos_type].values():
                    delete_num_from_data(eos_type, num)
                self.data[eos_type][label] = num

        def subscription_handler(address, *args):
            """Deals with all Eos automatic notifications."""
            address = address.split('/')
            # All currently supported notifications have their Eos type 
            # in keyword 4, so we can just dump everything else.
            eos_type = address[4]
            if eos_type in self.data.keys():
                num = args[1]
                self.send_osc_message(
                    '/eos/get/{0}/{1}'.format(eos_type, str(num)), 0)

        router = dispatcher.Dispatcher()
        router.map('/eos/out/get/group/*', data_reply_handler)
        router.map('/eos/out/get/preset/*', data_reply_handler)
        router.map('/eos/out/notify/*', subscription_handler)

        # Listen for OSC packets in a new thread
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

        # Subscribe to Eos updates so we can update the group and preset lists 
        # automatically
        self.send_osc_message('/eos/subscribe', 1)
        
        self.generate_label_dict()

    def generate_label_dict(self):
        """Populate the internal dict from the console.

        Sends count request commands which then cascade by requesting 
        information about all objects in the list when the count is 
        returned."""
        self.send_osc_message('/eos/get/group/count', 0)
        self.send_osc_message('/eos/get/preset/count', 0)

    def send_osc_message(self, addr, *args):
        """Send an OSC message with the specified address and arguments to the 
        client as defined in the config"""

        self.client.send_message(addr, *args)

    def send_eos_command(self, cmd):
        """Sends a clean Eos command."""
        self.send_osc_message('/eos/newcmd', cmd)

    def set_eos_user(self, user):
        """Sets the OSC user for Eos."""
        self.send_osc_message('/eos/user/', user)

    def set_preset_label(self, group, preset):
        if group.upper() not in self.data['group']:
            return 'No location called '+group
        if preset.upper() not in self.data['preset']:
            return 'No preset called '+preset
        group_n = self.data['group'][group.upper()]
        preset_n = self.data['preset'][preset.upper()]
        self.set_preset_number(group_n, preset_n)

    def set_preset_number(self, group, preset):
        cmd = ''.join(['Group ', str(group), ' Preset ', str(preset), '#'])
        self.send_eos_command(cmd)

    def get_groups(self):
        return self.data['group']

    def get_presets(self):
        return self.data['preset']


# Public API begins here

handler = EosHandler()

@hug.put('/group/apply_preset/label')
def set_preset_label(loc: hug.types.text, state: hug.types.text):
    """Set a location to a certain preset, by label."""
    return handler.set_preset_label(loc, state)

@hug.put('/group/apply_preset/number')
def set_preset_number(group: hug.types.number, preset: hug.types.number):
    """Apply a preset to a group by number."""
    handler.set_preset_number(group, preset)

@hug.get('/group')
def get_groups():
    return handler.get_groups()

@hug.get('/preset')
def get_presets():
    return handler.get_presets()
