#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
(c) by Lukas Brunner under a MIT License (https://mit-license.org)

Authors:
- Lukas Brunner || lukas.brunner@env.ethz.ch

Abstract: A collection of plotting functions.
"""
import os
from datetime import datetime
from typing import List, Tuple

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

map_names = {
    "global": "Global",
    "global-land": "Global (Land)",
    "europe-land": "in Europa (Land)",
    "europe": "in Europa",
    "wce-land": "in Zentraleuropa",
    "austria": "in Österreich",
}

map_names_en = {
    "global": "global",
    "global-land": "global (land)",
    "europe-land": "in Europe (land)",
    "europe": "in Europe",
    "wce-land": "in Central Europe",
    "austria": "in Austria",
}

current_path = os.path.dirname(os.path.abspath(__file__))


def plot_base(
    ax: plt.Axes,
    ds: xr.DataArray,
    mean: bool = False,
    median: bool = True,
    q_ranges: List[Tuple[float, float]] = [
        (0.0, 1.0),
        (0.1, 0.9),
        (0.2, 0.8),
        (0.3, 0.7),
        (0.4, 0.6),
    ],
    record: bool = True,
    german: bool = True,
    annotate: bool = True,
) -> tuple:
    """Plot background shading and basic axis."""
    if mean and median:
        raise ValueError('Only one of "median" and "mean" can be True')

    cummean = bool(ds.attrs.get("cummean", False))
    year = ds.attrs["year"]
    region = ds.attrs["region"]
    last_doy = ds.attrs["last_doy"]
    doys = ds["dayofyear"].values

    for q1, q2 in q_ranges:
        hh = ax.fill_between(
            doys,
            ds["tas_base"].quantile(q1, "year"),
            ds["tas_base"].quantile(q2, "year"),
            facecolor="k",
            edgecolor="none",
            alpha=0.1,
        )

    if mean:
        [h2] = ax.plot(doys, ds["tas_base"].mean("year"), color="k", lw=0.5)
        hh = (hh, h2)
    if median:
        [h2] = ax.plot(doys, ds["tas_base"].median("year"), color="k", lw=0.5)
        hh = (hh, h2)

    ax.set_xlim(doys[0], doys[-1])
    ax.set_xticks([1, 60, 121, 182, 243, 304, 365])
    ax.set_yticks(ax.get_yticks())
    ax.set_yticklabels(
        [int(ll) if float(ll).is_integer() else ll for ll in ax.get_yticks()]
    )
    ax.yaxis.set_ticks_position("both")
    if german:
        ax.set_ylabel("Temperatur ($^\\circ$C)")
        ax.set_xticklabels(
            ["1. Jän.", "1. März", "1. Mai", "1. Jul.", "1. Sep", "1. Nov.", "31. Dez."]
        )
        if year is not None and last_doy is not None and region is not None:
            date = datetime.strptime(f"{year}-{last_doy}", "%Y-%j").strftime("%d.%m.%Y")
            if cummean:
                ax.set_title(
                    "Kumulative Mitteltemperatur {} bis {}".format(
                        map_names[region], date
                    )
                )
            else:
                ax.set_title(
                    "Tagesmitteltemperatur {} bis {}".format(map_names[region], date)
                )
        if cummean:
            ax.text(
                0.99,
                0.4,
                "\n".join(
                    [
                        "\\textbf{Kumulative Mitteltemperatur}",
                        "Mittlere Temperatur vom 1. Jännner",
                        "bis zum angegebenen Tag",
                    ]
                ),
                ha="right",
                va="top",
                fontsize="small",
                transform=ax.transAxes,
            )
    else:
        ax.set_ylabel("Temperature ($^\\circ$C)")
        ax.set_xticklabels(
            ["1. Jan.", "1. Mar.", "1. May", "1. Jul.", "1. Sep", "1. Nov.", "31. Dec."]
        )
        if year is not None and last_doy is not None and region is not None:
            date = datetime.strptime(f"{year}-{last_doy}", "%Y-%j").strftime("%d.%m.%Y")
            if cummean:
                ax.set_title(
                    "Cumulative mean temperature {} to {}".format(
                        map_names_en[region], date
                    )
                )
            else:
                ax.set_title(
                    "Daily mean temperature {} to {}".format(map_names_en[region], date)
                )
        if cummean:
            ax.text(
                0.99,
                0.4,
                "\n".join(
                    [
                        "\\textbf{Cumulative mean temperature}",
                        "Mean temperature from January 1$^\\textnormal{st}$",
                        "until the indicated day",
                    ]
                ),
                ha="right",
                va="top",
                fontsize="small",
                transform=ax.transAxes,
            )
    if annotate:
        annotate_shading(ax, ds["tas_base"], german)

    return hh


def plot_target(
    ax: plt.Axes,
    ds: xr.Dataset,
    show_record: Tuple[bool, str] = "always",
    show_exceedance: float = 1.,
    show_rank: bool = True,
) -> "handle":
    """Plot the target year and related information.

    Parameters
    ----------
    ax : plt.Axes
    ds : xr.Dataset
    show_record : bool or 'always', optional, by default 'always'
        If False do not show days with a new record. If True only show the
        indicator if there is at least one day with a record. If 'always'
        always show it. TODO: remove - redundant with 'show_exceedance'
    show_exceedance : float, optional, by default 1.
        Several cases are disdinguished:
          - if absolute value larger than 1 do not show days with exceedances or new records
          - if exactly 1 show new heat records (default)
          - if exactly -1 show new cold records
          - if positive show exceedances of the given quantile
          - if negative show undercuts of given (absolut value) of quantile
    show_rank : bool, optional, by default True
        Annotate the last day with rank and anomaly.

    Returns
    -------
    handle
        For use in the figure legend.
    """
    [h2] = ax.plot(ds["dayofyear"], ds["tas"], color="darkred")
    # if show_record is not None:
    #     mark_record(ax, ds, show_record == "always")
    last_day_unseen = None
    if np.abs(show_exceedance) <= 1:
        mark_exceedance(ax, ds, show_exceedance)
        last_day_unseen = mark_unseen(ax, ds, show_exceedance)
    if show_rank:
        annotate_last_day(ax, ds, unseen=last_day_unseen)
    return h2


# def mark_record(ax: plt.Axes, ds: xr.Dataset, always: bool = False) -> None:
#     """Indicate days where the year has the maximum value."""
#     max_ = ds["tas"] >= ds["tas_base"].max("year")
#     # min_ = ds["tas"] <= ds["tas_base"].min("year")
#     # record = np.logical_or(max_, min_)
#     y_min = ds["tas_base"].min()  # for line placement
#     if np.any(max_) or always:
#         max_ = (max_.where(max_) * 0) + y_min
#         ax.axhline(y_min, color="k", ls="--", lw=0.5)
#         ax.text(
#             33,
#             y_min,
#             "Tage mit Hitzerekord: {}/{}".format(
#                 np.isfinite(max_).sum().values, np.isfinite(ds["tas"]).sum().values
#             ),
#             va="bottom",
#         )
#         ax.plot(ds["dayofyear"], max_, marker="s", ms=2, ls="none", color="darkred")
#         ds.attrs["show_record"] = "True"
        
        
def mark_unseen(ax: plt.Axes, ds: xr.Dataset, always: bool = False) -> None:
    """Indicate days where the year has values unseen in any year or day."""
    max_ = ds["tas"] >= ds["tas_base"].max()
    y_min = ds["tas_base"].min()  # for line placement
    if np.any(max_) or always:
        ax.axhline(ds['tas_base'].max(), color='purple', ls=':', lw=1.)
        ax.plot(ds["dayofyear"], ds['tas'].where(max_), color="purple")
        max_ = (max_.where(max_) * 0) + y_min
        ax.text(
            5,
            ds['tas_base'].max() * .995,
            "Tage mit absolutem Rekord: {}".format(np.isfinite(max_).sum().values),
            va="top",
        )
        ax.plot(ds["dayofyear"], max_, marker="s", ms=2, ls="none", color="purple")
        ds.attrs["show_unseen"] = "True"
        return max_
    return None


def mark_exceedance(ax: plt.Axes, ds: xr.Dataset, quantile: float, always: bool = True) -> None:
    """Indicate days where the year exceeds a given percentile."""
    year = ds.attrs["year"]
    # remove year itself (otherwise there will be no new records for in-sample)
    ds = ds.sel(year=ds["year"] != year)

    if quantile == 1:
        threshold = ds["tas"] >= ds["tas_base"].max("year")
        text = "Tage mit Hitzerekord"
    elif quantile == -1:
        threshold = ds["tas"] <= ds["tas_base"].min("year")
        text = "Tage mit Kälterekord"
    elif quantile == 0:
        threshold = ds["tas"] >= ds["tas_base"].min("year")
        text = "Tage über Minimum"
    elif quantile > 0:
        threshold = ds["tas"] >= ds["tas_base"].quantile(quantile, "year")
        text = "Tage in wärmsten {:.0f}\%".format((1-quantile) * 100)
    else:
        threshold = ds["tas"] <= ds["tas_base"].quantile(np.abs(quantile), "year")
        text = "Tage in kältesten {:.0f}\%".format(np.abs(quantile) * 100)

    y_min = ds["tas_base"].min()  # for line placement
    if np.any(threshold) or always:
        threshold = (threshold.where(threshold) * 0) + y_min
        ax.axhline(y_min, color="k", ls="--", lw=0.5)
        ax.text(
            33,
            y_min,
            "{}: {}/{} ({:.0f}\%)".format(
                text,
                np.isfinite(threshold).sum().values,
                np.isfinite(ds["tas"]).sum().values,
                np.isfinite(threshold).sum().values / np.isfinite(ds["tas"]).sum().values * 100
            ),
            va="bottom",
        )
        ax.plot(ds["dayofyear"], threshold, marker="s", ms=2, ls="none", color="darkred")
        ds.attrs["show_record"] = "True"


def annotate_last_day(ax: plt.Axes, ds: xr.Dataset, unseen: xr.DataArray=None) -> None:
    """Plot the anomaly and rank of the last available day of year."""
    year = ds.attrs["year"]
    doy_last = ds.attrs["last_doy"]
    ds_last = ds.sel(dayofyear=doy_last, drop=True)
    middle = ds_last["tas_base"].median("year").values  # TODO: add mean

    rank_last = ds_last["rank"].sel(year=year).values
    rank_total = ds_last["year"].size
    anom_last = (ds_last["tas"] - middle).values

    # print(middle)

    text = f"{anom_last:+.1f}$^\\circ$C\n{rank_last}/{rank_total}"
    
    color = 'darkred'
    if unseen is not None:
        unseen_last = unseen.sel(dayofyear=doy_last, drop=True).values
        if np.isfinite(unseen_last):
            color = 'purple'

    if doy_last > 321:  # adjust possition to avoid running out the plot
        x_pos = 360
        min_ = np.nanmin(ds["tas"].isel(dayofyear=ds["dayofyear"] > 321))
        ylim1, ylim2 = ax.get_ylim()
        y_pos = np.min([min_, middle]) - 0.03 * (ylim2 - ylim1)
        ha = "right"
        va = "top"
    else:
        x_pos = doy_last + 5
        y_pos = middle + 0.5 * anom_last
        ha = "left"
        va = "center"

    ax.vlines(doy_last, ds_last["tas"], middle, colors=color, ls=":", lw=1)
    ax.text(
        x_pos,
        y_pos,
        text,
        color=color,
        ha=ha,
        va=va,
        multialignment="left",
        bbox=dict(facecolor="w", alpha=0.4, edgecolor="none"),
    )


def annotate_shading(ax: plt.Axes, da: xr.DataArray, german: bool) -> None:
    """Add an explainer about the meaning of the shading.

    Parameters
    ----------
    ax : plt.Axes
    da : xr.DataArray
    """
    if german:
        # # upper percentile
        # doy = 90  # target possition
        # y_pos = da.sel(dayofyear=doy).quantile(.98, 'year')
        # ax.annotate(
        #     '10\\,\\% wärmste Jahre',
        #     (doy, y_pos),
        #     (30, da.sel(dayofyear=doy + 30).max().values),
        #     verticalalignment='center',
        #     arrowprops={'arrowstyle': '->'}, fontsize='small',
        # )

        # lower percentile
        doy = 120
        y_pos = da.sel(dayofyear=doy).quantile(0.02, "year").values
        ax.annotate(
            "10\\,\\% kälteste Jahre",
            (doy, y_pos),
            (150, da.sel(dayofyear=doy).min().values),
            verticalalignment="center",
            horizontalalignment="left",
            arrowprops={"arrowstyle": "->", "relpos": (0.5, 0.5)},
            fontsize="small",
        )
    else:
        # lower percentile
        doy = 120
        y_pos = da.sel(dayofyear=doy).quantile(0.02, "year").values
        ax.annotate(
            "10\\,\\% coldest years",
            (doy, y_pos),
            (150, da.sel(dayofyear=doy).min().values),
            verticalalignment="center",
            horizontalalignment="left",
            arrowprops={"arrowstyle": "->", "relpos": (0.5, 0.5)},
            fontsize="small",
        )


def plot_ccby(ax: plt.Axes, ds: xr.Dataset, twitter_handle: bool = True,) -> None:
    """Add a license to the plot.

    Parameters
    ----------
    ax : plt.Axes
    twitter_handle : bool, optional
        Whether to also add the Twitter handle, by default True
    loc : str, optional
        Location of the license, by default 'lower right'
    """
    if bool(ds.attrs.get("cummean", False)):
        if bool(ds.attrs.get("show_record", False)):
            yy = 0.05
        else:
            yy = 0.01
    else:
        # TODO: update placement
        yy = 0.86

    arr = mpimg.imread(os.path.join(current_path, "../../images/by.png"))
    imagebox = OffsetImage(arr, zoom=0.19)
    ab = AnnotationBbox(
        imagebox,
        (0.99, yy + 0.06),
        frameon=False,
        box_alignment=(1, 0),
        xycoords="axes fraction",
    )
    ax.add_artist(ab)
    ax.annotate(
        "Lukas Brunner",
        (0, 0),
        xytext=(0.99, yy + 0.03),
        fontsize="xx-small",
        ha="right",
        va="bottom",
        xycoords="axes fraction",
    )
    if twitter_handle:
        ax.annotate(
            "@luki_brunner",
            (0, 0),
            xytext=(0.99, yy),
            fontsize="xx-small",
            color="blue",
            ha="right",
            va="bottom",
            xycoords="axes fraction",
        )


def plot_legend(ax: plt.Axes, handles: list, ds: xr.Dataset):
    year_start = ds["year"][0].values
    # last not nan year in base
    year_end = ds["year"][np.isfinite(ds["tas_base"].sel(dayofyear=1, drop=True))][
        -1
    ].values
    years = "{}-{}".format(year_start, year_end)
    # ax.legend(handles, [years, ds.attrs["year"]], loc="upper left")
    # box: x, y, width, height
    ax.legend(handles, [years, ds.attrs["year"]], loc="best", bbox_to_anchor=(0, .2, .4, .6))


def plot_main(
    ds: xr.Dataset,
    ax: plt.Axes = None,
    dpi_ratio: float = 1.2,
    language: str = "german",
    show_exceedance: float = 1.1,
):
    """Main plotting function. Calls relevant subfunctions."""
    if ax is None:
        fig, ax = plt.subplots(
            figsize=(16 / dpi_ratio, 9 / dpi_ratio), dpi=150 * dpi_ratio
        )
    h1 = plot_base(ax, ds, german=language == "german")
    # show_record = True if bool(ds.attrs.get('cummean', False)) else 'always'
    # show_record = True
    h2 = plot_target(ax, ds, show_exceedance=show_exceedance)
    plot_legend(ax, [h1, h2], ds)
    plot_ccby(ax, ds)
    plt.gcf().tight_layout()
