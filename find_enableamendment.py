#!/usr/bin/env python3

from __future__ import print_function
import json, sys
from warnings import warn
from datetime import datetime

RIPPLED_HOST = "s2.ripple.com"
RIPPLED_PORT = 51234


# Python 2/3-agnostic stuff ----------------
if sys.version_info[:2] <= (2,7):
    import httplib
else:
    import http.client as httplib

def lookup_ledger(ledger_index=0, ledger_hash="", expand=False):
    assert ledger_index or ledger_hash

    #You should probably not pass both, but this'll let
    # rippled decide what to do in that case.
    params = {
        "transactions": True,
        "expand": expand
    }
    if ledger_index:
        params["ledger_index"] = ledger_index
    if ledger_hash:
        params["ledger_hash"] = ledger_hash

    result = json_rpc_call("ledger", params)

    if "ledger" in result:
        return result["ledger"]
    else:
        raise KeyError("Response from rippled doesn't have a ledger as expected")

def json_rpc_call(method, params={}):
    """
    Connect to rippled's JSON-RPC API.
    - method: string, e.g. "account_info"
    - params: dictionary (JSON object),
        e.g. {"account": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
              "ledger" : "current"}
    """
    command = {
        "method": method,
        "params": [params]
    }

    conn = httplib.HTTPConnection(RIPPLED_HOST, RIPPLED_PORT)
    conn.request("POST", "/", json.dumps(command))
    response = conn.getresponse()

    s = response.read()

    response_json = json.loads(s.decode("utf-8"))
    if "result" in response_json:
        return response_json["result"]
    else:
        warn(response_json)
        raise KeyError("Response from rippled doesn't have result as expected")


# This script also doesn't do any error handling (e.g. if one side of your search
# goes beyond the current ledger, it'll just die)

def search_ledger(ledger_index, tx_type):
    ledger = lookup_ledger(ledger_index=ledger_index, expand=True)
    for tx in ledger["transactions"]:
        if tx["TransactionType"] == tx_type:
            return tx["hash"]

    return False

try:
    ledger_index_start = int(sys.argv[1])
except (ValueError, IndexError):
    warn("Usage: python %s SOME_LEDGER_INDEX" % sys.argv[0])
    exit(1)

offset = 0
beyond_present_ledger = False
while 1:
    li = ledger_index_start - offset
    print("Searching ledger", li)
    tx_hash = search_ledger(li, "EnableAmendment")
    if tx_hash:
        print("Found in ledger %d: hash %s" % (li, tx_hash))
        break

    if offset != 0 and not beyond_present_ledger:
        li = ledger_index_start + offset
        print("Searching ledger", li)
        try:
            tx_hash = search_ledger(li, "EnableAmendment")
        except KeyError:
            #Assume we tried to look up a higher ledger index than the newest
            print("Ledger not found. Assuming we've hit upper bound of ledgers")
            beyond_present_ledger = True
        if tx_hash:
            print("Found in ledger %d: hash %s" % (li, tx_hash))
            break

    offset += 1
