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
        # reduced 2026/02 after reverting demand to timeslice level (removed DemandActivity,
        # demand techs no longer get v_flow_out_annual — fixes barrier factorization perf)
        ExpectedVals.CONSTR_COUNT: 2414,
        ExpectedVals.VAR_COUNT: 1900,
    },
    'utopia': {
        # reduced 2026/02 after reverting demand to timeslice level — model now has more
        # dispatch freedom (total demand matches per-timeslice, but individual demand techs
        # no longer individually constrained by DemandActivity)
        ExpectedVals.OBJ_VALUE: 34463.4797,
        ExpectedVals.EFF_DOMAIN_SIZE: 12312,
        ExpectedVals.EFF_INDEX_SIZE: 64,
        # reduced 2026/02 after reverting demand to timeslice level
        ExpectedVals.CONSTR_COUNT: 1291,
        ExpectedVals.VAR_COUNT: 1055,
    },
    'mediumville': {
        ExpectedVals.OBJ_VALUE: 7035.7275,
        ExpectedVals.EFF_DOMAIN_SIZE: 2800,
        ExpectedVals.EFF_INDEX_SIZE: 18,
        # reduced 2026/02 after reverting demand to timeslice level
        ExpectedVals.CONSTR_COUNT: 228,
        ExpectedVals.VAR_COUNT: 140,
    },
    'seasonal_storage': {
        ExpectedVals.OBJ_VALUE: 76661.0231,
        ExpectedVals.EFF_DOMAIN_SIZE: 24,
        ExpectedVals.EFF_INDEX_SIZE: 4,
        # reduced 2026/02 after reverting demand to timeslice level
        ExpectedVals.CONSTR_COUNT: 182,
        ExpectedVals.VAR_COUNT: 90,
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
