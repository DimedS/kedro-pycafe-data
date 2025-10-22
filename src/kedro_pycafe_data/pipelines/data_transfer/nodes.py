def fetch_and_save(snowpark_df):
    """Simply returns data read from Snowflake so Kedro saves it as CSV."""
    pdf = snowpark_df.to_pandas()
    return pdf