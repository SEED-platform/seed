# API: "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
# Import Permit Issuance API data into permit_issuance table

import pandas as pd
from sodapy import Socrata
from sqlalchemy import create_engine
import psycopg2

# API and Token
client = Socrata("data.cityofnewyork.us", 'O3jxmkAkib901njllRmAWkAGn')

# First 2000 results, returned as JSON from API / converted to Python list of dictionaries by sodapy.
results = client.get("ipu4-2q9a", limit=2000)

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

# Connect to the database
def connect(params_dic):
    # Connect to the PostgreSQL database server
    conn = None
    try:
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params_dic)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        conn = None
    print("Connection successful")
    return conn
conn = connect(param_dic)

# Bulk insert into the table
connect = "postgresql+psycopg2://%s:%s@%s:5433/%s" % (
    param_dic['user'],
    param_dic['password'],
    param_dic['host'],
    param_dic['database']
)

# Use to_sql method to append to dataframe to table
def to_alchemy(table_df):
    engine = create_engine(connect)
    table_df.to_sql(
        'test_table', 
        con=engine, 
        index=False, 
        if_exists='append'
    )
    print("Import to_sql done")

to_alchemy(table_df)