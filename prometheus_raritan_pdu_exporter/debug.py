import inspect
from typing import List, Union

from . import logger


def debug_responses(
        requests: List[str], response_ids: List[Union[int, str]],
        collect_id: str = '-') -> None:
    source = inspect.currentframe().f_back.f_locals['self']
    function = inspect.currentframe().f_back.f_code.co_name
    expected_ids = list(range(0, len(requests)))
    differences = list(set(expected_ids) - set(response_ids))

    if len(differences) > 0:
        names = [requests[difference] for difference in differences]
        logger.debug(
            f"({source.name}#{collect_id}) No {function} response for "
            f"{', '.join(names)}")


def debug_responses_named(
        requests: List[str], response_ids: List[str]):
    source = inspect.currentframe().f_back.f_locals['self']
    function = inspect.currentframe().f_back.f_code.co_name
    expected_ids = set(requests)
    differences = list(set(expected_ids) - set(response_ids))

    if len(differences) > 0:
        logger.debug(
            f"({source.name}) No {function} response for "
            f"{', '.join(differences)}")
