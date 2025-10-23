import os
from snowflake.snowpark import Session
import pandas as pd

def build_telemetry_data() -> pd.DataFrame:
    """
    Executes a chain of Snowflake SQL commands with temporary tables
    and returns the final aggregated DataFrame for new Kedro users per month.
    """

    # Add hardcoded DB and schema
    connection_params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": "HEAP_NTD_KEDRO",
        "warehouse": "HEAP_NTD_KEDRO_WH",
        "database": "DEMO_DB",
        "schema": "PUBLIC",
    }

    session = Session.builder.configs(connection_params).create()

    # --- Step 1 ---
    session.sql("""
        CREATE OR REPLACE TEMPORARY TABLE temp_dt_username AS
        SELECT DATE(time) AS dt,
               username,
               MAX(LEFT(PROJECT_VERSION, 4)) AS max_version_prefix,
               COUNT(*) AS cnt
        FROM HEAP_FRAMEWORK_VIZ_PRODUCTION.HEAP.KEDRO_PROJECT_STATISTICS
        WHERE DATE(time) >= '2024-09-01'
          AND (is_ci_env IS NULL OR is_ci_env = 'false')
        GROUP BY 1, 2
    """).collect()

    # --- Step 2 ---
    session.sql("""
        CREATE OR REPLACE TEMPORARY TABLE temp_username_min_max_dt AS
        SELECT username,
               MIN(dt) AS min_dt,
               MAX(dt) AS max_dt
        FROM temp_dt_username
        GROUP BY 1
    """).collect()

    # --- Step 3 ---
    session.sql("""
        CREATE OR REPLACE TEMPORARY TABLE temp_username_uniques AS
        SELECT username
        FROM temp_username_min_max_dt
        WHERE DATEDIFF('day', min_dt, max_dt) > 8
    """).collect()

    # --- Step 4 ---
    session.sql("""
        CREATE OR REPLACE TEMPORARY TABLE temp_dt_username_unique AS
        SELECT a.*
        FROM temp_dt_username a
        JOIN temp_username_uniques b
          ON a.username = b.username
         AND b.username IS NOT NULL
    """).collect()

    # --- Step 5 ---
    session.sql("""
        CREATE OR REPLACE TEMPORARY TABLE temp_dt_username_unique_first_date AS
        SELECT username, MIN(dt) AS first_date
        FROM temp_dt_username_unique
        GROUP BY username
        ORDER BY first_date
    """).collect()

    # --- Final result 1: new Kedro users ---
    new_users_df = session.sql("""
        SELECT first_year_month, COUNT(*) AS count
        FROM (
            SELECT *,
                   TO_CHAR(first_date, 'YYYY-MM') AS first_year_month
            FROM temp_dt_username_unique_first_date
        ) t
        WHERE first_year_month >= '2024-11'
        GROUP BY 1
        ORDER BY 1
    """).to_pandas()

    # --- Final result 2: monthly active users (MAU) ---
    mau_df = session.sql("""
        SELECT 
            TO_CHAR(DATE_TRUNC('month', dt), 'YYYY-MM') AS year_month,
            COUNT(DISTINCT username) AS mau
        FROM temp_dt_username_unique
        WHERE dt >= '2024-10-01'
        GROUP BY year_month
        ORDER BY year_month
    """).to_pandas()

    # --- 3️⃣ Kedro plugins MAU ---
    plugins_mau_df = session.sql("""
        SELECT 
            TO_CHAR(DATE_TRUNC('month', time), 'YYYY-MM') AS year_month,
            first_two_words,
            COUNT(DISTINCT username) AS unique_users
        FROM (
            SELECT 
                a.command,
                SPLIT(command, ' ')[0] || ' ' || SPLIT(command, ' ')[1] AS first_two_words,
                b.username,
                a.time
            FROM HEAP_FRAMEWORK_VIZ_PRODUCTION.HEAP.ANY_COMMAND_RUN a
            JOIN temp_username_uniques b 
                ON a.username = b.username
            WHERE time >= '2024-10-01'
        ) t
        WHERE first_two_words IN (
            'kedro mlflow',
            'kedro docker',
            'kedro airflow',
            'kedro databricks',
            'kedro azureml',
            'kedro vertexai',
            'kedro gql',
            'kedro boot',
            'kedro sagemaker',
            'kedro coda',
            'kedro kubeflow'
        )
        GROUP BY year_month, first_two_words
        ORDER BY year_month, unique_users DESC
    """).to_pandas()

    # --- 4️⃣ Kedro core commands MAU ---
    commands_mau_df = session.sql("""
        SELECT 
            TO_CHAR(DATE_TRUNC('month', time), 'YYYY-MM') AS year_month,
            first_two_words,
            COUNT(DISTINCT username) AS unique_users
        FROM (
            SELECT 
                a.command,
                SPLIT(command, ' ')[0] || ' ' || SPLIT(command, ' ')[1] AS first_two_words,
                b.username,
                a.time
            FROM HEAP_FRAMEWORK_VIZ_PRODUCTION.HEAP.ANY_COMMAND_RUN a
            JOIN temp_username_uniques b 
                ON a.username = b.username
            WHERE time >= '2024-10-01'
        ) t
        WHERE first_two_words IN (
            'kedro run',
            'kedro viz',
            'kedro new',
            'kedro pipeline',
            'kedro jupyter',
            'kedro ipython',
            'kedro package'
        )
        GROUP BY year_month, first_two_words
        ORDER BY year_month, unique_users DESC
    """).to_pandas()

    session.close()
    return new_users_df, mau_df, plugins_mau_df, commands_mau_df