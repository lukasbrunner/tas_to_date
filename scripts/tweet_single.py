#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
(c) 2021 under a MIT License (https://mit-license.org)

Authors:
- Lukas Brunner || lukas.brunner@env.ethz.ch

Abstract:

"""
import argparse
import locale
import os
from datetime import datetime
from glob import glob

import tweepy

from core.core_functions import plot_path
from core.plot_functions import map_names
from secret import access_token, access_token_secret, consumer_key, consumer_key_secret

locale.setlocale(locale.LC_TIME, locale.normalize("de"))


def parse_input():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(dest="region", type=str)
    parser.add_argument(dest="type", type=str, choices=["daily", "cummean"])
    parser.add_argument(dest="year", nargs="?", type=str, default="2023")
    parser.add_argument(dest="doy", nargs="?", type=str, default="*")
    return parser.parse_args()


def get_filename(cummean, region, year, doy):
    fn = "_".join(["tas", cummean, region, year, doy])
    fn = os.path.join(plot_path, region, year, cummean, fn + ".jpg")
    if doy == "*":
        return glob(fn)[-1]

    if not os.path.isfile(fn):
        raise IOError(f"File not found: {fn}")
    return fn


def tweet(fn, text):
    auth = tweepy.OAuthHandler(consumer_key, consumer_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    media = api.media_upload(fn)
    api.update_status(status=text, media_ids=[media.media_id])


def get_date(fn, year):
    doy = int(os.path.splitext(fn)[0].split("_")[-1])
    date = datetime.strptime(f"{year}-{doy:03d}", "%Y-%j")
    return date.strftime("%A %-d. %B %Y")


def get_text(date, region, type_):
    region = map_names[region]

    if type_ == "daily":
        return f"Temperatur {region} bis {date}"
    elif type_ == "cummean":
        return f"Kumulative Temperatur {region} bis {date}"


def main():
    args = parse_input()
    fn = get_filename(args.type, args.region, args.year, args.doy)
    date = get_date(fn, args.year)
    text = get_text(date, args.region, args.type)
    tweet(fn, text)


if __name__ == "__main__":
    main()
