#!/bin/python3
# encoding: utf-8
# copyleft jean-emmanuel doucet © 2023 (gplv3)

from pyalsa import alsaseq
from pyalsa.alsaseq import SEQ_EVENT_SYSEX
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from fnmatch import fnmatch
from sys import exit

"""
CLI Config
"""
parser = ArgumentParser(
    formatter_class=ArgumentDefaultsHelpFormatter,
    description="Simple tool for tuning synths that support MTS octave tuning messages (e.g. fluidsynth)"
)
parser.add_argument('--client', type=str, nargs='+', help='midi client name (wildcards allowed)', default='')
parser.add_argument('--port', type=str, nargs='+', help='midi port name (wildcards allowed)', default='*')
parser.add_argument("--tuning", type=float, nargs=12, help="tuning for each note starting with C, 12 floats between -1 and 1 (semi-tone)", default=[0,0,0,0,0,0,0,0,0,0])
parser.add_argument("--list", action='store_true', help="list clients and ports and exit")

config = parser.parse_args()
config.client = ' '.join(config.client)
config.port = ' '.join(config.port)

"""
MIDI tuning message
"""
mts = [
    0xF0, # sysex
    0x7F, # realtime sysex
    0x7F, # device id (any)
    0x08, # tuning request
    0x09, # octave tuning
    0x7F, # channels (whatever)
    0x7F, # channels (whatever)
    0x7F, # channels (whatever)
]
for t in config.tuning:
    cents = int(round((t + 1) / 2 * 16383)) # -1,1 range to 0,16383
    mts += [
        (cents  >> 7) & 0x7F, # note tuning lsb
        cents & 0x7F,         # note tuning msb
    ]

mts.append(0xF7) # sysex end

"""
MIDI setup
"""
seq = alsaseq.Sequencer(clientname='synthtuner')
output_id = seq.create_simple_port('out', alsaseq.SEQ_PORT_TYPE_MIDI_GENERIC | alsaseq.SEQ_PORT_TYPE_APPLICATION, alsaseq.SEQ_PORT_CAP_WRITE)

writes = alsaseq.SEQ_PORT_CAP_WRITE | alsaseq.SEQ_PORT_CAP_SUBS_WRITE
def is_valid_port(client_id, port_id):
    caps = seq.get_port_info(port_id, client_id)['capability']
    return not caps & alsaseq.SEQ_PORT_CAP_NO_EXPORT and caps & writes == writes

"""
MIDI list
"""

def print_list():
    list_str = ''
    for client in seq.connection_list():
        client_name, client_id, port_list = client
        client_name_printed = False
        for port in port_list:
            port_name, port_id, connection_list = port
            if is_valid_port(client_id, port_id):
                if not client_name_printed:
                    list_str += client_name + '\n'
                list_str += '  ' + port_name + '\n'
    print('Available input clients / ports:\n\n%s' % list_str)

if config.list:
    print_list()
    exit(0)

"""
MIDI connection
"""
connected = False
ignored_clients = ['System', 'jack_midi']
for client in seq.connection_list():
    client_name, client_id, port_list = client
    if fnmatch(client_name, config.client):
        for port in port_list:
            port_name, port_id, connection_list = port
            capability = seq.get_port_info(port_id, client_id)['capability']
            if is_valid_port(client_id, port_id) and fnmatch(port_name, config.port):
                print('Connecting to %s:%s' % (client_name, port_name))
                seq.connect_ports((seq.client_id, output_id), (client_id, port_id))
                connected = True

"""
MIDI send
"""
if connected:
    event = alsaseq.SeqEvent(SEQ_EVENT_SYSEX)
    event.set_data({'ext': mts})
    event.source = (seq.client_id, output_id)
    seq.output_event(event)
    seq.drain_output()
    print('Tuning sent.')
else:
    print('No matching port to connect to.')
    print_list()
