#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
(c) 2021 under a MIT License (https://mit-license.org)

Authors:
- Lukas Brunner || lukas.brunner@env.ethz.ch

Abstract:

"""
import os
import argparse
import tweepy
import base64
import requests
import regionmask
import numpy as np
from glob import glob
from datetime import datetime
from glob import glob
import locale
locale.setlocale(locale.LC_TIME, locale.normalize("de"))

from core.core_functions import plot_path
from core.plot_functions import map_names

from secret import (
    consumer_key, consumer_key_secret,
    access_token, access_token_secret
)

def parse_input():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(dest='year', type=str)
    parser.add_argument(dest='doy', nargs='?', type=str, default='*')
    return parser.parse_args()


def get_filename(cummean, region, year, doy):
    fn = '_'.join(['tas', cummean, region, year, doy])
    fn = os.path.join(plot_path, region, year, cummean, fn + '.jpg')
    if doy == '*':
        return glob(fn)[-1]

    if not os.path.isfile(fn):
        raise IOError(f'File not found: {fn}')
    return fn


def tweet(filenames, text):
    auth = tweepy.OAuthHandler(consumer_key, consumer_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    media_ids = [api.media_upload(fn).media_id for fn in filenames]
    api.update_status(status=text, media_ids=media_ids)


def get_date(fn, year):
    doy = int(os.path.splitext(fn)[0].split('_')[-1])
    date = datetime.strptime(f'{year}-{doy:03d}', '%Y-%j')
    return date.strftime('%A %-d. %B %Y')


def get_text(date, region, type_):
    region = map_names[region]

    if type_ == 'daily':
        return f'Temperatur {region} bis {date}'
    elif type_ == 'cummean':
        return f'Kummulative Temperatur {region} bis {date}'


def main():
    args = parse_input()
    filenames = [
        get_filename('daily', 'europe', args.year, args.doy),
        get_filename('daily', 'austria', args.year, args.doy),
        get_filename('cummean', 'europe', args.year, args.doy),
        get_filename('cummean', 'austria', args.year, args.doy)]
    date = get_date(filenames[0], args.year)
    text = f'Temperaturverlauf in Österreich und Europa bis {date}'
    tweet(filenames, text)


if __name__ == '__main__':
    main()