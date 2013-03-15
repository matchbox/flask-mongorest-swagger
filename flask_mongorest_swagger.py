"""
Basic Swagger (https://developers.helloreverb.com/swagger/) support for
Flask-MongoRest.

Usage:
```python
from flask.ext.mongorest import MongoRest, Resource, ResourceView
from flask_mongorest_swagger import Swagger, Parameter, Endpoint
from flask_mongorest_swagger import Operation, Model
from yourapp import app

rest_api = MongoRest(app)
swagger = Swagger(rest_api)

class ApiResource(mongorest.Resource):
    document = DocumentClass
    parameters = {
        'extra_parameter': Parameter('query', 'string',
                                     'Does something else')}

@swagger.register(url='/api-endpoint')
class ApiView(ResourceView):
    resource = ApiResource

@swagger.route(
    '/api-function', methods=['POST'],
    description='The description of this API view',
    endpoints=[Endpoint(
        Endpoint(
            '/api-function/',
            login_description,
            operations=[Operation(
                'POST', 'function', 'More description!',
                response_class='Token',
                parameters={
                    'data': Parameter(
                        'body', 'Input', 'Whatever you need to pass in',
                        required=True)},
                error_responses={401: 'Invalid e-mail/password'})])],
    models={
        'Input': Model('Input', {
            'input_string': Property('string', 'Input to the function')}),
        'Token': Model('Token', {
            'token': Property(
                'string', 'The token which comes back')})})
def api_function():
    return 'Thanks!'
```

This generates a Swagger API available at
<http://localhost:5000/api-docs.json>.

Author: Paul Swartz <pswartz@matchbox.net>
"""
from flask import jsonify as _jsonify, request, abort, Blueprint, url_for
from flask.ext.mongorest import methods
from mongoengine import fields
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict  # noqa
from operator import itemgetter
import re


VIEW_ARGS = re.compile(r'[{]([^{}]+)[}]')
LIST_METHODS = [methods.List, methods.Create, methods.BulkUpdate]
DETAIL_METHODS = [methods.Update, methods.Fetch, methods.Delete]


DEFAULT_METHOD_SUMMARY = {
    methods.List: 'List all %ss',
    methods.Create: 'Create a new %s',
    methods.BulkUpdate: 'Bulk update of %ss',
    methods.Update: 'Update a single %s',
    methods.Fetch: 'Get a single %s',
    methods.Delete: 'Delete a %s'
}


FIELD_TO_TYPE = {
    fields.StringField: 'string',
    fields.IntField: 'int',
    fields.FloatField: 'float',
    fields.BooleanField: 'boolean',
    fields.DateTimeField: 'Date',
    fields.ObjectIdField: 'string'}


def jsonify(data):
    response = _jsonify(data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


def all_values(_name, obj, *args, **kwargs):
    value = getattr(obj, _name, None)
    if value:
        yield value
    if args:
        for arg in args[:-1]:
            if arg:
                yield arg
    if kwargs.get(_name):
        yield kwargs[_name]
    if args:
        yield args[-1]
    else:
        yield None


def first_value(_name, obj, *args, **kwargs):
    for v in all_values(_name, obj, *args, **kwargs):
        if v:
            return v
    # if nothing works, return the last value
    return v


class Api(list):
    """
    A grouping of Endpoints.
    """
    def __init__(self, endpoints=None, models=None, description=''):
        if endpoints is None:
            endpoints = []
        super(Api, self).__init__(endpoints)
        self.description = description
        self.models = models or {}
        for endpoint in endpoints:
            self.models.update(endpoint.models)

    def extend(self, other):
        super(Api, self).extend(other)
        if isinstance(other, Api):
            self.models.update(other.models)


class Endpoint(dict):
    """
    Represents an individual API endpoint.
    """
    def __init__(self, path, description='', operations=None):
        super(Endpoint, self).__init__({
            'path': path,
            'description': description,
            'operations': operations or []})
        self.models = {}


class Operation(dict):
    """
    An Operation is one HTTP method at the given endpoint.
    """
    def __init__(self, method, nickname, summary='', notes='',
                 response_class='', parameters=None, error_responses=None):
        if parameters is None:
            parameters = []
        elif isinstance(parameters, dict):
            parameters = sorted((
                dict(d, name=k)
                for (k, d) in parameters.iteritems()),
                                key=itemgetter('name'))
        if error_responses is None:
            error_responses = []
        elif isinstance(error_responses, dict):
            error_responses = sorted((
                {'code': code, 'reason': reason}
                for (code, reason) in error_responses.iteritems()),
                                    key=itemgetter('code'))
        super(Operation, self).__init__({
            'httpMethod': method,
            'nickname': nickname,
            'summary': summary,
            'notes': notes,
            'responseClass': response_class,
            'parameters': parameters,
            'errorResponses': error_responses})


class Parameter(dict):
    """
    A Parameter is something passed to the endpoint, in the body, headers,
    path, or query.
    """

    def __init__(self, param_type, data_type, description='', required=False,
                 multiple=False, values=None, range=None):
        if param_type not in ('path', 'body', 'query', 'header'):
            raise ValueError('invalid param_type: %r' % (param_type,))
        if param_type == 'path':
            required = True
        d = {'paramType': param_type,
             'dataType': data_type,
             'description': description,
             'required': required,
             'multiple': multiple}
        if values:
            d['allowableValues'] = {'valueType': 'VALUES',
                                    'values': values}
        elif range:
            d['allowableValues'] = {'valueType': 'RANGE',
                                    'min': range[0],
                                    'max': range[1]}
        super(Parameter, self).__init__(d)


class Model(dict):
    """
    Represents a Model returned through the Swagger API.
    """
    def __init__(self, id_, properties=None):
        super(Model, self).__init__({
            'id': id_,
            'properties': properties or {}
        })

    @classmethod
    def from_resource(klass, resource):
        """
        Builds a model from a given `mongorest.Resource`.
        """
        id_ = resource.document.__name__
        properties = {}
        fields = resource.fields or resource.document._fields
        for name in fields:
            field = resource.document._fields[name]
            prop = Property.from_field(field)
            if prop is not None:
                properties[name] = prop
        return klass(id_, properties)


class Property(dict):
    def __init__(self, type_, description=None, subtype=None):
        d = dict(type=type_)
        if description:
            d['description'] = description
        if subtype:
            d['items'] = {'$ref': subtype}
        super(Property, self).__init__(d)

    @classmethod
    def from_field(klass, field):
        if field is None:
            return
        type_ = subtype = None
        description = field.help_text
        if type(field) in FIELD_TO_TYPE:
            # primitive types
            type_ = FIELD_TO_TYPE[type(field)]
        elif isinstance(field, fields.ListField):
            type_ = 'List'
            subprop = klass.from_field(field.field)
            if subprop:
                subtype = subprop['type']
        elif isinstance(field, fields.DictField):
            type_ = 'Object'  # XXX not a real Swagger type
            subprop = klass.from_field(field.field)
            if subprop:
                subtype = subprop['type']
        elif isinstance(field, fields.ReferenceField):
            type_ = 'string'
            if not description:
                'ID for a %s' % field.document_type.__name__
        elif isinstance(field, fields.EmbeddedDocumentField):
            type_ = field.document_type.__name__
        if type_ is None:
            type_ = repr(field)
        return klass(type_, description, subtype)


class Swagger(object):
    def __init__(self, mongorest, api_version=None, swagger_version="1.1",
                 url_prefix=None, document_name='api-docs'):
        self.mongorest = mongorest
        self.app = mongorest.app
        self.api_version = api_version
        self.swagger_version = swagger_version
        self.url_prefix = url_prefix or mongorest.url_prefix or ''
        self.document_name = document_name

        self.blueprint = Blueprint('swagger', __name__)
        self.blueprint.add_url_rule('/%s.json' % document_name,
                                    defaults={'format': 'json'},
                                    view_func=self.api_docs)
        #self.blueprint.add_url_rule('/%s.<format>' % document_name,
        #                            view_func=self.api_docs)
        self.blueprint.add_url_rule('/%s.<format>/<path:name>' % document_name,
                                    view_func=self.api_declaration,
                                    endpoint='declaration')

        self.app.register_blueprint(self.blueprint, url_prefix=self.url_prefix)

        self._apis = OrderedDict()

    def register(self, _view=None, **kwargs):
        """
        Wraps the MongoRest API @register decorator to capture the views
        passed in.  We keep track of them so that we can show them through
        the Swagger endpoints.
        """
        register_kwargs = dict(
            subdomain=kwargs.get('subdomain'),
            build_only=kwargs.get('build_only'),
            endpoint=kwargs.get('endpoint'),
            strict_slashes=kwargs.get('strict_slashes'),
            redirect_to=kwargs.get('redirect_to'),
            alias=kwargs.get('alias'),
            host=kwargs.get('host'))
        for key in ('name', 'url', 'pk_type'):
            if key in kwargs:
                register_kwargs[key] = kwargs[key]

        register_decorator = self.mongorest.register(**register_kwargs)

        def decorator(view):
            self.add_view(view, **kwargs)
            return register_decorator(view)

        if _view is None:
            return decorator
        else:
            return decorator(_view)

    def route(self, url, **kwargs):
        """
        Wraps `app.route()` to also take Swagger API arguments.  Useful for
        documenting APIs implemented as regular view functions.
        """
        name = kwargs.pop('name', None)
        description = kwargs.pop('description', None)
        endpoints = kwargs.pop('endpoints', None)
        models = kwargs.pop('models', None)
        route_decorator = self.app.route('%s%s' % (self.url_prefix, url),
                                         **kwargs)

        def decorator(func):
            self.add_func(func, name, endpoints, models, description)
            return route_decorator(func)

        return decorator

    def add_api(self, name, endpoints=None, models=None, description=''):
        if endpoints is None:
            endpoints = []
        if models is None:
            models = []
        api = Api(endpoints, models, description=description)
        if name in self._apis:
            self._apis[name].extend(api)
        else:
            self._apis[name] = api

    def add_view(self, view, **kwargs):
        document_name = view.resource.document.__name__
        name = first_value(
            'name', view.resource,
            kwargs.get('swagger_name'),
            document_name.lower(),
            **kwargs)
        url = kwargs.pop('url', '/%s/' % name)[1:]
        description = first_value('description', view.resource,
                                  'Operations about %s' % document_name,
                                  **kwargs)
        kwargs['description'] = description
        endpoints = self.endpoints_from_view(view, name, url, **kwargs)
        models = self.models_from_view(view)
        self.add_api(name, endpoints, models, description)

    def add_func(self, func, name=None, endpoints=None, models=None,
                 description=''):
        if name is None:
            name = func.__name__
        self.add_api(name, endpoints, models, description)

    def endpoints_from_view(self, _view, _name, _url, **kwargs):
        url = _url.replace('<', '{').replace('>', '}')  # noqa
        endpoints = []
        resource = _view.resource
        document_name = resource.document.__name__
        document_name_lower = document_name.lower()  # noqa

        for path_template, klasses, response_class in (
                ('/%(url)s', LIST_METHODS, 'List[%(document_name)s]'),
                ('/%(url)s{%(document_name_lower)s}/', DETAIL_METHODS,
                 '%(document_name)s')):
            path = path_template % locals()
            response_class = response_class % locals()
            operations = []
            for method in klasses:
                if method in _view.methods:
                    operations.append(self.operation_from_view_method(
                        _view, path, method, **kwargs))
            endpoints.append(Endpoint(path,
                                      first_value('description', resource, '',
                                                  **kwargs),
                                      operations))

        return endpoints

    def operation_from_view_method(self, _view, path, method, **kwargs):
        resource = _view.resource
        document_name = resource.document.__name__
        document_name_lower = document_name.lower()  # noqa
        parameters = {}
        error_responses = {}
        if _view.authentication_methods:
            error_responses[401] = 'Invalid authentication'
        if method in DETAIL_METHODS:
            error_responses[400] = 'Invalid %s ID' % (
                document_name_lower,)
            error_responses[404] = '%s not found' % document_name
        for extra in all_values('error_responses', resource, {},
                                **kwargs):
            error_responses.update(extra)
        if method.method == 'GET':
            parameters['_fields'] = Parameter(
                'query', 'string',
                'Comma-separated list of fields to return')
        if method == methods.List:
            parameters.update({
                '_skip': Parameter(
                    'query', 'int',
                    'The number of records to skip'),
                '_limit': Parameter(
                    'query', 'int',
                    'The maximum number of records to return',
                    range=(1, 1000))})
            if hasattr(resource, 'filters'):
                for name, filters in resource.filters.iteritems():
                    for f in filters:
                        field = resource.document._fields[name]
                        if isinstance(
                                field,
                                fields.EmbeddedDocumentField):
                            # this is a lookup which allows us to
                            # query subfields; throw them in as
                            # well
                            names, subfields = zip(
                                *field.document_type._fields.items())
                            keys = [
                                '%s__%s' % (name, sub)
                                for sub in names]
                            docs = [sub.help_text for sub in subfields]
                        else:
                            keys = [name]
                            docs = [field.help_text]
                        keys = [(key if f.op in ('', 'exact') else
                               '%s__%s' % (key, f.op))
                                for key in keys]
                        for key, doc in zip(keys, docs):
                            parameters[key] = Parameter(
                                'query', 'string',
                                first_value(
                                    '%s_description' % key,
                                    resource,
                                    doc,
                                    key.rsplit('__', 1)[-1].title(),
                                    **kwargs))
        for extra in all_values('parameters', resource, {}, **kwargs):
            parameters.update(extra)
        view_args = VIEW_ARGS.findall(path)
        if view_args:
            for arg in view_args:
                if arg not in parameters:
                    if arg == document_name_lower:
                        description = 'The %s ID' % arg
                    else:
                        description = ''
                    parameters[arg] = Parameter(
                        'path', 'string',
                        description)
        return Operation(
            method.method,
            '%s%s' % (
                method.__name__.lower(), document_name),
            first_value('%s_summary' % method.__name__.lower(),
                        resource,
                        DEFAULT_METHOD_SUMMARY[method] % (
                            document_name_lower,),
                        **kwargs),
            first_value('%s_notes' % method.__name__.lower(),
                        resource, '', **kwargs),
            response_class=document_name,
            parameters=parameters,
            error_responses=error_responses)

    def models_from_view(self, view):
        model = Model.from_resource(view.resource)
        models = {model['id']: model}
        for resource in view.resource.related_resources.values():
            model = Model.from_resource(resource)
            models[model['id']] = model
        return models

    def _base_data(self, **kwargs):
        adapter = self.app.create_url_adapter(request)
        data = dict({
            'swaggerVersion': self.swagger_version,
            'basePath': adapter.make_redirect_url(self.url_prefix),
        }, **kwargs)
        if self.api_version is not None:
            data['apiVersion'] = self.api_version
        return data

    def api_docs(self, format='json'):
        apis = []
        skip = len(self.url_prefix)
        for name, api in self._apis.iteritems():
            apis.append({
                'path': url_for('.declaration', format=format,
                                name=name)[skip:],
                'description': api.description
            })
        return jsonify(self._base_data(apis=apis))

    def api_declaration(self, format, name):
        api = self._apis.get(name)
        if api is None:
            abort(404)
        skip = len(self.url_prefix)
        return jsonify(self._base_data(
            resourcePath=url_for('.declaration', format=format,
                                 name=name)[skip:],
            apis=api,
            models=api.models))
