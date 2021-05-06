# AquawalletHD

Picking back up the development of :https://github.com/aquachain/aquachain-kv/. Its new home will be here.
A big thanks to https://github.com/aerth for their contributions to the project.

AQUAWALLETHD is simple GUI wallet solution for Aquachain with HD wallet support and built-in blockchain explorer.

# Installation

## Windows

- From the "Releases" page, download the .zip file that corresponds with your OS
- Unzip to a location of you choice
- Run AquawalletHD.exe
___
# IMPORTANT!
## Warning

As of now, seed phrases that are saved, imported, and create by the application are stored in plain text in the keystore. PROTECT YOUR SEED KEY. Use these features AT YOUR OWN RISK. Do not store seed phrase on a system that could in any way have compromised security and take great care managing these files.
___
# Known Issues

- Can't use IPC if using HTTP initially
- Wallet will crash if invalid wallet address is used
- Wallet will crash if there is no network connection when loading saved wallet
- App gives no feedback when funds are insufficient for tx
- Clicking the search button does not default to the search tab on blockchain screen
- Must restart application to adjust block limit in explorer
- After sending Tx the snackbar to add address to contacts does not save contact properly
___
# Coming soon...

- Seed phrase storage encryption algorithm
- Smart Contract functionality
- Ability to browse an addresses' transactions (similar to most block explorers)
- Mobile release
