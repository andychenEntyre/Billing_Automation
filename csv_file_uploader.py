import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://db_owner:YLQRKNFY8YtXQENFqkXzRsaqfoYtMqdY@40.160.31.40:5432/warehouse"
)

df = pd.read_csv("/Users/Andy.Chen/Billing_Automation/real_time_eligibility_check/APR_client_reinstatements_results.csv")

df.to_sql(
    "April_Client_Reinstatements_Results",
    engine,
    schema="andy_schema",
    if_exists="replace",  # or "append"
    index=False
)