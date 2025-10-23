from kedro.pipeline import Pipeline, Node
from .nodes import build_telemetry_data

def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=build_telemetry_data,
                inputs=None,
                outputs=["new_kedro_users_monthly", "mau_kedro"],
                name="build_telemetry_data",
            ),
        ]
    )