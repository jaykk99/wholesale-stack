# Vendored copy of crypto-payment-watcher

This folder is a vendored copy of the `paywatch` package from
jaykk99/crypto-payment-watcher (main at 0cc04dd, which includes the
multi-asset upgrade and the shipped default receive address pools).

Source: https://github.com/jaykk99/crypto-payment-watcher

Do not edit the vendored files casually. To update, copy a fresh
`src/paywatch/` from that repo over this folder, keep this note, and
re-run `python3 -m pytest tests/ -q`.

The shipped defaults in `default_addresses.json` are the owner's real
public receive addresses for BTC, ETH, BNB, and SOL. Receive addresses
are public by design: every buyer sees the assigned one at checkout.
Private keys and seeds must never be committed anywhere, and this
package never accepts one.

Environment configuration overrides the shipped defaults per asset
(see the crypto-payment-watcher README for PAYWATCH_ADDRESSES and the
per-asset variables). An explicitly empty env pool closes that asset.
