# -*- coding: utf-8 -*-
import revolut_bot
import sys
import yaml
import logging
import os
import time

from revolut import Revolut


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
    logging.basicConfig(level=config.get('log_level', 'INFO'))

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
        logging.info(f'Last transaction : {last_tr}')
        previous_currency = last_tr.from_amount.currency

        current_balance = last_tr.to_amount  # How much we currently have

        current_balance_in_other_currency = revolut_client.quote(
            from_amount=current_balance,
            to_currency=previous_currency
        )
        logging.info(
            f'Today : {current_balance} in '
            f'{previous_currency} : {current_balance_in_other_currency}'
        )

        last_sell = last_tr.from_amount  # How much did it cost before selling
        last_sell_plus_margin = revolut_bot.get_amount_with_margin(
            amount=last_sell,
            percent_margin=percent_margin
        )
        logging.info(
            f'Min value to buy : {last_sell} + {percent_margin}% '
            f'(margin) = {last_sell_plus_margin}'
        )
        buy_condition = current_balance_in_other_currency.real_amount > \
            last_sell_plus_margin.real_amount

        if buy_condition or forceexchange:
            if buy_condition:
                logging.info(
                    f'{current_balance_in_other_currency} > {last_sell_plus_margin}'
                )
            elif forceexchange:
                logging.info('[ATTENTION] Force exchange option enabled')
            logging.info('=> BUY')

            if simulate:
                logging.info('Simulation mode: do not really buy')
            else:
                exchange_transaction = revolut_client.exchange(
                    from_amount=current_balance,
                    to_currency=previous_currency,
                    simulate=simulate
                )
                logging.info(
                    f'{exchange_transaction.to_amount.real_amount} bought'
                )
                logging.info(f'Update history file : {filename}')
                revolut_bot.update_historyfile(
                    filename=filename,
                    exchange_transaction=exchange_transaction
                )
        else:
            logging.info(
                f'{current_balance_in_other_currency} < {last_sell_plus_margin}'
            )
            logging.info('=> DO NOT BUY')
        logging.info(f'Sleeping {repeat_every_min} minutes\n\n')
        time.sleep(repeat_every_min*60)


if __name__ == "__main__":
    main()
