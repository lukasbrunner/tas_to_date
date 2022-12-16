#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
(c) by Lukas Brunner under a MIT License (https://mit-license.org)

Authors:
- Lukas Brunner || lukas.brunner@env.ethz.ch

Abstract:

"""
import argparse
from datetime import datetime

from core.core_functions import combine_to_gif, load_plot_all
from core.utilities import regions

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument(
    dest="year",
    nargs="?",
    default=datetime.now().year,
    type=int,
    help="Year to process (by defaults to current year)",
)
parser.add_argument(
    "--regions",
    "-r",
    dest="regions",
    nargs="+",
    default=regions,
    type=str,
    help="Regions to process (by default all available regions)",
)
parser.add_argument(
    "--language",
    "-l",
    dest="language",
    type=str,
    default="german",
    choices=["german", "english"],
    help="Select language of plot labels",
)
parser.add_argument(
    "--overwrite",
    "-o",
    dest="overwrite",
    action="store_true",
    help="Overwrite existing plot files",
)
parser.add_argument(
    "--show-exceedance",
    "-e",
    dest="show_exceedance",
    type=float,
    default=1.1,
    help="If in [-1, 1] show exeedances of given quantile (see docstring for interpretation of negative values)",
)
args = parser.parse_args()

year = args.year
print(f"{year=}")

for region in args.regions:
    print("")
    print(f"{region=}")
    print("-" * 20)
    fn_daily, fn_cummean, fn_both = load_plot_all(
        region=region,
        year=year,
        overwrite=args.overwrite,
        language=args.language,
        show_exceedance=args.show_exceedance,
    )

    combine_to_gif(fn_daily, stepsize=1, delay=10)
    combine_to_gif(fn_cummean, stepsize=1, delay=10)
    combine_to_gif(fn_both, stepsize=1, delay=10)
