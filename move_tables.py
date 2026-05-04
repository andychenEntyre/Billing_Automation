import pandas as pd
from sqlalchemy import create_engine

src_engine = create_engine(
    "postgresql://db_owner:YLQRKNFY8YtXQENFqkXzRsaqfoYtMqdY@40.160.31.40:5432/warehouse_dev"
)
tgt_engine = create_engine(
    "postgresql://db_owner:YLQRKNFY8YtXQENFqkXzRsaqfoYtMqdY@40.160.31.40:5432/warehouse"
)

# df = pd.read_sql("SELECT * FROM public.march20_data", src_engine)

# df.to_sql(
#     "march20_data",
#     tgt_engine,
#     schema="public",
#     if_exists="replace",
#     index=False
# )

df = pd.read_sql("SELECT * FROM silver__stedi_eligibility_966d8115.stedi_eligibility_parsed", src_engine)

df.to_sql(
    "stedi_eligibility_parsed",
    tgt_engine,
    schema="public",
    if_exists="replace",
    index=False
)

# df = pd.read_sql("SELECT * FROM raw.stedi_eligibility_deal_stage", src_engine)

# df.to_sql(
#     "stedi_eligibility_deal_stage",
#     tgt_engine,
#     schema="public",
#     if_exists="replace",
#     index=False
# )