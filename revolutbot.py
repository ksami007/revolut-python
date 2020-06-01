# -*- coding: utf-8 -*-
from datetime import datetime

import revolut_bot
import yaml
import logging
import os
import time

from revolut import Revolut
from revolut import _DATETIME_FORMAT


CONFIG_FILE = 'revolutbot_config.yml'


def main():
    token = os.environ.get('REVOLUT_TOKEN')
    if not token:
        logging.error(
            'You don\'t seem to have a Revolut token. '
            'Please execute revolut_cli.py first to get one'
        )
        raise RuntimeError('No token were found in environmental variables')

    with open(CONFIG_FILE, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)

    # Set logging level
    logging.basicConfig(
        level=config.get('log_level', 'INFO'),
        format='%(levelname)s - %(message)s'
    )

    revolut_client = Revolut(device_id=config['cli_device_id'], token=token)

    simulate = config['simulate']
    filename = config['history_file']
    forceexchange = config['force_exchange']
    main_currency = config['main_currency']
    percent_margin = config['percent_margin']
    repeat_every_min = config['repeat_every_min']
    trade(
        revolut_client,
        simulate,
        filename,
        main_currency,
        forceexchange,
        percent_margin,
        repeat_every_min
    )


def trade(
    revolut_client,
    simulate,
    filename,
    main_currency,
    forceexchange,
    percent_margin,
    repeat_every_min
):
    """
    Continuously monitor the stock/commodity price.
    Two possible scenarios:
    If during last transaction you have sold commodity - monitor for cheaper offer to buy more;
    If during last transaction you bought commodity - monitor for higher offer to sell it.
    """

    while True:
        last_transactions = revolut_bot.get_last_transactions_from_csv(
            filename=filename
        )
        last_tr = last_transactions[-1]  # The last transaction
        from_currency = last_tr.from_amount.currency
        to_currency = last_tr.to_amount.currency

        if to_currency != main_currency:
            logging.info(
                f'Last transaction({last_tr.date.strftime(_DATETIME_FORMAT)}): '
                f'Bought {last_tr.to_amount} '
                f'for {last_tr.from_amount}'
            )
            action = 'sell'
            currency = to_currency
            commodity = last_tr.to_amount
            commodity_in_other_currency = revolut_client.quote(
                from_amount=commodity,
                to_currency=from_currency
            )
            last_price = last_tr.from_amount
            condition_price_with_margin = revolut_bot.get_amount_with_margin(
                amount=last_price,
                percent_margin=percent_margin
            )
            condition_met = commodity_in_other_currency.real_amount > \
                condition_price_with_margin.real_amount
        elif to_currency == main_currency:
            logging.info(
                f'Last transaction({last_tr.date.strftime(_DATETIME_FORMAT)}): '
                f'Sold {last_tr.from_amount} '
                f'for {last_tr.to_amount}'
            )
            action = 'buy'
            currency = from_currency
            percent_margin = -percent_margin
            commodity = last_tr.from_amount
            commodity_in_other_currency = revolut_client.quote(
                from_amount=commodity,
                to_currency=to_currency
            )
            last_price = last_tr.to_amount
            condition_price_with_margin = revolut_bot.get_amount_with_margin(
                amount=last_price,
                percent_margin=percent_margin
            )
            condition_met = commodity_in_other_currency.real_amount > \
                condition_price_with_margin.real_amount

        logging.info(
            f'Looking to {action} {currency}'
        )

        logging.info(
            f'Currently({datetime.now().strftime(_DATETIME_FORMAT)}): '
            f'{commodity} is worth {commodity_in_other_currency}'
        )
        logging.info(
            f'Desired value to {action} {currency}: '
            f'{last_price} with margin of {percent_margin}% '
            f'is {condition_price_with_margin}'
        )

        simulate_str = '| simulating' if simulate else ''
        sign = '>' if action == 'buy' else '<'
        if condition_met or forceexchange:
            if forceexchange:
                logging.info('[ATTENTION] Force exchange option enabled')
            else:
                logging.info(
                    f'Action: '
                    f'{condition_price_with_margin} {sign} {commodity_in_other_currency} '
                    f'====> {action.upper()}ING your {last_tr.to_amount.currency} {simulate_str}'
                )

            if not simulate:
                exchange_transaction = revolut_client.exchange(
                    from_amount=commodity,
                    to_currency=from_currency,
                    simulate=simulate
                )
                logging.info(
                    f'Result: Just bought {exchange_transaction.to_amount.real_amount}. '
                    f'Updating history file : {filename}'
                )
                revolut_bot.update_historyfile(
                    filename=filename,
                    exchange_transaction=exchange_transaction
                )
        else:
            logging.info(
                f'Action: '
                f'{commodity_in_other_currency} {sign} {condition_price_with_margin} '
                f'====> NOT {action.upper()}ING {currency} {simulate_str}'
            )
        logging.info(f'Sleeping for {repeat_every_min} minutes\n\n')
        time.sleep(repeat_every_min*60)


if __name__ == "__main__":
    main()
