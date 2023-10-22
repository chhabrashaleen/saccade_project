# definitions of different ways to read the data
import os

WIN_PATH = r"E:\git\saccade_project\mktdata\\"

'''
for linux go to saccade_project directory and then run:
export PYTHONPATH=$(pwd)
'''
LINUX_PATH = r"./mktdata/"
PATH = WIN_PATH if os.name == "nt" else LINUX_PATH

inputSCH = PATH + r"SCH.log"
inputSCS = PATH + r"SCS.log"

OUTPUT_PATH = r"E:\git\saccade_project\output"
output_file = r"\output1.log"

# Defining parameters for reading data = columns, index and types
delim = ','
# myskiprows = (0)

