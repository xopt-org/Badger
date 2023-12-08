import json
from copy import deepcopy

from xopt.generators import get_generator, get_generator_defaults
from xopt.resources.testing import TEST_VOCS_BASE


class TestFactory:
    def test_generator_generation(self):
        from badger.factory import list_generators

        generator_names = list_generators()

        # test serializing and loading from objects
        for name in generator_names:
            gen_config = get_generator_defaults(name)
            gen_class = get_generator(name)

            if name in ["mobo", "cnsga", "mggpo"]:
                gen_config["reference_point"] = {"y1": 10.0}
                json.dumps(gen_config)

                gen_class(vocs=TEST_VOCS_BASE, **gen_config)
            elif name in ["multi_fidelity"]:
                test_vocs = deepcopy(TEST_VOCS_BASE)
                test_vocs.constraints = {}
                json.dumps(gen_config)

                gen_class(vocs=test_vocs, **gen_config)
            elif name in ["bayesian_exploration"]:
                test_vocs = deepcopy(TEST_VOCS_BASE)
                test_vocs.objectives = {}
                test_vocs.observables = ["f"]
                json.dumps(gen_config)

                gen_class(vocs=test_vocs, **gen_config)
            else:
                json.dumps(gen_config)
                gen_class(vocs=TEST_VOCS_BASE, **gen_config)
