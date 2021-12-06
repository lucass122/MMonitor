from dash import html
from flask import send_from_directory

from mmonitor.config import images_path
from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.calculations.horizon_r import generate_image


@app.server.route(f'{images_path}/<image>.png')
def serve_image(image):
    """
    Allows dash to display png images from  ../resources/images/
    """

    return send_from_directory(images_path, f'{image}.png')


class Horizon(BaseApp):
    """
    App to display the taxonomy abundances in a horizon plot.
    Calls an R script and uploads the generated image.
    """

    _WIDTH = 1500
    _HEIGHT = 1000

    def __init__(self, sql: MMonitorDBInterface):
        super().__init__(sql)
        self._generate_image()
        self._init_layout()
        self._init_callbacks()

    def _generate_image(self) -> None:
        """
        Generate the necessary horizon.png file.
        """

        q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
        df = self._sql.query_to_dataframe(q)
        generate_image(df, self._WIDTH, self._HEIGHT)

    def _init_layout(self) -> None:
        header = html.H1("Horizon plot of taxonomy abundances")
        image = html.Img(
            src=f'{images_path}/horizon.png',
            style={'display': 'block', 'margin-left': 'auto', 'margin-right': 'auto', 'padding': '20px'}
        )
        container = html.Div([header, image])

        self.layout = container

    def _init_callbacks(self) -> None:
        pass