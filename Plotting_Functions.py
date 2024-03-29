import pandas as pd
import numpy as np
import os
import math
from scipy import stats
import matplotlib.pyplot as plt
#Table plotting
from pandas.plotting import table 

import matplotlib.ticker as mtick
import matplotlib.colors as colors
import matplotlib.cbook as cbook

from datetime import datetime
from datetime import date

"""
Functions for Operating on Time Series Data and Adding Domain Information 
"""
#Function: load time series data and convert to formats used in plotting and visualization
def prepare_TS(TS_path,position=False,var_by_code_path=None,subset_codes=None,reindex=False):
    """
    Reads a time series table and returns a Pandas DataFrame in a format compatible for editing.
    
    Arguments
    ----------
    TS_path: path to file with time series information. May use frequency or percentage tables.
    
    position (optional, default=False): if True, create a position column using the variants by code dataset. This column is required for adding domain information.
    
    var_by_code_path (optional, default=None): path to the output of variants by code for the protein. Required to give position data for the mutation codes so the regions can be checked.
    
    subset_residues (optional, default=None): a list of variant codes to subset for may be entered to return time series information for just those residues.
    
    reindex (optional, default=False): if True, make the variant codes the index of the dataframe and remove the 'code' column. If further operations are desired on the 'code' column, this should be set to False.
    """
    TS=pd.read_csv(TS_path)

    #Rename first column to "Code"
    newcols=list(TS.columns)
    newcols[0]="Code"
    TS.columns=newcols

    #Subset for Specific residues if desired
    if subset_codes:
        if type(subset_codes)!=list:
            raise ValueError("Must pass a list or 'None' to subset_residues")
        else:
            TS=TS[TS["Code"].isin(subset_codes)]
            
    #If reindex==True, make the "Code" column of the time series data the new index
    if reindex==True:
        TS.index=TS["Code"]
        TS=TS.drop("Code",axis=1)
    
    #Creation of position column if desired: requires the variant by code dataset
    if position==True:
        #If the variant by code path is not provided, return an error
        if var_by_code_path==None:
            raise ValueError("If position is set to 'True', the path to the variants by code dataset must be entered.")
        else:
            #Region checking requires positions, but the time series data has mutation codes
            #Code-Position table: will be merged with time series data to add a position column
            codes=pd.read_csv(var_by_code_path)
            #Form code-position table
            code_position=codes[["Code","Position"]]

            #Use the regions objects to create a new column with the code 
            TS=pd.merge(left=TS,right=code_position,on="Code",how="left")
            #A "NaN" will appear in the "Zero Mutations in Spike" row since it is not associated with a position. This will be filled with "-".
            TS=TS.fillna(value="-")
    
    return TS

#Class for storing data from the reference file
class Protein_Region:
    def __init__(self,name,start,end):
        """
        Creates an object storing the bounds of a protein region (subunit, domain, etc.).
        
        Instance Variables
        --------------------
        name (string): the name of the region. The name should have the capitalization desired 
        start (integer): the amino acid position of the start of the region
        end (integer): the amino acid position of the end of the region
        """
        #Name, start, and end are passed after reading each entry in the reference CSV file
        self.__name=name
        self.__start=int(start)
        self.__end=int(end)
    def __str__(self):
        """
        When calling print() on this class, the string below is returned.
        """
        return "[{0}: residue {1} to residue {2}]".format(self.__name,self.__start,self.__end)
    def check_position(self,position):
        """
        Takes a amino acid position and returns the boolean "True" if the position is within the class, and "False" if not.
        """
        if (position>=self.__start) and (position<=self.__end):
            return True
        else:
            return False
    def get_name(self):
        """
        Returns the region name.
        """
        return self.__name

def initialize_regions(region_path):
    """
    Creates a list of Protein_Region objects for storing infomration on each region in the file.
    
    Arguments
    ----------
    region_path: path to the file containing position information on the regions (domains, subdomains, subunits etc.) for the protein.
    
    Returns a list of Protein_Region objects containing the names of each region along with their start and end positions.
    """
    regions=[]

    with open(region_path,"r") as file:
        lines=file.readlines()
        #Define region type, in the format desired in the table
        for line in lines[1:]:
            #Remove newline character from line
            line=line.strip()
            #Read the name, start position, and end position of the region from the comma separated fields
            name,start,end=line.split(",")
            #Create a Protein_Region() object and add it to the list of region objects
            regions.append(Protein_Region(name,start,end))
    return regions

#Region checker function
def region_checker(position, regions):
    #The "Total Mutations in <protein>" row contains a dash for the position. Return a dash for this row as region membership does not apply.
    if position=="-":
        return "-"
    #Test each region to see if the position falls within the regions given.
    for region in regions:
        if region.check_position(position)==True:
            #If the position falls within a region, return the name of the region.
            return region.get_name()
    #If the position does not fit within any of the regions, return "Other".
    return "Other"

def add_region_column(data,region_type,region_path,target_col="Position"):
    """
    Function accepts a time series table with a position column, and adds a column for region information
    
    arguments
    ----------
    data: a dataframe containing variant information or time series dat. The dataframe must have a position column for the function to work.
    
    region_type: the type of region information to be added (Domain, Subdomain, Subunit, etc.). The value passed here will be the name of the column created in the time series data.

    region_path: path to the CSV file giving information on regions.
    
    target_col: string giving the name of the position column to use for calculating domain info.
    
    output
    ---------
    Returns the dataframe passed with the new column.
    """
    #Initiate region objects
    regions=initialize_regions(region_path)
    #Run domain checker on the position column and store output in a new column with the name of the region type (domain, subdomain, subunit etc.) 
    data[region_type]=data[target_col].apply(lambda position:region_checker(position,regions))
    return data

def add_dashes(df,new_colname):
    """
    Adds a new column to an existing DataFrame consisting of dashes for all values.
    
    Arguments
    ---------
    df: A Pandas DataFrame.
    
    new_colname: String giving the name of new column to be created. 
    
    Returns
    ---------
    df: The input DataFrame with the new column added.
    """
    dashes=[]
    for i in range(len(df)):
        dashes.append("-")
    df[new_colname]=dashes
    return df

def rearrange_cols(df,firstcols):
    """
    Takes a dataframe and a list of columns to put first, and returns a dataframe with those columns first and other columns appearing after the defined columns in the same order as before.
    """
    if type(firstcols) != list:
        raise ValueError("Column names must be given as a list.")
    return df[firstcols+[column for column in df.columns if column not in firstcols]]

def code_region_index(TS,code_colname="Code",region_colname=None,protein=None):
    """
    Accepts a time series dataframe and sets the index equal to the variant codes along with domain information, protein information, or both depending on the arguments passed. 
    
    arguments
    ----------
    TS: a time series table. The time series table must have a column for the code and region name for this function to work.
    
    code_colname (default="Code"): the name of the column in the time series dataframe giving the variant code information.
    
    region_colname: the name of the column in the time series dataframe giving the region information.
    
    protein (string, default=None): If passed to the function, the index will be formatted with the protein name along with the region name and the variant code.
    
    returns
    ----------
    TS: A time series table indexed according to "<code> (<region name>)"
    """
    #If a protein name is given, create an index with the format <protein>: <code> (<region>). 
    if protein and region_colname:
        #In the lambda function, x is a row of the dataframe
        TS.index=TS.apply(lambda x: display_region_and_protein(x[code_colname],x[region_colname],protein),axis=1)
        #Drop the code and region columns
        TS=TS.drop([code_colname,region_colname],axis=1)
    
    #If a protein name is given, create an index with the format <protein>: <code>.
    elif protein and not region_colname:
        #In the lambda function, x is a row of the dataframe
        TS.index=TS.apply(lambda x: display_protein(x[code_colname],protein),axis=1)
        #Drop the code and region columns
        TS=TS.drop([code_colname],axis=1)
    
    #If a region column is given but not a protein name, create an index wtih the format <code> (<region>).
    elif region_colname and not protein:
        TS.index=TS.apply(lambda x: display_region(x[code_colname],x[region_colname]),axis=1)
        #Drop the code and region columns
        TS=TS.drop([code_colname,region_colname],axis=1)
        
    #If only code information is provided, return a warning and add just the code to the index.
    else:
        import warnings
        warnings.warn("Both region_colname and protein are not defined. The index has been set to 'Code' without addition of region and protein information.",category=RuntimeWarning)
        TS.index=TS[code_colname]
        #Drop the code and region columns
        TS=TS.drop([code_colname],axis=1)
                      
    return TS

def display_region(code,region):
    """
    Returns a string in the format <code> (<region>) for a variant event passed to it.

    Arguments
    ----------
    code: string giving the mutation code.

    region: string giving the mutation region.
    """
    #Special case: "Zero_Mutations_in_<protein>" does not have a corresponding domain column (this is a blank instead). In this case, only include the "Code" column in the string.
    if region=="-":
        return code
    else:
        #Return the first and second columns as a string in the format below.
        return "{0} ({1})".format(code,region)
    
def display_protein(code,protein):
    """
    Returns a string in the format <protein>: <code> for a variant event passed to it.

    Arguments
    ----------
    code: string giving the mutation code.

    protein: sting giving the protein name.
    """
    #Special case: "Zero_Mutations_in_<protein>". protein is already mentioned in this code entry and no position is given.
    if str(code).lower()=="zero_mutations_in_{}".format(protein.lower()): #str.lower used to detect this column regardless of the case of the protein name input
        #Leave this code as-is
        return code
    else:
        return "{0}: {1}".format(protein,code)
    
def display_region_and_protein(code,region,protein):
    """
    Returns a string in the format <protein>: <code> (<region>) for a variant event passed to it.

    Arguments
    ----------
    code: string giving the mutation code.

    region: string giving the mutation region.

    protein: sting giving the protein name.
    """
    #Special case: "Zero_Mutations_in_<protein>". protein is already mentioned in this code entry and no position is given.
    if region=="-":
        #Leave this code as-is
        return code
    else:
        return "{0}: {1} ({2})".format(protein,code,region)

def aggregate_TS(proteins,TS_dir,region_paths=None,continent="Global",position=False):
    """
    Produces an aggregate time series matrix from multiple time series inputs.
    
    arguments
    ----------
    proteins: a list of protein names to add to the aggregate matrix
    
    TS_dir: path to the directory containing time series percentage tables for each protein
    
    region_paths (optional, default=None): a dictionary specifying the pathway to the desired region information file for the protein if applicable. All names of region pathways (domain, subdomain, subunit) should be the same for all proteins to avoid unexpected results. If "None" is entered, region information will not be added to the aggregate matrix.
    
    position (optional, default=False): if True, returns an aggregate matrix with both a position and protein column so individual proteins and amino acid positions can be selected. Index will not be set if True. If false, a time series matrix with no position or protein column and an index with the protein, variant code, and region (if specified), will be returned.
    
    Output
    ----------
    A time series matrix containing information on each of the proteins entered will be returned.
    """
    no_regions=False
    #If a dictionary is not passed to region_paths, create a dictionary of "None" for each protein to skip domain addition
    if region_paths==None:
        no_regions=True
        region_paths={}
        for protein in proteins:
            region_paths[protein]=None
    
    #In case an incomplete dictionary of region paths is passed to the function, 
    region_paths=check_region_paths(proteins,region_paths)
    
    if no_regions==False:
        for protein in proteins:
            if region_paths[protein]!=None:
                #Extract region name of region first (filename is last element of path, and region name is the second underscore-separated field)
                region_name=region_paths[protein].split("/")[-1]
                region_name=region_name.split("_")[1]
                #.csv might be in the second field. Remove it if that is the case
                if ".csv" in region_name:
                    region_name=region_name.split(".")[0]
    
    #Initialize list to add time series matrices to
    TS_list=[]
    
    for protein in proteins:
        #Code path is computed for every protein
        code_path="../Variant_Call/{0}/{0}_all_by_code.csv".format(protein)
        #If a path is provided to a region info file, prepare time series with position info
        if region_paths[protein]:
            TS=prepare_TS(TS_path="{0}{1}_Percent_{2}.csv".format(TS_dir,protein,continent),
                                position=True,
                                var_by_code_path=code_path)
            #Remove "zero_mutations" column
            TS=TS[1:]        
            #Using Position info, add domain info
            
            #Add region column
            TS=add_region_column(TS,region_type=region_name,region_path=region_paths[protein])
            
            if position==False:    
                #Format index with protein name, code, and region for each variant
                TS=code_region_index(TS,code_colname="Code",region_colname=region_name,protein=protein)
                TS=TS.drop("Position",axis=1)
            
            elif position==True:
                #Add column with protein name for all entries so variants can be indexed by protein as well as position
                TS["Protein"]=protein

        else:
            #Load and prepare time series matrix
            TS=prepare_TS("{0}{1}_Percent_{2}.csv".format(TS_dir,protein,continent),var_by_code_path=code_path,position=True)
            #Remove "zero_mutations" column 
            TS=TS[1:]
            if position==False:
                #Format index to include code and protein information, and region info if it exists
                TS=code_region_index(TS,"Code",protein=protein)
                TS=TS.drop("Position",axis=1)
            
            #If position==True, add a column for 'protein' and do not drop position column so time series matrix can be indexed
            elif position==True:
                TS["Protein"]=protein
            
            #If region information is specified for at least one protein in the complex but not the current protein, add a column of dashes for the current protein. This is not needed if the position column is not desired.
            if no_regions==False and position==True:
                TS[region_name]="-"
        #Add formatted time series matrix to list
        TS_list.append(TS)
    
    return pd.concat(TS_list,axis=0)

def check_region_paths(proteins,region_paths):
    """
    Corrects region_paths dictionary to avoid errors caused by incomplete key entries. Allows user to only specify proteins for which region information is desired by filling in 'None' for all proteins not included in the region_paths dictionary.
    """
    for protein in proteins:
        try:
            region_paths[protein]
        #A KeyError will be returned if there is no entry for the protein. If this happens, define the key for the protein as 'None'.
        except KeyError:
            region_paths[protein]=None
    return region_paths

def complex_region_query(protein,resi,target_protein,target_resi):
    """
    Accepts a target protein and a list of target residues on that protein and returns True if the time series entry matches the target residues of the target protein. Designed to be used with Pandas.apply() on a time series matrix with a protein and position column to search for time series entries matching a defined region.
    
    protein (string): the protein of the entry to be queried against the target. One protein should be entered here as it appears in the time series data.
    
    resi (integer): the residue number of the entry to be queried against the target.
    
    target_protein (string): the target protein to check the time sreies entry against. One protein should be entered as it appears in the time series data.
    
    target_resi (list of integers): target residues to check the time series entry against. Each element must be an integer for the function to work properly.
    """
    return (protein==target_protein) and any([resi==target for target in target_resi])

def aggregate_codes(proteins,var_call_dir,region_paths=None,region_name=None,continent="Global",parent_TS_dir=None,region_labels=False,drop_position=True,add_protein=False):
    """
    For a list of proteins entered, create an aggregate dataset of the variants by code tables for each protein.
    
    Arguments
    ----------
    protein (list): a list of proteins for which an aggregate dataset is desired.
    
    var_call_dir: path to the output of the MSA_reader()
    
    region_paths (optional,default=None):
    
    region_name (optional, default=None): 

    region_label (optional, default=False): If True, format code column to contain protein and region information; if false, just protein information is added. If subsetting an aggregate time series matrix for mutation codes based on the aggregate codes table, region_label must be set to True. It is reccomended to set this to False for printing a table for reports. 
    
    drop_position (optional, default=True): If True, the codes table is returned without a position column. If False, the column is included in the table.
    
    add_protein (optional, default=False): If True, the table will include a colum for "Protein" giving the name of the protein associated with each variant code.
    
    Returns
    ----------
    Dataframe giving information for each unique variant in the complex.    
    """
    #1. Global aggregate table: computed if continent is set to "Global"
    if continent=="Global":
        #Create list for storing variant codes data for each protein
        codes_ag=[]   
        #If region information is provided but is incomplete, fill incomplete regions with 'None'.
        if region_paths:
            region_paths=check_region_paths(proteins,region_paths)

        #Iterate through protein list and form datasets for concatenation
        for protein in proteins:
            #1.A. load variants by code dataset
            path="{0}{1}/{1}_all_by_code.csv".format(var_call_dir,protein)
            codes=pd.read_csv(path)

            #1.B. Add region information only if region_paths is specified
            if region_paths:
                #If a path to region information is provided, add region information to the table
                if region_paths[protein]:
                    codes=add_region_column(codes,region_name,region_paths[protein])
                #Otherwise, add dashes to the region information column
                else:
                    codes=add_dashes(codes,region_name)

            #1.C. If region_labels=True, modify "Code" column to contain region information along with protein information.
            if region_labels==True:
                if region_paths and region_paths[protein]:
                    codes["Code"]=codes.apply((lambda x:display_region_and_protein(x["Code"],x[region_name],protein)),axis=1)
                else:
                    codes["Code"]=codes.apply((lambda x:display_protein(x["Code"],protein)),axis=1)
            #Otherwise, modify "Code" column to be equal to the protein name
            else:
                codes["Code"]=codes.apply(lambda x:display_protein(x["Code"],protein),axis=1)


            #1.D. Modify "Type" column with long type information
            codes["Type"]=codes["Type"].apply(lambda x:long_types(x))

            #1.E. Drop "Position" column if drop_position==True
            if drop_position==True:
                codes=codes.drop("Position",axis=1)
                
            #1.F. Add a colmn with the protein name for all entries if add_protein==True
            if add_protein==True:
                codes["Protein"]=protein
                
            #1.G. Add dataframe to list of aggregate datasets
            codes_ag.append(codes)
        
        #Form and return aggregate dataset
        return pd.concat(codes_ag,axis=0)
    
    #2. If continent is not global, table of codes must be computed using alternate means
    else:
        #Extra arguments required for continent_specific code data
        if not parent_TS_dir:
            raise ValueError("If continent-specific aggregate code table is desired, the parent time series directory must be specified using the 'parent_TS_dir' argument.")
        codes_ag=[]
        
        for protein in proteins:
            #2.A. Form path to frequency file for the protein
            #Default directory is "Time_Series_Frequency" and default filename is "<protein>_Frequency_<continent>.csv". 
            #This function will not work if this is changed.
            freq_path="{0}/Time_Series_Frequency/{1}_Frequency_{2}.csv".format(parent_TS_dir,protein,continent)  
            #Form path for variants by code dataset
            var_code_path="{0}{1}/{1}_all_by_code.csv".format(var_call_dir,protein)

            #2.B. Load time series frequency data using prepare_TS()
            TSF=prepare_TS(freq_path,position=False,var_by_code_path=var_code_path,subset_codes=None,reindex=True)
            #Take type, code, and position columns from variants by code dataset 
            codes=pd.read_csv(var_code_path)
            codes=codes[["Code","Type","Position"]]

            #2.C. Compute total number of sequences (first row of dataframe) for protein so prevalence can be normalized across proteins
            total=TSF.iloc[0,:].sum()

            #2.D. Remove the top two rows of the frequency table and the position dataframe (total genomes and zero mutations rows)
            TSF=TSF.iloc[2:,:]

            #2.E. Take the row-wise sum of variant frequencies (total number of occurences for each variant for this continent)
            sums=TSF.sum(axis=1)

            #2.F. Divide the row-wise sum of variant frequencies by the total number of sequences for the protein
            norm=sums/total

            #2.G. Formation of table: Join frequencies and normalized frequencies to code, position, and type information
            norm=norm.to_frame(name="Percentage")
            #Pull code information out of index and add to column
            norm.reset_index(inplace=True)
            #Perform same operation for frequency data (sums)
            sums=sums.to_frame(name="Frequency")
            sums.reset_index(inplace=True)
            #Merge frequency and percentage columns to the position information
            codes=pd.merge(left=norm,right=codes,on="Code")
            codes=pd.merge(left=codes,right=sums,on="Code")
            #Convert "type" column to long format ('substitution' instead of 'sub')
            codes["Type"]=codes["Type"].apply(lambda x: long_types(x))

            #2.H. Add domain column or blank column if region_paths is not equal to None
            if region_paths:
                #If a path to region information is provided, add region information to the table
                if region_paths[protein]:
                    codes=add_region_column(codes,region_name,region_paths[protein])
                #Otherwise, add dashes to the region information column
                else:
                    codes=add_dashes(codes,region_name)

            #2.I. Format the 'code' column to contain domain and protein info if specified, or just protein info otherwise.
            if region_labels==True:
                #If region information is given for the protein, format the code column to <protein>: <code>(<region>)
                if region_paths and region_paths[protein]:
                    codes["Code"]=codes.apply((lambda x:display_region_and_protein(x["Code"],x[region_name],protein)),axis=1)
                else:
                    codes["Code"]=codes.apply((lambda x:display_protein(x["Code"],protein)),axis=1)
            else:
                codes["Code"]=codes.apply((lambda x:display_protein(x["Code"],protein)),axis=1)

            #2.J. Drop position column if drop_position==True
            if drop_position==True:
                codes=codes.drop("Position",axis=1)
            
            #2.I. Add a colmn with the protein name as an entry if add_protein==True
            if add_protein==True:
                codes["Protein"]=protein
                
            #Append table to the list of tables
            codes_ag.append(codes)
        
        #Form and return aggregate dataset
        return pd.concat(codes_ag,axis=0)

def prepare_top_n(var_call_dir,TS_dir,protein,continent="Global",n=10,aggregate=False,region_path=None,by_continent=False,drop_position=True):
    """
    Outputs the time series data for the top n most common variants for the protein or proteins entered, on the provided continent.

    Arguments
    ----------
    var_events_dir: The path to the variant call directory with outputs from the MSA_Reader functions.

    TS_dir: Path to the time series percentage directory.

    protein (string if aggregate==False or list if aggregate==True): The name of the protein, or a list of multiple protein names if an aggregate time series matrix is desired. If aggregate=True, protein must be a list. If aggregate=False, protein must be a string.

    continent (string): the continent for which to perform the analysis. May be "Global","North America","South America","Africa","Oceania","Europe", or "Asia".

    n (optional, default=10): Integer giving the number of top variants to plot, the default being the top ten.
    
    region_path (optional, default: None): If region information is desired, a string giving the path to the region information file (domain,subunit,subdomain info etc.) must be provided. For aggregate analysis of multiple proteins, region_path must be a dictionary giving the paths for each protein for which region info is desired.
    
    by_continent (optional, default: False): if True, use the n most common variants in the continent indicated instead of worldwide. 
    
    drop_position (optional, default: True): set to False to include the position column in the output matrix.
    
    Returns
    ----------
    TS: a time series matrix indexed accoring to the top n most common variants in the defined continent. 
    """
    from math import sqrt
    import sys

    #Ensure n is in integer format
    n=int(n)
        
    #A. Function for Multi-Protein Complex (such as RNA-dependent RNA Polymerase)
    #Check if aggregate==True and protein is passed as a list
    if aggregate==True and type(protein)==list:
        #A.1. If region_paths is specified, check format of related arguments
        if region_path:
            #A.1.a. Return an error if region_paths is defined as a format other than a dictionary
            if type(region_path)!=dict:
                raise ValueError("If region information is desired for an aggregate time series matrix, a dictionary must be used specifying the path of the region information for each protein.")
            #A.1.b. If some keys are not entered for region path, insert 'None' for those proteins.
            region_path=check_region_paths(protein,region_path)

        #A.2. Form aggregate time series percentage matrix for plotting.
        TS=aggregate_TS(protein,TS_dir,region_path,continent=continent)

        #A.3. Subset time series data for the n most common variants globally or for the specified continent.
        #A.3.a. If by continent==True, get top ten variants by continent
        if by_continent==True:
            #A.3.a.1. Form an aggregate frequency table for the continent entered. 
            #Path to file: go up to parent time series directory to fetch frequency table
            from os.path import dirname
            #Store list of individual time series 
            #If "/" is added at the end of TS_dir, calling dirname() twice will go up one directory 
            parent_dir=dirname(dirname(TS_dir))
            #Create the aggregate code table for the continent  
            cont_ag=aggregate_codes(protein,var_call_dir,region_path,region_name="Region",continent=continent,parent_TS_dir=parent_dir,region_labels=True)
            #Sort in descending order by prevalence (prevalence must be used instead of frequency due to possibly unequal sample sizes for different proteins).
            cont_ag=cont_ag.sort_values(by=["Percentage"],ascending=False)
            #Select the codes of the top n most prevalent variants
            top_n=cont_ag[0:n]["Code"]
            #Subset the aggregate time series matrix for the top n most common variants (code information is in index).
            TS=TS[TS.index.isin(list(top_n))]
            
        #A.3.b. Otherwise, use the global top ten.
        else:
            #Form aggregate table
            code_ag=aggregate_codes(protein,var_call_dir,region_path,region_name="Region",continent="Global",region_labels=True)
            #Sort in descending order by prevalence (prevalence must be used instead of frequency due to possibly unequal sample sizes for different proteins).
            code_ag=code_ag.sort_values(by=["Percentage"],ascending=False)
            #Select the codes of the top n most prevalent variants
            top_n=code_ag[0:n]["Code"]
            #Subset the aggregate time series matrix for the top n most common variants.
            TS=TS[TS.index.isin(list(top_n))]
            
        #A.4.a. Sort the index according to the order of the top n values 
        TS=TS.reindex(list(top_n))
            
    #B. Function for Single Protein
    elif aggregate==False and type(protein)==str:
        #Check region_path argument: must be a string for single-protein analysis
        if region_path and type(region_path)!=str:
            raise ValueError("For single-protein analyis, region_path must be provided as a string.")
        
        #B.1. Load and prepare (singular) time series data
        #Form time series path
        TS_path="{0}{1}_Percent_{2}.csv".format(TS_dir,protein,continent)
        #Form path to variants by code file (global, variants by code dataset contains only worldwide info)
        var_code_path="{0}{1}/{1}_all_by_code.csv".format(var_call_dir,protein)
        
        #Prepare time series data (uses function from this script)
        TS=prepare_TS(TS_path=TS_path,var_by_code_path=var_code_path,position=True)

        #B.2. Add region data if it exists, otherwise make the "Code" column the index and drop from analysis.
        if region_path:
            #A column for position must be set up before doing this (uses function from this script)
            TS=add_region_column(TS,region_type="Region",region_path=region_path)
            #Set the index to include mutation code and region info (uses function from this script)
            TS=code_region_index(TS,code_colname="Code",region_colname="Region")
        else:
            TS.index=TS["Code"]
            TS=TS.drop("Code",axis=1)
        
        #B.3. Drop position column from the time series table
        #The "Position" Column, created by prepare_TS() and used if a region path is defined, is no longer necessary and will be dropped from analysis. 
        if drop_position==True:
            TS=TS.drop("Position",axis=1)
        
        #B.4. Subset for top n variants, worldwide or for the specified continent.
        #B.4.a. If by_continent is set to True, subset variant codes by the top n most common variants on the desired continent
        if by_continent==True:
            #B.4.b. Form path for time series frequency data
            #The time series frequency data is required to determine the top n most common variants by continent
            #Edit TS path to go up to the parent time series directory
            rejoin="/"
            #Split into a list and remove the last two elements (goes back up to directory with all time series data)
            parent_dir=TS_path.split("/")[:-2]
            #Re-form string, then add to path to point to frequency data for current protein and continent 
            parent_dir=rejoin.join(parent_dir)
            
            #Default directory is "Time_Series_Frequency" and default filename is "<protein>_Frequency_<continent>.csv". 
            #This function will not work if this is changed.
            TS_freq="{0}/Time_Series_Frequency/{1}_Frequency_{2}.csv".format(parent_dir,protein,continent)    

            #B. Calculation of top n variants for continent
            #Load time series frequency data using prepare_TS()
            TSF=prepare_TS(TS_freq,position=True,var_by_code_path=var_code_path,subset_codes=None,reindex=True)
            #Re-name index according to domain information if region information is given
            if region_path:
                TSF=add_region_column(TSF,region_type="Region",region_path=region_path)
                TSF=code_region_index(TSF,region_colname="Region")
            
            #Drop the position column from the time series matrix
            TSF=TSF.drop("Position",axis=1)
            #Remove the top two rows (total genomes and zero mutations rows)
            TSF=TSF.iloc[2:,:]
            #Take the row-wise sum of variant frequencies (total number of occurences for each variant for this continent)
            sums=TSF.sum(axis=1)
            #Sort total frequencies by descending order and take the top n entries (default 10)
            sums=sums.sort_values(ascending=False)[0:n]
            
            #Subset time series matrix for the n most common variants for the continent 
            TS=TS[TS.index.isin(list(sums.index))]
            
            #Sort according to the order of the top n variants
            TS=TS.reindex(list(sums.index))

        #B.2.b. If by_continent is false, get top ten variants worldwide accross all time points
        else:
            #Read variants by code file
            codes=pd.read_csv(var_code_path)
            #Take top n values
            top_n=codes.sort_values(by="Frequency",ascending=False)[0:n]
            #Add domain information if given, set code column to the format <code> (<region>)
            if region_path:
                top_n=add_region_column(top_n,region_type="Region",region_path=region_path)
                top_n["Code"]=top_n.apply(lambda x:display_region(x["Code"],x["Region"]),axis=1)
        
            #Subset the time series data for the top n most common variants from the code data (default 10)
            TS=TS[TS.index.isin(list(top_n["Code"]))]
            
            #Sort according to order of top n variants
            TS=TS.reindex(list(top_n["Code"]))
    else:
        raise ValueError("Invalid combination for arguments 'aggregate' and 'protein'. Accepted combinations: 1. Protein as a list and aggregate==True 2. Protein as a string and aggregate==False.")
 
    return TS

def top_n_TS_graph(var_call_dir,TS_path,protein,continent,n=10,region_path=None,aggregate=False,by_continent=False,output=None):
    """
    Creates a grapth of the top ten most common variants for the protein.

    Arguments
    ----------
    var_code_path: the path of the directory containing outputs from MSA_reader() for the indicated protein.

    TS_path: the path of the time series data for the protein.

    protein (string or list): The name of the protein, or a list of protein names if aggregate=True.

    continent (string): the continent for which to perform the analysis. May be "Global","North America","South America","Africa","Oceania","Europe", or "Asia"

    n (optional, default=10): Integer giving the number of top variants to plot, the default being the top ten.
    
    region_path (optional, default= None): The path to a region information file for a protein, or a dictionary of paths if aggregate=True. This file will be a CSV file with three fields: the name of the region (subunit, domain, etc.), the residue at which the region begins, and the residue at which the region ends.

    aggregate (optional,default= False): If true, retrieves time series data for a list of proteins rather than a single protein

    by_continent (optional, default= False): if True, use the n most common variants in the continent indicated instead of worldwide. 
    
    output: the path of the output graph, saved as a .png (default: no path)
    """
    from math import sqrt
    import sys

    #Prepare time series data for visualization
    TS=prepare_top_n(var_call_dir=var_call_dir,TS_dir=TS_path,protein=protein,continent=continent,n=n,aggregate=aggregate,region_path=region_path,by_continent=by_continent)

    #Line Graph for Variant Prevalence Over Time
    x=newdates
    labels=list(df.index)

    #Create Figure Frame
    fig=plt.figure(figsize=(14,8))
    ax = fig.add_axes([0.1,0.2,0.7,0.7])

    #Dictionaries giving the colors and markers to be used for each continent
    color_list=["firebrick","#1E399A","purple","forestgreen","chocolate","gold","darkcyan","black","palevioletred","saddlebrown"]
    marker_list=["o","D","s"]

    #Create lines for each variant
    for i in range(0,len(df),1):
        line_obj=ax.plot(x,df.iloc[i,:],ls='-',marker=marker_list[i%len(marker_list)],label=labels[i],color=color_list[i%len(color_list)],markersize=7)

    #Legend
    leg=ax.legend(bbox_to_anchor=(1.02,0.9),fontsize=14,loc="upper left",markerscale=1.5)
    leg.set_title("Mutation",prop={'weight':'medium','size':18})

    #Rotate X-axis tick labels
    plt.setp(ax.get_xticklabels(), rotation= 45, ha="right",rotation_mode="anchor",fontsize=10)

    #Y-axis text parameters
    plt.setp(ax.get_yticklabels(),fontsize=12)

    #Adjust y-axis ticks
    ax.set_yticks(np.arange(0,1.1,0.1))
    ax.set_yticks(np.arange(0,1.1,0.02),minor=True);

    #Upper bound is the number of columns in the dataframe minus 1.0 (indexing starts at zero), plus 0.5 for space
    ax.set_xlim(left=-0.5,right=df.shape[1]-0.5)
    ax.set_ylim(-0.02,1.01)

    #Set axes labels
    ax.set_ylabel("Prevalence of Mutation",fontsize=12)
    ax.set_xlabel("Collection Date of Sample",fontsize=12)

    #Figure Title
    if continent=="Global":
        fig.suptitle("Most Common Mutations for {}: Global Prevalence".format(protein),fontsize=26,fontweight='medium')
    else:
        fig.suptitle("Most Common Mutations for {}: Prevalence in {}".format(protein,continent),fontsize=26,fontweight='medium')

    #Create a grid
    ax.grid(which='major',axis='both',color="#DDDDDD",alpha=0.3)

    if output:
        plt.savefig(output)

    plt.show()
    
def line_plot(TS,
              graph_dates,
              protein=None,
              continent="Global",
              complex_name=None,
              color_by_variant=None,
              color_list=["firebrick","#1E399A","purple","forestgreen","lightcoral","chocolate","gold","darkcyan","black","#AAAAFF"],
              marker_list=["o","D","^","s"],
              figsize=(14,8),
              axes_bounds="default",
              center_title_to_figure=True,
              x_tick_properties=None,
              y_tick_properties=None,
              fontsize_x_label=12,
              fontsize_y_label=12,
              output=None):
    """
    Creates a line plot from time series data

    Arguments
    ----------
    TS: A time series matrix.

    Graph_dates: A list of dates that will be displayed on the x-axis tick labels. Can be in any format but must correspond to the dates in the TS matrix to properly represent data.
    
    Protein (string): the name of the protein for printing the title. 
    
    Complex_name: If applicable and specified, print the title of the complex (i.e. RdRP) instead of the protein name. Highly reccomended for aggregate analyses.
    
    color_by_variant (optional, default=None): Can pass a dictionary with variant names as keys and a dictionary of matplotlib line2D properties (such as marker size, marker color, etc.) to plot each unique variant with a desired style.
    
    color_list (list): If color_by_variant=None, a list of colors may be passed here. Plotting will cycle through the marker list, moving to the next color each time a new line is created from the data.
    
    marker_list (list): If color_by_variant=None, a list of markers may be passed here. Plotting will cycle through the marker list, moving to the next marker each time a new line is created from the data.
    
    figsize (tuple): Set the size of the figure in inches (width,height).
    
    axes_bounds: May be "default" or "RdRP". Setting the window to "RdRP" changes the width of the window to accomodate longer domain labels in the legend for the polymerase complex.
    
    center_title_to_figure (default=True): If false, the title is centered to the plotting window instead of the figure (the figure includes the plotting window and the legend)
    
    fontsize_x_label (int, default=12): Defines the font size of the x-axis label in points.
    
    fontsize_y_label (int, default=12): Defines the font size of the y-axis label in points.
    
    fontsize_x_ticks (int, default=10): Defines the font size of the x-axis tick labels in points.
     
    fontsize_y_ticks (int, default=12): Defines the font size of the y-axis tick labels in points.
    
    x_label_rotation (int, default=45): Degrees of counterclockwise rotation from horizontal position on axis (90=vertical labels, 0=horizontal labels).
    """
    import matplotlib.ticker as mtick
    
    ##### Argument Set-up #####
    #Fill default values of x_tick_properties if they are not specified
    x_tick_properties=fill_defaults(x_tick_properties,{'labelsize':10,'rotation':45})
               
    #Check and fill y-axis property kwargs
    y_tick_properties=fill_defaults(y_tick_properties,{'labelsize':12})
    #####
    
    #Line Graph for Variant Prevalence Over Time
    x=graph_dates
    labels=list(TS.index)

    #Axes bounds relative to the figure vary based on size of legend. Special axes bounds used for the RdRP are saved here.
    #Axes bounds can be chosen with the string "axes_ratio"
    if axes_bounds=="default":
        ax_bound=[0.1,0.2,0.7,0.7]
    elif axes_bounds=="RdRP":
        ax_bound=[0.1,0.2,0.6,0.7]
    
    #Create Figure Frame
    fig=plt.figure(figsize=figsize)
    ax = fig.add_axes(ax_bound)

    #Standard: plot each variant with default color scheme unless color_by_variant is specified
    if color_by_variant==None:
        for i in range(0,len(TS),1):
            line_obj=ax.plot(x,TS.iloc[i,:],ls='-',marker=marker_list[i%len(marker_list)],ms=7,mew=1,mec="#FFFFFFEE",label=labels[i],color=color_list[i%len(color_list)])
    #If color_by_variant is specified, pass the kwargs corresponding to the current variant name to the plot function
    else:
        for i in range(0,len(TS),1):
            line_obj=ax.plot(x,TS.iloc[i,:],ls='-',label=labels[i],**color_by_variant[labels[i]])
            
    #Legend
    leg=ax.legend(bbox_to_anchor=(1.02,0.9),fontsize=14,loc="upper left",markerscale=1.5)
    leg.set_title("Mutation",prop={'weight':'medium','size':18})

    #X-tick properties (ticks and label placement)
    ax.tick_params(which="major",axis='x',width=1.25,**x_tick_properties)
    #X-tick text properties
    plt.setp(ax.get_xticklabels(), ha="right",rotation_mode="anchor")

    #Y-axis tick/label parameters
    ax.tick_params(which="major",axis='y',width=1.25,**y_tick_properties)

    #Adjust y-axis ticks
    ax.set_yticks(np.arange(0,1.1,0.1))
    ax.set_yticks(np.arange(0,1.1,0.02),minor=True);

    #Upper bound is the number of columns in the dataframe minus 1.0 (indexing starts at zero), plus 0.5 for space
    ax.set_xlim(left=-0.5,right=TS.shape[1]-0.5)
    ax.set_ylim(-0.02,1.01)

    #Y-axis tick labels as percentage
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1,decimals=0))
    
    #Set axes labels
    ax.set_ylabel("Prevalence of Mutation",fontsize=fontsize_y_label)
    ax.set_xlabel("Collection Date of Sample",fontsize=fontsize_x_label)

    #Define figure title
    if protein and continent=="Global":
        title="Most Common Mutations for {}: Global Prevalence".format(protein)
    elif protein and continent!="Global":
        title="Most Common Mutations for {}: {}".format(protein,continent)
    elif complex_name and continent=="Global":
        title="Most Common Mutations for {}: Global Prevalence".format(complex_name)
    elif complex_name and continent!="Global":
        title="Most Common Mutations for {}: {}".format(complex_name,continent)
    #Warn and print no title for invalid combinations
    elif (complex_name and protein) or (not complex_name and not protein):
        warnings.warn("Invalid combination of input for 'protein' and 'complex_name' arguments. Please specify input for either 'protein' or 'complex_name' (not both or neither).",category=UserWarning)
    
    #Center title to figure if default axes bounds are used. Center title to axes if RdRP bounds are used.
    if axes_bounds=="RdRP" or center_title_to_figure==False:
        ax.set_title(title,fontsize=26,fontweight='medium',pad=20)
    else:
        fig.suptitle(title,fontsize=26,fontweight='medium')
    
    #Create a grid
    ax.grid(which='major',axis='both',color="#DDDDDD",alpha=0.3)

    if output:
        plt.savefig(output,bbox_inches = "tight",dpi=450)

    plt.show()

def TS_Heatmap(data,title,dates,outfile=None,figsize=(18,9),barsize=0.8,barfontsize=14,xtitlesize=12,y_tick_properties=None,x_tick_properties=None,**cbar_kwargs):
    """
    Creates a heatmap from the time series subset selected with the title entered.
    
    Aruguments
    ----------
    data: Pandas DataFrame of time series data to be visualized.
    
    title: Desired title for plot.
    
    dates: Date labels generated from the Plotting_Functions.dates_for_graph() function. 
    
    outfile: Path for writing the heatmap as a .png (default=None).
    
    figsize: Tuple giving the width and height of the figure in inches (default=(18,9)).
    
    barsize: Decimal value giving the size of the color bar relative to the plot (default=0.8).
    """
    import matplotlib.ticker as mtick
    import matplotlib.colors as colors
    import matplotlib.cbook as cbook

    #Fill kwarg dictionaries with default values if they are unspecified
    #Default x-axis font size=10
    x_tick_properties=fill_defaults(x_tick_properties,{'labelsize':10,'rotation':45})
    
    #Check and fill y-axis property kwargs
    y_tick_properties=fill_defaults(y_tick_properties,{'labelsize':12})
    
    #Create list from variant names for labels and define data
    intervals=dates
    variants=list(data.index)
    heatmap_values=data.values

    #Create Figure and Heatmap
    fig,ax = plt.subplots(tight_layout=True,figsize=figsize)
    im=ax.imshow(heatmap_values,cmap=plt.cm.YlGnBu,norm=colors.LogNorm(vmin=0.001,vmax=1))

    #Set Ticks and Tick Labels
    ax.set_xticks(np.arange(len(intervals)))
    ax.set_yticks(np.arange(len(variants)))
    ax.set_xticklabels(intervals)
    ax.set_yticklabels(variants)
    ax.tick_params(which="major",axis='y',width=1.25,**y_tick_properties)
    ax.tick_params(which="major",axis='x',width=1.25,**x_tick_properties)

    #X-axis Label
    ax.set_xlabel("Collection Date of Sample",fontsize=xtitlesize)
    
    #Define Colorbar
    cbar=plt.colorbar(im, ax=ax, shrink=barsize, format=mtick.PercentFormatter(xmax=1,decimals=2),ticks=[0.001,0.002,0.005,0.01,0.02,0.05,0.1,0.2,0.5,1],**cbar_kwargs)
    cbar=cbar.ax.set_ylabel("Percentage of Sequences With Mutation", rotation=-90, va="bottom",fontsize=barfontsize)#Scale fontsize to change with changes in the bar size

    #Minor ticks, which center labels above intervals and variants, and create a border between values
    ax.set_xticks(np.arange(len(intervals)+1)-.5, minor=True)
    ax.set_yticks(np.arange(len(variants)+1)-0.5, minor=True)
    ax.grid(which="minor", color="#000000", linestyle='-', linewidth=0.4)
    ax.tick_params(which="minor", bottom=False, left=False)

    #Rotate labels
    plt.setp(ax.get_xticklabels(), rotation=x_tick_properties['rotation'],ha='right',rotation_mode='anchor')
    #plt.setp(ax.get_yticklabels(), )

    ax.set_title(title, fontsize=24, pad=15)
    if outfile:
        plt.savefig(outfile,dpi=450)

    plt.show()

def multi_page_heatmap(data,
                       dates,
                       n_per_page=75,
                       common_title=None,
                       outfile_prefix=None,
                       figsize=(16,20),
                       barsize=0.6,
                       barfontsize=14,
                       xtitlesize=12,
                       y_tick_properties=None,
                       x_tick_properties=None,
                       cbar_kwargs={'aspect':30}):
    """
    For data with large numbers of rows, multi_page_heatmap() will create several different heatmaps to visualize all of the data.
    
    Arguments
    -----------
    data: the data to be visualize. This should be the full data: the data will be split into pages automatically.
    
    dates: Date labels generated from the Plotting_Functions.dates_for_graph() function. 
    
    n_per_page (default=75): An integer specifying the number of entries to include on each page.
    
    common_title: A title to put at the top of the page. If '<page>' is entered, it will be replaced with the current page (ex. 'page 1 of 3')
    
    outfile_prefix: If output to file is desired, a path prefix can be entered here with the relative path also defined. "_<page number>_of_<total pages>.png" will be added at the end.
    
    outfile: Path for writing the heatmap as a .png (default=None).
    
    figsize: Tuple giving the width and height of the figure in inches (default=(18,9)).
    
    barsize: Decimal value giving the size of the color bar relative to the plot (default=0.8).
    """
    #Number of pages: equal to whole number of len(data) divided by n_per_page, plus one if there is a remainder 
    n_pages=len(data)//n_per_page
    if len(data)%n_per_page!=0:
        n_pages+=1

    #Creating heatmap data: make one for each page, slicing in multiples of n_per_page
    for page in range(1,n_pages+1):
        #Create slice intervals for the current page based on the number of entries desired per page
        lower=n_per_page*(page-1)
        upper=n_per_page*page
        #Do not use an upper slice for the last page
        if page!=n_pages:
            Tslice=data.iloc[lower:upper,:]
        else:
            Tslice=data.iloc[lower:,:]
        #Create title for current page    
        page_title=common_title.replace("<page>",f"Page {page} of {n_pages}")
        #Create output path for current page
        if outfile_prefix:
            outfile=outfile_prefix+f"_{page}_of_{n_pages}.png"
        else:
            outfile=None
                
        #Construct dictionary of colorbar kwargs that may change for different pages
        page_n_kwargs=dict()
        for kwarg in cbar_kwargs:
            page_n_kwargs[kwarg]=cbar_kwargs[kwarg]
        
        #Scale color bar aspect ratio for last page based on number of entries
        try:
            page_n_kwargs["aspect"]=(page_n_kwargs["aspect"])*(len(Tslice)/n_per_page)
        except KeyError:
            page_n_kwargs["aspect"]=(30)*(len(Tslice)/n_per_page)
        
        #Scale color bar bar size based on number of entries on last page
        page_n_barsize=barsize*(len(Tslice)/n_per_page)
               
        #Make a heatmaps for the current page
        TS_Heatmap(data=Tslice,
                   title=page_title,
                   dates=dates,
                   outfile=outfile,
                   figsize=figsize,
                   barsize=page_n_barsize, 
                   barfontsize=barfontsize,
                   xtitlesize=xtitlesize,
                   y_tick_properties=y_tick_properties,
                   x_tick_properties=x_tick_properties,
                   **page_n_kwargs)
    
def confirm_output(output):
    choice=input("Write to {}? (y/n) ".format(output))
    if choice=="y":
        plt.savefig(output)
        print("Figure saved to {}.".format(output))
    elif choice=="n":
        pass
    else:
        print("Invalid selection. Please try again.")
        confirm_output(output)
        
def variant_color_cycler(unique_variants):
    """
    Returns a dictionary with matplotlib line2D kwargs used to determine the style of a line plot; properties are assigned to each variant. A maximum of 60 unique variants are supported by the function.
    
    Arguments:
    ----------
    unique_variants: a list of unique variants in time series data to be plotted. The names of the variants passed should be exactly the same as how they appear in the legend of the plot.
    """
    markers=["o","D","p","^","s"]
    color_list=["firebrick","#1E399A","purple","#ABC44C","chocolate","lightcoral","gold","darkcyan","black","#AAAAFF","#111111","#2B8A0A"]

    #Create dictionary for storing kwargs 
    var_kwargs={}
    for i in range(len(unique_variants)):
        var_name=unique_variants[i]
        #Color repeats at the end of the list
        color=color_list[i%len(color_list)]
        #Marker is switched after each complete iteration through the color list
        marker=markers[i//len(color_list)]
        #Create dictionary entry of kwargs for variant i
        kwargs={}
        kwargs["marker"]=marker
        kwargs["color"]=color

        #Use special settings for black line
        if (color=="#111111"):
            kwargs["mfc"]="#888888"
            kwargs["mec"]="#111111"
        else:
            kwargs["mec"]="#00000088"
        #Marker size and marker edge width: make pentagon and triangle markers larger
        if marker=="p" or marker=="^":
            kwargs["ms"]=10
            kwargs["mew"]=1
        else:
            kwargs["ms"]=8
            kwargs["mew"]=1
        #Add kwargs for variant i to the dictionary of variant kwargs, using the variant name as the key
        var_kwargs[var_name]=kwargs
    return var_kwargs

def color_shape_cycler(unique_variants,color_list=None,marker_list=None):
    """
    Returns a dictionary with matplotlib line2D kwargs used to determine the style of a line plot; properties are assigned to each variant. A maximum of len(color_list)*len(marker_list) unique variants are supported by the function (60 with default color list (12 colors) and marker list (5 shapes)).
    
    Arguments:
    ----------
    unique_variants: a list of unique variants in time series data to be plotted. The names of the variants passed should be exactly the same as how they appear in the legend of the plot.
    
    color_list (optional, default=None): May specify a list of colors to use in the cycler. The number of unique variants supported is equal to the number of colors passed times the number of markers. The default color list (12 colors) is used if this is unspecified.
    
    marker_list (optional, default=None): May specify a list of markers to use in the cycler. The number of unique variants supported is equal to the number of colors passed times the number of markers. The default marker list (5 markers) is used if this is unspecified.
    """
    if marker_list==None:
        markers=["o","D","p","^","s"]
    else:
        markers=marker_list
        
    #Use default definition of color list if a color list is not specified
    if not color_list:
        color_list=["firebrick","#1E399A","purple","#ABC44C","chocolate","lightcoral","gold","darkcyan","black","#AAAAFF","#111111","#2B8A0A"]

    #Create dictionary for storing kwargs 
    var_kwargs={}
    #Return an error if the number of unique variants exceeds the number of unique color-marker combinations (60 by default).
    if len(unique_variants)>len(markers)*len(color_list):
         raise ValueError("Cannot create unique color-shape combinations for more than len(color_list)*len(shape_list) variants (60 by default).")
            
    for i in range(len(unique_variants)):
        var_name=unique_variants[i]
        
        #Color and shape cycler: shift shape cycling at the end of a full cycle through the color list (when the floor division i//len(color_list) changes
        color=color_list[i%len(color_list)]
        markershift=i//len(color_list)
        marker=markers[(i+markershift)%len(markers)]
       
        #Create dictionary entry of kwargs for variant i
        kwargs={}
        kwargs["marker"]=marker
        kwargs["color"]=color

        #Use special settings for black line
        if (color=="#111111"):
            kwargs["mfc"]="#888888"
            kwargs["mec"]="#111111"
        else:
            kwargs["mec"]="#00000088"
            
        #Marker size and marker edge width: make pentagon and triangle markers larger
        if marker=="p" or marker=="^":
            kwargs["ms"]=10
            kwargs["mew"]=1
        else:
            kwargs["ms"]=8
            kwargs["mew"]=1
            
        #Add kwargs for variant i to the dictionary of variant kwargs, using the variant name as the key
        var_kwargs[var_name]=kwargs
    return var_kwargs

def fill_defaults(prop_kwargs,default_properties):
    """
    Takes a dictionary of keyword arguments passed to a function and fills default arguments with values if they are not provided
    """
    #If the dictionary of kwargs is not provided, return the dictionary of default_properties.
    if not prop_kwargs:
        return default_properties
    
    if type(prop_kwargs) and type(prop_kwargs)!=dict:
        raise ValueError(f"The specified value '{prop_kwargs}' is not a dictionary.")
    
    if type(prop_kwargs)==dict:
        #Test each default property to see if it exists.
        for prop in default_properties:
            try:
                prop_kwargs[prop]
            #A key error will be returned if the default property does not exist.
            except KeyError:
                #Fill the property with the default setting in this case.
                prop_kwargs[prop]=default_properties[prop]
                    
    return prop_kwargs

def variant_combos(combo_path,var_A,var_B,verbose=False,outfile=None):
    """
    Analyzes variant combinations data to determine the number of sequences for which two specified variants ocurr together in, and the number of sequences in which each variant occurs separately.
    
    Arguments
    -----------
    combo_path (string): path to the variant combinations file for the protein with the desired variants. This will be in Time_Series_Tables/Variant_Combinations/ by default.
    
    var_A (string): Code of first variant to analyze, as it appears in the output from the MSA_reader function.  
    
    var_B (string): Code of second variant to analyze, as it appears in the output from the MSA_reader function.  
    
    verbose (default=False): If true, output sequence counts to the console
    
    outfile (default=None): Write table to CSV at the path specified.
    
    Returns
    -----------
    Tuple of four integer values, which can be used in the construction of a 2x2 contingecy tablle:
    
    AandB_total: number of sequences with both variant A and variant B.
    
    AnotB_total: number of sequences with variant A and not variant B.
    
    BnotA_total: number of sequences with variant B and not variant A.
    
    notAB_total: number of sequences with neither variant.
    """
    combos=pd.read_csv(combo_path,sep="\t")
    combos=combos.drop("Unnamed: 0",axis=1)
    #Must fill N/A value for variants observed in the reference cluster
    combos=combos.fillna(" ")
    
    #If verbose output specified, print total sequences with each variant
    if verbose==True:
        print("-"*45)
        print("Total Sequences with Variant A:",combos[combos["Variants"].apply(lambda x:(var_A in x))]["Cluster_Size"].sum())
        print("Total Sequences with Variant B:",combos[combos["Variants"].apply(lambda x:(var_B in x))]["Cluster_Size"].sum())
        print("-"*45)
    
    #Sequences with variant A and not variant B
    AnotB=combos[combos["Variants"].apply(lambda x:(var_A in x) and (var_B not in x))]
    #Total number of sequences=Sum of cluster sizes listed
    AnotB_total=AnotB["Cluster_Size"].sum()
    if verbose==True:
        print("Number of seuquences with {} and not {}: {}".format(var_A,var_B,AnotB_total))
    
    #Sequences with variant B and not variant A
    BnotA=combos[combos["Variants"].apply(lambda x:(var_A not in x) and (var_B in x))]
    BnotA_total=BnotA["Cluster_Size"].sum()
    if verbose==True:
        print("Number of seuquences with {} and not {}: {}".format(var_B,var_A,BnotA_total))
        
    #Sequences with both variant A and variant B
    AandB=combos[combos["Variants"].apply(lambda x:(var_A in x) and (var_B in x))]
    AandB_total=AandB["Cluster_Size"].sum()
    if verbose==True:
        print("Number of seuquences with {} and {}: {}".format(var_A,var_B,AandB_total))
    
    #Sequences wtih neither variant A nor B
    notAB=combos[combos["Variants"].apply(lambda x:(var_A not in x) and (var_B not in x))]
    notAB_total=notAB["Cluster_Size"].sum()
    if verbose==True:
        print("Number of seuquences with neither {} nor {}: {}".format(var_A,var_B,notAB_total))
        print("Sum of all elements==Total:",(AandB_total+BnotA_total+AnotB_total+notAB_total)==combos["Cluster_Size"].sum())
    
    #Return a Pandas Dataframe with the results, and write to CSV if a path is specifed
    table=pd.DataFrame([[AandB_total,AnotB_total],[BnotA_total,notAB_total]],index=[f"{var_A} present",f"{var_A} absent"],columns=[f"{var_B} present",f"{var_B} absent"])
   
    if outfile:
        table.to_csv(outfile)
    
    return table

"""
Origional_Plotting_Functions #######################################################################################################
"""
def var_uniq_by_domain(df):
    #Print the number of mutations observed for each domain
    #For each domain name, store data for the name and the number of variants observed
    data=[]
    for domain in list(df.Domain.unique()):
        #Store values for domain and number of variants in the domain
        dom=domain
        n_var=len(df[df["Domain"]==domain])
        #Append data for entry as a list, to the list of data
        data.append([dom,n_var])
    #Create a dataframe from the list after iteration
    Vars_by_domain=pd.DataFrame(data,columns=["Domain","Number of Unique Variants"])
    return Vars_by_domain

def long_types(x):
    """
    Converts the following short mutation types to their long form:
    
    sub -> Substitution
    ins -> Insertion
    del -> Deletion
    ext -> Extension
    delins -> Insertion-Deletion
    """
    long_types={'sub':"Substitution",
               'ins':"Insertion",
               'del':"Deletion",
               'ext':"Extension",
               'delins':"Insertion-Deletion"}
    try:
        output=long_types[x]
    #If an error is returned, print a more detailed error message
    except Exception:
        raise ValueError("Data provided does not match the possible mutation types")
    return output

def dates_for_graph(start_dates,end_dates,date_range=True,numeric_month=True,year=None,format_override=None):
    """
    Taking the lists start_dates and end_dates as input, dates_for_graph transforms dates to format used for plotting.
    
    Optional arguments
    -------------
    date_range (default=True): If True, intervals are printed as a range between start and end dates in each category. If False, only the start date is printed.
    
    year (default=None): If none, only the month and day are included in the labels (mm/dd). if "all" the year is included in short format (mm/dd/yy) for all entries. If 'first', the year is given in full format, for the first label and any labels that are the first in a new year.
    
    format_override (default=None): may pass a string using datetime.strftime() format codes to manually specify a format. see https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior for valid codes. This can be set with date_range to show both the start and end dates, or just the start date.
    """
    newdates=[]
    if format_override==None:
        if year==None:
            for i in range(len(start_dates)):
                #Print start and end dates in mm/dd format as a range if date_range==True, and just the start date if date_range==False.
                if date_range==True:
                    if numeric_month==True:
                        newdates.append("{}-{}".format(start_dates[i].strftime("%m/%d"),end_dates[i].strftime("%m/%d")))
                    elif numeric_month==False:
                        newdates.append("{}-{}".format(start_dates[i].strftime("%b %d"),end_dates[i].strftime("%b %d")))
                elif date_range==False:
                    if numeric_month==True:
                        newdates.append("{}".format(start_dates[i].strftime("%m/%d")))
                    elif numeric_month==False:
                        newdates.append("{}".format(start_dates[i].strftime("%b %d")))

        elif year=="first":
            #Find the indeces of time stamps in the input that will be reported with the year (first date printed and first date of every new year)
            #The first element is always given with a year
            give_year_i=[0]
            #Find dates that are the first in a new year, if they exist
            for i in range(len(end_dates)):
                if i==0:
                    #Store the year of the first entry as year_before. 
                    #This is updated with each sample and corresponds to the year of the (i-1)th date. 
                    year_before=int(end_dates[i].strftime("%Y"))
                if i>=1:
                    year=int(end_dates[i].strftime("%Y"))
                    #If the year for the current date is different than the year of the last date, store the index of the year
                    if year!=year_before:
                        give_year_i.append(i)
                    #Update year_before with the year of the current date for comparison with the next date.
                    year_before=year
            #Print date labels with a year for all indicated indeces
            for i in range(len(start_dates)):
                if any(i==index for index in give_year_i):
                    #Print the year before the mm/dd stamp
                    year=end_dates[i].strftime("%Y")
                    if date_range==True:
                        if numeric_month==True:
                            newdates.append("{}: {}-{}".format(year,start_dates[i].strftime("%m/%d"),end_dates[i].strftime("%m/%d")))
                        elif numeric_month==False:
                            newdates.append("{}: {}-{}".format(year,start_dates[i].strftime("%b %d"),end_dates[i].strftime("%b %d")))
                    elif date_range==False:
                        if numeric_month==True:
                            newdates.append("{}: {}".format(year,start_dates[i].strftime("%m/%d")))
                        elif numeric_month==False:
                            newdates.append("{}: {}".format(year,start_dates[i].strftime("%b %d")))
                #Outputs for date ranges that are not on a new year
                else:
                    if date_range==True:
                        if numeric_month==True:
                            newdates.append("{}-{}".format(start_dates[i].strftime("%m/%d"),end_dates[i].strftime("%m/%d")))
                        elif numeric_month==False:
                            newdates.append("{}-{}".format(start_dates[i].strftime("%b %d"),end_dates[i].strftime("%b %d")))
                    elif date_range==False:
                        if numeric_month==True:
                            newdates.append("{}".format(start_dates[i].strftime("%m/%d")))
                        elif numeric_month==False:
                            newdates.append("{}".format(start_dates[i].strftime("%b %d")))
        elif year=="all":
            for i in range(len(start_dates)):
                #Print start and end dates in mm/dd/yy format as a range if date_range==True, and just the start date if date_range==False.
                if date_range==True:
                    if numeric_month==True:
                        newdates.append("{}-{}".format(start_dates[i].strftime("%m/%d/%y"),end_dates[i].strftime("%m/%d/%y")))
                    elif numeric_month==False:
                        newdates.append("{}-{}".format(start_dates[i].strftime("%b %d %y"),end_dates[i].strftime("%b %d %y")))
                else:
                    if numeric_month==True:
                        newdates.append("{}".format(start_dates[i].strftime("%m/%d/%y"),end_dates[i].strftime("%m/%d/%y")))
                    elif numeric_month==False:
                        newdates.append("{}".format(start_dates[i].strftime("%b %d %y"),end_dates[i].strftime("%b %d %y")))
    
    #If manual_override is specified, pass the datetime format string to .strftime.
    elif format_override:
        for i in range(len(start_dates)):
            if date_range==True:
                newdates.append("{}-{}".format(start_dates[i].strftime(format_override),end_dates[i].strftime(format_override)))
            elif date_range==False:
                newdates.append("{}".format(start_dates[i].strftime(format_override)))
    return newdates
    
def var_uniq_by_domain(df):
    """
    Accepts the variant codes dataset and returns a DataFrame giving the number of mutations observed for each domain.
    """
    data=[]
    for domain in list(df.Domain.unique()):
        #Store values for domain and number of variants in the domain
        dom=domain
        n_var=len(df[df["Domain"]==domain])
        #Append data for entry as a list, to the list of data
        data.append([dom,n_var])
    #Create a dataframe from the list after iteration
    Vars_by_domain=pd.DataFrame(data,columns=["Domain","Number of Unique Variants"])
    return Vars_by_domain
    
def plot_n_seq(n_seq_path,graph_dates,color_dict,marker_list,remove_end=0,log=False,output_path=None,figsize=(14,8),x_tick_properties=None,y_tick_properties=None,line_kwargs=None,y_max=None,y_tick_freq=(500,100)):
    """
    Creates a plot for number of sequences by continent and saves it as a .png to the output path, if specified.
    
    Arguments
    ----------
    
    y_max (int): May specify the upper bound of the y-limits using this argument.
    
    y_tick_freq (tuple): The first element of the tuple specifies the frequency of major tick marks with labels, and the second element specifes the frequency of minor tick marks. Default is (500,100).
    """
    ##### Argument Set-up #####
    #Fill default values of x_tick_properties if they are not specified
    x_tick_properties=fill_defaults(x_tick_properties,{'labelsize':10,'rotation':45})
               
    #Check and fill y-axis property kwargs
    y_tick_properties=fill_defaults(y_tick_properties,{'labelsize':12})
    
    #Check for incompatible arguments log=True and user defined y-max
    if y_max and log==True:
        raise ValueError("Cannot specify argument y_max when log=True")
    #####           
       
    #Extract protein name from path: by default, protein name is after the last forward slash and before the first underscore
    protein=n_seq_path.split("/")[-1]
    protein=protein.split("_")[0]
    
    #Load total sequences by continent file
    if remove_end==0:
        n_seq=pd.read_csv(n_seq_path)
    elif remove_end>0:
        n_seq=pd.read_csv(n_seq_path).iloc[:,:-remove_end]
    elif remove_end<0:
        raise ValueError("Negative value specified for remove_end.")
    
    #Rename first column to "Continent" and make it the index
    newcols=list(n_seq.columns)
    newcols[0]="Continent"
    n_seq.columns=newcols
    n_seq.index=n_seq["Continent"]
    #Remove 'continent' column
    n_seq=n_seq.drop("Continent",axis=1)
    #Remove 'worldwide' row
    n_seq=n_seq.drop("Worldwide",axis=0)

    #Sort based on average number of sequences
    n_seq["avg"]=n_seq.mean(axis=1)
    n_seq=n_seq.sort_values(by="avg",ascending=False)
    n_seq=n_seq.drop("avg",axis=1)
    
    #Create line plot of total number of sequences by continent

    #Line Graph for Variant Prevalence Over Time
    x=graph_dates
    labels=list(n_seq.index)

    #Create Figure Frame
    fig=plt.figure(figsize=figsize)
    ax = fig.add_axes([0.1,0.2,0.7,0.7])

    #Create lines for each of the six continents
    for i in range(0,len(n_seq),1):
        line_obj=ax.plot(x,n_seq.iloc[i,:],ls='-',label=labels[i],color=color_dict[labels[i]],marker=marker_list[i%len(marker_list)],**line_kwargs)

    leg=ax.legend(bbox_to_anchor=(1.02,0.9),fontsize=14,loc="upper left",markerscale=2 if line_obj[0].get_markersize()<=6 else 1.5)
    leg.set_title("Continent",prop={'weight':'medium','size':18})
    
    #Set axes limits
    #Y limits: automatically calculate if not defined by the user, and do not calculate for log scale
    if log==False and not y_max:
        #Automatic calculation: if the number of sequences in any given week is greater than 7500, adjust the limits of the plot accordingly.
        max_value=n_seq.max(axis=1).max()
        if (max_value)>7500:
            #Increase the axis to the next 500 increment above the max; increment by another 500 if the max will be close to the new interval.
            if max_value%500>250:
                ymax=((max_value//500)+2)*500
            else:
                ymax=((max_value//500)+1)*500
        else:
            ymax=7500
    elif log==False and y_max:
        ymax=y_max

    elif log==True:
        max_value=n_seq.max(axis=1).max()
        #Automatic Y-axis max calculation for log-10 scale
        #The y-axis max value will be 10^(order_of_magnitude_of_max_value+1)
        order_of_magnitude=(math.log10(max_value))//1
        #for a max value of 5,000, this will be 10,000, for a max value of 20,000, this will be 100,000, and so on.
        ymax=10**(order_of_magnitude+1)

    #If log==False, set y-axis limits with the maximum value defined above. 
    if log==False:
        ax.set_ylim(-20,ymax)
    
    #If log==True, set y-axis limits using a log scale.
    elif log==True:
        #Create a logarithmic scale for the y-axis
        plt.yscale(value="symlog",linthresh=1,subs=[2, 3, 4, 5, 6, 7, 8, 9])
        #Set y axis labels to standard notation (default is scientific with log scales)
        ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0f'))
        #Y-axes limits: set based on max value
        ax.set_ylim(bottom=-0.02,top=ymax)
    
    #X limits: number of columns minus one (zero-index) plus 0.5
    ax.set_xlim(left=-0.5,right=n_seq.shape[1]-0.5)
    
    #X-tick properties (ticks and label placement)
    ax.tick_params(which="major",axis='x',width=1.25,**x_tick_properties)
    #X-tick text properties
    plt.setp(ax.get_xticklabels(), ha="right",rotation_mode="anchor")

    #Y-axis tick/label parameters
    ax.tick_params(which="major",axis='y',width=1.25,**y_tick_properties)
    #plt.setp(ax.get_yticklabels(),**y_tick_properties)

    #Adjust y-axis ticks (only use for linear graphs)
    if log==False:
        ax.set_yticks(np.arange(0,ymax+1,y_tick_freq[0]))
        ax.set_yticks(np.arange(0,ymax+1,y_tick_freq[1]),minor=True);
    
    #Set axes labels
    ax.set_ylabel("Number of Sequences Analyzed",fontsize=12)
    ax.set_xlabel("Collection Date of Sample",fontsize=12)

    #Figure Title
    fig.suptitle("Weekly Number of Sequences Analyzed by Continent: {}".format(protein),fontsize=26,fontweight='medium')

    #Create a grid
    ax.grid(which='major',axis='both',color="#DDDDDD",alpha=0.3)

    if output_path:
        plt.savefig(output_path,dpi=450)

    plt.show()
    
def plot_top_ten(protein,TS_dir,var_code_path,output_directory,start_date,end_date):
    """
    Creates a plot giving the prevalence of the top ten variants for the protein entered across all continents for which time series data exists.
    
    Arguments
    ----------
    protein: name of the protein for which time series data will be plotted (string).
    
    TS_dir: path to the directory where time series percentage data is stored. All files in this directory that contain the protein name will be plotted on a separate plot (ideally there should be one file with the protein name for each continent where output is desired). 
    
    var_code_path: path to the variants by code file for the protein. By default, this file is created by the MSA_reader() in the directory corresponding to the protein name.
    
    output_directory: path to the directory for storing the output plots.
    
    start_date: start date for the analysis. Must be in ISO format, and must be a Sunday for proper plotting.
    
    end_date: end date for the analysis. Must be in ISO format, and must be a Saturday for proper plotting.
    """
    #Search time series percentage directory for all files pertaining to the protein entered
    for file in os.listdir(TS_dir):
        if protein in file:
            #Get continent: assuming the filenames follow defaults, the continent name is after the last underscore and before the period
            continent=file.split(".")[0]
            continent=continent.split("_")[-1]
            #Time series path: add the time series directory before the filename
            TS_path=TS_dir+file
            #Output path for file: if specified graphs will be created in the output directory with the pattern (<Spike>_Top_Ten_<Continent>.png)
            if output_directory:
                output_path=output_directory+protein+"_Top_Ten_"+continent+".png"
            #Function for creating Graph
            top_n_TS_graph(var_code_path,TS_path,protein,continent,start_date,end_date,foutput=output_path if output_directory else None)

def initialize_n_by_continent(n_seq_file):
    """
    Given a file giving the total number of sequences by continent, the function will return a Pandas DataFrame with columns for each week and rows for each continent in the analysis. 
    """
    n_all=pd.read_csv(n_seq_file)
    #Change name of first column to "Continent" and make column the index.
    newcols=list(n_all.columns)
    newcols[0]="Continent"
    n_all.columns=newcols
    n_all.index=n_all["Continent"]
    n_all=n_all.drop("Continent",axis=1)
    return n_all