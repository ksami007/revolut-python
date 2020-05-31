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
    percent_margin = config['percent_margin']
    repeat_every_min = config['repeat_every_min']
    to_buy_or_not_to_buy(
        revolut_client,
        simulate,
        filename,
        forceexchange,
        percent_margin,
        repeat_every_min
    )


def to_buy_or_not_to_buy(
    revolut_client,
    simulate,
    filename,
    forceexchange,
    percent_margin,
    repeat_every_min
):

    while True:
        last_transactions = revolut_bot.get_last_transactions_from_csv(
            filename=filename
        )
        last_tr = last_transactions[-1]  # The last transaction
        logging.info(
            f'Last transaction({last_tr.date.strftime(_DATETIME_FORMAT)}): '
            f'Purchased {last_tr.to_amount} '
            f'for {last_tr.from_amount}'
        )
        previous_currency = last_tr.from_amount.currency

        # How much we currently have
        current_balance = last_tr.to_amount
        current_balance_in_other_currency = revolut_client.quote(
            from_amount=current_balance,
            to_currency=previous_currency
        )
        logging.info(
            f'Now({datetime.now().strftime(_DATETIME_FORMAT)}): '
            f'Your {current_balance} is worth {current_balance_in_other_currency}'
        )

        last_sell = last_tr.from_amount  # How much did it cost before selling
        last_sell_plus_margin = revolut_bot.get_amount_with_margin(
            amount=last_sell,
            percent_margin=percent_margin
        )
        logging.info(
            f'Minimum value to sell yours {last_tr.to_amount.currency}: '
            f'{last_sell} + {percent_margin}% '
            f'of margin is {last_sell_plus_margin}'
        )
        buy_condition = current_balance_in_other_currency.real_amount > \
            last_sell_plus_margin.real_amount

        simulate_str = '| simulating' if simulate else ''
        if buy_condition or forceexchange:
            if forceexchange:
                logging.info('[ATTENTION] Force exchange option enabled')
            else:
                logging.info(
                    f'Action: '
                    f'{current_balance_in_other_currency} > {last_sell_plus_margin} '
                    f'====> SELLING your {last_tr.to_amount.currency} {simulate_str}'
                )

            if not simulate:
                exchange_transaction = revolut_client.exchange(
                    from_amount=current_balance,
                    to_currency=previous_currency,
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
                f'{current_balance_in_other_currency} < {last_sell_plus_margin} '
                f'====> NOT SELLING your {last_tr.to_amount.currency} {simulate_str}'
            )
        logging.info(f'Sleeping for {repeat_every_min} minutes\n\n')
        time.sleep(repeat_every_min*60)


if __name__ == "__main__":
    main()
