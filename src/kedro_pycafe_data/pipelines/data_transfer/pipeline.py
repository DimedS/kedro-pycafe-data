"""
This is a boilerplate pipeline 'data_transfer'
generated using Kedro 1.0.0
"""

from kedro.pipeline import Node, Pipeline  # noqa
from .nodes import fetch_and_save

def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=fetch_and_save,
                inputs="pypi_kedro_downloads",
                outputs="pypi_kedro_downloads_table",
                name="fetch_and_save_snowflake_data",
            ),
        ]
    )