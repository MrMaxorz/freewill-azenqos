import zipfile
import os
import shutil
import params_disp_df
import sqlite3
import pandas as pd
import gsm_query
import integration_test_helpers
import numpy as np



def test():
    azmfp = "../example_logs/gsm_log/868263034952973-31_08_2020-18_08_49.azm"
    dbfp = integration_test_helpers.unzip_azm_to_tmp_get_dbfp(azmfp)
    
    with sqlite3.connect(dbfp) as dbcon:
        df = gsm_query.get_gsm_current_channel_disp_df(dbcon, "2020-08-31 18:04:13.816")
        print("df.head():\n %s" % df.head(20))
        print(df.iloc[13,1]) 
        print(len(df)) 
        print(len(df.columns)) 
        assert df.iloc[13,1] == 9
        assert len(df) == 16
        assert len(df.columns) == 2

        

if __name__ == "__main__":
    test()
