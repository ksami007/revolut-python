# revolut-python

# Description

Non-official client for the [Revolut Bank](https://www.revolut.com/)

## Requirements

- python 3

## CLI tool : revolut.py

```bash
Usage: revolut.py [OPTIONS]

  Get the account balances on Revolut

Options:
  -d, --deviceid TEXT  your device id (or set the env var REVOLUT_DEVICE_ID)
  -t, --token TEXT     your Revolut token (or set the env var REVOLUT_TOKEN)
  -l, --language TEXT  language ("fr" or "en"), for the csv header and
                       separator
  --version            Show the version and exit.
  --help               Show this message and exit.
 ```

 Example output :

 ```csv
Account name,Balance,Currency
EUR wallet,100.50,EUR
GBP wallet,20.00,GBP
USD wallet,0.00,USD
AUD wallet,0.00,AUD
BTC wallet,0.00123456,BTC
```

## TODO

- [x] Create a CLI tool to get the balance (like https://github.com/tducret/ingdirect-python)
- [x] Explain how to use the CLI tool
- [ ] Create a tool to exchange automatically a currency when it grows
- [ ] Create the PIP package
- [ ] Create the Docker image