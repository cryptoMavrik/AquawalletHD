#!/usr/bin/env python
import json

settings_json = json.dumps([
    {'type': 'title',
        'title': 'Settings'},
    {'type': 'options',
        'title': 'Type of currency',
        'desc': 'Please select your local currency',
        'section': 'Aquachain',
        'key': 'currency',
        'options': ['USD', 'CAD', 'Euro']},
    {'type': 'string',
        'title': 'RPC Host',
        'section': 'Aquachain',
        'key': 'rpchost'},
    {'type': 'string',
        'title': 'IPC Path',
        'section': 'Aquachain',
        'key': 'ipcpath'},
    {'type': 'string',
        'title': 'Keystore',
        'section': 'Aquachain',
        'key': 'keystore'},
    {'type': 'string',
        'title': 'Fuel price',
        'section': 'Aquachain',
        'key': 'fuelprice'},
    {'type': 'numeric',
        'section': 'Aquachain',
        'title': 'Node refresh timing',
        'key': 'noderefresh'},
    {'type': 'numeric',
        'section': 'Aquachain',
        'title': 'HD Wallets',
        'key': 'hdwallets'},
    {'type': 'numeric',
        'title': 'Block limit',
        'section': 'Aquachain',
        'key': 'blocklimit'}])


default_settings = {
    'currency': 'USD',
    'rpchost': 'https://c.onical.org',
    'ipcpath': '',
    'keystore': 'data/aquakeys',
    'Theme': 'Dark',
    'fuelprice': '0.1',
    'blocklimit': '25',
    'noderefresh': '10',
    'hdwallets': '1'
    }
