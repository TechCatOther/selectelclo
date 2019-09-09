import logging
import json
from flask import Flask, abort, request, Response, jsonify
from werkzeug.exceptions import HTTPException
from keystoneauth1.exceptions import HttpError as KeystoneHttpError

from auth import SelOSAuth
from compute import SelOSCompute, SelOSFlavor

app = Flask(__name__)
openstack_auth = SelOSAuth(cloud_name='openstack')   # Shared session for openstack API connect


@app.route('/v1/<path:service_name>/<path:service_action_name>', methods=['GET', 'POST'])
def action(service_name, service_action_name):
    """
    Main action processing
    :param service_name: One from list of services. Available: servers
    :param service_action_name: For servers: list, create
    :return:
    """
    data = ''  # returning without errors content
    logging.debug("Method: {}, Action: {}, Service: {}".format(request.method, service_action_name, service_name))

    if service_name == 'servers':
        s_compute = SelOSCompute(session=openstack_auth.session)
        if request.method == 'GET' and service_action_name == 'list':
        # List servers
            try:
                data = s_compute.list()
            except ValueError as err:
                logging.error("Can't get list: {}".format(err))
                abort(500)
        elif request.method == 'POST' and service_action_name == 'create':
        # Create servers
            try:
                options = request.json
                data = s_compute.create(options)
            except ValueError as err:
                logging.error("Error when creating: {}".format(err))
                abort(err)
        else:
            abort(404)
    elif service_name == 'flavors':
        s_flavor = SelOSFlavor(session=openstack_auth.session)
        if request.method == 'GET' and service_action_name == 'list':
        # List flavors
            try:
                data = s_flavor.list()
            except ValueError as err:
                logging.error("Cant get flavor list: {}".format(err))
                abort(500)
    else:
        abort(404)
    return jsonify(data)


@app.route('/')
def index():
    """
    Output API version
    :return:
    """
    return jsonify({'version': 'v1.0'})


@app.errorhandler(HTTPException)
def handle_exception(e):
    response = e.get_response()
    response.data = json.dumps({
        e.name: {
            "code": e.code,
            "message": e.description
        }
    })
    response.content_type = "application/json"
    return response


@app.errorhandler(KeystoneHttpError)
def handle_keystone_exception(e):
    logging.error("Request error return: {}".format(vars(e.response)))
    response = Response(status=e.http_status, content_type="application/json")
    error_data = {
        type(e).__name__: {
            "code": e.http_status,
            "message": e.message,
        }
    }
    response.data = json.dumps(error_data)
    return response


def main():
    logging.basicConfig(format='%(asctime)-15s %(message)s', level=logging.DEBUG)
    app.run(host='127.0.0.1',
            port=5000,
            debug=True)


if __name__ == '__main__':
    main()
