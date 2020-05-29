"""
Simple JSON-RPC service without transport layer

This library is intended as an auxiliary library for easy an implementation of JSON-RPC services
with Unix/TCP socket-like transport protocols that do not have complex special requirements. You
need to utilize some suitable transport protocol with this library to actually provide a working
JSON-RPC service.

Features:
- Easy to use, small size, well tested.
- Supports JSON-RPC v2.0. Compatible with v1.x style calls with the exception of v1.0
  class-hinting.
- Optional argument type validation that significantly eases development of jsonrpc method_data.

No support for JSON-RPC v1.0

Example:

    import jsonrpcbase

    chat_service = jsonrpcbase.JSONRPCService()

    def login(username, password, timelimit=0):
        (...)
        return True

    def receive_message(**kwargs):
        (...)
        return chat_message

    def send_message(msg):
        (...)

    if __name__ == '__main__':

        # Adds the method login to the service as a 'login'.
        chat_service.add(login, types=[basestring, basestring, int])

        # Adds the method receive_message to the service as a 'recv_msg'.
        chat_service.add(receive_message, name='recv_msg', types={"msg": basestring, "id": int})

        # Adds the method send_message as a 'send_msg' to the service.
        chat_service.add(send_message, 'send_msg')

        (...)

        # Receive a JSON-RPC call.
        jsonmsg = my_socket.recv()

        # Process the JSON-RPC call.
        result = chat_service.call(jsonmsg)

        # Send back results.
        my_socket.send(result)
"""
import json
import logging
import jsonschema

DEFAULT_JSONRPC = (2, 0)

log = logging.getLogger(__name__)


class JSONRPCService(object):
    """
    The JSONRPCService class is a JSON-RPC
    """

    def __init__(self):
        self.method_data = {}

    def add(self, f, name=None, schema=None):
        """
        Adds a new method to the jsonrpc service.

        Arguments:
        f -- the remote function
        name -- name of the method in the jsonrpc service
        types -- list or dictionary of the types of accepted arguments
        required -- list of required keyword arguments

        If name argument is not given, function's own name will be used.

        Argument types must be a list if positional arguments are used or a dictionary if
        keyword arguments are used in the method in question.

        Argument required MUST be used only for methods requiring keyword arguments, not for
        methods accepting positional arguments.
        """
        if name is None:
            fname = f.__name__  # Register the function using its own name.
        else:
            fname = name
        self.method_data[fname] = {'method': f, 'schema': schema}

    def call(self, jsondata, metadata=None):
        """
        Calls jsonrpc service's method and returns its return value in a JSON string or None
        if there is none.

        Arguments:
        jsondata -- remote method call in jsonrpc format
        metadata -- optional additional data for the function call (eg. an auth token)
        """
        try:
            request_data = json.loads(jsondata)
        except ValueError as err:
            err = self._get_err(ParseError(data={'details': str(err)}))
            return json.dumps(err)
        result = self.call_py(request_data, metadata)
        if result is not None:
            return json.dumps(result)
        return None

    def call_py(self, rdata, metadata=None):
        """
        Calls jsonrpc service's method and returns its return value in python object format or
        None if there is none.

        This method is same as call() except the return value is a python object instead of
        JSON string. This method is mainly only useful for debugging purposes.
        """
        # set some default values for error handling
        request = self._get_default_vals()
        try:
            if isinstance(rdata, dict) and rdata:
                # It's a single request.
                self._fill_request(request, rdata)
                return self._handle_request(request, metadata)
            elif isinstance(rdata, list):
                if not rdata:
                    # Empty list
                    log.exception('Raising InvalidRequestError for empty batch call')
                    data = {'details': 'Batch request array is empty'}
                    raise InvalidRequestError(data=data)
                # It's a batch.
                requests = []
                responds = []
                for rdata_ in rdata:
                    # set some default values for error handling
                    request_ = self._get_default_vals()
                    try:
                        self._fill_request(request_, rdata_)
                    except InvalidRequestError as e:
                        err = self._get_err(e, request_['id'])
                        if err:
                            responds.append(err)
                        continue
                    except JSONRPCError as e:
                        err = self._get_err(e, request_['id'])
                        if err:
                            responds.append(err)
                        continue
                    requests.append(request_)
                for request_ in requests:
                    try:
                        respond = self._handle_request(request_, metadata)
                    except JSONRPCError as e:
                        respond = self._get_err(e, request_['id'], request_['jsonrpc'])
                    # Don't respond to notifications
                    if respond is not None:
                        responds.append(respond)
                if responds:
                    return responds
                # Nothing to respond.
                return None
            else:
                # empty dict, list or wrong type
                log.exception(f'Raising InvalidRequestError for: {rdata}')
                raise InvalidRequestError
        except InvalidRequestError as e:
            return self._get_err(e, request['id'])
        except JSONRPCError as e:
            return self._get_err(e, request['id'], request['jsonrpc'])
        except jsonschema.exceptions.ValidationError as e:
            return self._invalid_params_response(e, request['id'], request['jsonrpc'])

    def _invalid_params_response(self, err, id=None, jsonrpc=DEFAULT_JSONRPC):
        """
        Returns an error message for a jsonschema validation error on the params.
        """
        resp = {'id': id}
        self._fill_ver(jsonrpc, resp)
        resp['error'] = {
            'message': 'Invalid params',
            'data': {
                'details': err.message,
            },
            'code': -32602,
        }
        return resp

    def _get_err(self, e, id=None, jsonrpc=DEFAULT_JSONRPC):
        """
        Returns jsonrpc error message.
        """
        # Do not respond to notifications when the request is valid.
        if id is None and not isinstance(e, ParseError) and not isinstance(e, InvalidRequestError):
            return None
        respond = {'id': id}
        self._fill_ver(jsonrpc, respond)
        respond['error'] = e.dumps()
        return respond

    def _fill_ver(self, ver, respond):
        """
        Fills version information to the respond from the internal tuple version.
        """
        if ver == (2, 0):
            respond['jsonrpc'] = '2.0'
        elif ver == (1, 1):
            respond['version'] = '1.1'
        # No other case possible; _get_jsonrpc will have raised an error or set a default

    def _get_jsonrpc(self, rdata):
        """
        Returns jsonrpc request's jsonrpc value as a tuple of integers.

        InvalidRequestError will be raised if the jsonrpc value has invalid value.
        """
        if rdata.get('jsonrpc') == '2.0':
            # v2.0
            return (2, 0)
        elif rdata.get('version') == '1.1':
            # v1.1
            return (1, 1)
        # Invalid or missing version
        if 'jsonrpc' in rdata or 'version' in rdata:
            log.exception(f'Raising InvalidRequestError for invalid version in {rdata}')
            raise InvalidRequestError(data={'details': 'Invalid JSON-RPC version'})
        else:
            log.exception(f'Raising InvalidRequestError for missing version in {rdata}')
            raise InvalidRequestError(data={'details': 'Missing JSON-RPC version'})

    def _get_id(self, rdata):
        """
        Returns jsonrpc request's id value or None if there is none.

        InvalidRequestError will be raised if the id value has invalid type.
        """
        if 'id' in rdata:
            if type(rdata['id']) in (str, int, float):
                return rdata['id']
            else:
                # invalid type
                log.exception(f'Raising InvalidRequestError for invalid `id` type in {rdata}')
                data = {'details': 'Invalid type for the `id` field'}
                raise InvalidRequestError(data=data)
        else:
            # It's a notification.
            return None

    def _get_method(self, rdata):
        """
        Returns jsonrpc request's method value.

        InvalidRequestError will be raised if it's missing or is wrong type.
        MethodNotFoundError will be raised if a method with given method name does not exist.
        """
        if 'method' in rdata:
            if not isinstance(rdata['method'], str):
                log.exception(f'Raising InvalidRequestError, invalid method type in {rdata}')
                data = {'details': 'Invalid type for the "method" field; must be a string'}
                raise InvalidRequestError(data=data)
        else:
            log.exception(f'Raising InvalidRequestError, missing method in {rdata}')
            data = {'details': 'The required "method" field is missing'}
            raise InvalidRequestError(data=data)
        if rdata['method'] not in self.method_data:
            data = {'available_methods': list(self.method_data.keys())}
            raise MethodNotFoundError(data=data)
        return rdata['method']

    def _get_params(self, rdata):
        """
        Returns a list of jsonrpc request's method parameters.
        """
        if 'params' in rdata:
            if type(rdata['params']) in (dict, list, None):
                return rdata['params']
            else:
                # wrong type
                log.exception(f'Raising InvalidRequestError for: {rdata}')
                data = {'details': 'Invalid type for the `params` field'}
                raise InvalidRequestError(data=data)
        else:
            return None

    def _fill_request(self, request, rdata):
        """Fills request with data from the jsonrpc call."""
        if not isinstance(rdata, dict):
            log.exception(f'Raising InvalidRequestError for: {rdata}')
            raise InvalidRequestError
        request['id'] = self._get_id(rdata)
        request['jsonrpc'] = self._get_jsonrpc(rdata)
        request['method'] = self._get_method(rdata)
        request['params'] = self._get_params(rdata)

    def _call_method(self, request, metadata=None):
        """Calls given method with given params and returns it value."""
        method = self.method_data[request['method']]['method']
        schema = self.method_data[request['method']]['schema']
        params = request['params']
        if schema:
            jsonschema.validate(params, schema)
        result = None
        try:
            result = method(params, metadata)
        except Exception as err:
            log.exception(f"Method {request['method']} threw an exception: {err}")
            # Exception was raised inside the method.
            data = {'details': err.__class__.__name__, 'method': request['method']}
            if hasattr(err, 'message'):
                data['details'] += ': ' + err.message
            raise ServerError(data=data)
        return result

    def _handle_request(self, request, metadata=None):
        """Handles given request and returns its response."""
        result = self._call_method(request, metadata)
        # Do not respond to notifications.
        if request['id'] is None:
            return None
        respond = {}
        self._fill_ver(request['jsonrpc'], respond)
        respond['result'] = result
        respond['id'] = request['id']
        return respond

    def _get_default_vals(self):
        """
        Returns dictionary containing default jsonrpc request/responds values for
        error handling purposes.
        """
        ver = '.'.join(str(i) for i in DEFAULT_JSONRPC)
        return {"jsonrpc": ver, "id": None}


class JSONRPCError(Exception):
    """
    JSONRPCError class based on the JSON-RPC 2.0 specs.
    code - number
    message - string
    """
    code = 0
    message = None
    data = None

    def __init__(self, data=None):
        self.data = data

    def dumps(self):
        """Return the Exception data in a format for JSON-RPC."""
        error = {
            'code': self.code,
            'message': str(self.message),
        }
        if self.data is not None:
            error['data'] = self.data
        return error


# ===============================================================================
# Exceptions
#
# The error-codes -32768 .. -32000 (inclusive) are reserved for pre-defined
# errors.
#
# Any error-code within this range not defined explicitly below is reserved
# for future use
# ===============================================================================

class ParseError(JSONRPCError):
    """Invalid JSON. An error occurred on the server while parsing the JSON text."""
    code = -32700
    message = 'Parse error'


class InvalidRequestError(JSONRPCError):
    """The received JSON is not a valid JSON-RPC Request."""
    code = -32600
    message = 'Invalid Request'


class MethodNotFoundError(JSONRPCError):
    """The requested remote-procedure does not exist / is not available."""
    code = -32601
    message = 'Method not found'


class InternalError(JSONRPCError):
    """Internal JSON-RPC error."""
    code = -32603
    message = 'Internal error'


# -32099..-32000 Server error. Reserved for implementation-defined server-errors.

class ServerError(JSONRPCError):
    """Generic server error."""
    code = -32000
    message = 'Server error'
