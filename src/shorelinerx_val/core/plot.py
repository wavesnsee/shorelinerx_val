import pandas as pd
import numpy as np
from pathlib import Path
from bokeh.models import (LinearColorMapper, Slider, CustomJS, ColorBar, Span, WMTSTileSource, RadioButtonGroup, Label,
                          Select, HoverTool, ColumnDataSource, Div)
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column, row, gridplot

from shorelinerx_val.core import stats


def timeseries():
    return

def scatter(df_dbw: pd.DataFrame, df_stats: pd.DataFrame):

    p1 = figure(
        title="Shorelinerx vs Groundtruth beach width",
        x_axis_label="Groundtruth waterline position along transects (m)",
        y_axis_label="Shorelinerx waterline position along transects (m)",
        width=400, height=350,
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
        width=400, height=350,
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
        width=820, height=300,
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

    # shorelinerx and insitu timeseries of beach width

    # scatter
    p1 = scatter(df_dbw, df_stats)

    # box distribution of the error
    p2 = box_error(df_dbw)

    # histogram of error
    p3 = histo_error(df_dbw)

    # Add global title
    title = Div(text=f"<h2>Shorelinerx Validation at {site}</h2>", align="center",
                styles={"margin-bottom": "10px"})

    layout_stats = row(p1, p2)
    layout_stats = column(title, layout_stats, p3)
    output_file(odir.joinpath(f'validation_sx_{site}.html'))
    print('\n --> %s \n' % (odir.joinpath('validation_sx.html')))
    save(layout_stats)

    return