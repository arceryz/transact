#!/bin/python
# Script that lists all bank transactions using the Nordigen API.
# Your will be redirected to your banks website to verify an agreement.
import requests as req
import json
import os


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
    print("!!! %s%s" % (str(msg), ": " + str(resp) if resp != None else ""))

STATUS_OK = 0
STATUS_EXPIRED = 403
STATUS_ERROR_UNKNOWN = 1


#################################################################################
# User configuration.
#################################################################################

conf = load_json("conf.json")
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

account = {
    "access": "",
    "refresh": ""
}

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
# Agreements/Linking.
#
# With this we have certainty that the access token is valid. 
# We can now use the API without worrying about the token.
#################################################################################

save_account(conf["account_file"])

