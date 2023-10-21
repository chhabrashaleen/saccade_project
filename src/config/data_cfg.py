# definitions of different ways to read the data
import os

from src.constants import *

WIN_PATH = r"E:\git\saccade_project\mktdata"
LINUX_PATH = r""  """not defined yet"""
PATH = WIN_PATH if os.name == "nt" else LINUX_PATH
input_file = PATH + r"\SCH.log"

OUTPUT_PATH = r"E:\git\saccade_project\output"
output_file = r"\output1.log"

# Defining parameters for reading data = columns, index and types
delim = ','
# myskiprows = (0)

