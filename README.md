Flask-MongoRest-Swagger
=======================
### Automatic Swagger API generation for Flask-MongoRest

Flask-MongoRest-Swagger takes the API you've built with
[Flask-MongoRest](https://github.com/elasticsales/flask-mongorest), and
automatically generates API documentation compatible with the [Swagger
framework](https://developers.helloreverb.com/swagger/).  You get beautiful,
functional documentation for free!



Installation
------------
You can install Flask-MongoRest-Swagger with `pip`, either

1. `pip install flask-mongorest-swagger` or
2. `pip install https://github.com/matchbox/flask-mongorest-swagger` (if you've got Git installed)


Dependencies
------------
* Flask >= 0.7
* Flask-MongoRest >= 0.1.1
* ordereddict >= 1.1 (only if you're on Python 2.4-2.6)


Example
------
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

if __name __ == '__main__':
    app.run()
```

This generates a Swagger API available at
<http://localhost:5000/api-docs.json>.  You can also see a working example at
<https://api.studentrecord.com/doc/>.


License
-------
Flask-MongoRest-Swagger is released under the MIT license.  See `LICENSE` for more details.


Changelog
---------
See `CHANGES.md` for the changes in each release of Flask-MongoRest-Swagger.


Contributing
------------
Pull requests are always appreciated!


Thanks to
---------
* Swagger <https://developers.helloreverb.com/swagger/>
* Flask <http://flask.pocoo.org/>
* Flask-MongoRest <https://github.com/elasticsales/flask-mongorest>
* Matchbox <http://matchbox.net/>

