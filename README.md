EnableAmendment Finder
======================

This is a simple Python (2 or 3) script to search for EnableAmendment type transactions in the Ripple Consensus Ledger. It uses s2.ripple.com (the full history server) to look up ledgers starting from a "guesstimate" Ledger Index. Example:

    $ python find_enableamendment.py 22721275
    Searching ledger 22721275
    Searching ledger 22721274
    Searching ledger 22721276
    Searching ledger 22721273
    Searching ledger 22721277
    Searching ledger 22721272
    Searching ledger 22721278
    Searching ledger 22721271
    Searching ledger 22721279
    Searching ledger 22721270
    Searching ledger 22721280
    Searching ledger 22721269
    Searching ledger 22721281
    Found in ledger 22721281: hash 0E589DE43C38AED63B64FF3DA87D349A038F1821212D370E403EB304C76D70DF

> **Tip:** There's a bug (RIPD-1098) in rippled's tx command that causes it to return "not found" when you try to look up pseudo-transactions. You can use the [transaction_entry](https://ripple.com/build/rippled-apis/#transaction-entry) command instead to look up pseudo-transactions.

To get a good "guesstimate" ledger index to start from, try using the [Data API's Get Ledger Tool](https://ripple.com/build/data-api-tool/#get-ledger) with a date. 

> **Note:** This script finds "any" EnableAmendment pseudo-transaction, which can include the "GotMajority", "LostMajority" or "Enabled" versions of the pseudo-tx.  See https://ripple.com/build/transactions/#enableamendment for explanation of that.


