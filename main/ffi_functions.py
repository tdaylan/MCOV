# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 22:19:31 2020

@author: Lindsey Gordon @lcgordon

All functions for accessing FFI light curves + producing their custom feature vectors

class FFI_lc()

Functions: 
    * eleanor_lc  - pulls data from ra and dec list
    * open_eleanor_lc_files  - opens the saved light curves
    * create_save_featvec_different_timeaxes - produces featvecs and saves them
    * build_simbad_extragalactic_database  - produces text file list of the targets
    * get_radecfromtext
    
Updated: 8/22/2020
"""
import numpy as np
import numpy.ma as ma 
import pandas as pd 
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import (inset_axes, InsetPosition, mark_inset)

from pylab import rcParams
rcParams['figure.figsize'] = 10,10
rcParams["lines.markersize"] = 2
from scipy.signal import argrelextrema


import astropy
import astropy.units as u
from astropy.io import fits
import scipy.signal as signal
from astropy.stats import SigmaClip
from astropy.utils import exceptions
from astroquery import exceptions
from astroquery.exceptions import RemoteServiceError
#from astropy.utils.exceptions import AstropyWarning, RemoteServiceError

from datetime import datetime
import os
import shutil
from scipy.stats import moment, sigmaclip

import sklearn
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import Normalizer
from sklearn import metrics
import fnmatch

from sklearn.metrics import confusion_matrix
from sklearn.neighbors import LocalOutlierFactor

import astroquery
from astroquery.simbad import Simbad
from astroquery.mast import Catalogs
from astroquery.mast import Observations

import eleanor

import pdb
import fnmatch as fm

import plotting_functions as pf
import data_functions as df


def test_ffi():
    """make sure the module loads in"""
    print("FFI functions loaded in.")
    
    
class FFI_lc(object):
    """
    init params:
        * path to save everything into
        * maglimit for max magnitude value to query simbad for
        * tls = False - whether or not you want to produce the tls features 
            which currently do not run in spyder (still ugh)
        
    what it does: 
        - creates folder in path
        - creates simbad database text file of all galaxies with Vmag <=maglimit
        - accesses eleanor light curves from FFI files for those galaxies
        - produces the v0 feature vectors for those light curves and saves into file
        - if tls = True, produces the v1 feature vectors and saves into file
        
    Functions: 
    * eleanor_lc  - pulls data from ra and dec list
    * open_eleanor_lc_files  - opens the saved light curves
    * create_save_featvec_different_timeaxes - produces featvecs and saves them
    * build_simbad_extragalactic_database  - produces text file list of the targets
    * get_radecfromtext - pulls ra and dec from simbad database
        
    modified [lcg 08232020 - fixes]
    """

    def __init__(self, path=None, simbadquery="Vmag <=19", tls=False):

        if maglimit is None:
            print('Please pass a magnitude limit')
            return
        if path is None:
            print('Please pass a path to save into')
            return

        self.simbadquery = simbadquery
        self.path = path + 'ffi_lc_limit{}/'.format(self.maglimit)
        self.catalog = self.path + "simbad_catalog.txt"
        self.lightcurvefilepath = self.path + "eleanor_lightcurves_{}.fits".format(self.simbadquery)
        self.features0path = self.path + "eleanor_features_v0.fits"
        self.features1path = self.path + "eleanor_features_v1.fits"
        
        try:
            os.mkdir(self.path)
            success = 1
        except OSError:
            print('Directory exists already!')
            success = 0

        if success == 1:
            print("Producing RA and DEC list")
            self.build_simbad_extragalactic_database()
            print("Accessing RA and DEC list")
            self.ralist, self.declist = self.get_radecfromtext()
            print("Getting and saving eleanor light curves into a fits file")
            self.radecall = np.column_stack((self.ralist, self.declist))
            self.gaia_ids = self.eleanor_lc()
            print("Producing v0 feature vectors")
            self.gaia_ids, self.times, self.intensities = self.open_eleanor_lc_files()
            self.version = 0
            self.savetrue = True
            self.features = self.create_save_featvec_different_timeaxes()
            if tls:
                print("Producing v1 feature vectors")
                self.version = 1
                self.features = self.create_save_featvec_different_timeaxes()
    
    def build_simbad_extragalactic_database(self):
        '''Object type follows format in:
        http://vizier.u-strasbg.fr/cgi-bin/OType?$1'''
        
        # -- querying object type -------------------------------------------------
        customSimbad = Simbad()
        customSimbad.TIMEOUT = 1000
        # customSimbad.get_votable_fields()
        customSimbad.add_votable_fields('otype')
        customSimbad.add_votable_fields('ra(:;A;ICRS;J2000)', 'dec(:;D;ICRS;2000)')
        table = customSimbad.query_criteria(self.simbadquery, otype='G')
        objects = list(table['MAIN_ID'])
        ras = list(table['RA___A_ICRS_J2000'])
        decs = list(table['DEC___D_ICRS_2000'])
    
        # >> now loop through all of the objects
        for i in range(len(objects)):
            # >> decode bytes object to convert to string
            obj = objects[i].decode('utf-8')
            ra = ras[i]
            dec = decs[i]
           
            with open(self.catalog, 'a') as f:
                    f.write(obj + ',' + ra + ',' + dec + ',' + '\n')
        return
    
    def get_radecfromtext(self):
        ''' pulls ra and dec from text file containing all targets
        '''
        ra_all = []
        dec_all = []
        
        with open(self.catalog, 'r') as f:
            lines = f.readlines()
            for line in lines:
                name, ra, dec, empty = line.split(',')
                    
                ra_all.append(ra)
                dec_all.append(dec)
                    
        return np.asarray(ra_all), np.asarray(dec_all)
    
    def eleanor_lc(self):
        """ 
        retrieves + produces eleanor light curves from FFI files
        """
        import eleanor
        from astropy import units as u
        from astropy.coordinates import SkyCoord
        import warnings
        warnings.filterwarnings('ignore')
        from eleanor.utils import SearchError
        
        download_dir = os.path.join(os.path.expanduser('~'), '.eleanor', 'tesscut')
        print(download_dir)
        
        gaia_ids = []
        
        
        for n in range(len(self.radecall)):
            try:
                coords = SkyCoord(ra=self.radecall[n][0], dec=self.radecall[n][1], unit=(u.deg, u.deg))
                #try:
                files = eleanor.Source(coords=coords, tic=0) #by not providing a sector argument, will ONLY retrieve most recent sector
                print('Found TIC {0} (Gaia {1}), with TESS magnitude {2}, RA {3}, and Dec {4}'
                             .format(files.tic, files.gaia, files.tess_mag, files.coords[0], files.coords[1]))
                data = eleanor.TargetData(files)
                plt.figure(figsize=(16,6))
        
                q = data.quality == 0
                fluxandtime = [data.time[q], data.raw_flux[q]]
                lightcurve = np.asarray(fluxandtime)
                    #print(lightcurve)
                if n == 0: #setting up fits file + save first one            
                    hdr = fits.Header() # >> make the header
                    hdu = fits.PrimaryHDU(lightcurve, header=hdr)
                    hdu.writeto(self.lightcurvefilepath)
                                                
                elif n != 0: #saving the rest
                    fits.append(self.lightcurvefilepath, lightcurve)
                    print(int(n))
                   
                gaia_ids.append(int(files.gaia))
            except (SearchError, ValueError):
                print("Some kind of error - either no TESS image exists, no GAIA ID exists, or there was a connection issue")
            
            #if os.path.isdir(download_dir) == True:
             #   shutil.rmtree(download_dir)
              #  print("All files deleted")
                
        fits.append(self.lightcurvefilepath, np.asarray(gaia_ids))
        print("All light curves saved into fits file")
        return gaia_ids
    
    def open_eleanor_lc_files(self):
        """ opens the fits file that the eleanor light curves are saved into
        parameters:
            * path to the fits file
        returns:
            * list of gaia_ids
            * time indexes
            * intensities
        modified [lcg 08212020]"""
        f = fits.open(self.lightcurvefilepath, memmap=False)
        gaia_ids = f[-1].data
        target_nums = len(f) - 1
        all_timeindexes = []
        all_intensities = []
        for n in range(target_nums):
            all_timeindexes.append(f[n].data[0])
            all_intensities.append(f[n].data[1])
                
        f.close()
            
        return gaia_ids, np.asarray(all_timeindexes), np.asarray(all_intensities)
    
    def create_save_featvec_different_timeaxes(self):
        """Produces the feature vectors for each light curve and saves them all
        into a single fits file. all light curves have their OWN time axis
        this is set up to work on the eleanor light curves
        Parameters:
            * yourpath = folder you want the file saved into
            * times = all time axes
            * intensities = array of all light curves (NOT normalized)
            * sector, camera, ccd = integers 
            * version = what version of feature vector to calculate for all. 
                default is 0
            * save = whether or not to save into a fits file
        returns: list of feature vectors + fits file containing all feature vectors
        requires: featvec()
        modified: [lcg 08212020]"""
        
        feature_list = []
        
        if self.version == 0:
            fname_features = self.features0path
            #median normalize for the v0 features
            for n in range(len(self.intensities)):
                self.intensities[n] = normalize(self.intensities[n], axis=0)
        elif self.version == 1: 
            fname_features = self.features1path
            import transitleastsquares
            from transitleastsquares import transitleastsquares
            #mean normalize the intensity so goes to 1
            for n in range(len(self.intensities)):
                self.intensities[n] = mean_norm(self.intensities[n], axis=0)
    
        print("Begining Feature Vector Creation Now")
        for n in range(len(self.intensities)):
            feature_vector = df.featvec(self.times[n], self.intensities[n], v=self.version)
            feature_list.append(feature_vector)
            
            if n % 25 == 0: print(str(n) + " completed")
        
        feature_list = np.asarray(feature_list)
        
        if self.savetrue:
            hdr = fits.Header()
            hdr["VERSION"] = self.version
            hdu = fits.PrimaryHDU(feature_list, header=hdr)
            hdu.writeto(fname_features)
            fits.append(fname_features, self.gaia_ids)
        else: 
            print("Not saving feature vectors to fits")
        
        return feature_list
    
    def open_eleanor_features(self):
        """ 
        opens all eleanor features in a given folderpath
        returns a single array of ALL features and list of gaia_ids
        """
        filepaths = []
        for root, dirs, files in os.walk(self.path):
            for name in files:
                #print(name)
                if name.startswith(("eleanor_features")):
                        filepaths.append(root + "/" + name)
        print(filepaths)
        f = fits.open(filepaths[0], memmap=False)
        features = f[0].data
        gaia_ids = f[1].data
        f.close()
        for n in range(len(filepaths) - 1):
            f = fits.open(filepaths[n+1], memmap=False)
            features_new = f[0].data
            features = np.column_stack((features, features_new))
            f.close()
        
        return features, gaia_ids

#%%

def eleanor_lc(path, ra_declist, plotting = False):
    """ 
    retrieves + produces eleanor light curves from FFI files
    """
    import eleanor
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    import warnings
    warnings.filterwarnings('ignore')
    from eleanor.utils import SearchError
    
    gaia_ids = []
    filename = path + "eleanor_lightcurves_from_radeclist.fits"
    
    for n in range(len(ra_declist)):
        try:
            coords = SkyCoord(ra=ra_declist[n][0], dec=ra_declist[n][1], unit=(u.deg, u.deg))
            #try:
            files = eleanor.Source(coords=coords, tic=0) #by not providing a sector argument, will ONLY retrieve most recent sector
            print('Found TIC {0} (Gaia {1}), with TESS magnitude {2}, RA {3}, and Dec {4}'
                         .format(files.tic, files.gaia, files.tess_mag, files.coords[0], files.coords[1]))
            data = eleanor.TargetData(files)
            plt.figure(figsize=(16,6))
    
            q = data.quality == 0
            if plotting and n % 20 == 0: 
                    plt.scatter(data.time[q], data.raw_flux[q]/np.nanmedian(data.raw_flux[q])+0.06, c='black', s=0.5)
                    plt.scatter(data.time[q], data.corr_flux[q]/np.nanmedian(data.corr_flux[q]) + 0.03, c='red', s=0.5)
                    plt.ylabel('Normalized Flux')
                    plt.xlabel('Time [BJD - 2457000]')
                    plt.title("(" + str(ra_declist[n][0]) + str(ra_declist[n][1]) + ")")
                    plt.savefig(path + str(n) + 'lightcurveplotted.png')
                    plt.show()
                    plt.close()
                
            fluxandtime = [data.time[q], data.raw_flux[q]]
            lightcurve = np.asarray(fluxandtime)
                #print(lightcurve)
            if n == 0: #setting up fits file + save first one            
                hdr = fits.Header() # >> make the header
                hdu = fits.PrimaryHDU(lightcurve, header=hdr)
                hdu.writeto(filename)
                                            
            elif n != 0: #saving the rest
                fits.append(filename, lightcurve)
                print(int(n))
               
            gaia_ids.append(int(files.gaia))
        except (SearchError, ValueError):
            print("Some kind of error - either no TESS image exists, no GAIA ID exists, or there was a connection issue")
        
        if os.path.isdir("/Users/conta/.eleanor/tesscut") == True:
            shutil.rmtree("/Users/conta/.eleanor/tesscut")
            print("All files deleted")
    fits.append(filename, np.asarray(gaia_ids))
    print("All light curves saved into fits file")
    return gaia_ids

def open_eleanor_features(folderpath):
    """ 
    opens all eleanor features in a given folderpath
    returns a single array of ALL features and list of gaia_ids
    """
    filepaths = []
    for root, dirs, files in os.walk(folderpath):
        for name in files:
            #print(name)
            if name.startswith(("eleanor_features")):
                    filepaths.append(root + "/" + name)
    print(filepaths)
    f = fits.open(filepaths[0], memmap=False)
    features = f[0].data
    gaia_ids = f[1].data
    f.close()
    for n in range(len(filepaths) - 1):
        f = fits.open(filepaths[n+1], memmap=False)
        features_new = f[0].data
        features = np.column_stack((features, features_new))
        f.close()
    
    return features, gaia_ids

def open_eleanor_lc_files(path):
    """ opens the fits file that the eleanor light curves are saved into
    parameters:
        * path to the fits file
    returns:
        * list of gaia_ids
        * time indexes
        * intensities
    modified [lcg 08212020]"""
    f = fits.open(path, memmap=False)
    gaia_ids = f[-1].data
    target_nums = len(f) - 1
    all_timeindexes = []
    all_intensities = []
    for n in range(target_nums):
        all_timeindexes.append(f[n].data[0])
        all_intensities.append(f[n].data[1])
        
    f.close()
    
    return gaia_ids, np.asarray(all_timeindexes), np.asarray(all_intensities)

def create_save_featvec_different_timeaxes(yourpath, times, intensities, gaia_ids, filelabel, version=0, save=True):
    """Produces the feature vectors for each light curve and saves them all
    into a single fits file. all light curves have their OWN time axis
    this is set up to work on the eleanor light curves
    Parameters:
        * yourpath = folder you want the file saved into
        * times = all time axes
        * intensities = array of all light curves (NOT normalized)
        * sector, camera, ccd = integers 
        * version = what version of feature vector to calculate for all. 
            default is 0
        * save = whether or not to save into a fits file
    returns: list of feature vectors + fits file containing all feature vectors
    requires: featvec()
    modified: [lcg 08212020]"""
    

    fname_features = yourpath + "/"+ filelabel + "_features_v"+str(version)+".fits"
    feature_list = []
    
    if version == 0:
	#median normalize for the v0 features
        for n in range(len(intensities)):
            intensities[n] = normalize(intensities[n], axis=0)
    elif version == 1: 
        import transitleastsquares
        from transitleastsquares import transitleastsquares
        #mean normalize the intensity so goes to 1
        for n in range(len(intensities)):
            intensities[n] = mean_norm(intensities[n], axis=0)

    print("Begining Feature Vector Creation Now")
    for n in range(len(intensities)):
        feature_vector = df.featvec(times[n], intensities[n], v=version)
        feature_list.append(feature_vector)
        
        if n % 25 == 0: print(str(n) + " completed")
    
    feature_list = np.asarray(feature_list)
    
    if save == True:
        hdr = fits.Header()
        hdr["VERSION"] = version
        hdu = fits.PrimaryHDU(feature_list, header=hdr)
        hdu.writeto(fname_features)
        fits.append(fname_features, gaia_ids)
    else: 
        print("Not saving feature vectors to fits")
    
    return feature_list

def build_simbad_extragalactic_database(maglim, out='./simbad_v19galaxies.txt'):
    '''Object type follows format in:
    http://vizier.u-strasbg.fr/cgi-bin/OType?$1'''
    
    # -- querying object type -------------------------------------------------
    customSimbad = Simbad()
    customSimbad.TIMEOUT = 1000
    # customSimbad.get_votable_fields()
    customSimbad.add_votable_fields('otype')
    customSimbad.add_votable_fields('ra(:;A;ICRS;J2000)', 'dec(:;D;ICRS;2000)')
    table = customSimbad.query_criteria('Vmag <=' + str(maglim), otype='G')
    objects = list(table['MAIN_ID'])
    ras = list(table['RA___A_ICRS_J2000'])
    decs = list(table['DEC___D_ICRS_2000'])

    # >> now loop through all of the objects
    for i in range(len(objects)):
        # >> decode bytes object to convert to string
        obj = objects[i].decode('utf-8')
        ra = ras[i]
        dec = decs[i]
       
        with open(out, 'a') as f:
                f.write(obj + ',' + ra + ',' + dec + ',' + '\n')
                
def get_radecfromtext(directory):
    ''' pulls ra and dec from text file containing all targets
    '''
    ra_all = []
    dec_all = []
    
    # >> find all text files in directory
    fnames = fm.filter(os.listdir(directory), '*.txt')
    
    for fname in fnames:
        # >> read text file
        with open(directory + fname, 'r') as f:
            lines = f.readlines()
            for line in lines:
                name, ra, dec, empty = line.split(',')
                
                ra_all.append(ra)
                dec_all.append(dec)
                
    return np.asarray(ra_all), np.asarray(dec_all)




def clip_feature_outliers(path, features, time, flux, gaia_ids, sigma, version=0, plot=True):
    """ isolate features that are significantly out there and crazy
    plot those outliers, and remove them from the features going into the 
    main lof/plotting/
    also removes any TLS features which returned only nans
    parameters: 
        *path to save shit into
        * features (all)
        * time axis (1) (ALREADY PROCESSED)
        * flux (all) (must ALREADY BE PROCESSED)
        * ticids (all)
        
    returns: features_cropped, ticids_cropped, flux_cropped, outlier_indexes 
    modified [lcg 07272020 - changed plotting size issue]"""
    path = path + "clipped-feature-outliers/"
    try:
        os.makedirs(path)
    except OSError:
        print ("Creation of the directory %s failed" % path)
    else:
        print ("Successfully created the directory %s" % path)
    
    #rcParams['figure.figsize'] = 8,3
    if version==0:
        features_greek = [r'$\alpha$', 'B', r'$\Gamma$', r'$\Delta$', r'$\beta$', r'$\gamma$',r'$\delta$',
                  "E", r'$\epsilon$', "Z", "H", r'$\eta$', r'$\Theta$', "I", "K", r'$\Lambda$', "M", r'$\mu$'
                  ,"N", r'$\nu$']
    elif version==1: 
        features_greek = ["M", r'$\mu$',"N", r'$\nu$']

    outlier_indexes = []
    for i in range(len(features[0])):
        column = features[:,i]
        column_std = np.std(column)
        column_top = np.mean(column) + column_std * sigma
        column_bottom = np.mean(column) - (column_std * sigma)
        for n in range(len(column)):
            #find and note the position of any outliers
            if column[n] < column_bottom or column[n] > column_top or np.isnan(column[n]) ==True: 
                outlier_indexes.append((int(n), int(i)))
                
    print(np.asarray(outlier_indexes))
        
    outlier_indexes = np.asarray(outlier_indexes)
    
    if plot:
        for i in range(len(outlier_indexes)):
            target_index = outlier_indexes[i][0] #is the index of the target on the lists
            feature_index = outlier_indexes[i][1] #is the index of the feature that it triggered on
            plt.figure(figsize=(8,3))
            plt.scatter(time[target_index], flux[target_index], s=0.5)
            target = gaia_ids[target_index]
            #print(features[target_index])
            
            if np.isnan(features[target_index][feature_index]) == True:
                feature_title = features_greek[feature_index] + "=nan"
            else: 
                feature_value = '%s' % float('%.2g' % features[target_index][feature_index])
                feature_title = features_greek[feature_index] + "=" + feature_value
            print(feature_title)
            
            plt.title("GAIA_ID " + str(int(target)) + " ", fontsize=8)
            plt.tight_layout()
            plt.savefig((path + "featureoutlier-TICID" + str(int(target)) + ".png"))
            plt.show()
    else: 
        print("not plotting today!")
            
        
    features_cropped = np.delete(features, outlier_indexes, axis=0)
    gaia_ids_cropped = np.delete(gaia_ids, outlier_indexes)
    flux_cropped = np.delete(flux, outlier_indexes, axis=0)
    time_cropped = np.delete(time, outlier_indexes, axis=0)
        
    return features_cropped, gaia_ids_cropped, flux_cropped, time_cropped, outlier_indexes

def plot_lof_FFI(time, intensity, targets, features, n, path,
             momentum_dump_csv = '../../Table_of_momentum_dumps.csv',
             n_neighbors=20, target_info=False,
             prefix='', mock_data=False, addend=1., feature_vector=False,
             n_tot=100, log=False):
    """ Plots the 20 most and least interesting light curves based on LOF.
    Parameters:
        * time : array with shape 
        * intensity
        * targets : list of TICIDs
        * n : number of curves to plot in each figure
        * path : output directory
        * n_tot : total number of light curves to plots (number of figures =
                  n_tot / n)
        * feature vector : assumes x axis is latent dimensions, not time  
        * mock_data : if True, will not plot TICID label
        * target_input : [sector, camera, ccd]
    Outputs:
        * Text file with TICID in column 1, and LOF in column 2 (lof-*.txt)
        * Log histogram of LOF (lof-histogram.png)
        * Top 20 light curves with highest and lowest LOF
        * Random 20 light curves
    modified [lcg 07012020 - includes inset histogram plotting]
    """
    # -- calculate LOF -------------------------------------------------------
    print('Calculating LOF')
    clf = LocalOutlierFactor(n_neighbors=n_neighbors)
    fit_predictor = clf.fit_predict(features)
    negative_factor = clf.negative_outlier_factor_
    
    lof = -1 * negative_factor
    ranked = np.argsort(lof)
    largest_indices = ranked[::-1][:n_tot] # >> outliers
    smallest_indices = ranked[:n_tot] # >> inliers
    
    # >> save LOF values in txt file
    print('Saving LOF values')
    with open(path+'lof-'+prefix+'.txt', 'w') as f:
        for i in range(len(targets)):
            f.write('{} {}\n'.format(int(targets[i]), lof[i]))
      
    # >> make histogram of LOF values
    print('Make LOF histogram')
    #plot_histogram(lof, 20, "Local Outlier Factor (LOF)", time, intensity,
     #              targets, path+'lof-'+prefix+'histogram-insets.png',
      #             insets=True, log=log)
    pf.plot_histogram(lof, 20, "Local Outlier Factor (LOF)", time, intensity,
                   targets, path+'lof-'+prefix+'histogram.png', insets=False,
                   log=log)

    # -- plot smallest and largest LOF light curves --------------------------
    print('Plot highest LOF and lowest LOF light curves')
    num_figs = int(n_tot/n) # >> number of figures to generate
    
    for j in range(num_figs):
        
        for i in range(2): # >> loop through smallest and largest LOF plots
            fig, ax = plt.subplots(n, 1, sharex=False, figsize = (8, 3*n))
            
            for k in range(n): # >> loop through each row
                if i == 0: ind = largest_indices[j*n + k]
                elif i == 1: ind = smallest_indices[j*n + k]\
                
                # >> plot momentum dumps
                with open(momentum_dump_csv, 'r') as f:
                    lines = f.readlines()
                    mom_dumps = [ float(line.split()[3][:-1]) for line in lines[6:] ]
                    inds = np.nonzero((mom_dumps >= np.min(time[ind])) * \
                                      (mom_dumps <= np.max(time[ind])))
                    mom_dumps = np.array(mom_dumps)[inds]
                for t in mom_dumps:
                    ax[k].axvline(t, color='g', linestyle='--')
                    
                # >> plot light curve
                ax[k].plot(time[ind], intensity[ind] + addend, '.k')
                ax[k].text(0.98, 0.02, '%.3g'%lof[ind],
                           transform=ax[k].transAxes,
                           horizontalalignment='right',
                           verticalalignment='bottom',
                           fontsize='xx-small')
                pf.format_axes(ax[k], ylabel=True)
                ax[k].set_title("GAIA ID " + str(targets[ind]))
                
    
            # >> label axes
            ax[n-1].set_xlabel('time [BJD - 2457000]')
                
            # >> save figures
            if i == 0:
                
                fig.suptitle(str(n) + ' largest LOF targets', fontsize=16,
                             y=0.9)
                fig.savefig(path + 'lof-' + prefix + 'kneigh' + \
                            str(n_neighbors) + '-largest_' + str(j*n) + 'to' +\
                            str(j*n + n) + '.png',
                            bbox_inches='tight')
                plt.close(fig)
            elif i == 1:
                fig.suptitle(str(n) + ' smallest LOF targets', fontsize=16,
                             y=0.9)
                fig.savefig(path + 'lof-' + prefix + 'kneigh' + \
                            str(n_neighbors) + '-smallest' + str(j*n) + 'to' +\
                            str(j*n + n) + '.png',
                            bbox_inches='tight')
                plt.close(fig)

def features_plotting_FFI(feature_vectors, path, clustering,
                         time, intensity, targets, folder_suffix='',
                         feature_engineering=True, version=0, eps=0.5, min_samples=10,
                         metric='euclidean', algorithm='auto', leaf_size=30,
                         p=2, target_info=False, kmeans_clusters=4,
                         momentum_dump_csv='./Table_of_momentum_dumps.csv'):
    """plotting (n 2) features against each other
    parameters: 
        * feature_vectors - array of feature vectors
        * path to where you want everythigns aved - ends in a backslash
        * clustering - what you want to cluster as. options are 'dbscan', 'kmeans', or 
        any other keyword which will do no clustering
        * time axis
        * intensities
        *target ticids
        * folder suffix
        *feature_engineering - default is true
        * version - what version of engineered features, irrelevant integer if feature_engienering is false
        * eps, min_samples, metric, algorithm, leaf_size, p - dbscan parameters, comes with defaults
        * target_info - default is false
        *momentum dumps - not sure entirely why it's needed here tbh
        
    returns: only returns labels for dbscan/kmeans clustering. otherwise the only
    output is the files saved into the folder as given thru path
    """
    #detrmine which of the clustering algoirthms you're using: 
    rcParams['figure.figsize'] = 10,10
    folder_label = "blank"
    if clustering == 'dbscan':
        # !! TODO parameter optimization (eps, min_samples)
        db = DBSCAN(eps=eps, min_samples=min_samples, metric=metric,
                    algorithm=algorithm, leaf_size=leaf_size,
                    p=p).fit(feature_vectors) #eps is NOT epochs
        classes_dbscan = db.labels_
        numclasses = str(len(set(classes_dbscan)))
        folder_label = "dbscan-colored"

    elif clustering == 'kmeans': 
        Kmean = KMeans(n_clusters=kmeans_clusters, max_iter=700, n_init = 20)
        x = Kmean.fit(feature_vectors)
        classes_kmeans = x.labels_
        folder_label = "kmeans-colored"
    else: 
        print("no clustering chosen")
        folder_label = "2DFeatures"
        
    #makes folder and saves to it    
    folder_path = path + folder_label
    try:
        os.makedirs(folder_path)
    except OSError:
        print ("Creation of the directory %s failed" % folder_path)
        print("New folder created will have -new at the end. Please rename.")
        folder_path = folder_path + "-new"
        os.makedirs(folder_path)
    else:
        print ("Successfully created the directory %s" % folder_path) 
 
    if clustering == 'dbscan':
        plot_classification_FFI(time, intensity, targets, db.labels_,
                            folder_path+'/', prefix='dbscan',
                            momentum_dump_csv=momentum_dump_csv,
                            target_info=target_info)
        pf.plot_pca(feature_vectors, db.labels_,
                    output_dir=folder_path+'/')
    elif clustering == 'kmeans':
        plot_classification_FFI(time, intensity, targets, x.labels_,
                            path+folder_label+'/', prefix='kmeans',
                            momentum_dump_csv=momentum_dump_csv,
                            target_info=target_info)
 
    colors = pf.get_colors()
    #creates labels based on if engineered features or not
    if feature_engineering:
        if version==0:
            graph_labels = ["Average", "Variance", "Skewness", "Kurtosis", "Log Variance",
                            "Log Skewness", "Log Kurtosis", "Maximum Power", "Log Maximum Power", 
                            "Period of Maximum Power (0.1 to 10 days)","Slope" , "Log Slope",
                            "P0", "P1", "P2", "Period of Maximum Power (0.001 to 0.1 days)"]
            fname_labels = ["Avg", "Var", "Skew", "Kurt", "LogVar", "LogSkew", "LogKurt",
                            "MaxPower", "LogMaxPower", "Period0_1to10", "Slope", "LogSlope",
                            "P0", "P1", "P2", "Period0to0_1"]
        elif version == 1: 
            
            graph_labels = ["TLS Best fit Period (days)", "TLS Best fit duration (days)", "TLS best fit depth (ppt from transit bottom",
                            "TLS Best fit Power"]
            fname_labels = ["TLSPeriod", "TLSDuration", "TLSDepth", "TLSPower"]
        elif version == 2:
            graph_labels = ["Average", "Variance", "Skewness", "Kurtosis", "Log Variance",
                            "Log Skewness", "Log Kurtosis", "Maximum Power", "Log Maximum Power", 
                            "Period of Maximum Power (0.1 to 10 days)","Slope" , "Log Slope",
                            "P0", "P1", "P2", "Period of Maximum Power (0.001 to 0.1 days)", "TLS Best fit Period (days)", "TLS Best fit duration (days)", "TLS best fit depth (ppt from transit bottom",
                            "TLS Best fit Power"]
            fname_labels = ["Avg", "Var", "Skew", "Kurt", "LogVar", "LogSkew", "LogKurt",
                            "MaxPower", "LogMaxPower", "Period0_1to10", "Slope", "LogSlope",
                            "P0", "P1", "P2", "Period0to0_1", "TLSPeriod", "TLSDuration", "TLSDepth", "TLSPower"]
            
        num_features = len(feature_vectors[0])
    else:
        # >> shape(feature_vectors) = [num_samples, num_features]
        num_features = np.shape(feature_vectors)[1]
        graph_labels = []
        fname_labels = []
        for n in range(num_features):
            graph_labels.append('\u03C6' + str(n))
            fname_labels.append('phi'+str(n))
    for n in range(num_features):
        feat1 = feature_vectors[:,n]
        graph_label1 = graph_labels[n]
        fname_label1 = fname_labels[n]
        for m in range(num_features):
            if m == n:
                continue
            graph_label2 = graph_labels[m]
            fname_label2 = fname_labels[m]                
            feat2 = feature_vectors[:,m]
 
            if clustering == 'dbscan':
                plt.figure() # >> [etc 060520]
                plt.clf()
                for n in range(len(feature_vectors)):
                    plt.scatter(feat1[n], feat2[n], c=colors[classes_dbscan[n]], s=2)
                plt.xlabel(graph_label1)
                plt.ylabel(graph_label2)
                plt.savefig((folder_path+'/' + fname_label1 + "-vs-" + fname_label2 + "-dbscan.png"))
                plt.show()
                plt.close()
                 
            elif clustering == 'kmeans':
                plt.figure() # >> [etc 060520]
                plt.clf()
                for n in range(len(feature_vectors)):
                    plt.scatter(feat1[n], feat2[n], c=colors[classes_kmeans[n]], s=2)
                plt.xlabel(graph_label1)
                plt.ylabel(graph_label2)
                plt.savefig(folder_path+'/' + fname_label1 + "-vs-" + fname_label2 + "-kmeans.png")
                plt.show()
                plt.close()
            elif clustering == 'none':
                plt.scatter(feat1, feat2, s = 2, color = 'black')
                plt.xlabel(graph_label1)
                plt.ylabel(graph_label2)
                plt.savefig(folder_path+'/' + fname_label1 + "-vs-" + fname_label2 + ".png")
                plt.show()
                plt.close()
                
    if clustering == 'dbscan':
        np.savetxt(folder_path+"/dbscan-classes.txt", classes_dbscan)
        return classes_dbscan
    if clustering == 'kmeans':
        return classes_kmeans
    
    
def plot_classification_FFI(time, intensity, targets, labels, path,
                        momentum_dump_csv = './Table_of_momentum_dumps.csv',
                        n=20, target_info=False,
                        prefix='', mock_data=False, addend=1.,
                        feature_vector=False):
    """ 
    """

    classes, counts = np.unique(labels, return_counts=True)
    # !!
    colors=['red', 'blue', 'green', 'purple', 'yellow', 'cyan', 'magenta',
            'skyblue', 'sienna', 'palegreen']*10
    
    # >> get momentum dump times
    
        
    for i in range(len(classes)): # >> loop through each class
        fig, ax = plt.subplots(n, 1, sharex=False, figsize = (8, 3*n))
        class_inds = np.nonzero(labels == classes[i])[0]
        if classes[i] == -1:
            color = 'black'
        elif classes[i] < len(colors) - 1:
            color = colors[i]
        else:
            color='black'
        
        for k in range(min(n, counts[i])): # >> loop through each row
            ind = class_inds[k]
            
            
            with open(momentum_dump_csv, 'r') as f:
                lines = f.readlines()
                mom_dumps = [ float(line.split()[3][:-1]) for line in lines[6:] ]
                inds = np.nonzero((mom_dumps >= np.min(time[ind])) * \
                                  (mom_dumps <= np.max(time[ind])))
                mom_dumps = np.array(mom_dumps)[inds]
            # >> plot momentum dumps
            for t in mom_dumps:
                ax[k].plot([t,t], [0, 1], '--g', alpha=0.5,
                           transform=ax[k].transAxes)            
            
            # >> plot light curve
            ax[k].plot(time[ind], intensity[ind] + addend, '.k')
            ax[k].text(0.98, 0.02, str(labels[ind]), transform=ax[k].transAxes,
                       horizontalalignment='right', verticalalignment='bottom',
                       fontsize='xx-small')
            pf.format_axes(ax[k], ylabel=True)
            ax[k].set_title("GAIA ID " + str(targets[ind]))

        if feature_vector:
            ax[n-1].set_xlabel('\u03C8')
        else:
            ax[n-1].set_xlabel('time [BJD - 2457000]')
    
        if classes[i] == -1:
            fig.suptitle('Class -1 (outliers)', fontsize=16, y=0.9,
                         color=color)
        else:
            fig.suptitle('Class ' + str(classes[i]), fontsize=16, y=0.9,
                         color=color)
        fig.savefig(path + prefix + '-class' + str(classes[i]) + '.png',
                    bbox_inches='tight')
        plt.close(fig)