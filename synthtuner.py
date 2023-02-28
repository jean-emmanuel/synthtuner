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
    cents = int((t + 1) / 2 * 16383) # -1,1 range to 0,16383
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

"""
MIDI list
"""
def print_list():
    port_list = ''
    for client in seq.connection_list():
        port_list += client[0] + '\n'
        for port in client[2]:
            port_list += '  ' + port[0] + '\n'
    print('Available clients / ports:\n\n%s' % port_list)

if config.list:
    print_list()
    exit(0)

"""
MIDI connection
"""
connected = False
for client in seq.connection_list():
    client_name, client_id, port_list = client
    if fnmatch(client_name, config.client):
        for port in port_list:
            port_name, port_id, connection_list = port
            if fnmatch(port_name, config.port):
                seq.connect_ports((seq.client_id, output_id), (client_id, port_id))
                print('Connected to %s:%s' % (client_name, port_name))
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
