#!/bin/python
# Script that lists all bank transactions using the Nordigen API.
# Your will be redirected to your banks website to verify an agreement.
import requests as req
import json
import os
import sys
from datetime import datetime
from time import sleep


#################################################################################
# Utilities.
#################################################################################

def save_json(dest, obj):
    fh = open(dest, "w")
    json.dump(obj, fh, indent=4)
    fh.close()

def load_json(dest):
    try:
        fh = open(dest, "r")
        data = json.load(fh)
        fh.close()
        return data
    except:
        return None

def api(req):
    return "https://bankaccountdata.gocardless.com/api/v2/%s" % req

def log(msg, resp=None):
    return
    print("!!! %s%s" % (str(msg), ": " + str(resp) if resp != None else ""),
          file=sys.stderr)


STATUS_OK = 0
STATUS_EXPIRED = 403
STATUS_ERROR_UNKNOWN = 1
STATUS_INVALID_INPUT = 400


#################################################################################
# User configuration.
#################################################################################

path = os.path.expanduser("~/.config/transact/")
conf = load_json(path + "conf.json")
if conf != None:
    log("Conf loaded from conf.json")
else:
    log("Could not load conf")
    exit()

def get_secret_key():
    return conf["secret_key"]

def get_secret_id():
    return conf["secret_id"]


#################################################################################
# Account.
#################################################################################

account = {}

def load_account():
    acc = load_json(path+"account.json")
    if acc != None:
        global account
        account = acc
        log("Account loaded from account.json")

def save_account():
    save_json(path+"account.json", account)

load_account()


#################################################################################
# Access management.
#################################################################################

def get_new_tokens():
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    json = {
        "secret_id": get_secret_id(),
        "secret_key": get_secret_key()
    }
    res = req.post(api("token/new/"), headers=headers, json=json).json()
    if "access" in res and "refresh" in res:
        account["access"] = res["access"]
        account["refresh"] = res["refresh"]
        log("Access & refresh tokens created")
        return STATUS_OK
    else:
        log("Error fetching tokens", res)
        return STATUS_ERROR_UNKNOWN

def refresh_access_token():
    if "refresh" not in account:
        return STATUS_EXPIRED
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    json = {
        "refresh": account["refresh"]
    }
    res = req.post(api("token/refresh/"), headers=headers, json=json).json()
    if "access" in res:
        account["access"] = res["access"]
        log("Access token refreshed")
        return STATUS_OK
    else:
        log("Refresh expired", res)
        return STATUS_EXPIRED

def get_access_status():
    if "access" not in account:
        return STATUS_EXPIRED
    headers = { 
        "accept": "application/json",
        "Authorization": "Bearer %s" % account["access"]
    }
    params = {
        "limit": "1",
        "offset": "1",
    }
    res = req.get(api("agreements/enduser/"), params=params, headers=headers).json()
    if "results" in res:
        log("Access token valid")
        return STATUS_OK
    else:
        log("Access expired", res)
        return STATUS_EXPIRED

# Refresh tokens if needed. We ensure that the access token is up to date.
# If it is not, we try to refresh it. If refreshing fails, then we just
# bail out and get new tokens altogether. If that fails we're doomed.
if get_access_status() != STATUS_OK:
    if refresh_access_token() != STATUS_OK:
        get_new_tokens()


#################################################################################
# Main program.
#################################################################################

def list_banks(country):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer %s" % account["access"]
    }
    params = {
        "country": country
    }
    res = req.get(api("institutions/"), headers=headers, params=params).json()
    if "status_code" in res:
        log("Error", res)
        print(res)
        print("Invalid input.")
        return STATUS_INVALID_INPUT
    else:
        print("%4s %-20s %-12s    %s" % ("", "Name", "BIC", "Id"))
        for i in range(len(res)):
            bank = res[i]
            print("%3d. %-20.20s %-12.12s >  %s" % (i+1, bank["name"], bank["bic"], bank["id"] ))
        return STATUS_OK

def create_link(inst):
    now = datetime.now()
    ref = "link:%s" % str(now)
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % account["access"]
    }
    data = {
        "redirect": "https://parcevval.itch.io/",
        "institution_id": inst,
        "reference": ref,
    }
    res = req.post(api("requisitions/"), headers=headers, json=data).json()
    if "id" in res:
        print(res["link"])
        account["reqid"] = res["id"]
        return STATUS_OK
    else:
        log("Error creating link", res)
        return STATUS_ERROR_UNKNOWN

def list_accounts():
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer %s" % account["access"]
    }
    res = req.get(api("requisitions/%s" % account["reqid"]),
                  headers=headers).json()
    if "accounts" in res:
        print("Bank: %s" % res["institution_id"])
        print("Accounts:")
        acclist = res["accounts"]
        account["bankaccount"] = acclist[0]
        for i in range(len(acclist)):
            bal = get_balance(acclist[i])
            print("%3d. %-40s %s" % (i+1, acclist[i], bal))
        return STATUS_OK
    else:
        log("Error", res)
        return STATUS_ERROR_UNKNOWN

def get_balance(accountid):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer %s" % account["access"]
    }
    res = req.get(api("accounts/%s/balances/" % account["bankaccount"]),
                  headers=headers).json()
    if "balances" in res:
        bc = res["balances"][0]
        amount = float(bc["balanceAmount"]["amount"])
        currency = bc["balanceAmount"]["currency"]
        output = "%-+8.2f %s" % (amount, currency)
        return output
    else:
        return "X"

def list_transactions(num):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer %s" % account["access"]
    }
    acc = account["bankaccount"]
    res = req.get(api("accounts/%s/transactions/" % acc),
                  headers=headers).json()
    bal = get_balance(acc)
    print("")
    if "transactions" in res:
        trlist = res["transactions"]["booked"]
        curmonth = -1
        for i in range(min(num, len(trlist))):
            tr = trlist[i]

            # Creditor/Debtor name and iban.
            name = ""
            iban = ""
            try:
                if "debtorName" in tr:
                    name = tr["debtorName"]
                    iban = tr["debtorAccount"]["iban"]
                elif "creditorName" in tr:
                    name = tr["creditorName"]
                    iban = tr["creditorAccount"]["iban"]
                else:
                    name = tr["remittanceInformationUnstructured"]
            except:
                pass

            # Currency.
            amount = float(tr["transactionAmount"]["amount"])
            currency = tr["transactionAmount"]["currency"]
            pad = ""
            if amount < 0:
                pad = " "*10
            amount_str = "%s%-+10.2f" % (pad, amount)

            # Date.
            dt = datetime.strptime(tr["bookingDate"], "%Y-%m-%d")
            if curmonth != dt.month:
                if curmonth >= 0:
                    print()
                curmonth = dt.month
            date = dt.strftime("%b %d")

            print("%5d.  %-8s %-21.20s %-21s %3.3s  %s" % 
                  (i+1, date, name, amount_str, currency, iban))
    print("")
    print("        Balance: %s" % bal)
    print("")
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: transact [COMMAND]")
        print("banks [COUNTRY]")
        print("link [ID]")
        print("list [NUMBER]")
        print("accounts")
        exit()
    arg = sys.argv[1:]
    if arg[0] == "banks":
        if len(arg) > 1:
            list_banks(arg[1])
        else:
            print("Usage: transact banks [COUNTRY]")
    if arg[0] == "link":
        if len(arg)>  1:
            create_link(arg[1])
        else:
            print("Usage: transact link [ID]")
    if arg[0] == "accounts":
        list_accounts()
    if arg[0] == "list":
        num = 10
        try:
            num = int(arg[1])
        except:
            pass
        list_transactions(num)

    save_account()
