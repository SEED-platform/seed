# API: "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
# Import Permit Issuance API data into permit_issuance table

import pandas as pd
from sodapy import Socrata
# For data abstraction - sqlalchemy
from sqlalchemy import create_engine 
# Driver library for database - psychopg2
import psycopg2
from dotenv import load_dotenv
import os

# API and Token
load_dotenv()
appToken = os.getenv('permitApiKey')
client = Socrata("data.cityofnewyork.us", appToken)


# First 2000 results, returned as JSON from API / converted to Python list of dictionaries by sodapy.
PERMIT_ISSUANCE = "ipu4-2q9a"
results = client.get(PERMIT_ISSUANCE, limit=2000)

# Convert to pandas DataFrame
results_df = pd.DataFrame.from_records(results)

# Query fields needed for the permit_issuance table
table_df = results_df.loc[:, ['bin__', 'job__', 'work_type', 'permit_status', 'permit_subtype']]

# Specify connection parameters
param_dic = {
    "host"      : "localhost",
    "database"  : "TestImport",
    "user"      : "postgres",
    "password"  : "postgres"
}

# Connect to the PostgreSQL database server
conn = None
try:
    # connect to the PostgreSQL server
    print('Connecting to the PostgreSQL database...')
    conn = psycopg2.connect(param_dic)
except (Exception, psycopg2.DatabaseError) as error:
    print(error)
    conn = None
print("Connection successful")

# Bulk insert into the table
# Use to_sql method to append dataframe to table
def to_alchemy(table_df):
    connect = "postgresql+psycopg2://%s:%s@%s:5433/%s" % (
    param_dic['user'],
    param_dic['password'],
    param_dic['host'],
    param_dic['database']
)
    engine = create_engine(connect)
    table_df.to_sql(
        'test_table', 
        con=engine, 
        index=False, 
        if_exists='append'
    )
    print("Import to_sql done")

to_alchemy(table_df)