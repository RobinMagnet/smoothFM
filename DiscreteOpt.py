import copy
import numpy as np
from smooth_utils import utils

from tqdm.auto import tqdm


class DiscreteOptimization():

    def __init__(self, mesh1, mesh2, p2p_12=None, p2p_21=None):

        self.mesh1 = copy.deepcopy(mesh1)
        self.mesh2 = copy.deepcopy(mesh2)

        self.opt_params = None
        self.sp_params = None

        self.p2p_12 = None
        self.p2p_21 = None

        self.FM_12 = None
        self.FM_21 = None

        self.p2p_12_init = None
        self.p2p_21_init = None

        if p2p_12 is not None:
            self.p2p_12_init = p2p_12.copy()

        if p2p_21 is not None:
            self.p2p_21_init = p2p_21.copy()

    def _set_params(self, method):
        self.sp_params = utils._do_sp_param(method)
        self.opt_params = utils._base_opt_params(method)

    def solve_FM_12(self, k):
        self.FM_12 = utils.solve_FM_12(self.mesh1, self.mesh2, k, self.p2p_21, p2p_12=self.p2p_12, params=self.sp_params)

    def solve_FM_21(self, k):
        self.FM_21 = utils.solve_FM_12(self.mesh2, self.mesh1, k, self.p2p_12, p2p_12=self.p2p_21, params=self.sp_params)

    def solve_p2p_12(self, n_jobs=1, precise=False):
        self.sp_params["ind1"] = 2
        self.p2p_12 = utils.solve_p2p_21_spectral(self.mesh2, self.mesh1, self.FM_21, FM_21=self.FM_12,
                                                  params=self.sp_params, n_jobs=n_jobs, precise=precise)

    def solve_p2p_21(self, n_jobs=1, precise=False):
        self.sp_params["ind1"] = 1
        self.p2p_21 = utils.solve_p2p_21_spectral(self.mesh1, self.mesh2, self.FM_12, FM_21=self.FM_21,
                                                  params=self.sp_params, n_jobs=n_jobs, precise=precise)

    def generate_klist(self):
        k_init = self.opt_params["k_init"]
        nit = self.opt_params["nit"]
        step = self.opt_params["step"]
        k_max = self.opt_params["k_max"]
        log_space = self.opt_params["log_space"]

        return utils.generate_klist(k_init, nit, step, k_max, log_space=log_space)

    def set_init(self, p2p_12=None, p2p_21=None):
        if p2p_12 is not None:
            self.p2p_12_init = p2p_12.copy()

        if p2p_21 is not None:
            self.p2p_21_init = p2p_21.copy()

    def _initialize(self, p2p_21=None, p2p_12=None):
        if p2p_21 is not None:
            self.p2p_21 = p2p_21.copy()
        elif self.p2p_21_init is not None:
            self.p2p_21 = self.p2p_21_init.copy()
        else:
            raise ValueError("NO INITIAL 2->1 MAP")

        if p2p_12 is not None:
            self.p2p_12 = p2p_12.copy()
        elif self.p2p_12_init is not None:
            self.p2p_12 = self.p2p_12_init.copy()
        else:
            raise ValueError("NO INITIAL 1->2 MAP")

        self.FM_12 = None
        self.FM_21 = None

    def fit(self, p2p_21=None, p2p_12=None, n_jobs=1, verbose=False):

        self._initialize(p2p_21=p2p_21, p2p_12=p2p_12)

        k_list = self.generate_klist()
        if verbose:
            k_list = tqdm(k_list)

        for it, k_curr in enumerate(k_list):

            for it_inner in range(self.opt_params["n_inner"]):

                self.solve_FM_12(k_curr)
                self.solve_FM_21(k_curr)

                self.solve_p2p_21(n_jobs=n_jobs)
                self.solve_p2p_12(n_jobs=n_jobs)


class SmoothDiscreteOptimization():

    def __init__(self, mesh1, mesh2, p2p_12=None, p2p_21=None):

        self.mesh1 = copy.deepcopy(mesh1)
        self.mesh2 = copy.deepcopy(mesh2)

        self.opt_params = None
        self.sp_params = None
        self.sm_params = None

        self.p2p_12 = None
        self.p2p_21 = None

        self.FM_12 = None
        self.FM_21 = None

        self.Y_12 = None
        self.Y_21 = None

        self.p2p_12_init = None
        self.p2p_21_init = None

        if p2p_12 is not None:
            self.p2p_12_init = p2p_12.copy()

        if p2p_21 is not None:
            self.p2p_21_init = p2p_21.copy()

        self.smooth_method = None

    def _set_params(self, method):
        self.sp_params = utils._base_sp_params()
        self.opt_params = utils._base_opt_params(method)
        self.sm_params = utils._base_sm_params(method)

    def solve_FM_12(self, k):
        self.FM_12 = utils.solve_FM_12(self.mesh1, self.mesh2, k, self.p2p_21, p2p_12=self.p2p_12, params=self.sp_params)

    def solve_FM_21(self, k):
        self.FM_21 = utils.solve_FM_12(self.mesh2, self.mesh1, k, self.p2p_12, p2p_12=self.p2p_21, params=self.sp_params)

    def solve_Y_12(self):
        self.sm_params['solver_ind'] = 1
        self.Y_12 = utils.solve_Y21(self.mesh2, self.mesh1, self.p2p_12, p2p_12=self.p2p_21, params=self.sm_params)

    def solve_Y_21(self):
        self.sm_params['solver_ind'] = 2
        self.Y_21 = utils.solve_Y21(self.mesh1, self.mesh2, self.p2p_21, p2p_12=self.p2p_12, params=self.sm_params)

    def solve_p2p_12(self, n_jobs=1, precise=False):
        self.p2p_12 = utils.solve_p2p_21_with_primal(self.mesh2, self.mesh1, self.FM_21, self.Y_12, FM_21=self.FM_12, Y_12=self.Y_21,
                                                     params_sp=self.sp_params, params_sm=self.sm_params, n_jobs=n_jobs, precise=precise)

    def solve_p2p_21(self, n_jobs=1, precise=False):
        self.p2p_21 = utils.solve_p2p_21_with_primal(self.mesh1, self.mesh2, self.FM_12, self.Y_21, FM_21=self.FM_21, Y_12=self.Y_12,
                                                     params_sp=self.sp_params, params_sm=self.sm_params, n_jobs=n_jobs, precise=precise)

    def _prefactor_system(self):
        self.sm_params['solver1'] = utils.generate_solver(self.mesh1, self.sm_params['smooth_weight'], self.sm_params['couple_weight'])
        self.sm_params['solver2'] = utils.generate_solver(self.mesh2, self.sm_params['smooth_weight'], self.sm_params['couple_weight'])

    def generate_klist(self):
        k_init = self.opt_params["k_init"]
        nit = self.opt_params["nit"]
        step = self.opt_params["step"]
        k_max = self.opt_params["k_max"]
        log_space = self.opt_params["log_space"]

        return utils.generate_klist(k_init, nit, step, k_max, log_space=log_space)

    def generate_smooth_reweight_list(self):
        w_min, w_max = self.opt_params['sm_weight_range']
        nit = self.opt_params["nit"]
        smooth_reweight_list = np.geomspace(w_min, w_max, 1+nit)

        return smooth_reweight_list

    def set_init(self, p2p_12=None, p2p_21=None):
        if p2p_12 is not None:
            self.p2p_12_init = p2p_12.copy()

        if p2p_21 is not None:
            self.p2p_21_init = p2p_21.copy()

    def _initialize(self, p2p_21=None, p2p_12=None):
        if p2p_21 is not None:
            self.p2p_21 = p2p_21.copy()
        elif self.p2p_21_init is not None:
            self.p2p_21 = self.p2p_21_init.copy()
        else:
            raise ValueError("NO INITIAL 2->1 MAP")

        if p2p_12 is not None:
            self.p2p_12 = p2p_12.copy()
        elif self.p2p_12_init is not None:
            self.p2p_12 = self.p2p_12_init.copy()
        else:
            raise ValueError("NO INITIAL 1->2 MAP")

        self.FM_12 = None
        self.FM_21 = None

        self.Y_12 = None
        self.Y_21 = None

        if self.sm_params["method"] == 'exact':
            self._prefactor_system()

    def fit(self, p2p_21=None, p2p_12=None, n_jobs=1, verbose=False):

        self._initialize(p2p_21=p2p_21, p2p_12=p2p_12)

        k_list = self.generate_klist()
        if verbose:
            k_list = tqdm(k_list)

        smooth_weight_list = self.generate_smooth_reweight_list()

        for it, k_curr in enumerate(k_list):

            self.sp_params['global_reweight'] = self.sp_params["global_weight"]
            self.sm_params['global_reweight'] = smooth_weight_list[it] * self.sm_params["global_weight"]

            for it_inner in range(self.opt_params["n_inner"]):

                self.solve_FM_12(k_curr)
                self.solve_FM_21(k_curr)

                self.solve_Y_21()
                self.solve_Y_12()

                self.solve_p2p_21(n_jobs=n_jobs)
                self.solve_p2p_12(n_jobs=n_jobs)
