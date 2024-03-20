#!/usr/bin/env python3

from abc import ABC, abstractmethod
import logging

import numpy as np
from pandas import DataFrame

_subgroup_labels_expected_2018 =   [16, 17, 18, 19,
                                    20, 21, 22, 23, 24, 25, 26,
                                    44, 45, 46, 47, 48, 49,
                                    50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
                                    60, 61, 62, 63,
                                    70, 71, 72, 73, 74, 75, 76, 77, 79,
                                    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
                                    90]

_subgroup_labels_expected_2023 =   [1, 2, 3, 4, 5, 6, 7, 8, 9,
                                    10, 11, 12, 13, 17, 18, 19,
                                    20, 21, 22, 23, 24, 25, 26,
                                    44, 45, 46, 47, 48, 49,
                                    50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
                                    60, 61, 62, 64, 65, 66, 67, 68, 69,
                                    70, 71, 72, 73, 74, 75, 76, 77, 79,
                                    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
                                    90, 91, 92, 93, 94, 95]

_subgroup_labels_expected_eclipse =   [1, 2, 3, 4, 5, 6, 7, 8, 9,
                                        10, 11, 12, 13, 17, 18, 19,
                                        20, 21, 22, 23, 24, 25, 26,
                                        44, 45, 46, 47, 48, 49,
                                        50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
                                        60, 61, 62, 64, 65, 66, 67, 68, 69,
                                        70, 71, 72, 73, 74, 75, 76, 77, 79,
                                        80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
                                        90, 91, 92, 93, 94, 95]

class BaseReducer(ABC):

    def __init__(self, configuration_version: str) -> None:
        self._configuration_version = configuration_version

        if self._configuration_version == '2018':
            self._subgroup_numbers_expected = _subgroup_labels_expected_2018
        elif self._configuration_version == '2023':
            self._subgroup_numbers_expected = _subgroup_labels_expected_2023
        elif self._configuration_version == 'ECLIPSE':
            self._subgroup_numbers_expected = _subgroup_labels_expected_eclipse
        else:
            raise ValueError('Configuration version '
                                f'{self._configuration_version} '
                                'is unknown')

        self._logger = logging.getLogger(__name__)
        self._missing_subgroups_feedback_given = False

    @abstractmethod
    def reduce_pandas(self, input_slice: DataFrame) -> DataFrame:
        pass

    @abstractmethod
    def reduce_numpy(self,
                        input_slice: np.array,
                        tpu_labels: list,
                        timestamps: list) -> DataFrame:
        pass

    def _adjust_reduced_data(self,
                                labels_reduced: np.array,
                                data_reduced: np.array) -> np.array:

        subgroup_count_expected = len(self._subgroup_numbers_expected)
        subgroup_count_observed = len(labels_reduced)//2

        if subgroup_count_observed < subgroup_count_expected:
            subgroup_numbers_observed =\
                    [int(label.removeprefix('m_'))\
                        for label in labels_reduced[:subgroup_count_observed]]

            missing_subgroups = np.setdiff1d(self._subgroup_numbers_expected,
                                                subgroup_numbers_observed)

            indices_missing =\
                    np.nonzero(np.isin(self._subgroup_numbers_expected,
                                                    missing_subgroups))[0]

            if not self._missing_subgroups_feedback_given:
                
                missing_subgroups_string = ''

                for subgroup in missing_subgroups:
                    missing_subgroups_string += f'{subgroup}, '

                self._logger.warning(f'Rack(s) {missing_subgroups_string} are '
                                        'missing. 2nd stage detection '
                                        'performance might be affected.')

                # missing_subgroup_indices_string =\
                #             ', '.join(str(indices_missing))\
                #                 if len(indices_missing) > 1\
                #                 else str(indices_missing[0])

                # self._logger.debug('Indices missing subgroups: '
                #                     f'{missing_subgroup_indices_string}')

                self._missing_subgroups_feedback_given = True

            data_reduced = np.insert(data_reduced,
                                        indices_missing,
                                        0, axis=1)

            data_reduced = np.insert(data_reduced,
                                        indices_missing +\
                                            subgroup_count_expected,
                                        0, axis=1)

            missing_labels_median =\
                [f'm_{subgroup}' for subgroup in missing_subgroups]

            labels_reduced = np.insert(labels_reduced,
                                        indices_missing,
                                        missing_labels_median)

            missing_labels_std =\
                [f'std_{subgroup}' for subgroup in missing_subgroups]

            labels_reduced = np.insert(labels_reduced,
                                        indices_missing +\
                                            subgroup_count_expected,
                                        missing_labels_std)

        return labels_reduced, data_reduced
