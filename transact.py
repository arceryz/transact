#!/bin/python
# Script that lists all bank transactions using the Nordigen API.
# Your will be redirected to your banks website to verify an agreement.
import requests as req
import json
import os
import sys
import datetime


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

conf = load_json("conf.json")
if conf != None:
    log("Conf loaded from conf.json")
else:
    err("Could not load conf")
    exit()

def get_secret_key():
    return conf["secret_key"]

def get_secret_id():
    return conf["secret_id"]


#################################################################################
# Account.
#################################################################################

account = {}

def load_account(file):
    acc = load_json(file)
    if acc != None:
        global account
        account = acc
        log("Account loaded from %s" % file)
    else:
        log("Invalid json file at %s" % file)

def save_account(file):
    save_json(file, account)

load_account(conf["account_file"])


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
if get_access_status() == STATUS_EXPIRED:
    if refresh_access_token() == STATUS_EXPIRED:
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
        print("Invalid input.")
        return STATUS_INVALID_INPUT
    else:
        print("%4s %-20s %-12s    %s" % ("", "Name", "BIC", "Id"))
        for i in range(len(res)):
            bank = res[i]
            print("%3d. %-20.20s %-12.12s >  %s" % (i+1, bank["name"], bank["bic"], bank["id"] ))
        return STATUS_OK

def create_link(inst):
    now = datetime.datetime.now()
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
        for i in range(len(acclist)):
            print("%3d. %s" % (i+1, acclist[i]))
        return STATUS_OK
    else:
        log("Error", res)
        return STATUS_ERROR_UNKNOWN

if __name__ == "__main__":
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
            print("Usage: transact link [ID")
    if arg[0] == "accounts":
        list_accounts()

    save_account(conf["account_file"])
