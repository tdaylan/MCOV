# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# 
# keras autoencoder model and plotting functions
# emma feb 2020
# 
# * convolutional autoencoder
#
#
# ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: 

import os
import pdb
import matplotlib.pyplot as plt
import numpy as np

# :: autoencoder ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def autoencoder(x_train, x_test, params, supervised = False, y_train=False,
                y_test=False):
    '''If supervised = True, must provide y_train, y_test'''
    from keras.layers import Input, Conv1D, MaxPooling1D, UpSampling1D
    from keras.layers import Reshape, Dense, Flatten, Dropout
    from keras.models import Model
    from keras import optimizers
    import keras.metrics

    input_dim = np.shape(x_train)[1]
    num_iter = int((params['num_conv_layers'] - 1)/2)
    
    input_img = Input(shape = (input_dim, 1))
    x = Conv1D(params['num_filters'][0], params['kernel_size'],
               activation=params['activation'], padding='same')(input_img)
    for i in range(num_iter):
        x = MaxPooling1D(2, padding='same')(x)
        x = Dropout(params['dropout'])(x)
        x = MaxPooling1D([params['num_filters'][i]],
                         data_format='channels_first')(x)
        x = Conv1D(params['num_filters'][1+i], params['kernel_size'],
                   activation=params['activation'], padding='same')(x)
    x = MaxPooling1D([params['num_filters'][i]], 
                     data_format='channels_first')(x)
    x = Flatten()(x)
    encoded = Dense(params['latent_dim'], activation=params['activation'])(x)

    x = Dense(int(input_dim/(2**(i+1))))(encoded)
    x = Reshape((int(input_dim/(2**(i+1))), 1))(x)
    for i in range(num_iter):
        x = Conv1D(params['num_filters'][num_iter+1], params['kernel_size'],
                   activation=params['activation'], padding='same')(x)
        x = UpSampling1D(2)(x)
        x = Dropout(params['dropout'])(x)
        x = MaxPooling1D([params['num_filters'][num_iter+1]],
                         data_format='channels_first')(x)
    decoded = Conv1D(1, params['kernel_size'],
                     activation=params['last_activation'], padding='same')(x)

    if params['optimizer'] == 'adam':
        opt = optimizers.adam(lr = params['lr'], 
                              decay=params['lr']/params['epochs'])
    elif params['optimizer'] == 'adadelta':
        opt = optimizers.adadelta(lr = params['lr'])
        
    if supervised:
        model = Model(input_img, encoded)
        print(model.summary())
        
        model.compile(optimizer=opt, loss=params['losses'],
                      metrics=['accuracy', keras.metrics.Precision(),
                      keras.metrics.Recall()])    
    
        history = model.fit(x_train, y_train, epochs=params['epochs'],
                            batch_size=params['batch_size'], shuffle=True,
                            validation_data=(x_test, y_test))
        
        
    else:
        model = Model(input_img, decoded)
        print(model.summary())
    
        model.compile(optimizer=opt, loss=params['losses'],
                      metrics=['accuracy', keras.metrics.Precision(),
                      keras.metrics.Recall()])    
    
        history = model.fit(x_train, x_train, epochs=params['epochs'],
                            batch_size=params['batch_size'], shuffle=True,
                            validation_data=(x_test, x_test))
        
    return history, model

# :: fake data ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def gaussian(x, a, b, c):
    '''a = height, b = position of center, c = stdev'''
    import numpy as np
    return a * np.exp(-(x-b)**2 / (2*c**2))

def signal_data(training_size = 10000, test_size = 100, input_dim = 100,
                 time_max = 30., noise_level = 0.0, height = 1., center = 15.,
                 stdev = 0.8, h_factor = 0.2, center_factor = 5.,
                 reshape=False):
    '''Generate training data set with flat light curves and gaussian light
    curves, with variable height, center, noise level as a fraction of gaussian
    height)
    '''

    x = np.empty((training_size + test_size, input_dim))
    y = np.empty((training_size + test_size))
    l = int(np.shape(x)[0]/2)
    
    # >> no peak data
    x[:l] = np.zeros((l, input_dim))
    y[:l] = 0.

    # >> with peak data
    time = np.linspace(0, time_max, input_dim)
    for i in range(l):
        a = height + h_factor*np.random.normal()
        b = center + center_factor*np.random.normal()
        x[l+i] = gaussian(time, a = a, b = b, c = stdev)
    y[l:] = 1.

    # >> add noise
    x += np.random.normal(scale = noise_level, size = np.shape(x))

    # >> partition training and test datasets
    x_train = np.concatenate((x[:int(training_size/2)], 
                              x[l:-int(test_size/2)]))
    y_train = np.concatenate((y[:int(training_size/2)], 
                              y[l:-int(test_size/2)]))
    x_test = np.concatenate((x[int(training_size/2):l], 
                             x[-int(test_size/2):]))
    y_test = np.concatenate((y[int(training_size/2):l], 
                             y[-int(test_size/2):]))

    if reshape:
        x_train = np.reshape(x_train, (np.shape(x_train)[0],
                                       np.shape(x_train)[1], 1))
        x_test = np.reshape(x_test, (np.shape(x_test)[0],
                                     np.shape(x_test)[1], 1))

    return x_train, y_train, x_test, y_test

def no_signal_data(training_size = 10000, test_size = 100, input_dim = 100,
                   noise_level = 0., min0max1=True, reshape=False):
    import numpy as np

    x = np.empty((training_size + test_size, input_dim))
    y = np.empty((training_size + test_size))
    l = int(np.shape(x)[0]/2)
    
    # >> no peak data
    if min0max1:
        x = np.zeros(np.shape(x))
    else:
        x = np.ones(np.shape(x))
    y = 0.

    # >> add noise
    x += np.random.normal(scale = noise_level, size = np.shape(x))

    # >> partition training and test datasets
    x_train = np.concatenate((x[:int(training_size/2)], 
                              x[l:-int(test_size/2)]))
    y_train = np.concatenate((y[:int(training_size/2)], 
                              y[l:-int(test_size/2)]))
    x_test = np.concatenate((x[int(training_size/2):l], 
                             x[-int(test_size/2):]))
    y_test = np.concatenate((y[int(training_size/2):l], 
                             y[-int(test_size/2):]))

    if reshape:
        x_train = np.reshape(x_train, (np.shape(x_train)[0],
                                       np.shape(x_train)[1], 1))
        x_test = np.reshape(x_test, (np.shape(x_test)[0],
                                     np.shape(x_test)[1], 1))
    
    return x_train, y_train, x_test, y_test

# :: partitioning tess data :::::::::::::::::::::::::::::::::::::::::::::::::::

def split_data(fname, train_test_ratio = 0.9, cutoff=16336,
               normalize_by_median=True, standardize=False):
    intensity = np.loadtxt(open(fname, 'rb'), delimiter=',')

    # >> truncate
    intensity = np.delete(intensity,np.arange(cutoff,np.shape(intensity)[1]),1)

    if normalize_by_median:
        # >> divide by median
        medians = np.median(intensity, axis = 1)
        medians = np.reshape(medians, (np.shape(medians)[0], 1))
        medians = np.repeat(medians, cutoff, axis = 1)
        intensity = intensity / medians - 1.
        
    if standardize: 
        # >> subtract by mean
        means = np.mean(intensity, axis = 1)
        means = np.reshape(means, (np.shape(means)[0],1))
        means = np.repeat(means, cutoff, axis = 1)
        intensity = intensity - means
        
        # >> divide by standard deviations
        stdevs = np.std(intensity, axis = 1, keepdims=True)
        intensity = intensity / stdevs
        

    # >> reshape data
    intensity = np.resize(intensity, (np.shape(intensity)[0],
                                      np.shape(intensity)[1], 1))

    # >> split test and train data
    split_ind = int(train_test_ratio*np.shape(intensity)[0])
    x_train = np.copy(intensity[:split_ind])
    x_test = np.copy(intensity[split_ind:])

    return x_train, x_test

# :: plotting :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


def corner_plot(activation, n_bins = 50, log = True):
    '''Creates corner plot for latent space.
    '''
    from matplotlib.colors import LogNorm
    latentDim = np.shape(activation)[1]

    fig, axes = plt.subplots(nrows = latentDim, ncols = latentDim,
                             figsize = (10, 10))

    # >> deal with 1 latent dimension case
    if latentDim == 1:
        axes.hist(np.reshape(activation, np.shape(activation)[0]), n_bins,
                  log=log)
        axes.set_ylabel('phi1')
        axes.set_ylabel('frequency')
    else:
        # >> row 1 column 1 is first latent dimension (phi1)
        for i in range(latentDim):
            axes[i,i].hist(activation[:,i], n_bins, log=log)
            axes[i,i].set_aspect(aspect=1)
            for j in range(i):
                if log:
                    norm = LogNorm()
                axes[i,j].hist2d(activation[:,j], activation[:,i],
                                 bins=n_bins, norm=norm)
                # >> remove axis frame of empty plots
                axes[latentDim-1-i, latentDim-1-j].axis('off')

            # >> x and y labels
            axes[i,0].set_ylabel('phi' + str(i))
            axes[latentDim-1,i].set_xlabel('phi' + str(i))

        # >> removing axis
        for ax in axes.flatten():
            ax.set_xticks([])
            ax.set_yticks([])
        plt.subplots_adjust(hspace=0, wspace=0)

    return fig, axes

def input_output_plot(x, x_test, x_predict, out = '', reshape = True,
                      inds = [0, -14, -10, 1, 2], addend = 0., sharey=False):
    '''Plots input light curve, output light curve and the residual.
    !!Can only handle len(inds) divisible by 3 or 5'''
    if len(inds) % 5 == 0:
        ncols = 5
    elif len(inds) % 3 == 0:
        ncols = 3
    ngroups = int(len(inds)/ncols)
    nrows = int(3*ngroups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8*1.6, 3*1.3*3),
                             sharey=sharey)
    for i in range(ncols):
        for ngroup in range(ngroups):
            if reshape:
                ind = int(ngroup*ncols + i)
                addend = 1. - np.median(x_test[inds[ind]])
                axes[ngroup*3, i].plot(x,
                                       x_test[inds[ind]][:,0]+addend, '.')
                axes[ngroup*3+1,i].plot(x,
                                        x_predict[inds[ind]][:,0]+addend, '.')
                residual = (x_test[inds[ind]][:,0] - \
                            x_predict[inds[ind]][:,0])
                # residual = (x_test[inds[ind]][:,0] - \
                #             x_predict[inds[ind]][:,0])/ \
                #             x_test[inds[ind]][:,0]
                axes[ngroup*3+2, i].plot(x, residual, '.')
            else:
                axes[ngroup*3, i].plot(x, x_test[inds[ind]]+addend, '.')
                axes[ngroup*3+1, i].plot(x, x_predict[inds[ind]]+addend, '.')
                residual = (x_test[inds[ind]] - x_predict[inds[ind]])
                # residual = (x_test[inds[ind]] - x_predict[inds[ind]])/ \
                #     x_test[inds[ind]]
                axes[ngroup*3+2, i].plt(x, residual, '.')
        axes[-1, i].set_xlabel('time [days]')
    for i in range(ngroups):
        axes[3*i, 0].set_ylabel('input\nrelative flux')
        axes[3*i+1, 0].set_ylabel('output\nrelative flux')
        axes[3*i+2, 0].set_ylabel('residual')
    # for ax in axes.flatten():
    #     ax.set_aspect(aspect=3./8.)
    fig.tight_layout()
    if out != '':
        plt.savefig(out)
        plt.close(fig)
    return fig, axes
    
def get_activations(model, x_test):
    from keras.models import Model
    layer_outputs = [layer.output for layer in model.layers][1:]
    activation_model = Model(inputs=model.input, outputs=layer_outputs)
    activations = activation_model.predict(x_test)
    return activations

def latent_space_plot(model, activations, out):
    # >> get ind for plotting latent space
    bottleneck_ind = np.nonzero(['dense' in x.name for x in \
                                 model.layers])[0][0]
    fig, axes = corner_plot(activations[bottleneck_ind-1])
    plt.savefig(out)
    plt.close(fig)
    return fig, axes

def kernel_filter_plot(model, out_dir):
    # >> get inds for plotting kernel and filters
    layer_inds = np.nonzero(['conv' in x.name for x in model.layers])[0]
    for a in layer_inds: # >> loop through conv layers
        filters, biases = model.layers[a].get_weights()
        fig, ax = plt.subplots()
        ax.imshow(np.reshape(filters, (np.shape(filters)[0],
                                       np.shape(filters)[2])))
        ax.set_xlabel('filter')
        ax.set_ylabel('kernel')
        plt.savefig(out_dir + 'layer' + str(a) + '.png')
        plt.close(fig)

def intermed_act_plot(x, model, activations, x_test, out_dir, addend=0.5,
                      inds = [0, -1], movie = True):
    '''Visualizing intermediate activations
    activation.shape = (test_size, input_dim, filter_num) = (116, 16272, 32)'''
    # >> get inds for plotting intermediate activations
    act_inds = np.nonzero(['conv' in x.name or \
                           'max_pool' in x.name or \
                           'dropout' in x.name or \
                           'reshape' in x.name for x in \
                           model.layers])[0]
    act_inds = np.array(act_inds) -1

    for c in range(len(inds)): # >> loop through light curves
        fig, axes = plt.subplots(figsize=(4,3))
        addend = 1. - np.median(x_test[inds[c]])
        axes.plot(np.linspace(np.min(x), np.max(x), np.shape(x_test)[1]),
                x_test[inds[c]] + addend, '.')
        axes.set_xlabel('time [days]')
        axes.set_ylabel('relative flux')
        plt.tight_layout()
        fig.savefig(out_dir+str(c)+'ind-0input.png')
        plt.close(fig)
        for a in act_inds: # >> loop through layers
            activation = activations[a]
            if np.shape(activation)[2] == 1:
                nrows = 1
                ncols = 1
            else:
                ncols = 4
                nrows = int(np.shape(activation)[2]/ncols)
            fig, axes = plt.subplots(nrows,ncols,figsize=(8*ncols*0.5,3*nrows))
            for b in range(np.shape(activation)[2]): # >> loop through filters
                if ncols == 1:
                    ax = axes
                else:
                    ax = axes.flatten()[b]
                x1 = np.linspace(np.min(x), np.max(x), np.shape(activation)[1])
                ax.plot(x1, activation[inds[c]][:,b] + addend, '.')
            if nrows == 1:
                axes.set_xlabel('time [days]')
                axes.set_ylabel('relative flux')
                # axes.set_aspect(aspect=3./8.)
            else:
                for i in range(nrows):
                    axes[i,0].set_ylabel('relative\nflux')
                for j in range(ncols):
                    axes[-1,j].set_xlabel('time [days]')
            fig.tight_layout()
            fig.savefig(out_dir+str(c)+'ind-'+str(a+1)+model.layers[a+1].name\
                        +'.png')
            plt.close(fig)

def epoch_plots(history, p, out_dir):
    label_list = [['loss', 'accuracy'], ['precision', 'recall']]
    key_list = [['loss', 'accuracy'], [list(history.history.keys())[-2],
                                       list(history.history.keys())[-1]]]
    for i in range(2):
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(history.history[key_list[i][0]], label=label_list[i][0])
        ax1.set_ylabel(label_list[i][0])
        ax2.plot(history.history[key_list[i][1]], '--', label=label_list[i][1])
        ax2.set_ylabel(label_list[i][1])
        ax1.set_xlabel('epoch')
        ax1.set_xticks(range(p['epochs']))
        ax1.legend(loc = 'upper left', fontsize = 'x-small')
        ax2.legend(loc = 'upper right', fontsize = 'x-small')
        fig.tight_layout()
        if i == 0:
            plt.savefig(out_dir + 'acc_loss.png')
        else:
            plt.savefig(out_dir + 'prec_recall.png')
        plt.close(fig)
    
def input_bottleneck_output_plot(x, x_test, x_predict, activations, model,
                                 out = '',
                                 reshape = True,
                                 inds = [0, 1, -1, -2, -3],
                                 addend = 0.5, sharey=False):
    '''Can only handle len(inds) divisible by 3 or 5'''
    bottleneck_ind = np.nonzero(['dense' in x.name for x in \
                                 model.layers])[0][0]
    bottleneck = activations[bottleneck_ind - 1]
    if len(inds) % 5 == 0:
        ncols = 5
    elif len(inds) % 3 == 0:
        ncols = 3
    ngroups = int(len(inds)/ncols)
    nrows = int(3*ngroups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(8*1.6, 3*1.3*3),
                             sharey=sharey)
    for i in range(ncols):
        for ngroup in range(ngroups):
            if reshape:
                ind = int(ngroup*ncols + i)
                addend = 1. - np.median(x_test[inds[ind]])
                axes[ngroup*3, i].plot(x, x_test[inds[ind]][:,0]+addend, '.')
                img = np.reshape(bottleneck[inds[ind]],
                                 (1, np.shape(bottleneck[inds[ind]])[0]))
                axes[ngroup*3+1, i].imshow(img)
                axes[ngroup*3+2, i].plot(x, x_predict[inds[ind]][:,0]+addend,
                                         '.')
            else:
                addend = 1. - np.median(x_test[inds[ind]])
                axes[ngroup*3, i].plot(x, x_test[inds[ind]]+addend, '.')
                axes[ngroup*3+2, i].plot(x, x_predict[inds[ind]]+addend, '.')
        axes[-1, i].set_xlabel('time [days]')
    for i in range(ngroups):
        axes[3*i, 0].set_ylabel('input\nrelative flux')
        axes[3*i+1, 0].set_ylabel('bottleneck')
        axes[3*i+2, 0].set_ylabel('output\nrelative flux')
    fig.tight_layout()
    if out != '':
        plt.savefig(out)
        plt.close(fig)
    return fig, axes
    

def movie(x, model, activations, x_test, p, out_dir, inds = [0, -1],
          addend=0.5):
    for c in range(len(inds)):
        fig, axes = plt.subplots(figsize=(8,3))
        ymin = []
        ymax = []
        for activation in activations:
            if np.shape(activation)[1] == p['latent_dim']:
                ymin.append(min(activation[inds[c]]))
                ymax.append(max(activation[inds[c]]))
            elif len(np.shape(activation)) > 2:
                if np.shape(activation)[2] == 1:
                    ymin.append(min(activation[inds[c]]))
                    ymax.append(max(activation[inds[c]]))
        ymin = np.min(ymin) + addend
        ymax = np.max(ymax) + addend
        addend = 1. - np.median(x_test[inds[c]])

        # >> plot input
        axes.plot(np.linspace(np.min(x), np.max(x), np.shape(x_test)[1]),
                  x_test[inds[c]] + addend, '.')
        axes.set_xlabel('time [days]')
        axes.set_ylabel('relative flux')
        axes.set_ylim(ymin=ymin, ymax=ymax)
        fig.tight_layout()
        fig.savefig('./image-000.png')

        # >> plot intermediate activations
        n=1
        for a in range(len(activations)):
            activation = activations[a]
            if np.shape(activation)[1] == p['latent_dim']:
                length = p['latent_dim']
                axes.cla()
                axes.plot(np.linspace(np.min(x), np.max(x), length),
                          activation[inds[c]] + addend, '.')
                axes.set_xlabel('time [days]')
                axes.set_ylabel('relative flux')
                axes.set_ylim(ymin=ymin, ymax =ymax)
                fig.tight_layout()
                fig.savefig('./image-' + f'{n:03}.png')
                n += 1
            elif len(np.shape(activation)) > 2:
                if np.shape(activation)[2] == 1:
                    length = np.shape(activation)[1]
                    y = np.reshape(activation[inds[c]], (length))
                    axes.cla()
                    axes.plot(np.linspace(np.min(x), np.max(x), length),
                              y + addend, '.')
                    axes.set_xlabel('time [days]')
                    axes.set_ylabel('relative flux')
                    axes.set_ylim(ymin = ymin, ymax = ymax)
                    fig.tight_layout()
                    fig.savefig('./image-' + f'{n:03}.png')
                    n += 1
        os.system('ffmpeg -framerate 2 -i ./image-%03d.png -pix_fmt yuv420p '+\
                  out_dir+str(c)+'ind-movie.mp4')

def latent_space_clustering(activation, x_test, x, out = './', n_bins = 50,
                            addend=1.):
    '''Clustering latent space
    '''
    from matplotlib.colors import LogNorm
    # from sklearn.cluster import DBSCAN
    from sklearn.neighbors import LocalOutlierFactor
    latentDim = np.shape(activation)[1]

    # >> deal with 1 latent dimension case
    if latentDim == 1:
        fig, axes = plt.subplots(figsize = (15,15))
        axes.hist(np.reshape(activation, np.shape(activation)[0]), n_bins,
                  log=True)
        axes.set_ylabel('phi1')
        axes.set_ylabel('frequency')
    else:
        # >> row 1 column 1 is first latent dimension (phi1)
        for i in range(latentDim):
            # axes[i,i].hist(activation[:,i], n_bins, log=log)
            # axes[i,i].set_aspect(aspect=1)
            for j in range(i):
                # >> plot latent space with inset plots
                fig, ax = plt.subplots(figsize = (15,15))
                
                h, xedges, yedges, img = ax.hist2d(activation[:,j],
                                                   activation[:,i],
                                                   bins=n_bins, norm=LogNorm())
                X = np.array((activation[:,j], activation[:,i])).T
                # clustering = DBSCAN().fit(np.array((activation[:,j],
                #                                     activation[:,i])).T)
                clf = LocalOutlierFactor()
                clf.fit_predict(X)
                lof = clf.negative_outlier_factor_
                inds = np.argsort(lof)[:10]
                # xextent = max(activation[:,j]) - min(activation[:,j])
                # yextent = max(activation[:,i]) - min(activation[:,i])
                # h = 0.097
                h = 0.047
                # x0 = 0.7
                x0 = 0.85
                # y0 = 0.85
                y0 = 0.9
                # xstep = h*8/3 + 0.05
                xstep = h*8/3 + 0.025
                # ystep = h+0.05
                ystep = h + 0.025
                for k in range(3):
                    # >> make inset axes
                    axins = ax.inset_axes([x0 - k*xstep, y0, h*8/3, h])
                    xp, yp = activation[:,j][inds[k]], activation[:,i][inds[k]]
                    x1, y1 = xp - 0.025, yp - 0.025
                    x2, y2 = xp + 0.025, yp + 0.025
                    axins.set_xlim(x1, x2)
                    axins.set_ylim(y1, y2)
                    ax.indicate_inset_zoom(axins)
                    
                    # >> plot light curves
                    axins.set_xlim(min(x), max(x))
                    axins.set_ylim(min(x_test[inds[k]]), max(x_test[inds[k]]))
                    axins.plot(x, x_test[inds[k]] + addend, '.')
                    axins.set_xticklabels('')
                    axins.set_yticklabels('')
                    axins.patch.set_alpha(0.5)
                # axins = ax.inset_axes([x0, y0+ystep, h*8/3, h])
                # axins = ax.inset_axes([x0+xstep, y0, h*8/3, h])
                # axins = ax.inset_axes([x0+2*xstep, y0, h*8/3, h])
                # axins = ax.inset_axes([0.7 - 2*(h)])
                
                # >> remove axis frame of empty plots
                # axes[latentDim-1-i, latentDim-1-j].axis('off')

                # >> x and y labels
                ax.set_ylabel('phi' + str(i))
                ax.set_xlabel('phi' + str(j))
                fig.savefig(out + 'phi' + str(j) + 'phi' + str(i) + '.png')
                
                # >> plot top 10 light curves
                fig1, ax1 = plt.subplots(10, figsize = (7,10*1.3*7*3/8))
                for k in range(10):
                    ax1[k].plot(x, x_test[inds[k]] + addend, '.')
                    ax1[k].set_ylabel('relative flux')
                ax1[-1].set_xlabel('time [days]')
                fig1.savefig(out + 'phi' + str(j) + 'phi' + str(i) + \
                            '-outliers.png')

        # >> removing axis
        # for ax in axes.flatten():
        #     ax.set_xticks([])
        #     ax.set_yticks([])
        # plt.subplots_adjust(hspace=0, wspace=0)

    return fig, ax


