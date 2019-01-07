# showhome

An HTTP API for controlling show control software and devices to make them useful for home automation. This gives simple access for home automation controllers such as Mycroft, reducing the complexity needed in the skills themselves.

A very limited ETC Eos implementation is demonstrated currently. 

## Installation

To run, clone this repository:
```
git clone https://github.com/jackdpage/showhome.git
cd showhome
```
Create a Python venv to install modules:
```
python3 -m venv venv
source venv/bin/activate
```
Install necessary modules (setup script coming soon):
```
pip install hug python-osc configparser
```

Run using hug (must be run from local directory):
```
cd showhome
hug -f __init__.py
```

Automated API documentation is displayed on any 404 request, so navigate to `localhost:8000/help` or similar.

Set the IP address and OSC ports of your Eos instance in `config/handler/eos.conf`.

## Usage

On running, showhome should connect to your console and download groups and presets lists. Assuming they are named, you can now use these names in the HTTP API.

For example, if you had Group 1 labelled 'KITCHEN' and Preset 1 labelled 'ON', you can apply this using cURL:
```
curl -H 'Content-Type: application/json' -X PUT -d '{"loc": "KITCHEN", "state": "ON"}' localhost:8000/eos/set/preset/label
```
