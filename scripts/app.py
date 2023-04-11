from shiny import App, render, ui

from core.core_functions import (
    load_base, 
    add_target_year, 
    set_last_doy, 
    calc_rank,
    calc_cummean,
)   
from core.plot_functions import plot_main

app_ui = ui.page_fluid(
    ui.h2("tas to date"),
    ui.input_selectize(
        id='region',
        label='Region',
        choices=[
            'global',
            'austria',
            ],
        selected='global',
    ),
    ui.input_selectize(
        id='cumsum',
        label='Aggregation',
        choices=[
            'Täglich',
            'Mittelwert',
        ],
        selected='Täglich',
    ),
    ui.input_slider(
        id='exceedance',
        label='Extreme',
        min=-1.1,
        max=1.1,
        value=1.1,
        step=.1,        
    ),
    ui.input_slider(
        id='year',
        label='Jahr',
        min=1950,
        max=2021,
        value=2021,
        step=1,
    ),
    ui.input_slider(
        id='last_doy',
        label='Tag im Jahr',
        min=1,
        max=365,
        value=150,
        step=1,
    ),
    ui.output_plot(
        id='plot',
        width='1500px',
        height='840px',
        ),
)


def server(input, output, session):

    @output
    @render.plot()
    def plot():

        ds = load_base(input.region())
        add_target_year(ds, year=input.year())
        ds = set_last_doy(ds, input.last_doy())
        
        if input.cumsum() == 'Mittelwert':
            ds = calc_cummean(ds)
        
        ds = calc_rank(ds)
        plot_main(ds, dpi_ratio=1.2, show_exceedance=input.exceedance())

app = App(app_ui, server)
