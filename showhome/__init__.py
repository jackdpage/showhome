import hug
import handler.eos
import handler.x32


@hug.get('/')
def hello_world():
    return 'Hello from root'

hug.API(__name__).extend(handler.x32, '/x32')
hug.API(__name__).extend(handler.eos, '/eos')
