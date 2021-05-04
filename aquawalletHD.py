#!/usr/bin/env python3


#Local Func
from data import aquasettings, keystore
from data.aquachain import AquaTool

#Core Func
import binascii
from Crypto.PublicKey import RSA
import datetime
import math
import os
from os import chmod
import requests, json
import subprocess
from subprocess import Popen, PIPE, STDOUT
import sys
import time
from mnemonic import Mnemonic

#Kivy Func
from kivy import Logger
from kivymd.app import MDApp
from kivy.animation import Animation
from kivy.base import runTouchApp
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Ellipse, Rectangle
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty, OptionProperty, ObjectProperty, NumericProperty
from kivy.properties import BoundedNumericProperty, ReferenceListProperty, BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.settings import SettingsWithSidebar
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

#KivyMD Func
from kivymd.material_resources import DEVICE_TYPE
import kivymd.material_resources as m_res
from kivymd.theming import ThemeManager, ThemableBehavior
from kivymd.uix.behaviors.backgroundcolorbehavior import SpecificBackgroundColorBehavior
from kivymd.uix.behaviors.elevation import RectangularElevationBehavior
from kivymd.uix.bottomsheet import MDListBottomSheet, MDGridBottomSheet
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton, MDRectangleFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import ILeftBody, IRightBody, OneLineListItem, TwoLineListItem, MDList
from kivymd.uix.card import MDCard, MDSeparator
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDToolbar

#Define Local Settings
aquachain_assets = 'data'
Builder.load_file(os.path.join(aquachain_assets, 'aquachain.kv'))
aquaconf = 'Aquachain' # the string
log = Logger

class IconLeftWidget(ILeftBody, MDIconButton):
    pass
class IconLeftWidget(IRightBody, MDIconButton):
    pass

#Kivy MDApp Class
class Aquachain(MDBoxLayout):
    # account chooser
    choose_account = []
    # account for send from and mine to
    coinbase = ""
    # public address for balance, recv.
    # if sending, use either mkeys or an rpc call
    addresses = []
    # map of account balances
    balances = {}
    # total balance sum
    balance = 0.00
    # current head block
    head = {}
    # private key storage
    private_keys = {}
    # history of sent transactions
    sent_tx = []
    synced = False
    #saved contacts placeholder
    contacts = {"saved": {'0x6086337ac44cdde1eeab5b539e6d1f69a7ca9133': 'donate'}}
    #recent tx placeholder
    recent =  {"recent": []}
    #config bug fix
    config = Config
    #List of Loaded Seed Phrases
    mkeys = []
    viewonly = True


    def __init__(self, app, **kwargs):
        super(Aquachain, self).__init__(**kwargs)
        self.theme_cls = ThemeManager()
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = 'Teal'
        self.theme_cls.primary_hue = '400'
        self.theme_cls.primary_dark_hue = '200'
        self.theme_cls.accent_palette = 'Red'
        self.theme_cls.accent_hue = '400'
        self.theme_cls.main_background_color = 'Grey 900'
        self.root = app
        self.config = app.config
        self.aqua = AquaTool(ipcpath=self.config.get(aquaconf, 'ipcpath'), rpchost=self.config.get(aquaconf, 'rpchost'))
        self.ids.balance.text = 'Click to Show'
        Clock.schedule_once(self.start_refresher, 1)
        self.block_cache = self.getblock_cache() # unused
        self.keystore = keystore.Keystore(directory=os.path.expanduser(self.config.getdefault(aquaconf, 'keystore', '.'))) # pubkey to filename
        log.info("using keystore: %s", self.keystore.directory)

    def start_refresher(self, dt):
        self.clock = Clock.schedule_interval(self.refresh_block, float(self.config.getdefault(aquaconf, 'noderefresh', '2.5')))

    def refresh_block(self, dt):
        log.debug("refreshing after %s seconds", dt)
        self.update()

    def getblock_cache(self):
        foo = []
        for i in range(self.config.getdefaultint(aquaconf, 'blocklimit', 100)):
            foo.append({})
        log.info(f"allocated {len(foo)}")
        return foo
    # get latest head block
    def update(self):
        log.debug("connecting to rpc: %s", self.aqua.providers[0])
        try:
            newhead = self.aqua.gethead()
            log.debug("connected to rpc: %s", self.aqua.providers[0])
        except Exception as e:
            Snackbar(text="Please start aquachain node or change host in settings", duration=0.5).show()
            log.info("unable to connect to rpc: %s", e)
            return

        if 'number' not in newhead:
            del(newhead)
            log.error("no head block")
            return

        if newhead == None or newhead == '':
            del(newhead)
            log.error("no head block!")
            return

        if 'number' in self.head and self.head['number'] == newhead['number']:
            del(newhead)
            log.debug("same head, bailing")
            return
        log.info("new head block")
        self.head = newhead
        if self.ids.scr_mngr.current == 'blockchain':
            self.getHistory(self.config.getdefaultint(aquaconf, 'blocklimit', 20))
        if not self.synced:
            self.getHistory(self.config.getdefaultint(aquaconf, 'blocklimit', 20))
        self.synced = True
        del(newhead)
        Snackbar(text=f"New blockchain height: {str(int(self.head['number'], 16))}").show()
        if 'number' in self.head:
            log.info("new head number %s", str(int(self.head['number'], 16)))
            log.info("header hash %s", self.head['hash'])
            log.info("header mined by %s", self.head['miner'])
            log.info("header version %s", self.head['version'])
            self.ids.block.text = str(int(self.head['number'], 16))
    #addresses are only rpc addresses
    def load_accounts_from_node(self):
        self.addresses.clear()
        self.addresses = self.aqua.getaccounts()
        Snackbar(text=f'found {len(self.addresses)} accounts from RPC').show()
        return

    def toggle_display_balance(self, text):
        if len(self.addresses) == 0 and len(self.balances) == 0:
            Snackbar(text="Open an account first", duration=1).show()
            return 'Click to Show'
        if text == 'Click to Show':
            self.refresh_balance()
            return str(self.balance)
        else:
            return 'Click to Show'

    def getblock_cache(self):
        foo = []
        for i in range(self.config.getdefaultint(aquaconf, 'blocklimit', 100)):
            foo.append({})
        log.info(f"allocated {len(foo)}")
        return foo

    def open_account(self, viewonly=False):
        self.viewonly = viewonly
        if self.ids.account_use_import.active == True:
            self.popup_import_mnem()
        elif self.ids.account_use_new.active == True:
            self.popup_mnem_gen()
        elif self.ids.account_use_file.active == True:
            self.popup_import_directory(viewonly=viewonly)
        elif self.ids.account_use_node.active:
            self.load_accounts_from_node()
            self.switch_view("coinbasechooser", "up")
        else:
            Snackbar(text="Oops you forgot to check one.").show()
            log.info(self.ids.account_use_new.active)

    def add_hdwallet(self, phrase, saving=True, num=1, viewonly=False):
        phrase = phrase.strip()
        words = phrase.split(" ")
        if len(words) != 12:
            log.error("invalid phrase length: %s \n", len(phrase.split(" ")))
            Snackbar(text="Phrase empty or invalid!").show()
            return
        for word in words:
            if word not in Mnemonic('english').wordlist:
                raise ValueError(f"invalid word: {word}")
        log.info("add_wallet: %s, saving=%s", words[0], saving)
        mkey = self.keystore.load_phrase(phrase)
        for existing in self.mkeys:
            if existing['phrase'] == phrase:
                log.info("dupe detect")
                Snackbar(text="Duplicate Wallet! Action Aborted!").show()
                return
        if saving:
            self.keystore.save_phrase(phrase)
        if not viewonly:
            self.mkeys.append({'phrase': phrase, "key": mkey})
            log.debug("added mkey (not viewonly)")
        for i in range(num):
            key = self.aqua.derive_hd(mkey, i)
            pub = key.public_key.address()
            log.info("added pubkey from mkey %s", pub)
            self.balances[pub] = self.aqua.getbalance(pub)
            log.info("New account #%s: %s", i, key.public_key.address())
        self.refresh_balance()

    def popup_mnem_gen(self):
        content = MDGridLayout(cols=1)
        phrase = self.aqua.generate_phrase()
        mnem = MDTextField(
                           multiline=True,
                           text=phrase,
                           hint_text="Seed Phrase",
                           required=False
                           )
        content.size_hint_y=None
        content.add_widget(mnem)
        def refresh(instance):
            mnem.text = self.aqua.generate_phrase()
            log.info(mnem.text)
            return True
        def copy2clip(instance):
            log.info(mnem.text)
            Clipboard.copy(mnem.text)
            Snackbar(text="Copied to clipboard!").show()
        def create(instance):
            log.info(mnem.text)
            self.add_hdwallet(mnem.text, num=self.config.getdefaultint(aquaconf, 'hdwallets', 1))
            dialog.dismiss()
            self.switch_view('coinbasechooser', 'up')
        dialog = MDDialog(title="[color=008080]Write down this phrase or generate new[/color]",
                          type="custom",
                          content_cls=content,
                          size_hint=(.8, .8),
                          auto_dismiss=False,
                          buttons=[
                                   MDFlatButton(
                                                text="CANCEL", text_color=self.theme_cls.accent_color,
                                                on_release=lambda *x: dialog.dismiss()
                                                ),
                                   MDFlatButton(
                                                text="GENERATE", text_color=self.theme_cls.primary_color,
                                                on_release=refresh
                                                ),
                                   MDFlatButton(
                                                text="COPY", text_color=self.theme_cls.primary_color,
                                                on_release=copy2clip
                                                ),
                                   MDFlatButton(
                                                text="CREATE", text_color=self.theme_cls.primary_color,
                                                on_release=create
                                                )]
                         )
        dialog.open()

    def popup_import_file(self, viewonly=False):
        return self.popup_import_directory(viewonly=viewonly)

    def popup_import_directory(self, viewonly=False):
        self.findkey(viewonly=viewonly)

    def findkey(self, viewonly=False):
        self.keystore.directory = self.config.get(aquaconf, 'keystore')
        content = MDGridLayout(cols=1, size_hint_y=None, row_default_height=dp(35))
        keylist = MDList(valign='top')
        keydrop = DropDown()
        content.add_widget(keylist)
        phrases = keystore.Keystore(directory=self.keystore.directory).listphrases()
        keys = []
        phrase = ''
        i=0
        for p in phrases:
            keys.append(p.split()[0])
            phrase = p
        for key in keys:
            log.debug(key)
            listitem = MDRaisedButton(text=key.capitalize(), size_hint=(1,None))
            listitem.bind(on_release=lambda listitem: keydrop.select(listitem.text))
            keydrop.add_widget(listitem)
        if keys == []:
            mainbutton = OneLineListItem(text='CREATE OR IMPORT A SEED', font_style='Subtitle1')
        else:
            mainbutton = OneLineListItem(text='SELECT A WALLET', font_style='Subtitle1')
        def doit(y):
            setattr(mainbutton, 'text', y)
        mainbutton.bind(on_release=keydrop.open)
        keydrop.bind(on_select=lambda instance, x: doit(x))
        keylist.add_widget(mainbutton)
        def getkey(instance):
            phrase = ''
            for t in phrases:
                if mainbutton.text.lower() in t:
                    phrase = t
            self.add_hdwallet(phrase, saving=False, viewonly=viewonly, num=self.config.getdefaultint(aquaconf, 'hdwallets', 1))
            popdialog.dismiss()
            self.switch_view('coinbasechooser', 'up')
        popdialog = MDDialog(title="[color=008080]Which key would you like to import?[/color]",
                             type="custom",
                             content_cls=content,
                             size_hint=(.55,.6),
                             auto_dismiss=False,
                             buttons=[
                                      MDFlatButton(
                                                   text='CANCEL',
                                                   theme_text_color= "Custom",
                                                   text_color= self.theme_cls.accent_color,
                                                   on_release=lambda *x: popdialog.dismiss()
                                                   ),
                                      MDFlatButton(
                                                   text='UNLOCK',
                                                   theme_text_color= "Custom",
                                                   text_color= self.theme_cls.primary_color,
                                                   on_release=getkey
                                                   )
                                     ]
                            )
        popdialog.open()

    def popup_import_mnem(self, viewonly=False):
        def findmnem(instance):
            try:
                self.add_hdwallet(
                                  mnem.text,
                                  saving=saving_choice.active,
                                  viewonly=viewonly,
                                  num=self.config.getdefaultint(
                                                                aquaconf,
                                                                'hdwallets',
                                                                1
                                                               )
                                 )
            except Exception as oo:
                Snackbar(text=f"Error: {oo}", duration=5).show()
                dialog.dismiss()
                return
            dialog.dismiss()
            self.switch_view('coinbasechooser', 'up')
        content = MDGridLayout(cols=1)
        mnem = MDTextField()
        mnem.hint_text = "Enter Seed"
        mnem.helper_text= "Enter Seed"
        chex = BoxLayout()
        saving_choice = MDCheckbox(
                                   text="Save to File",
                                   active=True,
                                   size_hint= (None,None),
                                   size= (dp(34),dp(48))
                                   )
        saving_label = MDLabel(
                               theme_text_color = "Primary",
                               text = "Save to file",
                               font_style = 'Body2'
                              )
        chex.add_widget(saving_choice)
        chex.add_widget(saving_label)
        content.add_widget(mnem)
        content.add_widget(chex)
        dialog = MDDialog(
            title="[color=008080]Enter mnemonic phrase to recover key[/color]",
            type="custom",
            content_cls=content,
            auto_dismiss=False,
            buttons=[
                    MDFlatButton(
                                 text="CANCEL",
                                 theme_text_color= "Custom",
                                 text_color= self.theme_cls.accent_color,
                                 on_release=lambda *x: dialog.dismiss()
                                 ),
                    MDFlatButton(
                                 text="IMPORT",
                                 theme_text_color= "Custom",
                                 text_color= self.theme_cls.primary_color,
                                 on_release=findmnem
                                 )
                    ]
            )
        dialog.open()
    # set new coinbase
    def set_coinbase(self, acct):
        self.coinbase = acct
        log.info("New coinbase is: %s",format(self.coinbase))

    def send_confirm(self, fromwallet, to, amount):
        content = GridLayout(cols= 1)
        contents = MDLabel(
                           text="Sending " + amount + "AQUA to " + to,
                           theme_text_color="Primary",
                           font_style="Subtitle2"
                          )
        content.add_widget(contents)
        def sendcoin(instance):
            self.sendCoin(fromwallet, to, amount)
            log.info("CONFIRM")
            dialog.dismiss()
            return
        dialog = MDDialog(
                          title="[color=008080]Are you sure?[/color]",
                          type="custom",
                          content_cls=content,
                          auto_dismiss=False,
                          buttons=[
                                   MDFlatButton(
                                                text="CANCEL TX",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.accent_color,
                                                on_release=lambda x: dialog.dismiss()
                                                ),
                                   MDRectangleFlatButton(
                                                         text="CONFIRM",
                                                         on_release=sendcoin
                                                         )
                                  ]
                         )
        dialog.open()
    # fill account chooser menu (address and balance)
    def fillMenu(self):
        self.ids.newlist.clear_widgets()
        dropdown = DropDown()
        accounts = []
        #if len(self.addresses) > 0:
        #    for acct in self.aqua.getaccounts():
        #        accounts.append(acct)
        for acct in self.balances:
            accounts.append(acct)
        # check no accounts
        if len(accounts) < 1:
            log.error("no accounts found. you must create a new account.")
            self.choose_account = []
            return
        # check already filled
        if len(self.choose_account) == len(accounts):
            log.debug("already filled, not refilling menu")
            return
        self.refresh_balance()
        self.choose_account = []
        # fill menu chooses coinbase
        log.info("fillMenu() filling with %s accounts: %s", len(accounts), accounts)
        mainbutton = TwoLineListItem(
                                     text='Coinbase (click to change)',
                                     secondary_text='Select Account' if self.coinbase == '' else self.coinbase,
                                     font_style='Subtitle2',
                                     secondary_font_style='Subtitle1'
                                     )

        def doit(y):
            setattr(mainbutton, 'secondary_text', y)
            check = y.split(" ")[1][:8]
            for addr in self.balances:
                if check in addr:
                    log.info("yes %s in %s", check, addr)
                    self.set_coinbase(addr)
                    return
                else:
                    log.info("not %s in %s", check, addr)
            for addr in self.addresses:
                if check in addr:
                    log.info("yes %s in %s", check, addr)
                    self.set_coinbase(addr)
                    return
                else:
                    log.info("not %s in %s", check, addr)
                log.error("skipping %s", addr)
        i = 0
        for account in accounts:
            log.debug(account)
            if account in self.balances:
                bal = self.balances[account]
            else:
                bal = self.aqua.getbalance(account)
            list_text = str(i+1)+ ':' + ' ' + str(account[:20]) + '        Balance:' + str(bal)
            listitem = MDRaisedButton(
                                      size_hint=(1,None),
                                      text = list_text
                                      )
            listitem.bind(on_release=lambda listitem: dropdown.select(listitem.text))
            dropdown.add_widget(listitem)
            i = i+1
        mainbutton.bind(on_release=dropdown.open)
        dropdown.bind(on_select=lambda instance, x: doit(x))
        self.ids.newlist.add_widget(mainbutton)

    #sendcoin using rpc's unlocked wallet
    def sendCoin(self, fromwallet, to, amount):
        gasprice = self.config.get(aquaconf, 'fuelprice')
        log.info("from: %s, to: %s, amount: %s", fromwallet, to, self.aqua.to_wei(amount))
        txhash = ''
        tx = {
            'from': self.aqua.checksum_encode(fromwallet),
            'to': self.aqua.checksum_encode(to),
            'value': hex(self.aqua.to_wei(amount)),
            'gasPrice': hex(self.aqua.to_wei(gasprice, 'gwei')),
            'gas': 21000,
            'nonce': hex(self.aqua.get_nonce(fromwallet, 'pending'))
        }
        if fromwallet in self.private_keys:
            log.info("sending transaction (HD): (%s) %s", fromwallet, tx)
            try:
                rawtx = self.aqua.sign_tx(self.private_keys[fromwallet], tx)
                log.info("Raw Signed TX: %s", rawtx)
                txhash = self.aqua.send_raw_tx(rawtx)
                if isinstance(txhash, Exception):
                    Snackbar('Transaction Failed', duration=1).show()
                    raise txhash
                log.info("Submitted TX: %s", txhash)
                Snackbar(text="Transaction Sent: %s" % txhash).show()
                self.addRecent(txhash)
                self.popup_contacts(tx['to'])
                return txhash
            except Exception as e:
                log.error("RPC returned error: %s", e)
                return ''
    # switch view
    def switch_view(self, page, direction):
        log.debug("switching view to %s, direction %s", page, direction)
        if page == 'send':
            if len(self.balances) == 0 and len(self.addresses) == 0:
                Snackbar(text="Open an account first", duration=1).show()
                self.switch_view('welcome', 'down')
                return
            if self.viewonly:
                Snackbar(text="You are in view-only mode").show()
                return
            self.fillMenu()
        if page == 'history':
            self.myHistory()
        if page == 'coinbasechooser':
            if len(self.balances) == 0 and len(self.addresses) == 0:
                Snackbar(text="Open an account first", duration=1).show()
                self.switch_view('welcome', 'down')
                return
            self.get_coinbase_view()
        if page == 'blockchain':
            self.getHistory(limit=self.config.getdefaultint(aquaconf, 'blocklimit', 10))
        if page == 'search':
            self.ids.blocktabs._current_tab = self.ids.blocktabs.tab_list[2]
            page = 'blockchain'

        if page == 'current_block':
            self.popup_block(self.head['hash'])
            return
        if page == 'addresses':
            self.build_address_book()
        self.ids.scr_mngr.transition.direction = direction
        self.ids.scr_mngr.current = page

    def get_coinbase_view(self):
        grid = self.ids.cbasegrid
        grid2 = self.ids.cbasegrid2
        grid.clear_widgets()
        grid2.clear_widgets()
        grid.add_widget(MDFlatButton(text="Type"))
        grid.add_widget(MDFlatButton(text="Balance"))
        grid.add_widget(MDFlatButton(text="Address"))
        grid2.add_widget(MDFlatButton(text="Type"))
        grid2.add_widget(MDFlatButton(text="Balance"))
        grid2.add_widget(MDFlatButton(text="Address"))
        def funky(instance):
            pub = instance.text
            log.info("clicked button: %s", instance.text)
            balance = str(self.aqua.getbalance(pub))
            log.info("launching popup: %s %s", pub, balance)
            self.popup_acct({
                             'Address': pub,
                             'Balance': str(balance),
                             'Type': 'personal'
                             })
        for acct in self.addresses:
            balance = self.aqua.getbalance(acct)
            log.info("found rpc account: %s", acct)
            grid2.add_widget(MDFlatButton(text="VIEW RPC"))
            grid2.add_widget(MDFlatButton(text=str(balance)))
            grid2.add_widget(MDFlatButton(text=acct))
        if not self.viewonly:
            for mkey in self.mkeys:
                if 'phrase' not in mkey:
                    continue
                for i in range(self.config.getdefaultint(aquaconf, 'hdwallets', 1)):
                    key = self.keystore.from_parent_key(mkey['key'], i)
                    pub = key.public_key.address()
                    if pub == '':
                        continue
                    balance = self.aqua.getbalance(pub)
                    self.private_keys[pub] = key._key.to_hex()
                    self.balances[pub] = balance
                    log.info("balance map: %s", self.balances)
                    grid.add_widget(MDFlatButton(text=f'HD ({mkey["phrase"].split(" ")[0]} {i})'))
                    grid.add_widget(MDFlatButton(text=str(balance)[:9]))
                    grid.add_widget(MDFlatButton(text=pub, on_release=funky))
        else:
            i = 1
            for pub in self.balances:
                balance = self.aqua.getbalance(pub)
                grid.add_widget(MDFlatButton(text=f'VIEW HD {i}'))
                grid.add_widget(MDFlatButton(text=str(balance)[:9]))
                grid.add_widget(MDFlatButton(text=pub))
                i += 1

    def popup_acct(self, acct):
        # callbacks
        pub = acct['Address']
        def copy2clip(instance):
            Clipboard.copy(acct['Address'])
            Snackbar(text="Copied to clipboard!").show()
        def coinbasesetter(instance):
            pub = acct['Address']
            self.set_coinbase(pub)
            Snackbar(text=f'New coin base: {pub}', duration=3).show()
        def send(instance):
            pub = acct['Address']
            self.ids.send_addr.text = pub
            self.switch_view('send', 'up')
            dialog.dismiss()
        grid = MDGridLayout(cols=1)
        dialog = MDDialog(
                          title='[color=008080]Account[/color]',
                          type="custom",
                          content_cls=grid,
                          auto_dismiss=False,
                          buttons=[
                                   MDFlatButton(
                                                text='Set Coinbase',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=coinbasesetter
                                                ),
                                   MDFlatButton(
                                                text='Copy',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=copy2clip
                                                ),
                                   MDFlatButton(
                                                text="Send TX",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=send
                                                ),
                                   MDFlatButton(
                                                text="OK",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=lambda x: dialog.dismiss()
                                                )
                                   ]
                         )
        log.info('acct: %s', acct)
        txt = ''
        grid2 = MDGridLayout(cols=3, spacing=dp(10))
        for text in acct:
            if text in ['Address', 'Balance', 'Type']:
                txt = str(acct[text])
            else:
                raise Exception("unknown field: %s" % text)
            foolabel = MDLabel(theme_text_color = "Primary", text=f'{text}: {txt}', font_style='Subtitle1')
            grid.add_widget(foolabel)
        grid.add_widget(grid2)
        dialog.open()

    def popup_miner(self, acct):
        # callbacks
        pub = acct['Address']
        def copy2clip(instance):
            Clipboard.copy(acct['Address'])
            Snackbar(text="Copied to clipboard!").show()
        def send(instance):
            pub = acct['Address']
            self.ids.send_addr.text = pub
            self.switch_view('send', 'up')
            dialog.dismiss()
        def add(instance):
            if acct['Type'] == 'Saved':
                Snackbar(text='Contact Already Exists').show()
            else:
                self.popup_addcontact(pub)
        grid = MDGridLayout(cols=1)
        dialog = MDDialog(
                          title='[color=008080]Miner Account[/color]',
                          type="custom",
                          content_cls=grid,
                          auto_dismiss=False,
                          buttons=[
                                   MDFlatButton(
                                                text="Add Contact",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=send
                                                ),
                                   MDFlatButton(
                                                text='Copy',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=copy2clip
                                                ),
                                   MDFlatButton(
                                                text="OK",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=lambda x: dialog.dismiss()
                                                )
                                   ]
                         )
        log.info('acct: %s', acct)
        txt = ''
        grid2 = MDGridLayout(cols=3, spacing=dp(10))
        for text in acct:
            if text in ['Address', 'Balance', 'Type']:
                txt = str(acct[text])
            else:
                raise Exception("unknown field: %s" % text)
            foolabel = MDLabel(theme_text_color = "Primary", text=f'{text}: {txt}', font_style='Subtitle1')
            grid.add_widget(foolabel)
        grid.add_widget(grid2)
        dialog.open()
    def popup_recent(self, acct):
        # callbacks
        pub = acct['Address']
        def add(instance):
            if acct['Type'] == 'Saved':
                Snackbar(text='Contact Already Exists').show()
            else:
                self.popup_addcontact(pub)
        def copy2clip(instance):
            Clipboard.copy(acct['Address'])
            Snackbar(text="Copied to clipboard!").show()
        def send(instance):
            pub = acct['Address']
            self.ids.send_addr.text = pub
            self.switch_view('send', 'up')
            dialog.dismiss()
        grid = MDGridLayout(cols=1)
        dialog = MDDialog(
                          title='[color=008080]Account[/color]',
                          type="custom",
                          content_cls=grid,
                          auto_dismiss=False,
                          buttons=[
                                   MDRaisedButton(
                                                text='Add Contact',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=add
                                                ),
                                   MDFlatButton(
                                                text='Copy',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=copy2clip
                                                ),
                                   MDFlatButton(
                                                text="Send TX",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=send
                                                ),
                                   MDFlatButton(
                                                text="OK",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=lambda x: dialog.dismiss()
                                                )
                                   ]
                         )
        log.info('acct: %s', acct)
        txt = ''
        grid2 = MDGridLayout(cols=3, spacing=dp(10))
        for text in acct:
            if text in ['Address', 'Balance', 'Type']:
                txt = str(acct[text])
            else:
                raise Exception("unknown field: %s" % text)
            foolabel = MDLabel(theme_text_color = "Primary", text=f'{text}: {txt}', font_style='Subtitle1')
            grid.add_widget(foolabel)
        grid.add_widget(grid2)
        dialog.open()

    def popup_saved(self, acct):
        # callbacks
        pub = acct['Address']
        def send(instance):
            pub = acct['Address']
            self.ids.send_addr.text = pub
            self.switch_view('send', 'up')
            dialog.dismiss()
        def remove(instance):
            pub = acct['Address']
            if pub in self.contacts['saved']:
                del(self.contacts['saved'][pub])
                self.write_contacts_file()
                self.build_address_book()
                Snackbar(text="removed contact").show()
            else:
                Snackbar(text="could not find contact").show()
            dialog.dismiss()
        def update_contact(instance):
            pub = acct['Address']
            note = self.contacts['saved'][pub]
            if len(note) == 1:
                note = note[0]
            self.popup_editcontact(pub=pub, note=note)
        grid = MDGridLayout(cols=1)
        dialog = MDDialog(
                          title='[color=008080]Account[/color]',
                          type="custom",
                          content_cls=grid,
                          auto_dismiss=False,
                          buttons=[
                                   MDFlatButton(
                                                text='Remove Contact',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=remove
                                                ),
                                   MDFlatButton(
                                                text='Edit Contact',
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=update_contact
                                                ),
                                   MDFlatButton(
                                                text="Send TX",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=send
                                                ),
                                   MDFlatButton(
                                                text="OK",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=lambda x: dialog.dismiss()
                                                )
                                   ]
                         )
        log.info('acct: %s', acct)
        txt = ''
        grid2 = MDGridLayout(cols=3, spacing=dp(10))
        if acct['Type'] == 'contact':
            pub = acct['Address']
            note = self.contacts['saved'][pub]
            if len(note) == 1:
                note = note[0]
            grid.add_widget(MDLabel(theme_text_color = "Primary", text='Note: '+note, font_style='Subtitle1'))
        for text in acct:
            if text in ['Address', 'Balance', 'Type']:
                txt = str(acct[text])
            else:
                raise Exception("unknown field: %s" % text)
            foolabel = MDLabel(theme_text_color = "Primary", text=f'{text}: {txt}', font_style='Subtitle1')
            grid.add_widget(foolabel)
        grid.add_widget(grid2)
        dialog.open()
    # refresh balance(s) and update displays
    def refresh_balance(self):
        log.info(self.balances)
        self.balance = 0.00
        if len(self.balances) > 0:
            for account in self.balances:
                if account == '':
                    continue
                bal = float(self.aqua.getbalance(account))
                self.balances[account] = bal
                self.balance += bal
        if len(self.balances) < 1 and len(self.addresses) < 1:
            log.info("no addresses")
            self.ids.balance.text = "no accounts"
            Snackbar(text ="No Accounts").show()
            return
        log.info("found %s rpc accounts: %s", len(self.addresses), self.addresses)
        for account in self.addresses:
            if account == '':
                continue
            bal = float(self.aqua.getbalance(account))
            self.balance += bal
        log.info("balance refreshed")

    def build_address_book(self):
        self.ids.saved_cont.clear_widgets()
        self.ids.saved_cont.add_widget(MDFlatButton(text="Name"))
        self.ids.saved_cont.add_widget(MDFlatButton(text="Address"))
        self.ids.recent_cont.clear_widgets()
        self.ids.recent_cont.add_widget(MDFlatButton(text="Amount"))
        self.ids.recent_cont.add_widget(MDFlatButton(text="Address"))
        self.ids.recent_cont.add_widget(MDFlatButton(text="TX"))
        add_btn = MDIconButton(
                               icon='plus',
                               on_release= lambda x: self.popup_addcontact('',''),
                               text_color= self.theme_cls.primary_color
                               )
        i=0
        c=0
        if os.path.isfile('data/contacts.json'):
            with open('data/contacts.json') as f:
                json_data = json.load(f)
                log.info(f'Json Data: {json_data}')
                self.contacts = json_data
                log.info(self.contacts)
        if os.path.isfile('data/recent.json'):
            with open('data/recent.json', 'r') as f:
                json_data = json.load(f)
                log.info(f'Json Data: {json_data}')
                self.recent = json_data
                log.info(self.recent)
        def foo(instance):
            bal = 'INVALID ACCT'
            try:
                bal = self.aqua.getbalance(instance.text)
            except Exception as e:
                Snackbar(text="invalid account?", duration=1).show()
                log.error("got error: %s", e)
            self.popup_saved({
                             'Address': instance.text,
                             'Balance': bal,
                             'Type':'contact'
                             })
        def foo_tx(hash):
            try:
                txhash = hash
                log.info(txhash)
                tx = self.aqua.gettransaction(txhash)
                self.popup_tx(tx)
            except Exception as e:
                Snackbar(text="Waiting for new block or the tx was invalid.", duration=1).show()
                log.debug("block not found: %s", e)
        def foo_acct(acct):
            pub = acct
            balance = self.aqua.getbalance(str(pub))
            try:
                log.info("launching popup: %s %s", pub, balance)
                self.popup_recent({
                               'Address': pub,
                               'Balance': balance,
                               'Type': 'personal'
                               })
            except Exception as e:
                Snackbar(test="Something went wrong").show()
                pass
        if 'saved' not in self.contacts:
            Snackbar(text="no contacts in saved file").show()
            pass
        for t in self.contacts['saved']:
            log.info("contacts %s: %s", t, self.contacts['saved'])
            address = t
            note = self.contacts['saved'][address]
            if len(note) == 1:
                note = note[0]
            self.ids.saved_cont.add_widget(MDFlatButton(text=note[:10]))
            self.ids.saved_cont.add_widget(MDFlatButton(text=address, on_release=foo))
        if 'recent' not in self.recent:
            Snackbar(text="No recent transactions.").show()
            pass
        for txhash in self.recent['recent']:
            tx = self.aqua.gettransaction(txhash)
            log.info(f"Loading recent tx: {tx}")
            if 'to' in tx:
                dest = tx['to']
                tx_hash = tx['hash']
                amount = self.aqua.from_wei(int(tx['value'], 16))
                c += 1
                self.ids.recent_cont.add_widget(MDFlatButton(text=str(amount)+' AQUA'))
                self.ids.recent_cont.add_widget(MDFlatButton(text=dest[:21] + '...', on_release=lambda x: foo_acct(dest)))
                self.ids.recent_cont.add_widget(MDFlatButton(text=tx['hash'][:21] + '...', on_release=lambda x: foo_tx(tx_hash)))
        self.ids.saved_cont.add_widget(add_btn)
    #save self.contacts to ~/.data/contacts.json
    def write_contacts_file(self):
        with open('data/contacts.json', 'w+') as f:
            log.info("dumping: %s", self.contacts)
            json.dump(self.contacts, f)
            return

    def popup_editcontact(self, pub='', note=''):
        self.popup_addcontact(overwrite=True, pub=pub, note=note)

    def popup_addcontact(self, pub='', note='', overwrite=False):
        grid = MDGridLayout(
                            cols=1,
                            size_hint=(1, 1),
                            height=dp(200),
                            spacing=dp(10),
                            row_default_height=dp(30)
                            )
        footext = MDTextField(text=note, valign="top", color_mode="primary")
        footext.hint_text='Name'
        footext2 = MDTextField(text=pub)
        footext2.hint_text='Address'
        def addcontact(instance):
            self.addContact(footext2.text, overwrite=overwrite)
            if footext.text in self.contacts['saved']:
                Snackbar(text=f'{footext2.text[:10]} already in address book', duration=3).show()
                dialog.dismiss()
                return
            else:
                self.contacts['saved'][footext2.text] = footext.text,
                try:
                    self.write_contacts_file()
                    self.build_address_book()
                except Exception as e:
                    log.error("error writing file: %s", e)
                    Snackbar(text=f"error: {e}")
                    return
                dialog.dismiss()
        grid.add_widget(footext)
        grid.add_widget(footext2)
        dialog = MDDialog(title='[color=008080]Add Contact[/color]',
                          type="custom",
                          content_cls=grid,
                          size_hint= (.7, .7),
                          auto_dismiss=True,
                          buttons=[
                                   MDRaisedButton(
                                                  text='Save',
                                                  on_release=addcontact
                                                  )
                                   ]
                          )
        dialog.open()

    def addContact(self, pub, note='', overwrite=False):
        if not overwrite and pub in self.contacts['saved']:
            Snackbar(text=f'{pub[:10]} already in address book', duration=3).show()
        else:
            self.contacts['saved'][f'{pub}'] = note
            try:
                self.write_contacts_file()
            except Exception as e:
                log.error("error writing file: %s", e)
                Snackbar(text=f"error: {e}")
                return
    #save self.recent to ~/.data/recent.json
    def write_recent_file(self):
        with open('data/recent.json', 'w+') as f:
            log.info("dumping: %s", self.recent)
            json.dump(self.recent, f)
            return

    def addRecent(self, txhash='0x'):
        if not txhash.startswith('0x'):
            log.info(f'Tx hash: {txhash} not valid')
            return
        else:
            try:
                self.recent['recent'].append(txhash),
                self.write_recent_file()
                log.info("saved recent transactions to file")
            except Exception as e:
                log.error("error writing file: %s", e)
                Snackbar(text=f"error: {e}")
                return

    def popup_contacts(self, contact):
        s = Snackbar(text=f'Add {contact[:10]} to Address Book?', button_text='OK', duration=5)
        def foo(contact):
            self.addContact(contact)
        s.button_callback=foo(contact)
        s.show()

    # get blockchain sample
    def getHistory(self, limit, start=0):
        def foo_acct(acct):
            pub = acct
            balance = self.aqua.getbalance(str(pub))
            try:
                log.info("launching popup: %s %s", pub, balance)
                self.popup_miner({
                               'Address': pub,
                               'Balance': balance,
                               'Type': 'personal'
                               })
            except Exception as e:
                Snackbar(test="Something went wrong").show()
                pass

        if 'number' in self.head:
            height = int(self.head['number'], 16)-start
            if limit > height:
                limit = height
            log.info("get history from height: %s", height)
            l = len(self.ids.container1.children)
            if l == 0:
                undef = '' # placeholder str
                log.info("generating history widgets")
                self.ids.container1.add_widget(MDFlatButton(text='Block'))
                self.ids.container1.add_widget(MDFlatButton(text='Hash'))
                self.ids.container1.add_widget(MDFlatButton(text='Difficulty'))
                self.ids.container1.add_widget(MDFlatButton(text='Miner'))
                self.ids.container1.add_widget(MDFlatButton(text='Tx'))
                self.ids.container1.add_widget(MDFlatButton(text='Timing'))
                for i in range(limit):
                    self.ids.container1.add_widget(MDFlatButton(on_release=lambda btn: self.popup_block(self.aqua.getblockbyhash(btn.id))))
                    self.ids.container1.add_widget(MDFlatButton(on_release=lambda btn: self.popup_block(self.aqua.getblockbyhash(btn.id))))
                    self.ids.container1.add_widget(MDFlatButton(on_release=lambda btn: self.popup_block(self.aqua.getblockbyhash(btn.id))))
                    self.ids.container1.add_widget(MDFlatButton(on_release=lambda btn: foo_acct(btn.id)))
                    self.ids.container1.add_widget(MDFlatButton(on_release=lambda btn: self.popup_block(self.aqua.getblockbyhash(btn.id))))
                    self.ids.container1.add_widget(MDFlatButton(on_release=lambda btn: self.popup_block(self.aqua.getblockbyhash(btn.id))))
            else:
                log.info("already have history widgets: %s", len(self.ids.container1.children))
            if len(self.ids.hist_tx.children) == 0:
                self.ids.hist_tx.add_widget(MDFlatButton(text='Status', bold=True))
                self.ids.hist_tx.add_widget(MDFlatButton(text='hash', bold=True))
                self.ids.hist_tx.add_widget(MDFlatButton(text='time', bold=True))
                for i in range(30):
                    log.debug(f'{i} widget is {len(self.ids.hist_tx.children)}')
                    self.ids.hist_tx.add_widget(MDFlatButton(text = f'{undef}',
                                                            on_release=lambda btn: self.popup_tx(self.aqua.gettransaction(btn.id)),
                                                             bold = True))
                    # txhash
                    self.ids.hist_tx.add_widget(MDFlatButton(on_release=lambda btn: self.popup_tx(self.aqua.gettransaction(btn.id))))
                    # time
                    self.ids.hist_tx.add_widget(MDFlatButton(on_release=lambda btn: self.popup_tx(self.aqua.gettransaction(btn.id))))
            ltx = len(self.ids.hist_tx.children)
            oldheader = self.head
            h = self.head
            if 'hash' in self.block_cache[0] and h['hash'] == self.block_cache[0]['hash']:
                return
            self.block_cache[0] = h
            l-=7
            it = 1
            for i in range(limit): # range most recent X blocks
                if i > 0:
                    h = self.aqua.getblock(height-i)
                    # self.block_cache[i] = h
                if 'number' in h:
                    log.debug("setting widget text: %s (%s)", h['hash'], i)
                    self.ids.container1.children[l-((i*5)+i)].id = h['hash']
                    self.ids.container1.children[l-((i*5)+i+1)].id = h['hash']
                    self.ids.container1.children[l-((i*5)+i+2)].id = h['hash']
                    self.ids.container1.children[l-((i*5)+i+3)].id = h['miner']
                    self.ids.container1.children[l-((i*5)+i+4)].id = h['hash']
                    self.ids.container1.children[l-((i*5)+i+5)].id = h['hash']
                    self.ids.container1.children[l-((i*5)+i)].text = str(int(h['number'], 16))
                    self.ids.container1.children[l-((i*5)+i+1)].text = h['hash'][:8]
                    self.ids.container1.children[l-((i*5)+i+2)].text = str(int(h['difficulty'], 16))
                    self.ids.container1.children[l-((i*5)+i+3)].text = h['miner'][:8]
                    self.ids.container1.children[l-((i*5)+i+4)].text = str(len(h['transactions']))
                    # calc timing
                    parent_timestamp = int(oldheader['timestamp'],16)
                    timestamp = int(h['timestamp'], 16)
                    timing = str(parent_timestamp-timestamp)
                    if timing == "0":
                        timing = "latest"
                    oldheader = h
                    self.ids.container1.children[l-((i*5)+i+5)].text = timing
                    # tx
                    txs = h['transactions']
                    statustext = 'Confirmed '+ '('+ str(i)+')'
                    if i == 0:
                        statustext = 'unconfirmed'
                    for t in txs: # for each tx in this block
                        # status
                        if ltx < (it+3+2):
                            break
                        self.ids.hist_tx.children[ltx-(it+3)].text = statustext
                        self.ids.hist_tx.children[ltx-(it+3)].id=t['hash']
                        self.ids.hist_tx.children[ltx-(it+3+1)].text = t['hash'][:20]
                        self.ids.hist_tx.children[ltx-(it+3+1)].id=t['hash']
                        timefmt = datetime.datetime.fromtimestamp(int(h['timestamp'], 16)).strftime('%Y-%m-%d %H:%M:%S')
                        self.ids.hist_tx.children[ltx-(it+3+2)].text = timefmt
                        self.ids.hist_tx.children[ltx-(it+3+2)].id=t['hash']
                        it += 3
                if i == height:
                    break
            log.info("showing recent blockchain")

    def lock(self):
        self.coinbase = ''
        self.balances = {}
        self.addresses = []
        self.balance = 0.0
        self.mkeys = []
        self.ids.send_addr.text = ''
        self.ids.amount.text = ''
        self.switch_view('welcome', direction='left')
        Snackbar(text='Accounts Cleared').show()

    def blockchain_search(self):
        self.ids.blockchain_search_content.clear_widgets()
        query = self.ids.blockchain_search_query.text
        self.ids.blockchain_search_query.text = ''
        if len(query) == 42:
            # address
            try:
                balance = self.aqua.getbalance(query)
                self.popup_acct({'Address': query, 'Balance': balance, 'Type': 'search'})
                return
            except Exception as e:
                log.error("cant convert query to int: %s", e)
                return

        elif len(query) == 66:
            # tx
            try:
                tx = self.aqua.gettransaction(query)
                self.popup_tx(tx)
                return
            except Exception as e:
                Snackbar(text="Tx invalid or Block is pending", duration=1).show()
                log.debug("block not found: %s", e)
                return

        elif len(query) < 12:
            # maybe block number
            try:
                i = int(query)
                block = self.aqua.getblock(i)
                self.popup_block(block)
            except Exception as e:
                log.error("cant convert query to int: %s", e)
            return
        widget = MDLabel(theme_text_color="Primary", text='Search Failed')
        self.ids.blockchain_search_content.add_widget(widget)

    def popup_block(self, block):
        log.info('BLOCK: %s', block)
        if isinstance(block, Exception):
            Snackbar(text=f'Error: {block}').show()
            return
        if not block:
            Snackbar(text='Loading chain...try again.').show()
            return
        else:
            log.debug(block)
            content = MDGridLayout(cols=2, spacing = dp(15), height = dp(200))
            for text in block:
                txt = StringProperty("")
                if text in ['transactions', 'uncles']:
                    txt = str(len(block[text]))
                elif text in ['version']:
                    txt = str(block[text])
                elif text in ['extraData']:
                    try:
                        txt =  binascii.unhexlify(block[text][2:]).decode("utf-8")
                    except Exception as e:
                        log.debug("got error decoding extradata: %s", e)
                        txt = block[text][:10]+'...'
                elif text in ['gasLimit', 'gasUsed', 'nonce', 'transactionIndex', 'difficulty', 'number', 'totalDifficulty']:
                    txt = str(int(block[text], 16))
                elif text in ['size']:
                    txt = str(int(block[text], 16)) + " bytes"
                elif text in ['timestamp']:
                    txt = datetime.datetime.fromtimestamp(int(block['timestamp'], 16)).strftime('%Y-%m-%d %H:%M:%S')
                elif text in ['hash', 'mixHash', 'parentHash', 'transactionsRoot', 'logsBloom', 'miner', 'receiptsRoot', 'sha3Uncles', 'stateRoot']:
                    txt = block[text][:10]
                else:
                    raise Exception("unknown field: %s" % text)
                foo = MDLabel(theme_text_color = "Custom", text_color= [.7,.9,.7,.5], text=("%s: " % text + "%s" % txt), font_style='Body2')#, bold=True)
                content.add_widget(foo)
        dialog = MDDialog(
                          title='[color=008080]Block number %s[/color]' % int(block['number'], 16),
                          type="custom",
                          content_cls=content,
                          auto_dismiss=True,
                          buttons=[
                                   MDFlatButton(
                                                text="OK",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=lambda *x: dialog.dismiss()
                                                )
                                   ]
                          )
        dialog.open()

    def popup_tx(self, tx):
        content = MDGridLayout(cols=2, spacing = dp(20), height=dp(150))
        log.info('TX: %s', tx)
        for text in tx:
            txt = StringProperty("")
            if text in ['gas', 'nonce', 'transactionIndex', 'blockNumber', 'v']:
                txt = str(int(tx[text][2:], 16))
            elif text in ['input']:
                l = len(tx[text])
                txt = f'contract: {l} bytes' if l > 2 else 'empty'
            elif text in ['size']:
                txt = str(int(tx[text], 16)) + " bytes"
            elif text in ['timestamp']:
                txt = datetime.datetime.fromtimestamp(int(tx['timestamp'], 16)).strftime('%Y-%m-%d %H:%M:%S')
            elif text in ['blockHash', 'from', 'to', 'r', 's', 'hash']:
                txt = tx[text][:10]
            elif text in ['value']:
                txt = str(self.aqua.from_wei(int(tx[text], 16))) + " AQUA"
            elif text in ['gasPrice']:
                txt = str(self.aqua.from_wei(int(tx[text], 16), denom='gwei')) + " gwei"
            else:
                raise Exception("unknown field: %s" % text)
            foo = MDLabel(theme_text_color = "Custom", text_color= [.7,.9,.7,.5], text=f'{text}: {txt}', font_style='Body1')
            content.add_widget(foo)
        content.add_widget(FloatLayout(size_hint = (1,1)))
        dialog = MDDialog(
                          title='[color=008080]Transaction: %s[/color]' % tx['hash'][:20],
                          type="custom",
                          content_cls=content,
                          size_hint=(.9, .9),
                          auto_dismiss=True,
                          buttons=[
                                   MDFlatButton(
                                                text="OK",
                                                theme_text_color= "Custom",
                                                text_color= self.theme_cls.primary_color,
                                                on_release=lambda *x: dialog.dismiss()
                                                )
                                   ]
                          )
        dialog.open()

# Application window specific
class AquachainApp(MDApp):
    title = 'Aquachain Wallet'
    icon = 'img/a100.png'
    config = Config
    use_kivy_settings = True
    #config.setdefaults( aquaconf, aquasettings.default_settings)
    aq = None

    def __init__(self, **kwargs):

        self.theme_cls = ThemeManager()
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = 'Teal'
        self.theme_cls.primary_hue = '400'
        self.theme_cls.primary_dark_hue = '200'
        self.theme_cls.accent_palette = 'Red'
        self.theme_cls.accent_hue = '400'
        self.theme_cls.main_background_color = 'Grey 900'
        super().__init__(**kwargs)

    def on_pause(self):
        Snackbar(text='LOCKED').show()
        log.info("locking wallet")
        self.aq.lock()
        return True

    def on_resume(self):
        pass

    def get_application_config(self):
        return super(AquachainApp, self).get_application_config(
            os.path.expanduser('data/aquaconfig.ini'))


    def build(self):
        # read settings
        self.config.read(self.get_application_config())
        self.settings_cls = SettingsWithSidebar
        self.aq = Aquachain(self)
        self.aq.aqua = AquaTool(ipcpath=self.config.get(aquaconf, 'ipcpath'), rpchost=self.config.get(aquaconf, 'rpchost'))
        self.aq.config = self.config
        return self.aq


    def build_config(self, config):
        Config.set('kivy', 'exit_on_escape', 0)
        Config.set('input', 'mouse', 'mouse,disable_multitouch')
        self.config.adddefaultsection(aquaconf)
        for config_field in aquasettings.default_settings:
            self.config.set(aquaconf, config_field, aquasettings.default_settings[config_field])
            log.info(f"setting {config_field}: {aquasettings.default_settings[config_field]}")
        self.config.setdefaults(aquaconf, aquasettings.default_settings)


    def build_settings(self, settings):
        self.config.read(self.get_application_config())
        settings.add_json_panel(aquaconf,
            self.config,
        data=aquasettings.settings_json)

    def on_config_change(self, config, section, key, value):
        if config is self.config:
            log.info("config changed: %s[%s] = \"%s\"", section, key, value)
            if section == aquaconf:
                if key == "rpchost":
                    self.aq.aqua = AquaTool(ipcpath=self.config.get(aquaconf, 'ipcpath'), rpchost=self.config.get(aquaconf, 'rpchost'))
                    self.aq.aqua.setrpc(self.config.get(aquaconf, 'rpchost'))
                if key == "Theme":
                    self.theme_cls.theme_style = self.config.get(aquaconf, 'Theme')
                if key == "ipcpath":
                    self.config.set(aquaconf, 'ipcpath', os.path.expanduser(value))
                    log.info("resolved ipc path to %s", self.config.get(aquaconf, 'ipcpath'))
                    self.aq.aqua = AquaTool(ipcpath=self.config.get(aquaconf, 'ipcpath'), rpchost=self.config.get(aquaconf, 'rpchost'))
                if key == 'blocklimit':
                    self.aq.getblock_cache()
                if key == 'hdwallets':
                    self.aq.get_coinbase_view()
                if key == 'noderefresh':
                    log.info("refreshing clock")
                    self.aq.clock.cancel()
                    self.aq.clock = Clock.schedule_interval(self.aq.refresh_block, float(value))
                if key == 'keystore':
                    log.info("keystore set")
                    self.config.set(aquaconf, 'keystore', os.path.expanduser(value))
                    self.aq.keystore.directory = os.path.expanduser(value)
            self.config.write()
        else:
            log.error("config error")
# run program
if __name__ == '__main__':
    try:
        AquachainApp().run()
    except Exception as e:
        log.error("fatal: %s", e)
        raise
