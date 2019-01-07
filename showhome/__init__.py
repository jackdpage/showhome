import hug
import handler.eos


@hug.get('/')
def hello_world():
    return 'Hello from root'


hug.API(__name__).extend(handler.eos, '/eos')
