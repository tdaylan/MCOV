# diagnostic pipeline for hyperparameter optimization 

import talos
import numpy as np
import modellibrary as ml

output_dir = 'plots/plots052020/'
report_path = 'plots/plots052020/051920103220.csv'

# >> load experiment log
analyze_object = talos.Analyze(report_path)
df, best_param_ind, p = ml.hyperparam_opt_diagnosis(analyze_object, output_dir,
                                                  supervised=False)
    
# >> x_train, x_test (mock_data)
training_size, test_size, input_dim = 1039, 116, 8896
noise_level = 0.5
center_factor, h_factor = 5., 0.2
    
x, x_train, y_train, x_test, y_test = \
    ml.signal_data(training_size=training_size,
                   test_size=test_size,
                   input_dim=input_dim,
                   noise_level=noise_level,
                   center_factor=center_factor,
                   h_factor=h_factor)
num_classes, orbit_gap_start, orbit_gap_end = False, False, False
ticid_train, ticid_test = False, False
rms_train, rms_test = False, False

# >> run model
history, model, x_predict = ml.run_model(x_train, y_train, x_test, y_test, p,
                              supervised=False)
ml.diagnostic_plots(history, model, p, output_dir, '', x, x_train, x_test,
                    x_predict, mock_data=True)