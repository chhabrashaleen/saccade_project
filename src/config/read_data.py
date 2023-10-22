from src.config.data_cfg import input_file, delim
from src.config.ref_data import *
import os
import re
import csv
import pandas as pd
from os.path import isfile
from src.bin.markets.tbt_datafeed.messages import *
from decimal import Decimal
import src.config.logger as log

logger = log.logger

# cwd = os.getcwd()  # Get the current working directory (cwd)
# files = os.listdir(cwd)  # Get all the files in that directory
# print("Files in %r: %s" % (cwd, files))

def get_data_from_log(path=input_file):
    '''gets the data from log files in pandas dataframe, doesnt always work'''

    data_df = pd.DataFrame()
    # data_df = pd.read_csv(filepath+input)
    if path and isfile(path):
        data_df = pd.read_csv(path, delimiter='\t')
        print('Found the data and loaded in dataframe')
        a = data_df.iloc[0]
        print(a," ",type(a))
    return data_df

def fetchTicks(instId: int, file=input_file):
    '''
    Read data row by row using raw reading.
    '''
    allTicks = []
    with open(file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            need = row[0]
            need = re.sub("\s+", delim, need.strip())
            entry = list(need.split(delim))
            tickTime = datetime.datetime.fromtimestamp(int(entry[0])/1e9)
            tickSize = Decimal('0.01') if str(entry[3]) == 'SCH' else Decimal('0.001')
            tr = TickRead(tickTime, int(entry[1]), str(entry[2]), str(entry[3]), str(entry[4]), Decimal(str(entry[5])), int(entry[6]), instId, tickSize)
            allTicks.append(tr)
    return allTicks

# allTicks = fetchTicks(input_file)
# get_data_from_log()