#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
(c) by Lukas Brunner under a MIT License (https://mit-license.org)

Authors:
- Lukas Brunner || lukas.brunner@env.ethz.ch

Abstract: Main functions for calculating time-series of cumulative
temperature in different regions.
"""
import os
from glob import glob
from typing import List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from .plot_functions import plot_main
from .utilities import average_region, kelvin_to_centigrade, time_to_dayofyear

mpl.rc("font", size=20)
plt.rcParams.update(
    {"text.usetex": True, "font.family": "sans-serif", "font.sans-serif": ["Helvetica"]}
)

load_path = "/scratch/shared/ERA5/"
plot_path = "../figures"

data_path = "../data"
fn_pattern = "tas_preprocessed_{region}.nc"


def preprocess_region(region: str, overwrite: bool = False) -> xr.Dataset:
    """Preprocess data to speed up further processing.

    - Rename spatial dimensions
    - cut and average region
    - convert time to year and day of the year
    - convert Kelvin to Centigrade
    - add some metadata
    """
    fn_save = os.path.join(data_path, fn_pattern.format(region=region))
    if not overwrite and os.path.isfile(fn_save):
        return

    path_era5 = os.path.join(load_path, "ERA5/2m_temperature/day/native/*.nc")
    path_era5_prelimbe = os.path.join(
        load_path, "ERA5_prelimbe/2m_temperature/day/native/*.nc"
    )
    filenames = glob(path_era5_prelimbe) + glob(path_era5)

    da_list = []
    for fn in filenames:
        year = int(fn.split("_")[-2])
        da = xr.open_dataset(fn, use_cftime=True)["t2m"]
        da = da.rename({"longitude": "lon", "latitude": "lat"})
        da = average_region(da, region)
        da = time_to_dayofyear(da)
        da = da.expand_dims({"year": [year]})
        da = kelvin_to_centigrade(da)
        da_list.append(da)
    da = xr.concat(da_list, dim="year")

    # set some metadata
    da.attrs["long_name"] = "Near Surface Air Temperature"
    da.attrs["original_files"] = ", ".join(filenames)
    ds = da.to_dataset(name="tas_base")
    ds.attrs["region"] = region

    ds.to_netcdf(fn_save)


def load_base(region: str) -> xr.Dataset:
    """Load data saved by preprocess_region."""
    fn = os.path.join(data_path, fn_pattern.format(region=region))
    ds = xr.open_dataset(fn, use_cftime=True)
    return ds


def load_year_current(region: str) -> xr.DataArray:
    """Separately load if year is current (i.e., not preprocessed)."""
    path = os.path.join(load_path, "ERA5_nrt/2m_temperature/day/native/*.nc")
    filenames = glob(path)
    da = xr.open_mfdataset(filenames, use_cftime=True)["t2m"]
    da = da.rename({"longitude": "lon", "latitude": "lat"})
    da = average_region(da, region)
    da = time_to_dayofyear(da)
    da = kelvin_to_centigrade(da)
    da.attrs["long_name"] = "Near Surface Air Temperature"
    da.attrs["original_files"] = ", ".join(filenames)
    return da


def add_target_year(ds_base: xr.Dataset, year: int,) -> xr.Dataset:
    """Extract of load target year and add it as separate variable."""
    try:
        da = ds_base.sel(year=year, drop=True)["tas_base"]
        doy = 365
    except KeyError:
        da = load_year_current(ds_base.attrs["region"])
        # TODO: I think doy is always just index+1 right?
        doy = da["dayofyear"].values[np.where(np.isfinite(da.values))[0][-1]]

    da.name = "tas"
    ds_base.attrs["year"] = year
    ds_base.attrs["last_doy"] = doy
    ds_base["tas"] = da


def calc_rank(ds: xr.Dataset) -> xr.Dataset:
    """Calculate the rank of the target year and add it as variable."""
    ds.load()
    year = ds.attrs["year"]
    if year > ds["year"].values[-1]:  # out of sample need to add it first
        da = ds["tas"].expand_dims({"year": [ds.attrs["year"]]})
        da = xr.concat([ds["tas_base"], da], dim="year")
    else:
        da = ds["tas_base"]
    # double argsort to get the rank then inverse (highest first)
    rank = da["year"].size - np.argsort(np.argsort(da, axis=0), axis=0)
    rank.name = "rank"
    return xr.merge([ds, rank])


def calc_cummean(ds: xr.Dataset) -> xr.Dataset:
    """Calculate the cummulative mean since the beginning of the year."""
    attrs = ds.attrs
    ds = ds.cumsum("dayofyear") / ds["dayofyear"]
    ds = set_last_doy(ds, attrs["last_doy"])
    ds.attrs = attrs
    ds.attrs["cummean"] = "True"
    return ds


def set_last_doy(ds: xr.Dataset, doy: int) -> xr.Dataset:
    """Manually set until which day of the year the target runs."""
    ds = ds.copy()
    ds["tas"] = ds["tas"].where(ds["dayofyear"] <= doy)
    ds["tas"].astype(np.float)
    ds.attrs["last_doy"] = doy
    return ds


def get_filename(ds: xr.Dataset, cummean: str, ext: str = ".jpg") -> str:
    region = ds.attrs["region"]
    year = str(ds.attrs["year"])
    doy = "{:03d}".format(ds.attrs["last_doy"])
    path = os.path.join(plot_path, region, year, cummean)
    os.makedirs(path, exist_ok=True)
    fn = "_".join(["tas", cummean, region, year, doy])
    return os.path.join(path, fn + ext)


def load_plot_single(
    region: str,
    year: int,
    last_doy: int = None,
    dpi_ratio: float = 1.2,
    save: bool = False,
    save_format: str = ".jpg",
):
    """Like load_plot_all but only for one day. See there for docstring."""
    ds = load_base(region)
    add_target_year(ds, year=year)

    if last_doy is not None:
        ds = set_last_doy(ds, last_doy)

    ds_cum = calc_cummean(ds)
    ds = calc_rank(ds)
    ds_cum = calc_rank(ds_cum)

    plot_main(ds, dpi_ratio=dpi_ratio)
    if save:
        fn = get_filename(ds, "daily", "")
        plt.savefig(fn + save_format, dpi=72)
        # try:
        #     os.remove(fn)
        #     sleep(1)
        # except FileNotFoundError:
        #     pass
        ds.to_netcdf(fn + ".nc")
    plt.show()
    plt.close()

    plot_main(ds_cum, dpi_ratio=dpi_ratio)
    if save:
        fn = get_filename(ds_cum, "cummean", "")
        plt.savefig(fn + save_format, dpi=72)
        ds_cum.to_netcdf(fn + ".nc")
    plt.show()
    plt.close()

    # fig, (ax1, ax2) = plt.subplots(
    #     2, figsize=(16/dpi_ratio, 18/dpi_ratio), dpi=75*dpi_ratio)
    # plot_main(ds, ax=ax1)
    # plot_main(ds_cum, ax=ax2)
    # if save:
    #     fn = get_filename(ds, 'both')
    #     plt.savefig(fn + save_format, dpi=72)
    # plt.show()
    # plt.close()

    return ds, ds_cum


def load_plot_all(
    region: str,
    year: int,
    dpi_ratio: float = 1.2,
    save_format: str = ".jpg",
    overwrite=False,
    produce_gif=True,
) -> List[str]:
    """Main function. Loops over all possible days.

    - load data
    - plot data
    - save plots
    - save data
    - procude gif (optional)
    """
    ds = load_base(region)
    add_target_year(ds, year=year)
    ds_cum = calc_cummean(ds)
    ds = calc_rank(ds)
    ds_cum = calc_rank(ds_cum)

    last_doy = ds.attrs["last_doy"]
    for doy in range(1, last_doy + 1):
        print_nr = 10
        print_denom = last_doy // print_nr + 1
        if doy % print_denom == 0:
            print(f"Processing day of year: {doy}")
        ds_sel = set_last_doy(ds, doy)
        ds_cum_sel = set_last_doy(ds_cum, doy)

        fn = get_filename(ds_sel, "daily", save_format)
        if overwrite or not os.path.isfile(fn):
            plot_main(ds_sel, dpi_ratio=dpi_ratio)
            plt.savefig(fn, dpi=72)
            plt.close()

        fn = get_filename(ds_cum_sel, "cummean", save_format)
        if overwrite or not os.path.isfile(fn):
            plot_main(ds_cum_sel, dpi_ratio=dpi_ratio)
            plt.savefig(fn, dpi=72)
            plt.close()

        fn = get_filename(ds_sel, "both", save_format)
        if overwrite or not os.path.isfile(fn):
            fig, (ax1, ax2) = plt.subplots(
                2, figsize=(16 / dpi_ratio, 18 / dpi_ratio), dpi=75 * dpi_ratio
            )
            plot_main(ds_sel, ax=ax1)
            plot_main(ds_cum_sel, ax=ax2)
            plt.savefig(fn, dpi=72)
            plt.close()

    fn = get_filename(ds, "daily", ".nc")
    if overwrite or not os.path.isfile(fn):
        # try:
        #     os.remove(fn)
        #     sleep(1)
        # except FileNotFoundError:
        #     pass
        ds.to_netcdf(fn)
    fn = get_filename(ds_cum, "cummean", ".nc")
    if overwrite or not os.path.isfile(fn):
        # try:
        #     os.remove(fn)
        #     sleep(1)
        # except FileNotFoundError:
        #     pass
        ds_cum.to_netcdf(fn)

    if produce_gif:
        combine_to_gif(get_filename(ds, "daily", save_format), overwrite=overwrite)
        combine_to_gif(
            get_filename(ds_cum, "cummean", save_format), overwrite=overwrite
        )
        combine_to_gif(get_filename(ds, "both", save_format), overwrite=overwrite)

    return (
        get_filename(ds, "daily", save_format),
        get_filename(ds_cum, "cummean", save_format),
        get_filename(ds, "both", save_format),
    )


def combine_to_gif(
    fn: str, stepsize: int = "auto", delay: int = 40, resize: int = 640, overwrite=False
):
    """Combine individual figures to gif.

    Parameters
    ----------
    fn : str
        full path (path + filename + extension) of ONE figure (will determine
        gif filename)
    stepsize : int, by default 'auto'
        If auto the stepsize will be chosen so that the gif has max 100 steps.
        Set to 1 to include all figures (might result in large file sizes).
    delay : int, by default 10
        See convert -h delay
    resize : int, by default 640
        See convert -h resize
    """
    path, fn = os.path.split(fn)
    fn, ext = os.path.splitext(fn)
    path_parent = "/".join(path.split("/")[:-1])
    fn += f"_stepsize-{stepsize}_delay-{delay}_size-{resize}"
    fn = os.path.join(path_parent, fn + ".gif")

    filenames = glob(os.path.join(path, f"*{ext}"))
    if stepsize == "auto":
        stepsize = len(filenames) // 100 + 1
    filenames = " ".join(filenames[::stepsize])

    if overwrite or not os.path.isfile(fn):
        os.system(f"convert -delay {delay} -resize {resize} {filenames} {fn}")
