'''===========================================================================================================================================================================
Title:        Master (main script) - dummy
Created:      Feb 2020
Authors:      Paolo Gabrielli
Organization: ETH Zurich, South Pole

Description:  Main script of the PPA assessment and optimization model (we might come up with a more catchy name!).
              It is used to (i)  read the input parameters as defined by the Excel interface (possibly web interface in future releases);
                            (ii) compute the financial and environmental performance of corporate PPA energy contracts

=========================================================================================================================================================================== '''


# IMPORT PACKAGES
import os, sys
import openpyxl
import pandas as pd
import datetime

# WORKING DIRECTORY
dir_work = os.getcwd()
dir_db   = os.path.join(os.path.dirname(dir_work), 'Data')   # directory containing databases
dir_res  = os.path.join(os.path.dirname(dir_work), 'Results') # directory to save results

# Add all subfolders to current path to import files (functions)
for path, subdirs, files in os.walk(dir_work) :
  sys.path.insert(0, path)

# IMPORTING FUNCTIONS DEFINED WITHIN WORKING DIRECTORY
from PPA import PPA

# DEFINE INPUT DATA

# Define source of input data (user interface)
wb    = openpyxl.load_workbook(filename="PPA_Model_Interface.xlsm", read_only=False, keep_vba=True)# open Excel workbook
sheet = wb['User Interface']                                                                       # select working sheet
data  = {'PPA' : {'location' : dict(),
                  'price' : dict()  },
         'generation' : dict()}

# PPA energy contract
data['PPA']['location']['project']   = str(sheet['C15'].value)                                     # location of RE project
data['PPA']['location']['corporate'] = str(sheet['C15'].value)                                     # location of corporate buyer

data['PPA']['discount'] = float(sheet['C16'].value)                                                # discount rate of RE project
data['PPA']['start']    = sheet['C21'].value.date()                                                # starting date of PPA contract
data['PPA']['end']      = sheet['C22'].value.date()                                                  # end date of PPA contract

data['PPA']['price']['type']  = str(sheet['C25'].value)                                            # type of PPA price
data['PPA']['price']['fixed'] = float(sheet['C26'].value)                                          # starting (fixed) value of the PPA price
data['PPA']['price']['floor'] = float(sheet['C28'].value)                                          # floor value of PPA price
data['PPA']['price']['ceil']  = float(sheet['C29'].value)                                          # ceil value of PPA price
data['PPA']['price']['index'] = float(sheet['C27'].value)                                          # multiplication factor to go from electricity market price to PPA price

# RE project generation
data['generation']['technology'] = 'PV'                                                            # RE technology
data['generation']['location']   = data['PPA']['location']['project']                              # location of RE project
data['generation']['capacity']   = 1                                                               # maximum generation capacity of RE project in MW
          
data['generation']['start'] = data['PPA']['start']                                                 # starting date of PPA contract
data['generation']['end']   = data['PPA']['end']                                                   # duration of PPA contract # End is also modified

# Load in forecast electricity spot prices
hpfc_df = pd.read_csv('final_hpfc.csv')
dt_index = [datetime.datetime.strptime(dt, '%d/%m/%Y %H:%M') for dt in hpfc_df['DateTime']]      # convert date time strings into array of date time objects
hpfc_df = pd.Series(hpfc_df['Price'].values, index=dt_index)

# Load in generation profile data
gen_data = pd.read_csv('GB_solar_data_final.csv')                                                  # read generation profile data in CSV file 
gen_data = pd.Series(gen_data['Capacity Factor'].values, index=dt_index)                           # declare gen_data with date time series as index
data['generation']['profile'] = gen_data                                                           # generation profile data 


#%%
# PRINT SOMETHING
test_ppa   = PPA(data['PPA'])
price      = test_ppa.build_ppa_price(hpfc_df)
test_ppa.get_gen_data(data['generation'])
fair_price = test_ppa.compute_fair_price('hourly')
