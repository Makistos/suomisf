"""
Tests for user email registration and password reset.

Covers:
- Registration accepting and storing an email address
- Duplicate email rejection
- POST /api/password/forgot (no account enumeration)
- POST /api/password/reset (valid token, single-use, invalid token,
  short password)
- Password length rule (8..128 characters) on registration and reset

Note: Run tests/scripts/setup_test_db.py before running these tests.
The 'log' mail backend (default in tests) does not send real email.
"""
import json
import uuid

from .base_test import BaseAPITest
from app.route_helpers import new_session
from app.orm_decl import User
from app.impl_users import _reset_serializer, _password_fingerprint


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _msg(resp) -> str:
    # Error bodies are json.dumps text without a JSON mimetype.
    return json.loads(resp.response.get_data(as_text=True))['msg']


def _delete_users(*names: str) -> None:
    session = new_session()
    for name in names:
        user = session.query(User).filter(User.name == name).first()
        if user:
            session.delete(user)
    session.commit()


class TestRegistrationEmail(BaseAPITest):
    """Registration with an email address."""

    def test_register_with_email_stores_it(self, api_client):
        name = _unique('reguser')
        email = f"{name}@example.com"
        resp = api_client.post('/api/register', data={
            'username': name, 'password': 'pw123456', 'email': email})
        assert resp.status_code == 200
        assert 'access_token' in resp.json

        session = new_session()
        user = session.query(User).filter(User.name == name).first()
        assert user is not None
        assert user.email == email
        _delete_users(name)

    def test_register_without_email_still_works(self, api_client):
        name = _unique('noemail')
        resp = api_client.post('/api/register', data={
            'username': name, 'password': 'pw123456'})
        assert resp.status_code == 200
        session = new_session()
        user = session.query(User).filter(User.name == name).first()
        assert user is not None
        assert user.email is None
        _delete_users(name)

    def test_register_duplicate_email_rejected(self, api_client):
        email = f"{_unique('dup')}@example.com"
        n1, n2 = _unique('u'), _unique('u')
        r1 = api_client.post('/api/register', data={
            'username': n1, 'password': 'pw123456', 'email': email})
        assert r1.status_code == 200
        r2 = api_client.post('/api/register', data={
            'username': n2, 'password': 'pw123456', 'email': email})
        assert r2.status_code == 401
        _delete_users(n1, n2)


class TestPasswordLength(BaseAPITest):
    """Registration and reset share one rule: 8 to 128 characters."""

    def _register(self, api_client, password):
        name = _unique('pwlen')
        resp = api_client.post('/api/register', data={
            'username': name, 'password': password})
        return name, resp

    def _exists(self, name):
        session = new_session()
        return session.query(User).filter(User.name == name).first()

    def test_register_seven_chars_rejected(self, api_client):
        name, resp = self._register(api_client, 'pw12345')
        assert resp.status_code == 400
        assert 'vähintään 8' in _msg(resp)
        assert self._exists(name) is None

    def test_register_empty_password_rejected(self, api_client):
        # Rejected before the length rule: login_options refuses empty
        # credentials with 401.
        name, resp = self._register(api_client, '')
        assert resp.status_code == 401
        assert self._exists(name) is None

    def test_register_129_chars_rejected(self, api_client):
        name, resp = self._register(api_client, 'a' * 129)
        assert resp.status_code == 400
        assert 'enintään 128' in _msg(resp)
        assert self._exists(name) is None

    def test_register_boundaries_accepted(self, api_client):
        for password in ('pw123456', 'a' * 128):
            name, resp = self._register(api_client, password)
            assert resp.status_code == 200, password
            _delete_users(name)


class TestPasswordReset(BaseAPITest):
    """Forgot-password and reset endpoints."""

    def _make_user(self, api_client):
        name = _unique('resetuser')
        email = f"{name}@example.com"
        resp = api_client.post('/api/register', data={
            'username': name, 'password': 'oldpass1', 'email': email})
        assert resp.status_code == 200
        return name, email

    def _token_for(self, name: str) -> str:
        session = new_session()
        user = session.query(User).filter(User.name == name).first()
        return _reset_serializer().dumps(
            {'uid': user.id, 'fp': _password_fingerprint(user)})

    def test_forgot_unknown_email_returns_200(self, api_client):
        resp = api_client.post('/api/password/forgot', data={
            'email': 'does_not_exist_xyz@example.com'})
        assert resp.status_code == 200

    def test_forgot_known_email_returns_200(self, api_client):
        name, email = self._make_user(api_client)
        resp = api_client.post('/api/password/forgot', data={'email': email})
        assert resp.status_code == 200
        _delete_users(name)

    def test_reset_with_valid_token_changes_password(self, api_client):
        name, _ = self._make_user(api_client)
        token = self._token_for(name)
        resp = api_client.post('/api/password/reset', data={
            'token': token, 'password': 'newpass1'})
        assert resp.status_code == 200
        # New password works, old one does not.
        ok = api_client.post('/api/login', data={
            'username': name, 'password': 'newpass1'})
        assert ok.status_code == 200
        bad = api_client.post('/api/login', data={
            'username': name, 'password': 'oldpass1'})
        assert bad.status_code == 401
        _delete_users(name)

    def test_reset_token_is_single_use(self, api_client):
        name, _ = self._make_user(api_client)
        token = self._token_for(name)
        first = api_client.post('/api/password/reset', data={
            'token': token, 'password': 'newpass1'})
        assert first.status_code == 200
        # Reusing the token fails: the password-hash fingerprint changed.
        second = api_client.post('/api/password/reset', data={
            'token': token, 'password': 'newpass2'})
        assert second.status_code == 400
        _delete_users(name)

    def test_reset_invalid_token(self, api_client):
        resp = api_client.post('/api/password/reset', data={
            'token': 'not-a-real-token', 'password': 'newpass1'})
        assert resp.status_code == 400

    def test_reset_seven_chars_rejected(self, api_client):
        name, _ = self._make_user(api_client)
        token = self._token_for(name)
        resp = api_client.post('/api/password/reset', data={
            'token': token, 'password': 'pw12345'})
        assert resp.status_code == 400
        assert 'vähintään 8' in _msg(resp)
        _delete_users(name)

    def test_reset_129_chars_rejected(self, api_client):
        name, _ = self._make_user(api_client)
        token = self._token_for(name)
        resp = api_client.post('/api/password/reset', data={
            'token': token, 'password': 'a' * 129})
        assert resp.status_code == 400
        assert 'enintään 128' in _msg(resp)
        _delete_users(name)

    def test_reset_short_password_rejected(self, api_client):
        name, _ = self._make_user(api_client)
        token = self._token_for(name)
        resp = api_client.post('/api/password/reset', data={
            'token': token, 'password': '123'})
        assert resp.status_code == 400
        _delete_users(name)
