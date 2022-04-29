from dataclasses import dataclass, field, InitVar
from typing import Union, Dict, Any
from urllib.parse import urljoin
from ssl import SSLCertVerificationError
from urllib.parse import urlparse, urlunparse

from aiohttp import (
    BasicAuth, ClientSession, ClientTimeout, TCPConnector, ServerTimeoutError)
from aiohttp.web import HTTPException

from . import logger


class JSONRPCError(Exception):
    def __init__(self, message: str, **kwargs):
        super().__init__(message)


class MultiResponseError(Exception):
    def __init__(self, id: Union[int, str]):
        super().__init__(
            f'Multiple responses returned in Response object for id: {id}')


@dataclass
class EmptyResponse(object):
    exception: Exception
    responses: list = field(init=False, default_factory=list)


@dataclass
class Response(object):
    id: Union[int, str] = field(default=None)
    ret: Union[dict, list] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.ret, list):
            if len(self.ret) > 1:
                logger.debug(self.ret)
                raise MultiResponseError(self.id)
            self.ret = self.ret[0]


@dataclass
class Responses(object):
    json: InitVar[dict]
    responses: list = field(init=False, default_factory=list)

    def __post_init__(self, json: dict):
        if 'error' in json.keys():
            raise JSONRPCError(json['error']['message'])

        if 'result' not in json.keys():
            raise JSONRPCError('Missing \'result\' key in json')

        responses = json['result'].get('responses', [])
        if not responses:
            raise JSONRPCError('No responses returned')

        for response in responses:
            json = response.get('json', {})
            if not json:
                raise JSONRPCError('Missing \'json\' key in response')

            id = json.get('id', None)
            error = json.get('error', None)
            if error:
                logger.error(f"Response (id: {id}): {error['message']}")
                continue

            ret = json.get('result', {}).get('_ret_', [])
            if not ret:
                continue

            if isinstance(ret, list):
                for ret_part in ret:
                    self.responses.append(Response(id=id, ret=ret_part))
            else:
                self.responses.append(Response(id=id, ret=ret))


@dataclass(frozen=True)
class RaritanAuth:
    name: str
    url: str
    user: str = field(repr=False)
    password: str = field(repr=False)
    verify_ssl: bool = field(default=False)

    def _strict_type_check(self):
        for (name, field_type) in self.__annotations__.items():
            if not isinstance(self.__dict__[name], field_type):
                current_type = type(self.__dict__[name])
                raise TypeError(
                    f'{name} is of type `{current_type}` but should be of '
                    f'type `{field_type}`')

    def __post_init__(self):
        self._strict_type_check()

        if self.verify_ssl:
            # None uses default ssl verification in aiohttp.TCPConnector
            super().__setattr__('verify_ssl', None)

        url = urlparse(self.url)

        if not url.scheme:
            url._replace(scheme='http')

        if self.name is None:
            super().__setattr__('name', url.netloc)

        super().__setattr__('url', urlunparse(url))


class Request:
    def __init__(self, auth: RaritanAuth, id: Any = 0, collect_id: str = None):
        self.auth = auth
        self.id = id
        self.requests = []
        self.collect_id = collect_id

    def __repr__(self):
        return str(self.json)

    @staticmethod
    def request(method: str, id: Any, params: Dict[str, Any] = None):
        return {
            'jsonrpc': '2.0', 'method': method,
            **({'params': params} if params else {}), 'id': id}

    def add(self, rid: Union[str, int], method: str, id: Any):
        self.requests.append({
            'json': self.request(method, id), 'rid': rid})

    @property
    def json(self):
        return self.request(
            method='performBulk', params={'requests': self.requests},
            id=self.id)

    async def send(self) -> Union[Responses, EmptyResponse]:
        auth = self.auth
        url = urljoin(auth.url, '/bulk')
        ssl = None if auth.verify_ssl else False

        async with ClientSession(
                timeout=ClientTimeout(total=10),
                auth=BasicAuth(auth.user, auth.password, encoding='utf-8'),
                headers={'Content-Type': 'application/json-rpc'},
                connector=TCPConnector(ssl=ssl)) as session:

            try:
                async with session.post(url, json=self.json) as response:
                    return Responses(await response.json())
            except SSLCertVerificationError as exc:
                logger.error(f'(#{self.collect_id}) {exc}')
            except HTTPException as exc:
                logger.warning(f'(#{self.collect_id}) {exc}')
            except ServerTimeoutError as exc:
                logger.warning(f'(#{self.collect_id}) {exc}')

            return EmptyResponse(exception=exc)  # noqa: F821
