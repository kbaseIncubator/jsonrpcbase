"""
minjsonrpc tests
"""

import minjsonrpc
from nose.tools import *

test_service = minjsonrpc.JSONRPCService()

@test_service()
def subtract(a, b):
    return a - b

@test_service()
def kwargs_subtract(**kwargs):
    return kwargs['a'] - kwargs['b']

@test_service()
def square(a):
    return a * a

@test_service()
def hello():
    return "Hello world!"

@test_service()
def noop(*args, **kwargs):
    pass

@test_service()
def broken_func(a):
    raise TypeError
    
def test_multiple_args():
    """
    Test valid jsonrpc multiple argument calls.
    """
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "subtract", "params": [42, 23], "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['result'], 19)
    assert_equal(result['id'], "1")

def test_kwargs():
    """
    Test valid jsonrpc keyword argument calls.
    """
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "kwargs_subtract", "params": {"a":42, "b":23}, "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['result'], 19)
    assert_equal(result['id'], "1")

def test_single_arg():
    """
    Test valid jsonrpc single argument calls.
    """
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "square", "params": [2], "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['result'], 4)
    assert_equal(result['id'], "1")
    
def test_no_args():
    """
    Test valid jsonrpc no argument calls.
    """
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "hello", "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['result'], "Hello world!")
    assert_equal(result['id'], "1")

def test_notification():
    """
    Test valid notification jsonrpc calls.
    """
    result = test_service.call_py('{"jsonrpc": "2.0", "method": "noop", "params": [1,2,3,4,5]}')
    assert_equal(result, None)
    
    result = test_service.call_py('{"jsonrpc": "2.0", "method": "hello"}')
    assert_equal(result, None)
    
def test_parse_error():
    """
    Test parse error triggering invalid json messages.
    """
    #rpc call with invalid JSON
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "subtract, "params": "bar", "baz]')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32700)
    assert_equal(result['id'], None)
    
def test_invalid_request_error():
    """
    Test invalid request error triggering invalid jsonrpc calls.
    """
    #rpc call with invalid Request object
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": 1, "params": "bar"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32600)
    assert_equal(result['id'], None)
    
def test_method_not_found_error():
    """
    Test method not found error triggering jsonrpc calls.
    """
    #rpc call of non-existent method
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "foofoo", "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32601)
    assert_equal(result['id'], "1")
    
def test_invalid_params_error():
    """
    Test invalid parameters error triggering jsonrpc calls.
    """
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "subtract", "params": ["bar"], "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32602)
    assert_equal(result['id'], "1")
    
def test_server_error():
    """
    Test server error triggering jsonrpc calls.
    """
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "broken_func", "params": [5], "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32000)
    assert_equal(result['id'], "1")
    
def test_version_handling():
    """
    Test version handling with jsonrpc calls.
    """
    result = test_service.call_py('{"jsonrpc": "9999", "method": "noop", "params": {"kwarg": 5}}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32600)
    
    result = test_service.call_py('{"jsonrpc": "2.0", "method": "noop", "params": {"kwarg": 5}}')
    
    assert_equal(result, None)
    
    result = test_service.call_py('{"version": "1.1", "method": "noop", "params": {"kwarg": 5}}')
    
    assert_equal(result, None)
    
    result = test_service.call_py('{"method": "noop", "params": {"kwarg": 5}}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32600)
    

def test_batch():
    """
    Test valid jsonrpc batch calls, no notifications.
    """
    results = test_service.call_py('''
    [
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "square", "params": [4], "id": "1"},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "subtract", "params": [12,3], "id": "2"},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "noop", "id": "3"}
    ]
    ''')
    
    assert_equal(len(results), 3)
    
    for result in results:
        assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
        
        if result['id'] == "1":
            assert_equal(result['result'], 16)
        if result['id'] == "2":
            assert_equal(result['result'], 9)
    
def test_notification_batch():
    """
    Test valid jsonrpc notification only batch calls.
    """
    result = test_service.call_py('''
    [
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "noop", "params": [1,2,4]},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "noop", "params": [7]}
    ]
    ''')
    
    assert_equal(result, None)
        
def test_empty_batch():
    """
    Test invalid empty jsonrpc calls.
    """
    #rpc call with an empty Array
    result = test_service.call_py('[]')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32600)
    assert_equal(result['id'], None)
    
def test_parse_error_batch():
    """
    Test parse error triggering invalid batch calls.
    """
    result = test_service.call_py('[ {"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                      '", "method": "sum", "params": [1,2,4], "id": "1"},{"jsonrpc": "2.0", "method" ]')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['error']['code'], -32700)
    assert_equal(result['id'], None)
    
def test_invalid_batch():
    """
    Test invalid jsonrpc batch calls.
    """
    results = test_service.call_py('[1,2,3]')
    
    assert_equal(len(results), 3)
    
    for result in results:
        assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
        assert_equal(result['error']['code'], -32600)
        assert_equal(result['id'], None)
        
def test_partially_valid_batch():
    """
    Test partially valid jsonrpc batch calls.
    """
    results = test_service.call_py('''
    [
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "square", "params": [2], "id": "1"},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "noop", "params": [7]},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "subtract", "params": [42,23], "id": "2"},
        {"foo": "boo"},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "foo.get", "params": {"name": "myself"}, "id": "5"},
        {"jsonrpc": "''' + minjsonrpc.DEFAULT_JSONRPC + '''", "method": "broken_func", "params": [5], "id": "9"} 
    ]
    ''')
    
    assert_equal(len(results), 5)
    
    for result in results:
        assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
        
        if result['id'] == "1":
            assert_equal(result['result'], 4)
        elif result['id'] == "2":
            assert_equal(result['result'], 19)
        elif result['id'] == "5":
            assert_equal(result['error']['code'], -32601)
        elif result['id'] == "9":
            assert_equal(result['error']['code'], -32000)
        elif result['id'] == None:
            assert_equal(result['error']['code'], -32600)
            
def test_alternate_name():
    """
    Test method calling with alternate name.
    """
    @test_service(name="fihello")
    def finnish_hello():
        return "Hei maailma!"
    
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "fihello", "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['result'], "Hei maailma!")
    assert_equal(result['id'], "1")
    
def test_method_adding():
    """
    Test method adding with the add() method instead of decorator.
    """
    def german_hello():
        return "Hallo Welt!"
    
    test_service.add(german_hello, "gerhello")
    
    result = test_service.call_py('{"jsonrpc": "' + minjsonrpc.DEFAULT_JSONRPC + 
                                              '", "method": "gerhello", "id": "1"}')
    
    assert_equal(result['jsonrpc'], minjsonrpc.DEFAULT_JSONRPC)
    assert_equal(result['result'], "Hallo Welt!")
    assert_equal(result['id'], "1")

if __name__ == '__main__':
    import nose
    nose.main()
