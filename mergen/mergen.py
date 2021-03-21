# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 20:27:13 2020

mergen.py
@author: LG and EC

To Do List:
    - fill in remaining functions
    - Set up pipeline function (kind of a run-all thing)
"""

from init import *
import data_utils as dt
import catalog_utils as ct
import learning_utils as lt
import plot_utils as pt
import feature_utils as ft

#mg = mergen()
#mg.folder_initiate()
#mg.intensities

class mergen(object):
    """ Main mergen class. Initialize this to work with everything else conveniently. """
    def __init__(self, datapath, savepath, datatype, momentum_dump_csv, filelabel = None):
        """Creates mergen object from which most common routines can easily be run
        Parameters:
            * datapath: string, where any data is being stored
            * savepath: string, where the subfolders should be saved into
            * datatype: string, indicates type of data being worked with. options are: 
                "SPOC", "FFI-Lygos", "FFI-QLP", "FFI-eleanor"
            * momentum_dump_csv: string, path to csv containing TESS momentum dumps (local)
            * filelabel: string, if you want to have all plots/files/folders labelled specially
        
        """
        self.datapath = datapath
        self.savepath = savepath
        self.datatype = datatype #SPOC or FFI
        self.mdumpcsv = momentum_dump_csv
        if filelabel is not None:
            self.filelabel = filelabel
        else:
            self.filelabel = "mergen"
        
        self.folder_initiate()
    
    def folder_initiate(self):
        """Makes all the big folders"""
        print("Setting up CAE folder")
        self.CAEpath = self.savepath + "CAE/"
        try:
            os.makedirs(self.CAEpath)
        except OSError:
            print ("Directory %s already exists" % self.CAEpath)
            
        print("Setting up ENF folder")
        self.ENFpath = self.savepath + "ENF/"
        try:
            os.makedirs(self.ENFpath)
        except OSError:
            print ("Directory %s already exists" % self.ENFpath)
        return
    
    def load_lightcurves_local(self):
        """Loads in data saved in metafiles on datapath"""
        #check for self.datatype to determine loading scheme. 
        #figure out consistent stuff for FFI original locations
        if self.datatype == "FFI-Lygos":
            self.times, self.intensities, self.errors, self.identifiers = dt.load_all_lygos(self.datapath)
        elif self.datatype == "SPOC":
            #whatever this is
            k = 0
        
        
            
    def download_and_load_lightcurves(self):
        """ ??? this is just the other option for if you want to run batch downloads and then make metafiles"""
        #YYY EMMA FILL THIS IN
        return

    def data_clean(self):
        """ Cleans data up - just BASE cleanup of normalizing + sigma clipping. CAE additional cleans done later"""
        self.intensities = dt.normalize(self.intensities)
        #is there anything else to be done??
        return
    
    def load_existing_features(self, typeFeatures):
        """ Load in feature metafiles stored in the datapath"""
        if typeFeatures == "ENF":
            self.features = dt.load_ENF_feature_metafile(self.ENFpath)
        elif typeFeatures == "CAE":
            ### EMMA FILL THIS IN
            k = 6
        return
    
    def generate_engineered(self, version = 0, save = True):
        """Run engineered feature creation"""
        self.features = ft.create_save_featvec_homogenous_time(self.ENFpath, self.times, self.intensities, 
                                                               self.filelabel, version=version, save=save):
    
        return
    
    def generate_CAE(self):
        """Run CAE feature creation """
        #EMMA FILL THIS IN
        return
    
    def run_all(self):
        return
