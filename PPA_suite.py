# PPA SUITE
# FUNCTIONS BELOW CALLED IN PPA CLASS BUT ALSO APPLICABLE ELSEWHERE

# IMPORT PACKAGES
import datetime as dt
import numpy    as np
import pandas   as pd 

# CONVERT EFFECTIVE ANNUAL DISCOUNT RATE INTO PERIODIC DISCOUNT RATE ==================================================================================================================================
"""
Computes the periodic discount rate based on a compounding frequency
Inputs: (i) 'eff_ann_rate' is the effective annual interest rate/discount factor
        (ii) 'freq' is the frequency of compounding declared as a string.
             Options available are: 'daily', 'weekly', 'monthly', 'quarterly' and 'annually'.
Returns periodic discount rate
"""
def compute_periodic_rate(eff_ann_rate,freq):

    N = num_compound_periods(freq)                                                                  # Call function to extract number of compound periods in a single year from dictionary                                                                                      
    periodic_rate = (1 + eff_ann_rate) ** (1 / N) - 1
    return periodic_rate

# RETURNS NUMBER OF COMPOUND PERIODS IN A YEAR FOR AN INPUT FREQUENCY ==================================================================================================================================
"""
Returns number of compounding periods within a year
Inputs: (i) 'freq' is the frequency of compounding declared as a string.
            Options available are: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly' and 
            'annually'.
"""
def num_compound_periods(freq):

    storage_dict = {'hourly'   : 8760, 
                    'daily'    : 365.25, 
                    'weekly'   : 52, 
                    'monthly'  : 12, 
                    'quarterly': 4, 
                    'annually' : 1,
                    'yearly'   : 1}     
    return storage_dict[freq]
   
# PROCESSES INPUT START DATE FROM STRING INTO DATETIME OBJECT==================================================================================================================================
"""
Processes a date as a string or a datetime object and specifies the hour as first hour of the 
date
Input: (i) 'date_start' is a string in date format "YYYY-mm-dd" or datetime object input without 
            time specified
Returns a date time object of with date of 'date_start' and time '00:00'
"""
def start_date_processor(date_start):

    if type(date_start) is dt.date:
        dt_start = dt.datetime.combine(date_start, dt.time(0,0))
    elif type(date_start) is dt.datetime:
        dt_start = dt.datetime.combine(date_start.date(), dt.time(0,0))
    elif type(date_start) is str:
        dt_start = date_start + ' 00:00'
        dt_start = dt.datetime.strptime(dt_start, '%Y-%m-%d %H:%M')
    return dt_start

# PROCESSES INPUT END DATE FROM STRING INTO DATETIME OBJECT AND SETS LAST HOUR OF THE DAY==================================================================================================================================
"""
Processes a date as a string or a datetime object and specifies the hour as last hour of the date
Input: (i) 'date_end' is a string in date format "YYYY-mm-dd" or datetime object input without time specified
Returns a date time object of with date of 'date_end' and time '23:00'
"""
def end_date_processor(date_end):

    if type(date_end) is dt.datetime:
        dt_end = dt.datetime.combine(date_end.date(), dt.time(23, 0))                               # set last hour of last day
    elif type(date_end) is dt.date:
        dt_end = dt.datetime.combine(date_end, dt.time(23, 0))                                      # set last hour of last day
    elif type(date_end) is str:
        dt_end = date_end + ' 23:00'                                                               # set last hour of last day
        dt_end = dt.datetime.strptime(dt_end, '%Y-%m-%d %H:%M')
    return dt_end


# COMPUTES NUMBER OF COMPOUND PERIODS FROM NOW TILL A GIVEN DATE==================================================================================================================================
"""
Computes the number of compounding periods from now till a given later date
Inputs: (i)  'dt_start' is the later date
        (ii) 'sett_freq' is the frequency of financial settlements declared as a string
             Options available are: 'daily', 'weekly', 'monthly', 'quarterly' and 'annually'.
Returns the number of compounding periods from now till dt_start
"""
def compute_compound_periods(dt_start, sett_freq):

    diff = dt_start - dt.datetime.now()                                                            # compute difference in time between present and a given date
    days_in_sett_freq = {'daily'    :1,
                         'weekly'   :7,
                         'monthly'  :30.5,
                         'quarterly':91,
                         'annually' :365.25}
    
    # Compute number of compounding periods till given date
    if sett_freq == 'hourly':        
        no_of_periods = diff.days * 24 + diff.seconds // 3600
    else:
        no_of_periods = diff.days/days_in_sett_freq[sett_freq]

    # Set number of periods to zero if input date is earlier than now
    if no_of_periods < 0:
        no_of_periods = 0

    return no_of_periods

# RESAMPLES HOURLY-INDEXED TIME SERIES DATA INTO SPECIFIED FREQUENCY==================================================================================================================================
"""
Resamples an hourly series into a specified frequency
Inputs: (i) 'series' is the hourly-indexed data series to be resampled
        (ii) 'sett_freq' is the frequency of financial settlement declared as a string.
             Options available are: 'daily', 'weekly', 'monthly', 'quarterly' and 'annually'.
Returns the resampled series
"""
def series_resample(series, sett_freq):

    if sett_freq == 'hourly':
        resampled = series
    else:
        resampled = series.resample(myfreq2(sett_freq)).sum()
    return resampled

# ASSOCIATE NAME TO RESAMPLING ARGUMENT =======================================================================================================================================
"""
Returns an acronym for resampling argument given a string input
"""
def myfreq2(arg):

    # Frequency dictionary: from name to acronym  
    freq = {'daily': 'd', 'weekly': 'W', 'monthly': 'M', 'quarterly':'Q', 'yearly': 'A'}
    return freq[arg]    

# COMPUTE ARRAY OF DISCOUNT FACTORS==================================================================================================================================
"""
Computes an array of discount factors for a given array of cashflows
Inputs: (i) 'len_cashflow' is the length of the array storing the cashflow data
        (ii) 'periodic_rate' is the discount factor for each compounding period between cashflows
        (iii) 'periods_to_first_settlement' is the number of compounding periods from now till first settlement
Returns an array of discount factors of equal length to an array of cashflows
"""
def compute_discount_factors(len_cashflow, periodic_rate, periods_to_first_settlement):

    disc_fact = np.empty(len_cashflow)                                                             # initialize empty array of equal size to cash flow array
    for iter in range(len_cashflow):
        if iter == 0:  # compute first discount factor independently
            disc_fact[iter] = 1 / ((1 + periodic_rate) ** (1 + periods_to_first_settlement))       # first settlement is performed at the end of the first period
        else:
            disc_fact[iter] = disc_fact[iter - 1] * (1 / (1 + periodic_rate))                      # subsequent discount factors are a product of their previous compounding period
    return disc_fact

# COMPUTE ARRAY OF CASH FLOWS==================================================================================================================================
"""
Computes an array of cash flows given an array of generation and price data
Inputs: (i)  Array of electricity spot prices for each hour 
        (ii) Array of energy generated for each hour
Returns a datetime-indexed Series object with cashflows for each hour
PLEASE NOTE:
# PANDAS.MULTIPLY WAS RESULTING IN ELEMENT BY ELEMENT MULTIPLICATION ERROR
# BY ADDING A MEANINGLESS ADDITIONAL ELEMENT TO THE PRODUCT ARRAY
# WORKAROUND: USE NUMPY.MULTIPLY ON SERIES VALUES ONLY
# THEN INSERT THE PRODUCT INTO A RE-DECLARED TIME SERIES

"""
def compute_cash_flow(gen_prof, spot_prices, tenor):
    revenue_base = np.multiply(gen_prof.values, spot_prices.values)
    revenue_base = pd.Series(revenue_base, tenor)
    return revenue_base