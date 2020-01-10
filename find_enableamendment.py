#!/usr/bin/env python3

import argparse
import json
import logging
import sys
from datetime import datetime

import requests

# Default values - Ripple's full history server
RIPPLED_HOST = "s2.ripple.com"
RIPPLED_PORT = 51234

ENABLEAMENDMENT_FLAGS = {
    "tfGotMajority": 0x00010000,
    "tfLostMajority": 0x00020000,
    "Enabled": 0, # Not a real flag, but useful
    "any": "any" # Wildcard entry
}
EAFLAG_NAMES = {v:k for k,v in ENABLEAMENDMENT_FLAGS.items()}

logger = logging.getLogger('find_enableamendment')
logger.addHandler(logging.StreamHandler(sys.stdout))

class LedgerNotFound(Exception):
    pass

class BoundsError(Exception):
    pass

class EnableAmendmentFinder:
    def __init__(self, args):
        self.rippled_host = args.rippled_host
        self.rippled_port = int(args.rippled_port)

        self.flag = ENABLEAMENDMENT_FLAGS[args.flag]

        self.start_ledger = args.start_ledger
        self.amendment_id = args.amendment_id

    def lookup_ledger(self, ledger_index=0):
        """
        Use JSON-RPC to get all transactions from a ledger.
        """
        assert ledger_index
        body = {
            "method": "ledger",
            "params": [{
                "ledger_index": ledger_index,
                "transactions": True,
                "expand": True
            }]
        }
        url = "https://%s:%d/" % (self.rippled_host, self.rippled_port)

        logger.info("Querying ledger %d from %s"%(ledger_index, url))
        response = requests.post(url, data=json.dumps(body))
        logger.debug("Lookup ledger response is: %s"%response)
        result = response.json()["result"]

        if "ledger" in result:
            return result["ledger"]
        else:
            raise KeyError("Response from rippled doesn't have a ledger as expected")

    def search_ledger(self, ledger_index):
        """
        Find a matching EnableAmendment transaction in the ledger matching
        the given index.
        """
        logger.info("Searching ledger %d" % ledger_index)
        try:
            ledger = self.lookup_ledger(ledger_index=ledger_index)
        except (KeyError):
            raise LedgerNotFound()
        logger.debug("Ledger %d has %d transactions." % (ledger_index, len(ledger["transactions"])))
        for tx in ledger["transactions"]:
            if tx["TransactionType"] == "EnableAmendment" and tx["Amendment"] == self.amendment_id:
                if self.flag == "any":
                    logger.info("Found with flag %s in ledger %d: hash %s" % (tx.get("Flags", 0), ledger_index, tx["hash"]))
                    return tx["hash"]
                elif self.flag and tx.get("Flags", 0) & self.flag:
                    logger.info("Found in ledger %d: hash %s" % (ledger_index, tx["hash"]))
                    return tx["hash"]
                elif not self.flag and not tx.get("Flags", 0):
                    logger.info("Found in ledger %d: hash %s" % (ledger_index, tx["hash"]))
                    return tx["hash"]
                else:
                    actual_flag = tx.get("Flags", 0)
                    logger.info("Found EnableAmendment with wrong flags: %s" %
                        EAFLAG_NAMES.get(actual_flag, "0x%08x"%actual_flag))

        return False

    def prev_flag_ledger(self, ledger_index):
        """
        EnableAmendment transactions only appear in ledgers whose index % 256 == 1.
        Find the nearest previous such ledger_index and return it.
        """
        flag_offset = (ledger_index % 256)
        if flag_offset > 0:
            return ledger_index - (flag_offset -1)
        else:
            return ledger_index - 255

    def find(self):
        offset = 0
        beyond_present_ledger = False
        beyond_oldest_ledger = False
        real_start = self.prev_flag_ledger(self.start_ledger)
        logger.info("Looking for {flag} EnableAmendment for amendment {a_id}".format(
            flag=EAFLAG_NAMES[self.flag],
            a_id=self.amendment_id
        ))
        while 1:
            if not beyond_oldest_ledger:
                li = real_start - offset
                try:
                    tx_hash = self.search_ledger(li)
                except LedgerNotFound:
                    #Assume we tried to look up a higher ledger index than the oldest available
                    logger.info("Ledger not found. Assuming we've hit lower bound of ledgers")
                    beyond_oldest_ledger = True
                if tx_hash:
                    return (li, tx_hash)

            if offset != 0 and not beyond_present_ledger:
                li = real_start + offset
                try:
                    tx_hash = self.search_ledger(li)
                except LedgerNotFound:
                    #Assume we tried to look up a higher ledger index than the newest
                    logger.info("Ledger not found. Assuming we've hit upper bound of ledgers")
                    beyond_present_ledger = True
                if tx_hash:
                    return (li, tx_hash)

            if beyond_oldest_ledger and beyond_present_ledger:
                raise BoundsError("Exceeded available ledger bounds on both ends...")
            offset += 256

# Example of a "tfGotMajority" pseudo-tx:
#   amendment: CC5ABAE4F3EC92E94A59B1908C2BE82D2228B6485C00AFF8F22DF930D89C194E
#   ledger 33895169
#   tx hash 515F5D268C7275A9FC8BEE8C81DE3DC4615F539B366943312E7A078C35C4ECAF


def main():
    parser = argparse.ArgumentParser(description="Find an EnableAmendment transaction for a given amendment")
    parser.add_argument("amendment_id", type=str, help="256-bit hex Amendment ID")
    parser.add_argument("start_ledger", type=int, help="ledger_index of approx. ledger to start looking from")
    parser.add_argument("--flag", "-f", type=str, choices=ENABLEAMENDMENT_FLAGS.keys(),
                        default="any", help="Status change to look for.")
    parser.add_argument("--rippled_host", type=str, default=RIPPLED_HOST, help="Use this server to look up amendment.")
    parser.add_argument("--rippled_port", type=str, default=RIPPLED_PORT, help="Use this JSON-RPC port on lookup server.")
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)

    print(EnableAmendmentFinder(args).find())

if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
