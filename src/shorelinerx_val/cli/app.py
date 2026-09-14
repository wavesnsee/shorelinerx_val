import sys
from pathlib import Path
import traceback
from typing import Annotated
import yaml
from pydantic import BaseModel
import typer

from shorelinerx_val.cli import val

app = typer.Typer(no_args_is_help=True)

class SatWaterlines(BaseModel):
    id: list[str]
    path: list[Path]
    color: list[str]

class AppConfig(BaseModel):
    site: str
    sdi: SatWaterlines
    f_insitu_bp: Path
    f_tr: Path
    table_tr_id: dict
    odir: Path


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)  # validation automatique

@app.command()
def main(
    input_yaml: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=True,
            help="Input yaml file containing parameters",
        ),
    ],
):
    # load configuration file
    conf = load_config(input_yaml)

    for _, f_inters in enumerate(conf.sdi.path):
        if not f_inters.exists():
            raise typer.Exit(f"Satellite derived intersections file {f_inters} does not exist")
    if not conf.f_insitu_bp.exists():
        raise typer.Exit("groundtruth beach profile's file")

    if not conf.odir.exists():
        conf.odir.mkdir(parents=True, exist_ok=True)

    try:
        # Run validation
        val.main(conf)

    except Exception as e:  # noqa: BLE001
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)
        typer.echo(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    app()
