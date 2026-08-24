import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from bokeh.plotting import figure, show, output_file, save
from bokeh.layouts import column
from bokeh.models import Range1d, ColumnDataSource, Slider, CustomJS, TapTool
from bokeh.palettes import Category10


def plot_profiles(f_parquet, odir):

    df = pd.read_parquet(f_parquet)

    dates = sorted(df['date'].unique())
    profile_ids = sorted(df['profile_id'].unique())

    # get static x_range and y_range for plots
    x = np.concatenate(df['cross_sh_d'].values)

    y = np.concatenate(df['elevation'].values)
    x_range = Range1d(x.min(), np.percentile(x, 90))
    y_range = Range1d(np.percentile(y, 10), y.max())

    # Color mapping
    palette = Category10[10]
    if len(profile_ids) > 10:
        palette = palette * ((len(profile_ids) // 10) + 1)
    color_map = {str(pid): palette[i % 10] for i, pid in enumerate(profile_ids)}

    # site name
    sitename = f_parquet.stem.split('_')[-1]

    # Main plot
    p_main = figure(
        width=900,
        height=500,
        title=f'Beach Profiles at {sitename} (vertical ref: MSL)',
        x_axis_label='Cross-shore distance (m)',
        y_axis_label='Elevation (m)',
        x_range=x_range,
        y_range=y_range,
        sizing_mode='stretch_width'
    )

    # Data sources
    main_source = ColumnDataSource(data=dict(xs=[], ys=[], profile_id=[], color=[]))
    selected_source = ColumnDataSource(data=dict(xs=[], ys=[], color=[]))
    detail_source = ColumnDataSource(data=dict(x=[], y=[]))

    # Renderers
    main_lines = p_main.multi_line(
        'xs', 'ys', source=main_source, color='color', line_width=2, legend_field='profile_id'
    )

    selected_line = p_main.multi_line(
        'xs', 'ys', source=selected_source, color='color', line_width=4, line_alpha=0.8
    )


    # Tap tool for selecting profiles
    tap_tool = TapTool(renderers=[main_lines])
    p_main.add_tools(tap_tool)

    # Prepare data for JS callbacks
    dates_str = [str(d) for d in dates]
    profile_ids_str = [str(p) for p in profile_ids]

    # Slider
    slider = Slider(start=0, end=len(dates) - 1, value=0, step=1, title=f'{dates_str[0]}', show_value=False)

    data_lookup = {}
    for _, row in df.iterrows():
        date = str(row['date'])
        pid = str(row['profile_id'])
        if date not in data_lookup:
            data_lookup[date] = {}
        data_lookup[date][pid] = {
            'xs': row['cross_sh_d'].tolist(),
            'ys': row['elevation'].tolist(),
        }

    # Slider callback
    slider_callback = CustomJS(
        args=dict(
            source=main_source,
            selected_source=selected_source,
            detail_source=detail_source,
            dates=dates_str,
            data=data_lookup,
            color_map=color_map,
            profile_ids=profile_ids_str,
            slider=slider,
            sizing_mode='stretch_width'
        ),
        code="""
        const idx = cb_obj.value;
        const date = dates[idx];
        const date_data = data[date];

        const xs = [];
        const ys = [];
        const pids = [];
        const colors = [];

        for (const pid of profile_ids) {
            if (date_data[pid]) {
                xs.push(date_data[pid].xs);
                ys.push(date_data[pid].ys);
                pids.push(pid);
                colors.push(color_map[pid]);
            }
        }

        source.data = {xs: xs, ys: ys, profile_id: pids, color: colors};
        selected_source.data = {xs: [], ys: [], color: []};
        detail_source.data = {x: [], y: []};
        slider.title = date;
        """,
    )

    slider.js_on_change('value', slider_callback)

    # Tap callback
    tap_callback = CustomJS(
        args=dict(
            source=main_source,
            selected_source=selected_source,
            detail_source=detail_source,
            data=data_lookup,
            dates=dates_str,
            slider=slider,
            color_map=color_map,
            sizing_mode='stretch_width'
        ),
        code="""
        const idx = slider.value;
        const date = dates[idx];
        const date_data = data[date];

        const selected = source.selected.indices;
        if (selected.length > 0) {
            const i = selected[0];
            const pid = source.data['profile_id'][i];
            const profile_data = date_data[pid];
            const color = color_map[pid];

            selected_source.data = {
                xs: [profile_data.xs],
                ys: [profile_data.ys],
                color: [color]
            };

            detail_source.data = {
                x: profile_data.xs,
                y: profile_data.ys
            };
        }
        """,
    )

    main_lines.data_source.selected.js_on_change('indices', tap_callback)

    # Initial data
    initial_date = dates_str[0]
    initial_data = data_lookup[initial_date]
    xs = []
    ys = []
    pids = []
    colors = []
    for pid in profile_ids_str:
        if pid in initial_data:
            xs.append(initial_data[pid]['xs'])
            ys.append(initial_data[pid]['ys'])
            pids.append(pid)
            colors.append(color_map[pid])
    main_source.data = {'xs': xs, 'ys': ys, 'profile_id': pids, 'color': colors}

    # Layout
    layout = column(slider, p_main, sizing_mode='stretch_width')

    html_name = f'beach_profiles_{sitename}.html'
    output_file(odir / html_name)
    save(layout)


if __name__ == '__main__':

    # output directory
    odir = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/plots/')

    # input parquet
    # f_parquet = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_narrabeen.parquet')
    f_parquet = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_duck.parquet')
    # f_parquet = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_trucvert.parquet')
    # f_parquet = Path('/home/florent/Projects/Shoreliner_CNES/validation/groundtruth/beach_profiles_torreypines.parquet')

    # plot beach profiles
    plot_profiles(f_parquet, odir)