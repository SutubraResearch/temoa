"""
a container for test values from legacy code (Python 3.7 / Pyomo 5.5) captured for
continuity/development testing

"""

from enum import Enum


class ExpectedVals(Enum):
    OBJ_VALUE = 'obj_value'
    EFF_DOMAIN_SIZE = 'eff_domain_size'
    EFF_INDEX_SIZE = 'eff_index_size'
    VAR_COUNT = 'count of variables in model'
    CONSTR_COUNT = 'count of constraints in model'


# these values were captured on base level runs of the .dat files in the tests/testing_data folder
test_vals = {
    'test_system': {
        # reduced after removing ancient 1-year-shift obj function bug
        ExpectedVals.OBJ_VALUE: 468551.6373,
        ExpectedVals.EFF_DOMAIN_SIZE: 30720,
        ExpectedVals.EFF_INDEX_SIZE: 74,
        # +420 in 2026/03: restored DemandActivity with reference-timeslice formulation
        # +48 in 2026/03: storage_level_last_tod ties v_storage_level[d_last] to v_storage_init
        ExpectedVals.CONSTR_COUNT: 2882,
        # +48 in 2026/03: v_storage_init added to break storage cycle → chain topology
        ExpectedVals.VAR_COUNT: 1948,
    },
    'utopia': {
        # increased 2026/03 after restoring DemandActivity — proportional dispatch now
        # constrains multi-tech demands (RH: RHE + RHO), reducing dispatch freedom
        ExpectedVals.OBJ_VALUE: 34711.5173,
        ExpectedVals.EFF_DOMAIN_SIZE: 12312,
        ExpectedVals.EFF_INDEX_SIZE: 64,
        # +180 in 2026/03: restored DemandActivity with reference-timeslice formulation
        # (auto-skipped for single-tech demands like RL)
        # +27 in 2026/03: storage_level_last_tod ties v_storage_level[d_last] to v_storage_init
        ExpectedVals.CONSTR_COUNT: 1498,
        # +27 in 2026/03: v_storage_init added to break storage cycle → chain topology
        ExpectedVals.VAR_COUNT: 1082,
    },
    'mediumville': {
        ExpectedVals.OBJ_VALUE: 7035.7275,
        ExpectedVals.EFF_DOMAIN_SIZE: 2800,
        ExpectedVals.EFF_INDEX_SIZE: 18,
        # +12 in 2026/03: restored DemandActivity with reference-timeslice formulation
        # +2 in 2026/03: storage_level_last_tod ties v_storage_level[d_last] to v_storage_init
        ExpectedVals.CONSTR_COUNT: 234,
        # +2 in 2026/03: v_storage_init added to break storage cycle → chain topology
        ExpectedVals.VAR_COUNT: 142,
    },
    'seasonal_storage': {
        # updated 2026/03: v_storage_init changes chain topology, HiGHS takes a slightly
        # different path (0.0012% change — numerical noise, not a model change)
        ExpectedVals.OBJ_VALUE: 76661.9476,
        ExpectedVals.EFF_DOMAIN_SIZE: 24,
        ExpectedVals.EFF_INDEX_SIZE: 4,
        # reduced 2026/02 after reverting demand to timeslice level
        # +2 in 2026/03: storage_level_last_tod ties v_storage_level[d_last] to v_storage_init
        ExpectedVals.CONSTR_COUNT: 184,
        # +2 in 2026/03: v_storage_init added to break storage cycle → chain topology
        ExpectedVals.VAR_COUNT: 92,
    },
    'survival_curve': {
        ExpectedVals.OBJ_VALUE: 31.9423,
        ExpectedVals.EFF_DOMAIN_SIZE: 64,
        ExpectedVals.EFF_INDEX_SIZE: 8,
        # reduced 2026/02 after reverting demand to timeslice level
        ExpectedVals.CONSTR_COUNT: 101,
        ExpectedVals.VAR_COUNT: 101,
    },
    'annualised_demand': {
        ExpectedVals.OBJ_VALUE: 1.9524,
        ExpectedVals.EFF_DOMAIN_SIZE: 36,
        ExpectedVals.EFF_INDEX_SIZE: 10,
        # reduced 2026/02 after reverting demand to timeslice level
        ExpectedVals.CONSTR_COUNT: 14,
        ExpectedVals.VAR_COUNT: 19,
    },
}
