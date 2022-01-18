import warnings
from datetime import datetime

import dask
import numpy as np
import regionmask
import xarray as xr

regions = {
    'global': {'region': 'global'},
    'global-land': {'region': 'global', 'land_sea': 'land'},
    'europe-land': {'region': 'EUR', 'land_sea': 'land'},
    'europe': {'region': 'EUR'},
    'wce-land': {'region': 'WCE', 'land_sea': 'land'},
    'austria': {'region': 'Austria'},
}

def area_weighted_mean(ds: 'xr.dataset', latn='lat', lonn='lon') -> 'xr.dataset':
    """Calculate area mean weighted by the latitude."""
    weights_lat = np.cos(np.radians(ds[latn]))
    return ds.weighted(weights_lat).mean((latn, lonn))


def set_antimeridian(
        dataarray: 'xr.DataArray',
        to: str='pacific',
        lonn: str='lon') -> 'xr.DataArray':
    """
    Flip the antimeridian (i.e. longitude discontinuity) between Europe
    (i.e., [0, 360)) and the Pacific (i.e., [-180, 180)).

    Parameters:
    - dataarray : xarray.DataArray
    - to : string, {'Pacific', 'Europe'}
      * 'Europe': Longitude will be in [0, 360)
      * 'Pacific': Longitude will be in [-180, 180)
    - lonn: string, optional

    Returns:
    dataarray_flipped : xarray.DataArray
    """
    lon = dataarray[lonn]
    lon_attrs = lon.attrs

    if to.lower() == 'europe':
        dataarray = dataarray.assign_coords(**{lonn: (lon % 360)})
    elif to.lower() == 'pacific':
        dataarray = dataarray.assign_coords(**{lonn: (((lon + 180) % 360) - 180)})
    else:
        errmsg = "to has to be one of ['Europe', 'Pacific'] not {}".format(to)
        raise ValueError(errmsg)

    idx = np.argmin(dataarray[lonn].values)
    dataarray = dataarray.roll(**{lonn: -idx}, roll_coords=True)
    dataarray[lonn].attrs = lon_attrs
    return dataarray


def make_regions() -> regionmask:
    """Create manually defined regions."""
    europe = np.array([
        [-10.0, 76.25],
        [39.0, 76.25],
        [39.0, 30.0],
        [-10.0, 30.0]
    ])
    return regionmask.Regions([europe], names=['Europe'], abbrevs=['EUR'])


def cut_region(
        dataset: 'xr.Dataset',  # TODO: currently I would want to pass a ds!
        region: str,
        land_sea: str = 'both'
        ) -> 'xr.Dataset':
    """
    Parameters
    ----------
    data_array : xarray.DataArray
    region : string, optional
        Either one IPCC AR6 regions
        (https://regionmask.readthedocs.io/en/stable/defined_scientific.html)
        or a country
    land_sea : string, optional, on of {'land', 'sea', 'both'}

    Returns
    -------
    data_array : xarray.DataArray
        A data_array with grid cells outside of the given area set to nan
        and longitudes and latitudes with only nan values dropped.

    Raises
    ------
    ValueError
        All values are masked.
    """
    # dataset = set_antimeridian(dataset)
    da = dataset

    if region.lower() == 'global' and land_sea == 'both':
        return dataset, None

    if region.lower() == 'global':
        mask = True
    elif region in regionmask.defined_regions.ar6.all.abbrevs:
        key = regionmask.defined_regions.ar6.all.map_keys(region)
        mask = regionmask.defined_regions.ar6.all.mask(da, wrap_lon=None) == key
    elif region in regionmask.defined_regions.natural_earth.countries_110.names:
        key = regionmask.defined_regions.natural_earth.countries_110.map_keys(region)
        mask = regionmask.defined_regions.natural_earth.countries_110.mask(da, wrap_lon=None) == key
    else:
        try:
            manual_regions = make_regions()
            key = manual_regions.map_keys(region)
            mask = manual_regions.mask(da, wrap_lon=None) == key
        except KeyError:
            raise IOError(f'Invalid region {region}')

    if land_sea == 'land':
        land = regionmask.defined_regions.natural_earth.land_110.mask(
            da, wrap_lon=None) == 0
        mask &= land
    elif land_sea == 'sea':
        land = regionmask.defined_regions.natural_earth.land_110.mask(
            da, wrap_lon=None) == 0
        mask &= ~land
    elif land_sea != 'both':
        raise IOError('Invalid land-sea mask string')

    if not np.any(mask):
        raise ValueError('all values masked')

    return dataset.where(mask, drop=True), mask.where(mask, drop=True)


def average_region(da: xr.DataArray, region: str) -> xr.DataArray:
    with dask.config.set(**{'array.slicing.split_large_chunks': False}):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            da, _ = cut_region(da, **regions[region])
    da = area_weighted_mean(da)
    return da


def kelvin_to_centigrade(da: xr.DataArray) -> xr.DataArray:
    da = da - 273.15
    da.attrs['units'] = 'degree_C'
    return da


def delete_last_day_leap_year(da: xr.DataArray) -> xr.DataArray:
    return da.where(da['dayofyear'] != 366, drop=True)


def time_to_dayofyear(
        da: xr.DataArray,
        delete_leap_year: bool=True) -> xr.DataArray:
    da = da.assign_coords(time=da['time.dayofyear'])
    da = da.rename({'time': 'dayofyear'})
    if delete_leap_year:
        da = delete_last_day_leap_year(da)
    return da
