import configparser


class Handler:
    '''A Handler sends messages to a device and exposes an API using hug.'''

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(['config/handler/'+self.name+'.conf'])

    def log(self, msg):
        print('[{0}] {1}'.format(self.name, msg))
