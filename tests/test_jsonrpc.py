"""Tests for prometheus_raritan_pdu_exporter/jsonrpc.py"""
import pytest

from prometheus_raritan_pdu_exporter.jsonrpc import (
    JSONRPCError, MultiResponseError, Response, Responses, RaritanAuth,
    Request)


def test_response():
    ret = {'foo': 'bar'}
    for resp in (Response(id=1, ret=ret), Response(id=1, ret=[ret])):
        assert resp.id == 1
        assert resp.ret['foo'] == 'bar'

    with pytest.raises(MultiResponseError):
        Response(id=1, ret=[{'foo': 'bar'}, {'bar': 'baz'}])


def test_responses_errors():
    """test the correct identification of errors"""
    # 'error' key present
    json = {'error': {'message': 'something went wrong'}}
    with pytest.raises(JSONRPCError):
        Responses(json=json)

    # missing 'result' key
    json = {'foo': 'bar'}
    with pytest.raises(JSONRPCError):
        Responses(json=json)

    # no responses returned
    json = {'result': {'responses': []}}
    with pytest.raises(JSONRPCError):
        Responses(json=json)


def test_responses_single():
    """correct bulk result with single response should pass"""
    json = {
        'result': {'responses': [
            {'json': {'id': 1, 'result': {'_ret_': {'foo': 'bar'}}}}]}}
    resp = Responses(json=json)
    assert len(resp.responses) == 1
    assert all(isinstance(response, Response) for response in resp.responses)
    assert resp.responses[0].id == 1
    assert resp.responses[0].ret['foo'] == 'bar'


def test_responses_multi_returns():
    """correct bulk result with multiple returns should pass"""
    json = {
        'result': {'responses': [
            {'json': {'id': 1, 'result': {'_ret_': [
                {'foo': 'bar'}, {'bar': 'baz'}]}}}]}}
    resp = Responses(json=json)
    assert len(resp.responses) == 2
    assert all(isinstance(response, Response) for response in resp.responses)
    assert resp.responses[0].id == 1
    assert resp.responses[0].ret['foo'] == 'bar'
    assert resp.responses[1].id == 1
    assert resp.responses[1].ret['bar'] == 'baz'


def test_responses_multi_responses():
    """correct bulk result with multiple returns should pass"""
    json = {
        'result': {'responses': [
            {'json': {'id': 1, 'result': {'_ret_': {'foo': 'bar'}}}},
            {'json': {'id': 2, 'result': {'_ret_': {'bar': 'baz'}}}}]}}
    resp = Responses(json=json)
    assert len(resp.responses) == 2
    assert all(isinstance(response, Response) for response in resp.responses)
    assert resp.responses[0].id == 1
    assert resp.responses[0].ret['foo'] == 'bar'
    assert resp.responses[1].id == 2
    assert resp.responses[1].ret['bar'] == 'baz'


def test_responses_multi_response_multi_returns():
    """correct bulk result with multiple responses and returns should pass"""
    json = {
        'result': {'responses': [
            {'json': {'id': 1, 'result': {'_ret_': [
                {'foo': 'bar'}, {'bar': 'baz'}]}}},
            {'json': {'id': 2, 'result': {'_ret_': [
                {'lorem': 'ipsum'}, {'dolor': 'sit amet'}]}}}]}}
    resp = Responses(json=json)
    assert len(resp.responses) == 4
    assert all(isinstance(response, Response) for response in resp.responses)
    assert resp.responses[0].id == 1
    assert resp.responses[0].ret['foo'] == 'bar'
    assert resp.responses[1].id == 1
    assert resp.responses[1].ret['bar'] == 'baz'
    assert resp.responses[2].id == 2
    assert resp.responses[2].ret['lorem'] == 'ipsum'
    assert resp.responses[3].id == 2
    assert resp.responses[3].ret['dolor'] == 'sit amet'


def test_responses_multi_responses_containing_errors():
    """correct bulk result with some error responses should pass"""
    json = {
        'result': {'responses': [
            {'json': {'id': 1, 'result': {'_ret_': {'foo': 'bar'}}}},
            {'json': {'id': 2, 'error': {'message': 'something went wrong'}}},
            {'json': {'id': 3, 'result': {'_ret_': {'bar': 'baz'}}}}]}}
    resp = Responses(json=json)
    assert len(resp.responses) == 2
    assert all(isinstance(response, Response) for response in resp.responses)
    assert resp.responses[0].id == 1
    assert resp.responses[0].ret['foo'] == 'bar'
    assert resp.responses[1].id == 3
    assert resp.responses[1].ret['bar'] == 'baz'


def test_raritan_auth():
    auth = RaritanAuth(
        name='foo', url='https://127.0.0.1:9840', user='admin', password='xxx')
    assert auth.name == 'foo'
    assert auth.url == 'https://127.0.0.1:9840'
    assert auth.user == 'admin'
    assert auth.password == 'xxx'
    assert not auth.verify_ssl
    assert auth.__dataclass_params__.frozen

    auth = RaritanAuth(
        name='foo', url='https://127.0.0.1:9840', user='admin', password='xxx',
        verify_ssl=True)
    assert auth.verify_ssl is None


def test_request_init():
    auth = RaritanAuth(
        name='foo', url='https://127.0.0.1:9840', user='admin', password='xxx')
    request = Request(auth=auth, id='bar')
    assert request.auth is auth
    assert request.id == 'bar'
    assert isinstance(request.requests, list)
    assert not request.requests


def test_request_request():
    pass


def test_request_add():
    auth = RaritanAuth(
        name='baz', url='https://127.0.0.1:9840', user='admin', password='xxx')
    request = Request(auth=auth, id='foo')

    expected_json = {'jsonrpc': '2.0', 'method': 'getFoo', 'id': 1}
    request.add(rid='unique_id/1', method='getFoo', id=1)
    assert len(request.requests) == 1
    assert request.requests[0]['json'] == expected_json
    assert request.requests[0]['rid'] == 'unique_id/1'

    expected_json = {'jsonrpc': '2.0', 'method': 'getBar', 'id': 2}
    request.add(rid='unique_id/2', method='getBar', id=2)
    assert len(request.requests) == 2
    assert request.requests[1]['json'] == expected_json
    assert request.requests[1]['rid'] == 'unique_id/2'
