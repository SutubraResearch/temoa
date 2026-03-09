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
        ExpectedVals.OBJ_VALUE: 468551.6373,
        ExpectedVals.EFF_DOMAIN_SIZE: 30720,
        ExpectedVals.EFF_INDEX_SIZE: 74,
        # upstream demand formulation (period-level + DemandActivity)
        ExpectedVals.CONSTR_COUNT: 2810,
        ExpectedVals.VAR_COUNT: 2008,
    },
    'utopia': {
        # upstream demand formulation (period-level + DemandActivity)
        ExpectedVals.OBJ_VALUE: 34711.5173,
        ExpectedVals.EFF_DOMAIN_SIZE: 12312,
        ExpectedVals.EFF_INDEX_SIZE: 64,
        ExpectedVals.CONSTR_COUNT: 1486,
        ExpectedVals.VAR_COUNT: 1122,
    },
    'mediumville': {
        ExpectedVals.OBJ_VALUE: 7035.7275,
        ExpectedVals.EFF_DOMAIN_SIZE: 2800,
        ExpectedVals.EFF_INDEX_SIZE: 18,
        ExpectedVals.CONSTR_COUNT: 232,
        ExpectedVals.VAR_COUNT: 148,
    },
    'seasonal_storage': {
        ExpectedVals.OBJ_VALUE: 76661.9476,
        ExpectedVals.EFF_DOMAIN_SIZE: 24,
        ExpectedVals.EFF_INDEX_SIZE: 4,
        ExpectedVals.CONSTR_COUNT: 183,
        ExpectedVals.VAR_COUNT: 93,
    },
    'survival_curve': {
        ExpectedVals.OBJ_VALUE: 31.9423,
        ExpectedVals.EFF_DOMAIN_SIZE: 64,
        ExpectedVals.EFF_INDEX_SIZE: 8,
        ExpectedVals.CONSTR_COUNT: 127,
        ExpectedVals.VAR_COUNT: 127,
    },
    'annualised_demand': {
        ExpectedVals.OBJ_VALUE: 1.9524,
        ExpectedVals.EFF_DOMAIN_SIZE: 36,
        ExpectedVals.EFF_INDEX_SIZE: 10,
        ExpectedVals.CONSTR_COUNT: 15,
        ExpectedVals.VAR_COUNT: 21,
    },
}
