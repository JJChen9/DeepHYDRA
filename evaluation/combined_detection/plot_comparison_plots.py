
import argparse
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score,\
                                precision_recall_fscore_support,\
                                matthews_corrcoef

import matplotlib.pyplot as plt

sys.path.append('.')

from spot import SPOT

run_endpoints = [1404,
                    8928,
                    19296,
                    28948]

channels_to_delete_last_run = [1357,
                                3685,
                                3184]

base_data_anomaly_starts = [247,
                                465,
                                4272]

base_data_anomaly_ends = [264,
                            465,
                            4277]


def load_numpy_array(filename: str):
    with open(filename, 'rb') as output_file:
        return np.load(output_file)


def get_anomalous_runs(x):
    '''
    Find runs of consecutive items in an array.
    As published in https://gist.github.com/alimanfoo/c5977e87111abe8127453b21204c1065
    '''

    # Ensure array

    x = np.asanyarray(x)

    if x.ndim != 1:
        raise ValueError('Only 1D arrays supported')

    n = x.shape[0]

    # Handle empty array

    if n == 0:
        return np.array([]), np.array([]), np.array([])

    else:

        # Find run starts

        loc_run_start = np.empty(n, dtype=bool)
        loc_run_start[0] = True

        np.not_equal(x[:-1], x[1:], out=loc_run_start[1:])
        run_starts = np.nonzero(loc_run_start)[0]

        # Find run values
        run_values = x[loc_run_start]

        # Find run lengths
        run_lengths = np.diff(np.append(run_starts, n))

        run_starts = np.compress(run_values, run_starts)
        run_lengths = np.compress(run_values, run_lengths)

        run_ends = run_starts + run_lengths

        return run_starts, run_ends


def adjust_predicts(score, label,
                    threshold=None,
                    pred=None,
                    calc_latency=False):
    """
    Calculate adjusted predict labels using given `score`, `threshold` (or given `pred`) and `label`.
    Args:
        score (np.ndarray): The anomaly score
        label (np.ndarray): The ground-truth label
        threshold (float): The threshold of anomaly score.
            A point is labeled as "anomaly" if its score is lower than the threshold.
        pred (np.ndarray or None): if not None, adjust `pred` and ignore `score` and `threshold`,
        calc_latency (bool):
    Returns:
        np.ndarray: predict labels
    """
    if len(score) != len(label):
        raise ValueError("score and label must have the same length")
    score = np.asarray(score)
    label = np.asarray(label)
    latency = 0
    if pred is None:
        predict = score > threshold
    else:
        predict = pred
    actual = label > 0.1
    anomaly_state = False
    anomaly_count = 0
    for i in range(len(score)):
        if actual[i] and predict[i] and not anomaly_state:
                anomaly_state = True
                anomaly_count += 1
                for j in range(i, 0, -1):
                    if not actual[j]:
                        break
                    else:
                        if not predict[j]:
                            predict[j] = True
                            latency += 1
        elif not actual[i]:
            anomaly_state = False
        if anomaly_state:
            predict[i] = True
    if calc_latency:
        return predict, latency / (anomaly_count + 1e-4)
    else:
        return predict


def get_scores(pred_train, pred_test, true, q=1e-3, level=0.8):
    """
    Run POT method on given score.
    Args:
        init_score (np.ndarray): The data to get init threshold.
            For `OmniAnomaly`, it should be the anomaly score of train set.
        score (np.ndarray): The data to run POT method.
            For `OmniAnomaly`, it should be the anomaly score of test set.
        label:
        q (float): Detection level (risk)
        level (float): Probability associated with the initial threshold t
    Returns:
        dict: pot result dict
    """

    # SPOT object
    spot = SPOT(q)

    # data import
    spot.fit(pred_train, pred_test)

    # initialization step
    spot.initialize(level=level,
                    min_extrema=False,
                    verbose=True)

    # run
    ret = spot.run()

    print(len(ret['alarms']))
    print(len(ret['thresholds']))

    pred = np.zeros_like(pred_test, dtype=np.uint8)

    pred[ret['alarms']] = 1

    pred = adjust_predicts(pred, true, 0.1)

    precision_max_f1_score,\
        recall_max_f1_score,\
        max_f1_score, _ = precision_recall_fscore_support(true,
                                                            pred,
                                                            average='binary')

    mcc_max_f1_score =\
        matthews_corrcoef(true, pred)

    auroc = roc_auc_score(true, pred)

    print(f'AUROC: {auroc:.3f}\t'
            f'F1: {max_f1_score:.3f}\t'
            f'MCC: {mcc_max_f1_score:.3f}\t'
            f'Precision: {precision_max_f1_score:.3f}\t'
            f'Recall: {recall_max_f1_score:.3f}')

    return max_f1_score,\
            precision_max_f1_score,\
            recall_max_f1_score,\
            mcc_max_f1_score,\
            ret['thresholds']


def get_scores_tranad(pred_train, pred_test, true, q=1e-3, level=0.02):
    """
    Run POT method on given score.
    Args:
        init_score (np.ndarray): The data to get init threshold.
            it should be the anomaly score of train set.
        score (np.ndarray): The data to run POT method.
            it should be the anomaly score of test set.
        label:
        q (float): Detection level (risk)
        level (float): Probability associated with the initial threshold t
    Returns:
        dict: pot result dict
    """

    lms = 0.99995
    while True:
        try:
            s = SPOT(q)  # SPOT object
            s.fit(pred_train, pred_test)  # data import
            s.initialize(level=lms, min_extrema=False, verbose=True)  # initialization step
        except: lms = lms * 0.999
        else: break
    ret = s.run(dynamic=False)  # run
    # print(len(ret['alarms']))
    # print(len(ret['thresholds']))
    pot_th = np.mean(ret['thresholds']) * 0.6
    # pot_th = np.percentile(score, 100 * lm[0])
    # np.percentile(score, 100 * lm[0])

    pred = pred_test > pot_th

    pred = adjust_predicts(pred, true, 0.1)

    precision_max_f1_score,\
        recall_max_f1_score,\
        max_f1_score, _ = precision_recall_fscore_support(true,
                                                            pred,
                                                            average='binary')

    mcc_max_f1_score =\
        matthews_corrcoef(true, pred)

    auroc = roc_auc_score(true, pred)

    print(f'AUROC: {auroc:.3f}\t'
            f'F1: {max_f1_score:.3f}\t'
            f'MCC: {mcc_max_f1_score:.3f}\t'
            f'Precision: {precision_max_f1_score:.3f}\t'
            f'Recall: {recall_max_f1_score:.3f}')

    return max_f1_score,\
            precision_max_f1_score,\
            recall_max_f1_score,\
            mcc_max_f1_score,\
            ret['thresholds']


def plot_results(data: np.array,
                    label: np.array):

    label = np.any(label, axis=1).astype(np.uint8)

    preds_method_3 = load_numpy_array('predictions/method_3.npy')
    preds_method_4 = load_numpy_array('predictions/method_4.npy')
    preds_merlin = load_numpy_array('predictions/merlin.npy')
    preds_clustering = load_numpy_array('predictions/clustering.npy')
    preds_tranad = load_numpy_array('predictions/tranad.npy')
    preds_tranad_train = load_numpy_array('predictions/tranad_train.npy')
    preds_l2_dist_train_mse = load_numpy_array('predictions/l2_dist_train_mse.npy')
    preds_l2_dist_mse = load_numpy_array('predictions/l2_dist_mse.npy')
    preds_l2_dist_train_smse = load_numpy_array('predictions/l2_dist_train_smse.npy')
    preds_l2_dist_smse = load_numpy_array('predictions/l2_dist_smse.npy')

    preds_method_3 = np.any(preds_method_3, axis=1).astype(np.uint8)
    preds_method_4 = np.any(preds_method_4, axis=1).astype(np.uint8)
    preds_merlin = np.any(preds_merlin, axis=1).astype(np.uint8)

    spot_train_size = int(len(preds_l2_dist_mse)*0.1)

    # Fix alignment

    preds_l2_dist_mse =\
        np.pad(preds_l2_dist_mse[1:], (0, 1),
                                'constant',
                                constant_values=(0,))
    
    preds_l2_dist_smse =\
        np.pad(preds_l2_dist_smse[1:], (0, 1),
                                'constant',
                                constant_values=(0,))
    
    preds_method_3 =\
        np.pad(preds_method_3, (1, 0),
                            'constant',
                            constant_values=(0,))
    preds_method_4 =\
        np.pad(preds_method_4, (1, 0),
                            'constant',
                            constant_values=(0,))
    
    _, _, _, _, thresh_tranad =\
        get_scores_tranad(preds_tranad_train,
                            preds_tranad, label, 0.01)
    
    preds_tranad = preds_tranad >= thresh_tranad

    preds_strada_tranad = np.logical_or(preds_clustering,
                                                preds_tranad)

    _, _, _, _, thresh_mse =\
        get_scores(preds_l2_dist_train_mse[:spot_train_size],
                                                preds_l2_dist_mse, label, 0.007)
    
    preds_l2_dist_mse = preds_l2_dist_mse >= thresh_mse

    preds_strada_mse = np.logical_or(preds_clustering,
                                        preds_l2_dist_mse)

    _, _, _, _, thresh_smse =\
        get_scores(preds_l2_dist_train_smse[:spot_train_size],
                                                preds_l2_dist_smse, label, 0.008)
    
    preds_l2_dist_smse = preds_l2_dist_smse >= thresh_smse

    preds_strada_smse = np.logical_or(preds_clustering,
                                        preds_l2_dist_smse)

    preds_all = {   '1L-Method 3': preds_method_3,
                    '1L-Method 4': preds_method_4,
                    'MERLIN': preds_merlin,
                    'DBSCAN': preds_clustering,
                    'Informer-MSE': preds_l2_dist_mse,
                    'Informer-SMSE': preds_l2_dist_smse,
                    'TranAD': preds_tranad,
                    'STRADA-MSE': preds_strada_mse,
                    'STRADA-SMSE': preds_strada_smse,
                    'STRADA-TranAD': preds_strada_tranad}

    colors = {  '1L-Method 3': '#D81B60',
                '1L-Method 4': '#1E88E5',
                'MERLIN': '#FFC107',
                'DBSCAN': '#004D40',
                'Informer-MSE': '#C43F42',
                'Informer-SMSE': '#6F8098',
                'TranAD': '#D4FC14',
                'STRADA-MSE': '#1CB2C5',
                'STRADA-SMSE': '#18F964',
                'STRADA-TranAD': '#1164B3'}

    positions = {   '1L-Method 3': 0,
                    '1L-Method 4': 1,
                    'MERLIN': 2,
                    'DBSCAN': 3,
                    'Informer-MSE': 4,
                    'Informer-SMSE': 5,
                    'TranAD': 6,
                    'STRADA-MSE': 7,
                    'STRADA-SMSE': 8,
                    'STRADA-TranAD': 9}
    
    SMALL_SIZE = 13
    MEDIUM_SIZE = 13
    BIGGER_SIZE = 13

    xlims = [(250, 500),
                (600, 800),
                (850, 1070),
                (1300, 1400),
                (1800, 2000),
                (2000, 2400),
                (3300, 3800),
                (6000, 8500),
                (14000, 15000)]
    
    plt.rc('font', size=SMALL_SIZE)
    plt.rc('axes', titlesize=BIGGER_SIZE)
    plt.rc('axes', labelsize=MEDIUM_SIZE)
    plt.rc('xtick', labelsize=SMALL_SIZE)
    plt.rc('ytick', labelsize=SMALL_SIZE)
    plt.rc('legend', fontsize=SMALL_SIZE)
    plt.rc('figure', titlesize=BIGGER_SIZE)
    

    for index, (xlim_lower, xlim_upper) in enumerate(xlims):

        fig, (ax_data, ax_pred) = plt.subplots(2, 1, figsize=(10, 6), dpi=300)

        plt.yticks(rotation=30, ha='right')

        ax_data.set_title('Data')
        ax_data.set_xlabel('Timestep')

        ax_data.set_xlim(xlim_lower,
                            xlim_upper)
        ax_data.set_ylim(-1, 100)

        ax_data.grid()


        ax_data.plot(data,
                        linewidth=0.9,
                        color='k')

        anomaly_starts, anomaly_ends =\
                    get_anomalous_runs(label)

        for start, end in zip(anomaly_starts,
                                    anomaly_ends):
            ax_data.axvspan(start, end, color='red', alpha=0.5)
            ax_pred.axvspan(start, end, color='red', alpha=0.5)

        ax_pred.set_yticks(list(positions.values()),
                                list(positions.keys()))

        ax_pred.set_title('Predictions')
        ax_pred.set_xlabel('Timestep')
        ax_pred.set_ylabel('Method')

        ax_pred.set_xlim(xlim_lower,
                            xlim_upper)

        for method, preds in preds_all.items():
            pred_starts, pred_ends =\
                get_anomalous_runs(preds)
                
            for start, end in zip(pred_starts, pred_ends):

                length = end - start

                ax_pred.barh(positions[method],
                                length,
                                left=start,
                                color=colors[method],
                                label=method,
                                height=0.9)

        plt.tight_layout()
        plt.savefig(f'plots/prediction_comparison_spot_{index}.png')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='HLT Dataset Comparison Plot Generator')

    parser.add_argument('--data-dir', type=str, default='../../../datasets/hlt')
  
    args = parser.parse_args()

    hlt_data_pd = pd.read_hdf(args.data_dir +\
                                    '/unreduced_hlt_test_set_x.h5')

    hlt_data_pd.iloc[run_endpoints[-2]:-1,
                            channels_to_delete_last_run] = 0

    hlt_data_pd.fillna(0, inplace=True)

    hlt_data_np = hlt_data_pd.to_numpy()

    labels_pd = pd.read_hdf(args.data_dir +\
                            '/unreduced_hlt_test_set_y.h5')

    labels_np = labels_pd.to_numpy()

    labels_np = np.greater_equal(labels_np, 1)

    plot_results(hlt_data_np, labels_np)