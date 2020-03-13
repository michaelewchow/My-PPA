''' ===========================================================================================================================================================================
Title:        PPA assessment module (simple)
Created:      11-Feb-2020
Authors:      Paolo Gabrielli, Michael Chow
Organization: ETH Zurich, South Pole

Description:  Class describing the power purchase agreement (PPA) energy contract.
              The class takes as inputs the properties of the PPA energy contract.
              Class objects allow various PPA-related functions to be performed.
              The following inputs should be provided: (i)   type and value of PPA price       <- model input
                                                       (ii)  time horizon of interest          <- model input
                                                       (iii) market (country) of interest      <- model input
                                                       (iv)  generation of RE project          <- generation object
                                                       (v)   electricity spot market price     <- market object
                                                       (vi)  nominal interest rate in decimals <- model input
              Refer to readme for detailed description of class methods and their respective equations.                                          
=========================================================================================================================================================================== '''


# IMPORT PACKAGES
import pandas as pd
import numpy  as np

# IMPORT FUNCTIONS WITHIN PPA 
from PPA_suite import compute_periodic_rate, start_date_processor, end_date_processor, \
compute_compound_periods, series_resample, compute_discount_factors, compute_cash_flow

# CLASS PROPERTIES ============================================================================================================================================================
class myPPA:

    location     = dict()                                                                          # locations of RE project and corporate buyer
    date_start   = []                                                                              # start date of the PPA energy contract in 'YYYY-MM-DD' string format or Datetime object
    date_end     = []                                                                              # end date of the PPA energy contract in 'YYYY-MM-DD' string format or Datetime object
    tenor        = []                                                                              # time horizon defining the PPA energy contract
    discount     = []                                                                              # effective annual discount rate of the PPA energy contract in decimals
    price_ppa    = dict()                                                                          # type of PPA price and properties (e.g. indexed, fixed, fixed w/ inflation)
    price_market = []                                                                              # time series-indexed spot market electricity price by hour
    generation   = dict()                                                                          # type of RE project and corresponding hourly generation profile as a capacity factor
    plot         = dict()                                                                          # characteristics of plotting function


    # CLASS CONSTRUCTION ========================================================================================================================================================
    def __init__(self, data):

        # Store class variables
        self.location['project']   = data['location']['project']
        self.location['corporate'] = data['location']['corporate']

        self.date_start = data['start']
        self.date_end   = data['end']
        self.discount   = data['discount']
        self.price_ppa  = data['price']
        
        # Plotting function
        self.plot['fig_width'] = 11                                                                # figure width
        self.plot['font_size'] = 18                                                                # font size
        self.plot['font_name'] = 'Segoe UI'                                                        # font name
        
        # Process date_start and date_end objects
        self.date_start = start_date_processor(self.date_start)
        self.date_end   = end_date_processor(self.date_end)
    # CLASS METHODS =============================================================================================================================================================

    # LOAD IN GENERATION DATA------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_gen_data(self, generation):
        self.generation = generation

    # SET PPA PRICE FROM DIRECT USER INPUT---------------------------------------------------------------------------------------------------------------------------------------------------------
    def build_ppa_price(self, spot_price_forecast):
        
        # SAVE SPOT PRICE FORECAST AS CLASS ATTRIBUTE
        self.price_market = spot_price_forecast
        
        # TENOR OF PPA CONTRACT 
        self.tenor = pd.date_range(start=self.date_start, end=self.date_end, freq='H')             # Time series runs till last hour of given end date

        # DEFINE TIME SERIES OF PPA PRICE
        ppa_price = pd.DataFrame(columns=['ppa_price'], index=self.tenor)

        # Fixed (flat) PPA price
        if self.price_ppa['type'] == 'fixed':
            ppa_price = self.price_ppa['fixed']

        # Variable PPA price based on market evolution
        elif self.price_ppa['type'] == 'indexed':
            ppa_price = self.price_market * self.price_ppa['index']                                           

        # Impose minimum threshold for PPA price
        if self.price_ppa['floor'] > 0:
            ppa_price[ppa_price < self.price_ppa['floor']] = self.price_ppa['floor']

        # Impose maximum threshold for PPA price
        if self.price_ppa['ceil'] > 0:
            print(self.price_ppa['ceil'])
            ppa_price[ppa_price > self.price_ppa['ceil']] = self.price_ppa['ceil']

        # Update PPA object
        self.price_ppa['price'] = ppa_price

        return self.price_ppa['price']
    
    # COMPUTE PPA FAIR MARKET PRICE ------------------------------------------------------------------------------------------------------------------------------------------------------
    def compute_fair_price(self, sett_freq):
            
        # Extract generation and spot price data for specified duration
        gen_prof    = self.generation['profile'][self.date_start:self.date_end]                                 
        spot_prices = self.price_market[self.date_start:self.date_end]                                      
        
        # Check equal number of data points in generation profile and electircity prices
        assert len(gen_prof) == len(spot_prices), \
          "generation profile series and electricity price series are not of equal length."        

        # Compute undiscounted cash flows
        revenue_base = compute_cash_flow(gen_prof, spot_prices, self.tenor)
        
        # Compute discount factors for each period and store in array
        revenue_sampled  = series_resample(revenue_base, sett_freq)                                # call function: resample revenue_base based on financial settlement frequency
        periodic_rate    = compute_periodic_rate(self.discount, sett_freq)                         # call function: compute periodic discount rate given
        compound_periods = compute_compound_periods(self.date_start, sett_freq)                    # call function: compute number of compounding periods from now till date_start
        disc_fact        = compute_discount_factors(len(revenue_sampled), periodic_rate,
                                                   compound_periods)                               # call function: compute array of discount factors matching each cash flow  
        
        # Compute ppa price
        nominator        = np.nansum(revenue_sampled*disc_fact)                                    # sum the products across all arrays
        gen_prof_sampled = series_resample(gen_prof, sett_freq)                                    # call function: resample generation profile based on financial settlement frequency
        denominator      = np.nansum(np.multiply(disc_fact, gen_prof_sampled.values))              # compute the denominator of the RHS of the equation
        ppa_price        = nominator/denominator
        print(f"PPA price from {self.date_start} to {self.date_end} -> {ppa_price}")
        return ppa_price

    # COMPUTE NPV ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    def compute_ppa_npv(self,sett_freq):
        
        # Extract generation and spot price data for specified duration
        gen_prof    = self.generation['profile'][self.date_start:self.date_end]*self.generation['capacity']
        spot_prices = self.price_market[self.date_start:self.date_end]

        # Compute undiscounted cash flows
        price_diff   = spot_prices - self.price_ppa['price']        
        revenue_base = compute_cash_flow(gen_prof, price_diff, self.tenor)                         # call function: compute undiscounted cash flows 
        
        # Compute discount factor for each compounding period
        revenue_sampled  = series_resample(revenue_base, sett_freq)                                # call function: resample revenue_base based on financial settlement frequency
        periodic_rate    = compute_periodic_rate(self.discount, sett_freq)                         # call function: compute periodic discount rate given
        compound_periods = compute_compound_periods(self.date_start, sett_freq)                    # call function: compute number of compounding periods from now till date_start
        disc_fact        = compute_discount_factors(len(revenue_sampled), periodic_rate,           # call function: compute array of discount factors matching each cash flow
                                                   compound_periods)                                        
        disc_revenue     = np.multiply(revenue_sampled.values, disc_fact)                          # compute array of discounted cash flows for each settlement period
        npv              = np.nansum(disc_revenue)
        print(f"NPV from {self.date_start} to {self.date_end} -> {npv}")                           # print output
        return npv

    # COMPUTE TOTAL ENERGY GENERATED FROM PPA------------------------------------------------------------------------------------------------------------------------------------------------
    def compute_gen_vol(self):

        gen_prof       = self.generation['profile'][self.date_start:self.date_end]                 # extract generation profile of specified duration from main object into array
        energy_profile = gen_prof * self.generation['capacity']                                    # generated energy profile of ppa as an array
        gen_vol        = np.nansum(energy_profile)                                                 # sum of energy generated during ppa
        print(f"Energy generated from {self.date_start} to {self.date_end} -> {gen_vol}")          # print output
        return gen_vol

    # CHANGE START DATE OF PPA------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_date_start(self, arg):
        self.date_start = start_date_processor(arg)
        
    # CHANGE END DATE OF PPA------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_date_end(self, arg):
        self.date_end = end_date_processor(arg)
        
    # CHANGE INTEREST RATE OF PPA------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_discount_rate(self, arg):
        self.discount = arg
        
    # CHANGE INTEREST RATE OF PPA------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_fixed_price(self, arg):
        self.price_ppa['price'] = arg
        