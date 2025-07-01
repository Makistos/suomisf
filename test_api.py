#!/usr/bin/env python3
"""
SuomiSF API Testing Script
Simple script to test API endpoints and validate responses.
"""

import requests
import json
from typing import Dict, Any, Optional
import time


class SuomiSFAPITester:
    """Simple API testing client for SuomiSF."""

    def __init__(self, base_url: str = "http://www.sf-bibliografia.fi/api"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.access_token: Optional[str] = None

    def login(self, username: str, password: str) -> bool:
        """Login and store access token."""
        try:
            response = self.session.post(f"{self.base_url}/login", json={
                "username": username,
                "password": password
            })

            if response.status_code == 200:
                data = response.json()
                response_data = data.get('response', {})
                self.access_token = response_data.get('access_token')
                if self.access_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })
                    print(f"✅ Login successful for user: {username}")
                    return True

            print(f"❌ Login failed: {response.status_code}")
            return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def test_endpoint(self, method: str, path: str,
                      data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a single API endpoint."""
        url = f"{self.base_url}{path}"

        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                return {"error": f"Unsupported method: {method}"}

            result = {
                "method": method.upper(),
                "url": url,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "response_time": response.elapsed.total_seconds()
            }

            try:
                result["response_data"] = response.json()
            except Exception:
                text = response.text
                if len(text) > 200:
                    result["response_text"] = text[:200] + "..."
                else:
                    result["response_text"] = text

            return result

        except Exception as e:
            return {
                "method": method.upper(),
                "url": url,
                "error": str(e),
                "success": False
            }

    def run_basic_tests(self) -> None:
        """Run a set of basic API tests."""
        print("🧪 Running SuomiSF API Tests")
        print("=" * 50)

        # Test public endpoints
        public_tests = [
            ("GET", "/frontpagedata"),
            ("GET", "/genres"),
            ("GET", "/roles/"),
            ("GET", "/countries"),
            ("GET", "/latest/works/5"),
            ("GET", "/latest/people/5"),
            ("GET", "/latest/editions/5"),
        ]

        print("\n📖 Testing Public Endpoints:")
        for method, path in public_tests:
            result = self.test_endpoint(method, path)
            status = "✅" if result.get("success") else "❌"
            print(f"{status} {method} {path} - {result.get('status_code', 'ERROR')}")
            time.sleep(0.1)  # Be nice to the server

        # Test search endpoints
        print("\n🔍 Testing Search Endpoints:")
        search_tests = [
            ("POST", "/searchworks", {"title": "test"}),
            ("POST", "/searchshorts", {"title": "test"}),
        ]

        for method, path, data in search_tests:
            result = self.test_endpoint(method, path, data)
            status = "✅" if result.get("success") else "❌"
            print(f"{status} {method} {path} - {result.get('status_code', 'ERROR')}")
            time.sleep(0.1)

        # Test filter endpoints
        print("\n🔄 Testing Filter Endpoints:")
        filter_tests = [
            ("GET", "/filter/people/test"),
            ("GET", "/filter/tags/test"),
            ("GET", "/filter/countries/fin"),
        ]

        for method, path in filter_tests:
            result = self.test_endpoint(method, path)
            status = "✅" if result.get("success") else "❌"
            print(f"{status} {method} {path} - {result.get('status_code', 'ERROR')}")
            time.sleep(0.1)

        print("\n📊 Test Summary:")
        print("- Public endpoints tested")
        print("- Search functionality tested")
        print("- Filter functionality tested")
        print("- Note: Admin endpoints require authentication")

    def test_authentication_flow(self, username: str, password: str) -> None:
        """Test the authentication flow."""
        print("\n🔐 Testing Authentication Flow:")

        # Test login
        login_result = self.test_endpoint("POST", "/login", {
            "username": username,
            "password": password
        })

        status = "✅" if login_result.get("success") else "❌"
        print(f"{status} Login attempt - {login_result.get('status_code', 'ERROR')}")

        if login_result.get("success"):
            # Extract token from response
            response_data = login_result.get("response_data", {})
            if isinstance(response_data, dict) and "response" in response_data:
                token_data = response_data["response"]
                if isinstance(token_data, dict) and "access_token" in token_data:
                    self.access_token = token_data["access_token"]
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })
                    print("✅ Token extracted and set for future requests")

        # Test token refresh if we have a refresh token
        if self.access_token:
            refresh_result = self.test_endpoint("POST", "/refresh")
            status = "✅" if refresh_result.get("success") else "❌"
            print(f"{status} Token refresh - {refresh_result.get('status_code', 'ERROR')}")


def main():
    """Main testing function."""
    tester = SuomiSFAPITester()

    print("SuomiSF API Testing Tool")
    print("========================")
    print(f"Base URL: {tester.base_url}")

    # Run basic tests
    tester.run_basic_tests()

    # Optional: Test authentication if credentials are provided
    print("\n" + "=" * 50)
    print("💡 To test authentication endpoints:")
    print("   python3 test_api.py --login <username> <password>")
    print("\n💡 To test individual endpoints:")
    print("   python3 test_api.py --test GET /api/works/1")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--login" and len(sys.argv) >= 4:
            tester = SuomiSFAPITester()
            username, password = sys.argv[2], sys.argv[3]
            tester.test_authentication_flow(username, password)
        elif sys.argv[1] == "--test" and len(sys.argv) >= 4:
            tester = SuomiSFAPITester()
            method, path = sys.argv[2], sys.argv[3]
            result = tester.test_endpoint(method, path)
            print(json.dumps(result, indent=2))
        else:
            print("Usage:")
            print("  python3 test_api.py                    # Run basic tests")
            print("  python3 test_api.py --login user pass  # Test authentication")
            print("  python3 test_api.py --test GET /path   # Test specific endpoint")
    else:
        main()
