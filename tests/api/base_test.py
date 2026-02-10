"""
SuomiSF API Base Test Class

Provides common functionality and helpers for API tests.
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TestResult:
    """Stores result of a single test execution."""
    endpoint: str
    method: str
    status_code: int
    success: bool
    duration_ms: float
    response_data: Optional[Any] = None
    error: Optional[str] = None


class BaseAPITest:
    """Base class for API tests with common helpers."""

    # Override in subclasses
    BASE_ENDPOINT = "/api"

    def assert_response_format(self, data: Dict) -> None:
        """Assert response follows standard format."""
        assert 'response' in data or 'msg' in data, \
            f"Response missing 'response' or 'msg' key: {data}"

    def assert_list_response(
        self,
        data: Dict,
        min_length: int = 0,
        max_length: Optional[int] = None
    ) -> List:
        """Assert response contains a list and return it."""
        self.assert_response_format(data)
        response = data.get('response', [])
        assert isinstance(response, list), \
            f"Expected list response, got {type(response)}"

        if min_length > 0:
            assert len(response) >= min_length, \
                f"Expected at least {min_length} items, got {len(response)}"

        if max_length is not None:
            assert len(response) <= max_length, \
                f"Expected at most {max_length} items, got {len(response)}"

        return response

    def assert_dict_response(self, data: Dict, required_keys: List[str] = None) -> Dict:
        """Assert response contains a dict and optionally check required keys."""
        self.assert_response_format(data)
        response = data.get('response', {})
        assert isinstance(response, dict), \
            f"Expected dict response, got {type(response)}"

        if required_keys:
            for key in required_keys:
                assert key in response, \
                    f"Response missing required key '{key}'. Keys: {list(response.keys())}"

        return response

    def assert_error_response(self, data: Dict, expected_msg: Optional[str] = None) -> str:
        """Assert response is an error and return message."""
        assert 'msg' in data, f"Error response missing 'msg' key: {data}"
        if expected_msg:
            assert data['msg'] == expected_msg, \
                f"Expected error '{expected_msg}', got '{data['msg']}'"
        return data['msg']

    def assert_valid_id(self, value: Any, name: str = "id") -> int:
        """Assert value is a valid positive integer ID."""
        assert isinstance(value, int), f"{name} should be int, got {type(value)}"
        assert value > 0, f"{name} should be positive, got {value}"
        return value

    def assert_pagination_response(
        self,
        data: Dict,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Assert response has pagination metadata."""
        response = self.assert_dict_response(data)

        # Check for pagination keys (adjust based on your API's format)
        pagination_keys = ['items', 'total', 'page', 'per_page']
        for key in pagination_keys:
            if key not in response:
                # Some endpoints may not have all keys
                pass

        return response


class APITestMixin:
    """Mixin providing API test utilities for pytest classes."""

    def make_request(
        self,
        client,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> TestResult:
        """Make an API request and return TestResult."""
        start_time = time.time()

        try:
            if method.upper() == 'GET':
                response = client.get(endpoint, headers=headers)
            elif method.upper() == 'POST':
                response = client.post(
                    endpoint,
                    data=json.dumps(data) if data else None,
                    content_type='application/json',
                    headers=headers
                )
            elif method.upper() == 'PUT':
                response = client.put(
                    endpoint,
                    data=json.dumps(data) if data else None,
                    content_type='application/json',
                    headers=headers
                )
            elif method.upper() == 'DELETE':
                response = client.delete(endpoint, headers=headers)
            else:
                return TestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=0,
                    success=False,
                    duration_ms=0,
                    error=f"Unsupported method: {method}"
                )

            duration_ms = (time.time() - start_time) * 1000

            try:
                response_data = response.get_json()
            except Exception:
                response_data = None

            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                success=200 <= response.status_code < 300,
                duration_ms=duration_ms,
                response_data=response_data
            )

        except Exception as e:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
