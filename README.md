# Transact

If you are like me and are annoyed with having to log in on your bank's 
website with all sorts of security checks taking a tedious amount of time, just
for checking your balance. Look no further, this script will help you. 

This simple script consisting of 1 python file allows you to list at any
time:

- Transaction history
- Balance

This script can NOT make transactions. It can only read transactions and
balance. You can see the contents of transact.py to see the exact extent of this
scripts' functionality.

Using a terminal interface you just call `transact transactions` and you get a 
neat list of transactions containing

- Date
- Creditor/Debtor name
- Amount subtracted/added
- Currency
- IBAN

This will allow you to keep track of money and integrate it in any user
interface of your choice (status bars, gui program, cli program).

# How to use

This script is still in a very early stage. Over the course of time it may
evolve with more advanced features. But the core of requesting transactions is
functional. Only one account is supported at a time.

## 1. Create account at [GoCardless](https://bankaccountdata.gocardless.com/overview/)

You will need an account at GoCardless at
[https://bankaccountdata.gocardless.com/overview/](https://bankaccountdata.gocardless.com/overview/).

## 2. Create API secrets.

You will need an API key and secrets to use the API safely. 
Go to
[https://bankaccountdata.gocardless.com/user-secrets/](https://bankaccountdata.gocardless.com/user-secrets/)
and create your secrets. *Store the secret key and secret id safely on your
computer!*.

## 3. Create conf.json 
You will need a config file at $HOME/.config/transact/conf.json containing
entries like the following:

```json
{
    "secret_key": "YOUR SECRET KEY",
    "secret_id": "YOUR SECRET ID",
}
```

## 4. Selecting bank.

You now need to select your bank. You can get a list of banks by calling
```sh
transact banks [COUNTRY CODE]
```
For a given country code (e.g nl=netherlands).
This will display in your terminal (if the API key is correct).
Write down your banks' id, as you will need it to link.


## 5. Link bank account.

Final step is to link your bank account. This can be done by passing the bank id
to the `link` command:

```sh
transact link [BANK ID]
```

You will be given back a URL which you need to visit to verify with your bank.
You will be redirected to your banks website to log in and authorize this script
for viewing only transactions.

Finally you need to actually connect your bank account by calling:

```sh
transact accounts
```

Which displays all accounts that are exposed by your bank. Currently this script
only uses the first bank account since multiple bank accounts are not supported.

## 6. List your transactions.

If all went well you can now list your transactions and get balance with:
```sh
transact transactions 10
```
You can specify the number of transactions you wish to see (or none) with the
integer argument preceding the command.
