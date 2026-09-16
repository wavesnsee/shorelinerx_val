import pandas as pd
import numpy as np
from pathlib import Path
from ESMBenchmarkViz import taylor_diagram
from bokeh.models import (CustomJS, WMTSTileSource, RadioButtonGroup, Label, RangeTool, Range1d, HoverTool,
                          ColumnDataSource, Div, Spacer, DataTable, TableColumn, NumberFormatter)
from bokeh.transform import linear_cmap
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column, row

from shorelinerx_val.core import stats, sx


def osm_tile(tile_choice: str):

    # OSM tiles
    if tile_choice == 'carto_light':
        tile = WMTSTileSource(
            url='https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{Z}/{X}/{Y}.png',
            attribution='&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )

    elif tile_choice == "Esri":
        tile = "Esri World Imagery"

    return tile


def transects(df_tr: pd.DataFrame, table_tr_id:dict, odir):

    # convert transects coordinates to web mercator
    df_tr = df_tr.to_crs(3857)

    # Create figure
    p = figure(title='Validation transects', width=1536, height=864, x_axis_type="mercator", y_axis_type="mercator",
               match_aspect=True)

    # Add OSM tiles
    tile_choice = 'Esri'
    p.add_tile(osm_tile(tile_choice))

    # Hide grid lines
    p.grid.visible = False

    # plot transects
    for i in range(len(df_tr)):
        p.line(df_tr.geometry[i].xy[0], df_tr.geometry[i].xy[1], line_width=2, color="red")

    # plot transects' names
    for i in range(len(df_tr)):
        label = Label(
            x=df_tr.geometry[i].xy[0][-1], y=df_tr.geometry[i].xy[1][-1],
            text=table_tr_id[i],
            x_offset=8, y_offset=0,
            text_font_size="12pt", text_baseline="middle",
            background_fill_color="white", background_fill_alpha=1,
            border_line_color="black", border_line_alpha=0.5,
        )
        p.add_layout(label)

    return p


def timeseries(ls_df_dbw:list[pd.DataFrame], mission: str, sdi_id: list[str], sdi_color: list[str]):
    '''
    plot timeseries of shorelinerx and groundtruth position along validation transects
    '''

    # Create a global title using a Div
    global_title = Div(text=f"<h2>Timeseries of waterline position along transects, groundtruth vs "
                            f"{' / '.join(sdi_id)}, mission: {mission}</h2>", sizing_mode='stretch_width')

    # tmin, tmax
    tmin = np.min([df_dbw['datetime_utc'].min() for df_dbw in ls_df_dbw])
    tmax = np.max([df_dbw['datetime_utc'].max() for df_dbw in ls_df_dbw])
    x_range = Range1d(tmin, tmax)

    # list of transects
    list_transects = sorted(list(set(ls_df_dbw[0]['transect_id'])))

    def subplot(ls_df_dbw, tr, x_range, sdi_id, sdi_color):

        p = figure(sizing_mode='stretch_width', height=200,
                   title=f"Waterline position along transect {tr}",
                   x_range=x_range)

        for i, df_dbw in enumerate(ls_df_dbw):
            # Create a ColumnDataSource from dataframe df_dbw
            source = ColumnDataSource(df_dbw[df_dbw['transect_id'] == tr])
            if i == 0:
                p.line('datetime_utc', 'bw_insitu_m', source=source, legend_label="groundtruth",
                       line_color="black", line_width=1.5)
            p.line('datetime_utc', 'beach_width_m', source=source, legend_label=sdi_id[i],
                   line_color=sdi_color[i], line_width=1.5)

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

    p_ts = [subplot(ls_df_dbw, tr, x_range, sdi_id, sdi_color) for tr in list_transects]

    # use the last transect's data to build the selector plot at the bottom
    selector = range_tool_selector(ls_df_dbw[0], list_transects[-1], x_range, tmin, tmax)

    layout = column(global_title, *p_ts, selector, sizing_mode='stretch_width')

    return layout


def scatter(ls_df_dbw: list[pd.DataFrame], ls_df_stats: list[pd.DataFrame], sdi_id: list[str],
            sdi_color: list[str]):

    p1 = figure(
        title=f"{', '.join(sdi_id)} vs Groundtruth waterline position",
        x_axis_label="Groundtruth waterline position along transects (m)",
        y_axis_label="Sat derived waterline position along transects (m)",
        match_aspect=True,
        width=400, height=400,
    )

    def sub_scatter(p1, ls_df_dbw, ls_df_stats, sdi_id, sdi_color):

        for i, df_dbw in enumerate(ls_df_dbw):

            # Create a ColumnDataSource from dataframe df_dbw
            source = ColumnDataSource(df_dbw)

            # corr
            df_stats = ls_df_stats[i]
            r2 = f", R2: {df_stats[df_stats['transect'] == 'ALL']['corr'].squeeze():.2f}"

            p1.scatter(
                x='bw_insitu_m', y='beach_width_m',
                size=4, alpha=0.8,
                color=sdi_color[i], line_color="white", line_width=0.5, source=source, legend_label=sdi_id[i] + r2
            )

        return

    # Add hover tool that shows product_id
    hover = HoverTool(
        tooltips=[
            ("product id", "@product_id"),
            ("cloud cover aoi", "@cloud_cover_aoi"),
        ],
        mode='mouse'
    )
    p1.add_tools(hover)

    # scatter plots
    sub_scatter(p1, ls_df_dbw, ls_df_stats, sdi_id, sdi_color)

    # 1:1 reference line
    bw_min = np.min([df_dbw['beach_width_m'].min() for df_dbw in ls_df_dbw])
    bw_max = np.max([df_dbw['beach_width_m'].max() for df_dbw in ls_df_dbw])

    lim = [bw_min, bw_max]
    p1.line(lim, lim, line_dash="dashed", line_color="black", line_width=1.5)

    p1.legend.click_policy = "hide"

    return p1


def box_error(ls_df_dbw: list[pd.DataFrame], sdi_id: list[str], sdi_color: list[str]):

    labels = [f"error_{sdi_id[i]}" for i in range(len(ls_df_dbw))]

    p2 = figure(
        title="Distribution of the error",
        x_range=labels,
        y_axis_label="Value (m)",
        width=450, height=400,
    )

    for i, (df_dbw, label, color) in enumerate(zip(ls_df_dbw, labels, sdi_color)):
        s = stats.box_stats(df_dbw['d_bw_insitu_m'], 'error')

        src = ColumnDataSource(dict(
            x=[label],
            q1=[s["q1"]],
            q2=[s["q2"]],
            q3=[s["q3"]],
            upper=[s["upper"]],
            lower=[s["lower"]],
            color=[color],
        ))

        # IQR box
        p2.vbar(x="x", top="q3", bottom="q1", width=0.5,
                source=src, fill_color="color", line_color="black",
                fill_alpha=0.6)
        # Whiskers
        p2.segment("x", "upper", "x", "q3", source=src,
                   line_color="black")
        p2.segment("x", "lower", "x", "q1", source=src,
                   line_color="black")
        # Whisker caps
        p2.rect("x", "upper", 0.2, 0.0001, source=src,
                line_color="black")
        p2.rect("x", "lower", 0.2, 0.0001, source=src,
                line_color="black")
        # Median line
        p2.rect("x", "q2", 0.5, 0.0001, source=src,
                line_color="white", line_width=2)

    return p2


def histo_error(ls_df_dbw: list[pd.DataFrame], sdi_id: list[str], sdi_color: list[str]):

    p3 = figure(
        title="Error histogram  (shorelinerx − groundtruth)",
        x_axis_label="Error (m)",
        y_axis_label="Count",
        width=400, height=400,
    )

    # bin edges
    bin_edges = np.arange(-20, 20.1, 1)

    for i, df_dbw in enumerate(ls_df_dbw):
        hist, edges = np.histogram(df_dbw['d_bw_insitu_m'], bins=bin_edges)

        p3.x_range = Range1d(-30, 30)

        p3.quad(
            top=hist, bottom=0,
            left=edges[:-1], right=edges[1:],
            fill_color=sdi_color[i], line_color="white", alpha=0.8, legend_label=sdi_id[i]
        )
    # Zero-error reference
    p3.line([0, 0], [0, hist.max()],
            line_dash="dashed", line_color="#444441", line_width=1.5)

    p3.legend.click_policy = "hide"
    p3.legend.location = "top_right"

    return p3


def table(ls_df_stats, sdi_id: list[str], sdi_color: list[str]):

    # backward compatibility: allow a single DataFrame too
    if isinstance(ls_df_stats, pd.DataFrame):
        ls_df_stats = [ls_df_stats]

    n = len(ls_df_stats)
    
    stat_cols = ["mae", "rmse", "mean", "std", "n_samples"]

    df_merged = None
    for df, label in zip(ls_df_stats, sdi_id):
        df_renamed = df[["transect"] + stat_cols].rename(
            columns={c: f"{c}_{label}" for c in stat_cols}
        )
        df_merged = df_renamed if df_merged is None else df_merged.merge(df_renamed, on="transect", how="outer")

    source = ColumnDataSource(data=df_merged.round(2))

    stat_titles = {
        "mae": "MAE (m)", "rmse": "RMSE (m)", "mean": "Bias (m)",
        "std": "std (m)", "n_samples": "n_samples",
    }

    columns = [TableColumn(field="transect", title="Transect")]
    header_rules = []  # one CSS rule per colored header

    # position 1 = "Transect" (no color); data columns start at position 2
    pos = 2
    for stat in stat_cols:
        for i, label in enumerate(sdi_id):
            field = f"{stat}_{label}"
            # title = f"{stat_titles[stat]} [{label}]" if n > 1 else stat_titles[stat]
            title = f"{stat_titles[stat]}" if n > 1 else stat_titles[stat]

            if stat == "n_samples":
                columns.append(TableColumn(field=field, title=title))
            else:
                columns.append(TableColumn(
                    field=field, title=title,
                    formatter=NumberFormatter(format="0.00", background_color=linear_cmap(
                        field_name=field, palette="RdYlGn9", low=4, high=12))
                ))

            # color = label_color[label]
            color = sdi_color[i]
            header_rules.append(
                f".slick-header-column:nth-child({pos}) {{ background-color: {color} !important; color: white !important; }}"
            )
            pos += 1

    header_css = "\n".join(header_rules)

    data_table = DataTable(source=source, columns=columns,
                           width=400 * max(n, 1) if n > 1 else 450, height=400,
                           index_position=None,
                           stylesheets=[f"""
                                        .slick-header-column {{
                                            font-weight: bold;
                                            font-size: 13px;
                                        }}
                                        .slick-cell {{
                                            font-size: 13px;
                                        }}
                                        {header_css}
                                    """],
                           )
    title = Div(text="<b>Validation statistics by transect, and globally (ALL) </b>", styles={"font-size": "12px"})
    table_with_title = column(title, data_table)
    return table_with_title


def taylor(ls_df_stats, ls_df_dbw, sdi_id, sdi_color):

    if len(ls_df_stats) < 2:
        return None
    else:
        corrs = [ls_df_stats[i][ls_df_stats[i]['transect']=='ALL']['corr'].values[0] for i in range(len(ls_df_stats))]
        std_devs = [ls_df_dbw[i]['beach_width_m'].std() for i in range(len(ls_df_dbw))]
        refstd = ls_df_dbw[0]['bw_insitu_m'].std()

    p5 = taylor_diagram(std_devs, corrs, sdi_id, refstd, normalize=True, step=0.1, reference_name='groundtruth',
                        colormap=sdi_color, bokeh_logo=False, width=400, show_plot=False)

    return p5

def statistics(ls_df_dbw: list[pd.DataFrame], ls_df_stats: list[pd.DataFrame], site, mission, sdi_id: list[str],
               sdi_color: list[str]):
    '''
    plot statistics of difference between sat waterlines and groundtruth position along validation transects
    '''

    # scatter
    p1 = scatter(ls_df_dbw, ls_df_stats, sdi_id, sdi_color)

    # box distribution of the error
    p2 = box_error(ls_df_dbw, sdi_id, sdi_color)

    # histogram of error
    p3 = histo_error(ls_df_dbw, sdi_id, sdi_color)

    # stats table
    p4 = table(ls_df_stats, sdi_id, sdi_color)

    # taylor diagram
    if len(ls_df_dbw) > 1:
        p5 = taylor(ls_df_stats, ls_df_dbw, sdi_id, sdi_color)

    # Add global title
    title = Div(text=f"<h2>{(' / ').join(sdi_id)} validation statistics at {site} for mission {mission}</h2>", align="center",
                styles={"margin-bottom": "10px"}, sizing_mode='stretch_width')
    layout_stats = row(p1, p2, p3)
    if len(ls_df_dbw) > 1:
        layout_stats = column(title, layout_stats, Spacer(height=40), row(p5, Spacer(width=20), p4))
    else:
        layout_stats = column(title, layout_stats, Spacer(height=40), p4)


    return layout_stats



def make(df_tr: pd.DataFrame, table_tr_id: dict, ls_df_dbw: list[pd.DataFrame], ls_df_stats: list[pd.DataFrame],
         site: str, sdi_id: list[str], sdi_color: list[str], odir: Path):

    # mission
    mission = sx.read_mission_name(ls_df_dbw[0])

    # transects
    layout_tr = transects(df_tr, table_tr_id, odir)

    # timeseries of sat and insitu waterline position
    layout_ts = timeseries(ls_df_dbw, mission, sdi_id, sdi_color)

    # stats
    layout_stats = statistics(ls_df_dbw, ls_df_stats, site, mission, sdi_id, sdi_color)

    # gather timeseries and stats plots in a single page, using a radio button group
    labels = ['Transects', 'Timeseries', 'Statistics']
    layouts_val = [layout_tr, layout_ts, layout_stats]

    # --- Radio button group ---
    radio = RadioButtonGroup(
        labels=labels,
        active=0,
        stylesheets=["""
            .bk-btn {
                background-color: #378ADD;
                color: white;
            }
            .bk-btn:hover {
            background-color: #3a5a8f;
            color: white
            }
            .bk-btn.bk-active {
                background-color: #2a4a7a;
            }
            .bk-btn.bk-active:hover {
            background-color: #1f3a63
            }
            """]
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
    f_out = odir.joinpath(f'val_{site}_{mission}_{'_'.join(sdi_id)}.html')
    output_file(f_out)
    print('\n --> %s \n' %f_out)
    save(layout, title='Validation Shorelinerx')

    return