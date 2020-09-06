# -*- coding: utf-8 -*-
from datetime import datetime

import revolut_bot
import yaml
import logging
import os
import time

from revolut import Revolut
from revolut import Transaction
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

    simulation = config['simulation']['enabled']
    data_path = config['data_path']
    transaction_filename = os.path.join(*[data_path, config['transaction_file']])
    sm_transaction_filename = None
    if config['simulation'].get('transaction_file'):
        sm_transaction_filename = os.path.join(
            *[data_path, config['simulation']['transaction_file']]
        )
    forceexchange = config['force_exchange']
    main_currency = config['main_currency']
    percent_margin = config['percent_margin']
    repeat_every_min = config['repeat_every_min']
    trade_commodity(
        revolut_client,
        transaction_filename,
        simulation,
        sm_transaction_filename,
        main_currency,
        forceexchange,
        percent_margin,
        repeat_every_min
    )


def trade_commodity(
    revolut_client,
    transaction_filename,
    simulation,
    sm_transaction_filename,
    main_currency,
    forceexchange,
    percent_margin,
    repeat_every_min
):
    """
    Continuously monitor the commodity price
    Two possible scenarios:
    If during last transaction you have sold commodity - monitor for cheaper offer to buy more;
    If during last transaction you bought commodity - monitor for higher offer to sell it.
    """

    while True:
        # If simulation mode enables and simulation file provided
        # Write/read all transactions from that file
        if simulation and sm_transaction_filename:
            filename = sm_transaction_filename
        elif simulation is False:
            filename = transaction_filename

        last_transaction = revolut_bot.get_last_transactions_from_csv(
            filename=filename
        )[-1]  # Get the last transaction from the list

        # For example: USD(from) to BTC(to)
        lt_from = last_transaction.from_amount
        lt_to = last_transaction.to_amount

        #  from_currency = last_tr.from_amount.currency
        #  to_currency = last_tr.to_amount.currency

        if lt_to.currency != main_currency and lt_from.currency == main_currency:
            logging.debug(
                f'Last transaction({last_transaction.date.strftime(_DATETIME_FORMAT)}): '
                f'Bought {lt_to} '
                f'for {lt_from}'
            )
            action = 'sell'
            min_max_str = 'minimum'
            commodity = lt_to
            last_price = lt_from
        elif lt_to.currency == main_currency:
            logging.debug(
                f'Last transaction({last_transaction.date.strftime(_DATETIME_FORMAT)}): '
                f'Sold {lt_from} '
                f'for {lt_to}'
            )
            action = 'buy'
            min_max_str = 'maximum'
            percent_margin = -percent_margin
            commodity = lt_from
            last_price = lt_to

        condition_price_with_margin = revolut_bot.get_amount_with_margin(
            amount=last_price,
            percent_margin=percent_margin
        )
        commodity_in_main_currency = revolut_client.quote(
            from_amount=commodity,
            to_currency=main_currency
        )

        if action == 'buy':
            condition_met = commodity_in_main_currency.real_amount < \
                condition_price_with_margin.real_amount
        elif action == 'sell':
            condition_met = commodity_in_main_currency.real_amount > \
                condition_price_with_margin.real_amount

        logging.debug(
            f'Looking to {action} {commodity.currency}'
        )

        logging.debug(
            f'Currently({datetime.now().strftime(_DATETIME_FORMAT)}): '
            f'Same amount of {commodity.currency} is worth {commodity_in_main_currency}'
        )
        logging.debug(
            f'Desired value to {action} same about of {commodity.currency}: '
            f'{last_price} with margin of {percent_margin}% '
            f'is {min_max_str} {condition_price_with_margin}'
        )
        logging.debug(f'CONDITION MET - {condition_met}')

        simulate_str = '| simulating' if simulation else ''
        sign = '>' if action == 'buy' else '<'
        #  condition_met = True # TODO: REMOVE!
        if condition_met or forceexchange:
            if forceexchange:
                logging.info('[ATTENTION] Force exchange option enabled')
            logging.debug(
                f'Action: '
                f'{condition_price_with_margin} {sign} {commodity_in_main_currency} '
                f'====> {action.upper()}ING {commodity.currency} {simulate_str}'
            )

            if forceexchange or simulation is False or (simulation and sm_transaction_filename):
                # TODO rewrite to return a real object for simulation
                if forceexchange and simulation is False:
                    # Real transaction
                    exchange_transaction = revolut_client.exchange(
                        from_amount=commodity,
                        to_currency=lt_from.currency
                    )
                else:
                    # Simulation transaction
                    exchanged_amount = revolut_client.quote(
                        from_amount=condition_price_with_margin,
                        to_currency=commodity.currency
                    )
                    exchange_transaction = Transaction(
                        from_amount=condition_price_with_margin,
                        to_amount=exchanged_amount,
                        date=datetime.now()
                    )
                logging.info(
                    f'Just({datetime.now().strftime(_DATETIME_FORMAT)}) '
                    f'{action.upper()}ED {exchange_transaction.to_amount} '
                    f'{simulate_str}'
                )
                logging.debug(
                    f'Updating history file : {filename}'
                )
                revolut_bot.update_historyfile(
                    filename=filename,
                    exchange_transaction=exchange_transaction
                )
        else:
            logging.debug(
                f'Action: '
                f'{commodity_in_main_currency} {sign} {condition_price_with_margin} '
                f'====> NOT {action.upper()}ING {commodity.currency} {simulate_str}'
            )
        logging.debug(f'Sleeping for {repeat_every_min} minutes\n\n')
        time.sleep(repeat_every_min*60)


if __name__ == "__main__":
    main()