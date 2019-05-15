import numpy as np

from .._base import DReprError
from .._yaml_base import YamlWriterMixin, YamlReaderMixin, YamlReaderException
from ._base import FitDReprBase
from .. import _AVAILABLE_REPRESENTATIONS
from ....fit import IndexedFit, HistFit, XYFit, XYMultiFit
from ..container.yaml_drepr import DataContainerYamlReader, DataContainerYamlWriter
from ..model.yaml_drepr import ParametricModelYamlReader, ParametricModelYamlWriter
from ..constraint.yaml_drepr import ConstraintYamlReader, ConstraintYamlWriter
from ....tools import get_compact_representation

__all__ = ['FitYamlWriter', 'FitYamlReader']

class FitYamlWriter(YamlWriterMixin, FitDReprBase):

    def __init__(self, fit, output_io_handle):
        super(FitYamlWriter, self).__init__(
            output_io_handle=output_io_handle,
            fit=fit)

    def _get_preface_comment(self):
        _preface_comment = super(FitYamlWriter, self)._get_preface_comment()
        _did_fit = self._kafe_object.did_fit
        if not _did_fit:
            _preface_comment += '\n# WARNING: No fit has been performed as of yet. Did you forget to run fit.do_fit()?\n'
        _preface_comment += '\n'
        if self._kafe_object.model_count == 1:
            _preface_comment += "# Model function: %s\n" % self._kafe_object._model_function.formatter.get_formatted(
                format_as_latex=False,
                with_expression=True,
                with_par_values=False
            )
        else:
            for _i in range(self._kafe_object.model_count):
                _preface_comment += "# Model function %s: %s\n" % (_i,
                    self._kafe_object._model_function.formatter.get_formatted(
                        model_index=_i,
                        format_as_latex=False,
                        with_expression=True,
                        with_par_values=False
                    )
                )

        if _did_fit:
            _cost = self._kafe_object.cost_function_value
            _ndf = self._kafe_object._cost_function.ndf
            _round_cost_sig = max(2, int(-np.floor(np.log(_cost)/np.log(10))) + 1)
            _rounded_cost = round(_cost, _round_cost_sig)
            _preface_comment += "# Cost: %s\n" % _rounded_cost
            _preface_comment += '# ndf: %s\n' % _ndf
            _round_cost_per_ndf_sig = max(2, int(-np.floor(np.log(_cost / _ndf)/np.log(10))) + 1)
            _preface_comment += "# Cost/ndf: %s\n\n" % round(_cost / _ndf, _round_cost_per_ndf_sig)

            # If asymmetric parameters errors were not calculated, check the loaded result dict
            _asymmetric_parameter_errors = self._kafe_object._fitter.asymmetric_fit_parameter_errors_if_calculated
            if _asymmetric_parameter_errors is None and self._kafe_object._loaded_result_dict is not None:
                _asymmetric_parameter_errors = self._kafe_object._loaded_result_dict['asymmetric_parameter_errors']

            _preface_comment += get_compact_representation(
                parameter_names=self._kafe_object.parameter_names,
                parameter_values=self._kafe_object.parameter_values,
                parameter_errors=self._kafe_object.parameter_errors,
                parameter_cor_mat=self._kafe_object.parameter_cor_mat,
                asymmetric_parameter_errors=_asymmetric_parameter_errors
            )
        _preface_comment += '\n'
        return _preface_comment

    @classmethod
    def _make_representation(cls, fit):
        _yaml_doc = dict()

        # -- determine fit type
        _type = cls._CLASS_TO_OBJECT_TYPE_NAME.get(fit.__class__, None)
        if _type is None:
            raise DReprError("Fit type unknown or not supported: %s" % fit.__class__)
        _yaml_doc['type'] = _type

        _yaml_doc['dataset'] = DataContainerYamlWriter._make_representation(fit._data_container)
        _yaml_doc['parametric_model'] = ParametricModelYamlWriter._make_representation(fit._param_model)

        #TODO cost function

        _yaml_doc['minimizer'] = fit._minimizer
        _yaml_doc['minimizer_kwargs'] = fit._minimizer_kwargs

        _yaml_doc['parameter_constraints'] = [ConstraintYamlWriter._make_representation(_parameter_constraint)
                                              for _parameter_constraint in fit.parameter_constraints]
        _fit_results = fit.get_result_dict_for_robots()
        _fit_results['parameter_values'] = _fit_results['parameter_values'].tolist()
        if _fit_results['did_fit']:
            _fit_results['parameter_cov_mat'] = _fit_results['parameter_cov_mat'].tolist()
            _fit_results['parameter_errors'] = _fit_results['parameter_errors'].tolist()
            _fit_results['parameter_cor_mat'] = _fit_results['parameter_cor_mat'].tolist()
        if _fit_results['asymmetric_parameter_errors'] is not None:
            _fit_results['asymmetric_parameter_errors'] = _fit_results['asymmetric_parameter_errors'].tolist()
        _yaml_doc['fit_results'] = _fit_results
        return _yaml_doc
    
class FitYamlReader(YamlReaderMixin, FitDReprBase):
    
    def __init__(self, input_io_handle):
        super(FitYamlReader, self).__init__(
            input_io_handle=input_io_handle,
            fit=None)

    @classmethod
    def _get_required_keywords(cls, yaml_doc, fit_class):
        if fit_class in (HistFit, XYFit):
            return ['dataset']
        else:
            return ['dataset', 'parametric_model']
    
    @classmethod
    def _modify_yaml_doc(cls, yaml_doc, kafe_object_class):
        if kafe_object_class is XYMultiFit:
            if 'x_data' in yaml_doc.keys():
                _x_data = yaml_doc.pop('x_data')
                _i = 0
                while 'model_function_%s' % _i in yaml_doc.keys():
                    if 'x_data_%s' not in yaml_doc:
                        yaml_doc['x_data_%s' % _i] = _x_data
                    _i += 1
            if 'y_data' in yaml_doc.keys():
                _y_data = yaml_doc.pop('y_data')
                _i = 0
                while 'model_function_%s' % _i in yaml_doc.keys():
                    if 'y_data_%s' not in yaml_doc:
                        yaml_doc['y_data_%s' % _i] = _y_data
                    _i += 1
        return yaml_doc
    
    @classmethod
    def _get_subspace_override_dict(cls, fit_class):
        _override_dict = {'model_parameters':'parametric_model',
                          'arg_formatters':'parametric_model',
                          'model_function_formatter':'parametric_model'}

        if fit_class is HistFit:
            _override_dict['n_bins'] = ['dataset', 'parametric_model']
            _override_dict['bin_range'] = ['dataset', 'parametric_model']
            _override_dict['bin_edges'] = ['dataset', 'parametric_model']
            _override_dict['raw_data'] = 'dataset'
            _override_dict['errors'] = 'dataset'
            _override_dict['model_density_function'] = 'parametric_model'
            _override_dict['model_density_function_name'] = 'parametric_model'
            _override_dict['latex_model_density_function_name'] = 'parametric_model'
            _override_dict['x_name'] = 'parametric_model'
            _override_dict['latex_x_name'] = 'parametric_model'
            _override_dict['expression_string'] = 'parametric_model'
            _override_dict['latex_expression_string'] = 'parametric_model'
        elif fit_class is IndexedFit:
            _override_dict['data'] = 'dataset'
            _override_dict['errors'] = 'dataset'
            _override_dict['model_function'] = 'parametric_model'
            _override_dict['model_function_name'] = 'parametric_model'
            _override_dict['latex_model_function_name'] = 'parametric_model'
            _override_dict['index_name'] = 'parametric_model'
            _override_dict['latex_index_name'] = 'parametric_model'
            _override_dict['expression_string'] = 'parametric_model'
            _override_dict['latex_expression_string'] = 'parametric_model'
        elif fit_class is XYFit:
            _override_dict['x_data'] = ['dataset', 'parametric_model']
            _override_dict['y_data'] = 'dataset'
            _override_dict['x_errors'] = 'dataset'
            _override_dict['y_errors'] = 'dataset'
            _override_dict['model_function'] = 'parametric_model'
            _override_dict['model_function_name'] = 'parametric_model'
            _override_dict['latex_model_function_name'] = 'parametric_model'
            _override_dict['x_name'] = 'parametric_model'
            _override_dict['latex_x_name'] = 'parametric_model'
            _override_dict['expression_string'] = 'parametric_model'
            _override_dict['latex_expression_string'] = 'parametric_model'
        elif fit_class is XYMultiFit:
            _override_dict['x_data'] = ['dataset', 'parametric_model']
            _override_dict['y_data'] = 'dataset'
            _override_dict['x_errors'] = 'dataset'
            _override_dict['y_errors'] = 'dataset'
            for _i in range(20): #TODO config
                _override_dict['x_data_%s' % _i] = ['dataset', 'parametric_model']
                _override_dict['y_data_%s' % _i] = 'dataset'
                _override_dict['model_function_%s' % _i] = 'parametric_model'
                _override_dict['model_function_name_%s' % _i] = 'parametric_model'
                _override_dict['latex_model_function_name_%s' % _i] = 'parametric_model'
                _override_dict['x_name_%s' % _i] = 'parametric_model'
                _override_dict['latex_x_name_%s' % _i] = 'parametric_model'
                _override_dict['expression_string_%s' % _i] = 'parametric_model'
                _override_dict['latex_expression_string_%s' % _i] = 'parametric_model'
            _override_dict['x_name'] = 'parametric_model'
            _override_dict['latex_x_name'] = 'parametric_model'
        else:
            raise YamlReaderException("Unknown fit type")
        return _override_dict
    
    @classmethod
    def _convert_yaml_doc_to_object(cls, yaml_doc):
        # -- determine fit class from type
        _fit_type = yaml_doc.pop('type')
        _class = cls._OBJECT_TYPE_NAME_TO_CLASS.get(_fit_type, None)

        _data = DataContainerYamlReader._make_object(yaml_doc.pop('dataset'), default_type=_fit_type)
        _parametric_model_entry = yaml_doc.pop('parametric_model', None)
        if _parametric_model_entry:
            _read_parametric_model = ParametricModelYamlReader._make_object(_parametric_model_entry, default_type=_fit_type)
            _read_model_function = _read_parametric_model._model_function_object
        else:
            _read_parametric_model = None
            _read_model_function = None
        #TODO cost function
        _minimizer = yaml_doc.pop('minimizer', None)
        _minimizer_kwargs = yaml_doc.pop('minimizer_kwargs', None)
        if _class is HistFit:
            _fit_object = HistFit(
                data=_data,
                model_density_function=_read_model_function,
                model_density_antiderivative=None,
                minimizer=_minimizer,
                minimizer_kwargs=_minimizer_kwargs
            )
        elif _class is IndexedFit:
            _fit_object = IndexedFit(
                data=_data,
                model_function=_read_model_function,
                minimizer=_minimizer,
                minimizer_kwargs=_minimizer_kwargs
            )
        elif _class is XYFit:
            _fit_object = XYFit(
                xy_data=_data,
                model_function=_read_model_function,
                minimizer=_minimizer,
                minimizer_kwargs=_minimizer_kwargs
            )
        elif _class is XYMultiFit:
            _fit_object = XYMultiFit(
                xy_data=_data,
                model_function=_read_model_function,
                minimizer=_minimizer,
                minimizer_kwargs=_minimizer_kwargs
            )
        if _read_parametric_model is not None:
            _fit_object._param_model = _read_parametric_model
        _constraint_yaml_list = yaml_doc.pop('parameter_constraints', None)
        if _constraint_yaml_list is not None:
            _fit_object._fit_param_constraints = [
                ConstraintYamlReader._make_object(_constraint_yaml, parameter_names=_fit_object.poi_names)
                for _constraint_yaml in _constraint_yaml_list
            ]
        _fit_results = yaml_doc.pop('fit_results', None)
        if _fit_results is not None:
            if _fit_results['did_fit']:
                _fit_results['parameter_cov_mat'] = np.asmatrix(_fit_results['parameter_cov_mat'])
                _fit_results['parameter_errors'] = np.array(_fit_results['parameter_errors'])
                _fit_results['parameter_cor_mat'] = np.asmatrix(_fit_results['parameter_cor_mat'])
            if _fit_results['asymmetric_parameter_errors'] is not None:
                _fit_results['asymmetric_parameter_errors'] = np.array(_fit_results['asymmetric_parameter_errors'])
        _fit_object._loaded_result_dict = _fit_results
        return _fit_object, yaml_doc
    
# register the above classes in the module-level dictionary
FitYamlReader._register_class(_AVAILABLE_REPRESENTATIONS)
FitYamlWriter._register_class(_AVAILABLE_REPRESENTATIONS)