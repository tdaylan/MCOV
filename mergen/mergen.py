"""
Created on Thu Oct  8 20:27:13 2020

mergen.py
@authors: Lindsey Gordon (@lgordon), Emma Chickles (@emmachickles), Tansu Daylan
          (@tdaylan)

The "Mergen" pipeline performs unsupervised classification and outlier detection
using TESS light curves. To do this, we use convolutional autoencoders and 
feature engineering to produce low-dimensional representations of light curves.
Note that we're undergoing some major restructuring, so documentation is
currently spotty!

The Mergen methods are organized into five main sections:
1) Initialization
2) Data and Preprocessing
3) Feature Generation
4) Clustering and Outlier Analysis
5) Loading Mergen Products

To Do List:
* Set up pipeline function (kind of a run-all thing)
* Include example script?
* Include option to process multiple sector
"""

from .__init__ import *
from . import data_utils    as dt
from . import catalog_utils as ct
from . import learn_utils   as lt
from . import plot_utils    as pt
from . import feature_utils as ft

class mergen(object):
    """ Main mergen class. Initialize this to work with everything else
    conveniently. """

    # ==========================================================================
    # == Initialization ========================================================
    # ==========================================================================

    def __init__(self, datapath, savepath, datatype, sector=None,
                 featgen=None,  metapath=None, timescale=None,
                 mdumpcsv=None, filelabel=None, runiter=False, numiter=1,
                 numclstr=None, parampath=None, clstrmeth=None):
        """Creates mergen object from which most common routines can easily be
        run
        Parameters:
            * datapath: string, directory data is stored in
            * savepath: string, directory produces will be saved
            * datatype: string, indicates type of data being worked with.
                        options are: 
                        "SPOC", "FFI-Lygos", "FFI-QLP", "FFI-eleanor"
            * sector  : list of ints, TESS Observation Sector numbers
            
            * featgen : string, feature generation methods (ENF, CAE, DAE, VAE)
              * ENF : engineered features
              * CAE : features extracted from time-series data using a 
                      convolutional autoencoder
              * DAE : features extracted from LS-periodograms using a deep
                      autoencoder
              * VAE : features extracted from a variational autoencoder
            
            * mdumpcsv : string, path to csv file containing TESS momentum dumps
            * filelabel : string, if you want to have all plots/files/folders
                          labelled specially        
            * sector  : int, TESS Observational Sector number (1,2,...,26,...)
            * runiter : bool, if True, runs iterative CAE scheme
            * numiter : int, number of iterations in the iterative CAE scheme
            * numclstr : int, number of clusters assumed by the GMM clustering
                         algorithm
            * parampath : string, path to txt file containing autoencoder
                        parameters
        """
        
        self.featgen = featgen
        
        self.sector   = sector
        self.numclstr = numclstr
        self.clstrmeth = clstrmeth

        self.datapath = datapath
        self.savepath = savepath
        self.metapath = metapath
        self.datatype = datatype # >> SPOC or FFI
        # self.ensbpath = self.savepath+'Ensemble-Sector_'+str(self.sector)+'/'
        self.ensbpath = self.savepath # !!
        self.mdumpcsv = mdumpcsv

        if filelabel is not None:
            self.filelabel = filelabel
        else:
            self.filelabel = "mergen"

        if parampath is not None:
            self.parampath = parampath
        else:
            self.parampath = savepath + 'caehyperparams.txt'

        # >> iterative scheme
        self.runiter = runiter
        self.numiter = numiter
        self.batch_fnames = None
        
        self.initiate_folder()

    def initiate_folder(self):
        """Create directories for each of the desired feature generation
        methods."""
        if type(self.featgen) != type(None):
            self.featpath = self.savepath+self.featgen+"/"
        dt.create_dir(self.featpath)

    def initiate_meta(self):
        dt.init_meta_folder(self.metapath)

    def run(self):
        # >> load data
        self.load_lightcurves_local()
        
        # >> preprocessing and feature generation
        if self.featgen == "DAE":
            self.data_preprocess("DAE")
            self.generate_dae_features()
            self.run_feature_analysis("DAE")
            self.run_vis("DAE")
        if self.featgen == "CAE":
            self.data_preprocess("CAE")
            self.generate_cae_features()   
            self.run_feature_analysis("CAE")
            self.run_vis("CAE")
        if self.featgen == "ENF":
            self.data_preprocess("ENF")
            self.generate_engineered()
            self.run_feature_analysis("ENF")
            self.run_vis("ENF")
            
    def run_pretrained(self):
        """Skips feature extraction and loads saved extracted features."""
        self.load_lightcurves_local()        
        self.load(self.featgen)
        self.run_vis(self.featgen)

    # ==========================================================================
    # == Data and Preprocessing ================================================
    # ==========================================================================

    def load_lightcurves_local(self, lcdir, sector):
        """Load in data saved in metafiles on datapath"""
        #check for self.datatype to determine loading scheme. 
        #figure out consistent stuff for FFI original locations
        if self.datatype == "FFI-Lygos":
            self.time, self.flux, self.errors, self.objid = \
            dt.load_all_lygos(self.datapath)
        elif self.datatype == "SPOC":
            # self.flux, self.time, self.objid, self.target_info = \
            # dt.load_data_from_metafiles(self.datapath, self.sector)

            self.flux, self.time, self.meta = \
                    dt.load_data_from_metafiles(lcdir, sector)
        
    def download_lightcurves(self):
        """Downloads and process light SPOC light curves, if not already
        downloaded."""
        dt.bulk_download_lc(self.datapath, sector=self.sector)

    def clean_data(self):
        """Masks out data points with nonzero QUALITY flags."""
        dt.qual_mask(self)

    def preprocess_data(self):
        if self.featgen == "ENF":
            self.flux = dt.normalize(self.flux)
        if self.featgen == "CAE": # >> returns training and testing sets
            self.x_train, self.x_test = \
            lt.autoencoder_preprocessing(self.flux, self.time, self.parampath,
                                         ticid=self.objid,
                                         data_dir=self.datapath,
                                         output_dir=self.featpath)
        if self.featgen == "DAE": # !!
            self.x_train, self.flux, self.objid, self.target_info, self.freq, self.time=\
            lt.DAE_preprocessing(self.flux, self.time, self.parampath,
                                 self.objid, self.target_info,
                                 data_dir=self.datapath, sector=self.sector,
                                 output_dir=self.featpath)

    
    # ==========================================================================
    # == Feature Generation ====================================================
    # ==========================================================================

    def generate_features(self):
        dt.create_dir(self.featpath+'model/')
        if self.featgen == "ENF":
            self.generate_engineered()
        elif self.featgen == "DAE":
            self.generate_dae_features()
        elif self.featgen == "CAE":
            self.generate_cae_features()

    def generate_engineered(self, version = 0, save = True):
        """ Run engineered feature creation"""
        self.feats = ft.create_save_featvec_homogenous_time(self.ENFpath,
                                                            self.time, 
                                                            self.flux,
                                                            self.filelabel,
                                                            version=version,
                                                            save=save)

    def generate_dae_features(self):
        """Trains deep autoencoder to extract representative features from

        periodograms."""
        self.model, self.hist, self.feats = \
        lt.deep_autoencoder(self.x_train, self.x_train,
                            parampath=self.parampath,
                            ticid_train=self.objid,
                            output_dir=self.featpath+'model/',
                            batch_fnames=self.batch_fnames)
        

    def generate_cae_features(self):
        """Train convolutional autoencoder to extract representative
        features from lightcurves.
        Returns: 
            *
 model : Keras Model object
            * hist : Keras history dictionary
            * feats : CAE-derived features
            * rcon : reconstructions of the input light curves"""        
        self.model, self.hist, self.feats, self.feats_test, self.rcon_test, \
        self.rcon = lt.conv_autoencoder(x_train=self.x_train,
                                        y_train=self.x_train, 
                                        params=self.parampath,
                                        output_dir=self.featpath+'model/',

                                        ticid_train=self.objid,
                                        batch_fnames=self.batch_fnames)
        # lt.conv_autoencoder(x_train=self.x_train, y_train=self.x_train, 
        #                                 params=self.parampath,
        #                                 output_dir=self.savepath,
        #                                 ticid_train=self.objid)
    def produce_ae_visualizations(self):
        if self.featgen == "DAE":
            pt.produce_ae_visualizations(self.freq[0], self.x_train, self.rcon,
                                         self.featpath, self.objid,
                                         self.target_info,
                                         psd=True)

        if self.featgen == "CAE":
            pt.produce_ae_visualizations(self.time, self.x_train, self.rcon,
                                         self.featpath, self.objid,
                                         self.target_info,
                                         psd=False)

    # ==========================================================================
    # == Clustering and Outlier Analysis =======================================
    # ==========================================================================
    
    # >> featgen : feature generation method, e.g. 'CAE', 'DAE', 'ENF'    

    def generate_clusters(self):
        """Run clustering algorithm on feature space.
        Returns:
            * clstr : array of cluster numbers, shape=(len(objid),)"""
        print('Performing clustering analysis in feature space...')
        if self.clstrmeth == 'gmm':
            if type(self.numclstr) == type(None):
                self.numclstr = lt.gmm_param_search(self.feats, self.featpath,
                                                    tsne=self.tsne)

            self.clstr = lt.run_gmm(self.objid, self.feats,
                                    numclstr=self.numclstr,
                                    savepath=self.featpath,
                                    runiter=self.runiter, numiter=self.numiter)

        elif self.clstrmeth == 'hdbscan':
            lt.quick_hdbscan_param_search(self.feats, output_dir=self.featpath,
                                          tsne=self.tsne)

    def generate_tsne(self):
        """Reduces dimensionality of feature space for visualization."""
        self.tsne = lt.run_tsne(self.feats, savepath=self.featpath+'model/')

    def generate_predicted_otypes(self):
        """Predicts object types using known classifications.
        Returns:
            * potype : array of predicted object types, shape=(len(objid),)"""
        self.potype = \
            lt.label_clusters(self.ensbpath+self.featgen+'/', self.sector,
                              self.objid, self.clstr, self.totype, self.numtot,
                              self.otdict)

    def produce_clustering_visualizations(self):
        '''Produces t-SNEs, confusion matrices, distribution plots, ensemble
        summary pie charts.'''
        pt.produce_clustering_visualizations(self.feats, self.numtot,
                                             self.numpot, self.tsne,
                                             self.ensbpath+self.featgen+'/',
                                             self.otdict, self.objid,
                                             self.sector, self.datapath,
                                             self.metapath)

    def generate_novelty_scores(self):
        """Returns: * nvlty : novelty scores, shape=(len(objid),)"""
        self.nvlty = pt.generate_novelty_scores(self.feats, self.objid,
                                                self.ensbpath+self.featgen+'/')

    def generate_rcon(self):
        self.rcon = lt.load_reconstructions(self.ensbpath+self.featgen+'/',
                                            self.objid)

    def produce_novelty_visualizations(self):
        pt.produce_novelty_visualizations(self.nvlty, self.featpath, self.objid,
                                          self.sector, self.feats,
                                          self.datapath, mdumpcsv=self.mdumpcsv,
                                          tsne=self.tsne,
                                          datatype=self.datatype)
        
    def run_feature_analysis(self):
        self.load_true_otypes()
        self.generate_tsne()

        self.generate_clusters()
        self.generate_predicted_otypes()
        self.numerize_otypes()
        
        self.generate_novelty_scores()
        
    def run_vis(self):
        self.produce_clustering_visualizations()
        self.produce_novelty_visualizations()

    # ==========================================================================
    # == Loading Mergen Products ===============================================
    # ==========================================================================

    def load_features(self):
        """ Load in feature metafiles stored in the datapath"""
        if self.featgen == "ENF":
            self.feats = dt.load_ENF_feature_metafile(self.ENFpath)
        elif self.featgen == "CAE": 
            self.feats = \
                lt.load_bottleneck_from_fits(self.featpath, self.objid,
                                             self.runiter, self.numiter)
        elif self.featgen == "DAE": 
            self.feats = \
                lt.load_DAE_bottleneck(self.featpath)

    def load_gmm_clusters(self):
        """ clstr : array of cluster numbers, shape=(len(objid),)"""
        self.clstr = \
            lt.load_gmm_from_txt(self.ensbpath+self.featgen+'/', self.objid,
                                 self.runiter, self.numiter, self.numclstr)

    def load_reconstructions(self):
        self.rcon = lt.load_reconstructions(self.ensbpath+self.featgen+'/',
                                            self.objid)

    def load_nvlty(self):
        self.nvlty = pt.load_novelty_scores(self.ensbpath+self.featgen+'/',
                                            self.objid)

    def load_true_otypes(self):
        """ totype : true object types"""
        if os.path.exists(self.savepath+'totype.txt'):
            self.totype = np.loadtxt(self.savepath+'totype.txt', skiprows=1,
                                   dtype='str', delimiter=',')[:,2]
        else:
            self.totype = dt.load_otype_true_from_datadir(self.metapath,
                                                          self.objid,
                                                          self.sector,
                                                          self.savepath)
        unqtot = np.unique(self.totype)
        self.otdict = {i: unqtot[i] for i in range(len(unqtot))}
        self.numtot = np.array([np.nonzero(unqtot == ot)[0][0] for \
                                ot in self.totype])

    def numerize_otypes(self):
        """
        * unqtot : unique true object types
        * otdict : cluster num to object type dictionary, e.g. {0: 'RR-Lyrae', 1:...}
        * numtot : numerized true object types, shape=(len(objid),)
        * numpot : numerized predicted object types, shape=(len(objid),)
        """
        unqtot = np.unique(self.totype)
        self.numpot = np.array([np.nonzero(unqtot == ot)[0][0] for \
                                ot in self.potype])

    def load_pred_otypes(self):
        """ potype : predicted object types"""
        self.potype = dt.load_otype_pred_from_txt(self.ensbpath+self.featgen+'/',
                                                  self.sector, self.objid)

    def load_tsne(self):
        self.tsne = lt.load_tsne_from_fits(self.featpath+'model/')
            
    def load(self):
        self.load_features()
        # self.load_reconstructions()
        
        self.load_true_otypes()

        self.load_nvlty()
        self.load_gmm_clusters()

        self.load_pred_otypes()
        self.numerize_otypes()
        
        self.load_tsne()
