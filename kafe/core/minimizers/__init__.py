import abc

from ...config import kc

__all__ = ['get_minimizer']

AVAILABLE_MINIMIZERS = dict()

_MINIMIZER_NAME_ALIASES = dict()

try:
    from .scipy_optimize_minimizer import MinimizerScipyOptimize
    __all__.append('MinimizerScipyOptimize')
    AVAILABLE_MINIMIZERS.update({
        'scipy': MinimizerScipyOptimize,
    })
    _MINIMIZER_NAME_ALIASES['scipy.optimize'] = 'scipy'
except ImportError:
    pass

try:
    from .iminuit_minimizer import MinimizerIMinuit
    __all__.append('MinimizerIMinuit')
    AVAILABLE_MINIMIZERS.update({
        'iminuit': MinimizerIMinuit,
    })
except ImportError:
    pass

try:
    from .root_tminuit_minimizer import MinimizerROOTTMinuit
    __all__.append('MinimizerROOTTMinuit')
    AVAILABLE_MINIMIZERS.update({
        'root.tminuit': MinimizerROOTTMinuit,
    })
    _MINIMIZER_NAME_ALIASES['minuit'] = 'root.tminuit'
    _MINIMIZER_NAME_ALIASES['root'] = 'root.tminuit'
except ImportError:
    pass

# raise if no minimizers can be imported
if not AVAILABLE_MINIMIZERS:
    raise RuntimeError("Fatal error: no minimizers found! Please ensure that "
                       "at least one of the following Python packages is installed: "
                       "['scipy', 'iminuit', 'ROOT']")

def get_minimizer(minimizer_spec=None):
    global AVAILABLE_MINIMIZERS
    # for 'None', return the default minimizer
    if minimizer_spec is None:
        # go through the default minimizers in the order specified in config
        _minimizer_specs = kc('core', 'minimizers', 'default_minimizer_list')

        # try every spec until a minimizer is found
        for _minimizer_spec in _minimizer_specs:
            _minimizer_spec = _minimizer_spec.lower()
            _minimizer_spec = _MINIMIZER_NAME_ALIASES.get(_minimizer_spec, _minimizer_spec)
            _minimizer = AVAILABLE_MINIMIZERS.get(_minimizer_spec, None)
            if _minimizer is not None:
                return _minimizer

        raise ValueError(
            "Could not find any minimizer in default list: {}! Available: {}".format(_minimizer_specs, list(AVAILABLE_MINIMIZERS.keys())))
    else:
        _minimizer_spec = minimizer_spec.lower()
        _minimizer_spec = _MINIMIZER_NAME_ALIASES.get(_minimizer_spec, _minimizer_spec)
        _minimizer = AVAILABLE_MINIMIZERS.get(_minimizer_spec, None)
        if _minimizer is not None:
            return _minimizer

        raise ValueError(
            "Unknown minimizer '{}'! Available: {}".format(minimizer_spec, list(AVAILABLE_MINIMIZERS.keys())))


class MinimizerBase(object):
    """
    Purely abstract class. Defines the minimal interface required by all specializations.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def minimize(self): pass

    @abc.abstractproperty
    def hessian(self): pass

    @abc.abstractproperty
    def hessian_inv(self): pass

    @abc.abstractproperty
    def function_value(self): pass