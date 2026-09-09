import pandas as pd
import numpy as np
from pathlib import Path
from bokeh.models import (CustomJS, WMTSTileSource, RadioButtonGroup, Label, RangeTool, Range1d, HoverTool,
                          ColumnDataSource, Div, Spacer)
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column, row, gridplot

from shorelinerx_val.core import stats


def timeseries(df_dbw:pd.DataFrame):
    '''
    plot timeseries of shorelinerx and groundtruth position along validation transects
    '''

    # Create a global title using a Div
    global_title = Div(text="<h2>Timeseries of waterline position along transects</h2>", sizing_mode='stretch_width')

    # tmin, tmax
    tmin = df_dbw['datetime_utc'].min()
    tmax = df_dbw['datetime_utc'].max()
    x_range = Range1d(tmin, tmax)

    # list of transects
    list_transects = sorted(list(set(df_dbw['transect_id'])))

    def subplot(df_dbw, tr, x_range):

        # Create a ColumnDataSource from dataframe df_dbw
        source = ColumnDataSource(df_dbw[df_dbw['transect_id'] == tr])

        p = figure(sizing_mode='stretch_width', height=200,
                   title=f"Waterline position along transect {tr}",
                   x_range=x_range)

        p.line('datetime_utc', 'bw_insitu_m', source=source, legend_label="groundtruth",
               line_color="black", line_width=1.5)
        p.line('datetime_utc', 'beach_width_m', source=source, legend_label="shorelinerx",
               line_color="#378ADD", line_width=1.5)

        p.yaxis.axis_label = f'Waterline position (m)'
        p.legend.click_policy = "hide"

        return p

    def range_tool_selector(df_dbw, tr, x_range, tmin, tmax):
        '''
        small overview plot with a RangeTool that controls `x_range` (the shared
        range used by the main plots above)
        '''
        source = ColumnDataSource(df_dbw[df_dbw['transect_id'] == tr])

        select = figure(sizing_mode='stretch_width', height=130,
                        title="Drag to select a time range (applies to all plots above)",
                        x_range=Range1d(tmin, tmax),  # own, fixed, full-extent range
                        tools="", toolbar_location=None,
                        y_axis_type=None, background_fill_color="#efefef")

        select.line('datetime_utc', 'bw_insitu_m', source=source,
                    line_color="black", line_width=1)
        select.line('datetime_utc', 'beach_width_m', source=source,
                    line_color="#378ADD", line_width=1)

        range_tool = RangeTool(x_range=x_range)
        range_tool.overlay.fill_color = "navy"
        range_tool.overlay.fill_alpha = 0.2

        select.add_tools(range_tool)
        select.ygrid.grid_line_color = None

        return select

    p_ts = [subplot(df_dbw, tr, x_range) for tr in list_transects]

    # use the last transect's data to build the selector plot at the bottom
    selector = range_tool_selector(df_dbw, list_transects[-1], x_range, tmin, tmax)

    layout = column(global_title, *p_ts, selector, sizing_mode='stretch_width')

    return layout


def statistics(df_dbw, df_stats, site):
    '''
    plot statistics of difference between shorelinerx and groundtruth position along validation transects
    '''

    # scatter
    p1 = scatter(df_dbw, df_stats)

    # box distribution of the error
    p2 = box_error(df_dbw)

    # histogram of error
    p3 = histo_error(df_dbw)

    # Add global title
    title = Div(text=f"<h2>Shorelinerx validation statistics at {site}</h2>", align="center",
                styles={"margin-bottom": "10px"}, sizing_mode='stretch_width')
    layout_stats = row(p1, p2)
    layout_stats = column(title, layout_stats, Spacer(height=30), p3)

    return layout_stats


def scatter(df_dbw: pd.DataFrame, df_stats: pd.DataFrame):

    p1 = figure(
        title="Shorelinerx vs Groundtruth waterline position",
        x_axis_label="Groundtruth waterline position along transects (m)",
        y_axis_label="Shorelinerx waterline position along transects (m)",
        match_aspect=True,
        width=400, height=400,
    )

    # Create a ColumnDataSource from dataframe df_dbw
    source = ColumnDataSource(df_dbw)

    # Add hover tool that shows product_id
    hover = HoverTool(
        tooltips=[
            ("product id", "@product_id"),
            ("cloud cover aoi", "@cloud_cover_aoi"),
        ],
        mode='mouse'
    )
    p1.add_tools(hover)

    p1.scatter(
        x='bw_insitu_m', y='beach_width_m',
        size=4, alpha=0.8,
        color="#378ADD", line_color="white", line_width=0.5, source=source
    )
    # 1:1 reference line
    lim = [np.min([df_dbw['bw_insitu_m'].min(), df_dbw['beach_width_m'].min()]),
           np.max([df_dbw['bw_insitu_m'].max(), df_dbw['beach_width_m'].max()])
           ]
    # labels
    p1.line(lim, lim, line_dash="dashed", line_color="black", line_width=1.5)

    label_mae = Label(
        x=150, y=70, x_units="screen", y_units="screen",
        text=f"MAE (m): {df_stats[df_stats['transect'] == 'ALL']['mae'].squeeze():.2f}", text_color="white", text_font_size="10px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    label_rmse = Label(
        x=150, y=40, x_units="screen", y_units="screen",
        text=f"RMSE (m): {df_stats[df_stats['transect'] == 'ALL']['rmse'].squeeze():.2f}", text_color="white",
        text_font_size="10px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    label_corr = Label(
        x=150, y=10, x_units="screen", y_units="screen",
        text=f"R2: {df_stats[df_stats['transect'] == 'ALL']['corr'].squeeze():.2f}", text_color="white",
        text_font_size="10px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )

    p1.add_layout(label_mae)
    p1.add_layout(label_rmse)
    p1.add_layout(label_corr)

    return p1


def box_error(df_dbw: pd.DataFrame):

    statistics = [stats.box_stats(df_dbw['d_bw_insitu_m'], 'error')]

    labels = [s["label"] for s in statistics]
    src = ColumnDataSource(dict(
        x=labels,
        q1=[s["q1"] for s in statistics],
        q2=[s["q2"] for s in statistics],
        q3=[s["q3"] for s in statistics],
        upper=[s["upper"] for s in statistics],
        lower=[s["lower"] for s in statistics],
        color=["#1D9E75"],
    ))

    p2 = figure(
        title="Distribution of the error",
        x_range=labels,
        y_axis_label="Value (m)",
        width=400, height=400,
    )

    # IQR box
    p2.vbar(x="x", top="q3", bottom="q1", width=0.5,
            source=src, alpha=0.6)
    # Whiskers
    p2.segment("x", "upper", "x", "q3", source=src, line_color="black")
    p2.segment("x", "lower", "x", "q1", source=src, line_color="black")
    # Whisker caps
    p2.rect("x", "upper", 0.2, 0.0001, source=src, line_color="black")
    p2.rect("x", "lower", 0.2, 0.0001, source=src, line_color="black")
    # Median line
    p2.rect("x", "q2", 0.5, 0.0001, source=src,
            line_color="white", line_width=2)

    return p2


def histo_error(df_dbw: pd.DataFrame):
    hist, edges = np.histogram(df_dbw['d_bw_insitu_m'], bins=150)

    p3 = figure(
        title="Error histogram  (shorelinerx − groundtruth)",
        x_axis_label="Error (m)",
        y_axis_label="Count",
        width=1090, height=400,
    )
    p3.quad(
        top=hist, bottom=0,
        left=edges[:-1], right=edges[1:],
        fill_color="#378ADD", line_color="white", alpha=0.8,
    )
    # Zero-error reference
    p3.line([0, 0], [0, hist.max()],
            line_dash="dashed", line_color="#444441", line_width=1.5)

    return p3


def make(df_dbw: pd.DataFrame, df_stats: pd.DataFrame, site: str, odir: Path):

    # keep only rows where both beach widths exist (shorelinerx and insitu)
    mask_valid = df_dbw[['beach_width_m', 'bw_insitu_m']].notna().all(axis=1)
    df_dbw = df_dbw[mask_valid]

    # timeseries of shorelinerx and insitu waterline position
    layout_ts = timeseries(df_dbw)

    # stats
    layout_stats = statistics(df_dbw, df_stats, site)

    # gather timeseries and stats plots in a single page, using a radio button group
    labels = ['Timeseries', 'Statistics']
    layouts_val = [layout_ts, layout_stats]

    # --- Radio button group ---
    radio = RadioButtonGroup(
        labels=labels,
        active=0,
        button_type="success"
    )

    # Set initial visibility: only the first layout is visible
    for i, layout in enumerate(layouts_val):
        layout.visible = (i == 0)

    # Simple loop: show only the plot matching the active index
    callback = CustomJS(args=dict(plots=layouts_val), code="""
            for (let i = 0; i < plots.length; i++) {
                plots[i].visible = (i === cb_obj.active);
            }
        """)
    radio.js_on_change("active", callback)

    layout = column(radio, *layouts_val, sizing_mode='stretch_width')

    # save
    f_out = odir.joinpath(f'validation_sx_{site}.html')
    output_file(f_out)
    print('\n --> %s \n' %f_out)
    save(layout, title='Validation Shorelinerx')

    return