from __future__ import absolute_import

import os
import json
import re

from app import create_app, data_api_client
from datetime import datetime, timedelta
from mock import patch
from werkzeug.http import parse_cookie
from lxml import html

from dmutils.formats import DATETIME_FORMAT


class BaseApplicationTest(object):
    def setup_method(self, method):
        # We need to mock the API client in create_app, however we can't use patch the constructor,
        # as the DataAPIClient instance has already been created; nor can we temporarily replace app.data_api_client
        # with a mock, because then the shared instance won't have been configured (done in create_app). Instead,
        # just mock the one function that would make an API call in this case.
        self.app_env_var_mock = patch.dict('gds_metrics.os.environ', {'PROMETHEUS_METRICS_PATH': '/_metrics'})
        self.app_env_var_mock.start()

        self.session_mock = patch('dmutils.session.init_app')
        self.session_mock.start()

        self.app = create_app('test')
        self.client = self.app.test_client()
        self.get_user_patch = None

    def teardown_method(self, method):
        self.teardown_login()
        self.app_env_var_mock.stop()
        self.session_mock.stop()

    @staticmethod
    def user(id, email_address, supplier_id, supplier_name, name,
             is_token_valid=True, locked=False, active=True, role='buyer',
             userResearchOptedIn=True):

        hours_offset = -1 if is_token_valid else 1
        date = datetime.utcnow() + timedelta(hours=hours_offset)
        password_changed_at = date.strftime(DATETIME_FORMAT)

        user = {
            "id": id,
            "emailAddress": email_address,
            "name": name,
            "role": role,
            "locked": locked,
            'active': active,
            'passwordChangedAt': password_changed_at,
            "userResearchOptedIn": userResearchOptedIn
        }

        if supplier_id:
            supplier = {
                "supplierId": supplier_id,
                "name": supplier_name,
            }
            user['role'] = 'supplier'
            user['supplier'] = supplier
        return {
            "users": user
        }

    @staticmethod
    def _get_fixture_data(fixture_filename):
        test_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".")
        )
        fixture_path = os.path.join(
            test_root, 'fixtures', fixture_filename
        )
        with open(fixture_path) as fixture_file:
            return json.load(fixture_file)

    @staticmethod
    def _get_search_results_fixture_data():
        return BaseApplicationTest._get_fixture_data(
            'search_results_fixture.json'
        )

    @staticmethod
    def _get_g9_search_results_fixture_data():
        return BaseApplicationTest._get_fixture_data(
            'g9_search_results_fixture.json'
        )

    @staticmethod
    def _get_search_results_multiple_page_fixture_data():
        return BaseApplicationTest._get_fixture_data(
            'search_results_multiple_pages_fixture.json'
        )

    @staticmethod
    def _get_frameworks_list_fixture_data():
        return BaseApplicationTest._get_fixture_data('frameworks.json')

    @staticmethod
    def _get_g4_service_fixture_data():
        return BaseApplicationTest._get_fixture_data('g4_service_fixture.json')

    @staticmethod
    def _get_g5_service_fixture_data():
        return BaseApplicationTest._get_fixture_data('g5_service_fixture.json')

    @staticmethod
    def _get_g6_service_fixture_data():
        return BaseApplicationTest._get_fixture_data('g6_service_fixture.json')

    @staticmethod
    def _get_framework_fixture_data(framework_slug):
        return {
            'frameworks': next(f for f in BaseApplicationTest._get_frameworks_list_fixture_data()['frameworks']
                               if f['slug'] == framework_slug)
        }

    @staticmethod
    def _get_dos_brief_fixture_data(multi=False):
        if multi:
            return BaseApplicationTest._get_fixture_data('dos_multiple_briefs_fixture.json')
        else:
            return BaseApplicationTest._get_fixture_data('dos_brief_fixture.json')

    @staticmethod
    def _get_dos_brief_responses_fixture_data():
        return BaseApplicationTest._get_fixture_data('dos_brief_responses_fixture.json')

    @staticmethod
    def _get_supplier_fixture_data():
        return BaseApplicationTest._get_fixture_data('supplier_fixture.json')

    @staticmethod
    def _get_supplier_with_minimum_fixture_data():
        return BaseApplicationTest._get_fixture_data('supplier_fixture_with_minium_data.json')

    @staticmethod
    def _get_suppliers_by_prefix_fixture_data():
        return BaseApplicationTest._get_fixture_data(
            'suppliers_by_prefix_fixture.json')

    @staticmethod
    def _get_suppliers_by_prefix_fixture_data_page_2():
        return BaseApplicationTest._get_fixture_data(
            'suppliers_by_prefix_fixture_page_2.json')

    @staticmethod
    def _get_suppliers_by_prefix_fixture_with_next_and_prev():
        return BaseApplicationTest._get_fixture_data(
            'suppliers_by_prefix_fixture_page_with_next_and_prev.json')

    @staticmethod
    def _strip_whitespace(whitespace_in_this):
        return re.sub(r"\s+", "",
                      whitespace_in_this, flags=re.UNICODE)

    @staticmethod
    def _normalize_whitespace(whitespace_in_this):
        # NOTE proper xml-standard way of doing this is a little more complex afaik
        return re.sub(r"\s+", " ",
                      whitespace_in_this, flags=re.UNICODE).strip()

    @classmethod
    def _squashed_element_text(cls, element):
        return element.text + "".join(
            cls._squashed_element_text(child_element) + child_element.tail for child_element in element
        )

    def teardown_login(self):
        if self.get_user_patch is not None:
            self.get_user_patch.stop()

    def login_as_supplier(self):
        with patch('app.main.views.auth.data_api_client') as login_api_client:
            login_api_client.authenticate_user.return_value = self.user(
                123, "email@email.com", 1234, 'Supplier Name', 'Name', role='supplier')

            self.get_user_patch = patch.object(
                data_api_client,
                'get_user',
                return_value=self.user(123, "email@email.com", 1234, 'Supplier Name', 'Name', role='supplier')
            )
            self.get_user_patch.start()

            self.client.post("/user/login", data={
                'email_address': 'valid@email.com',
                'password': '1234567890'
            })

            login_api_client.authenticate_user.assert_called_once_with(
                "valid@email.com", "1234567890")

    def login_as_buyer(self, user_research_opt_in=True):
        with patch('app.main.views.auth.data_api_client') as login_api_client:
            login_api_client.authenticate_user.return_value = self.user(
                123, "buyer@email.com", None, None, 'Name')

            self.get_user_patch = patch.object(
                data_api_client,
                'get_user',
                return_value=self.user(
                    123, "buyer@email.com", None, None, 'Some Buyer',
                    userResearchOptedIn=user_research_opt_in)
            )
            self.get_user_patch.start()

            self.client.post("/user/login", data={
                'email_address': 'valid@email.com',
                'password': '1234567890'
            })

            login_api_client.authenticate_user.assert_called_once_with(
                "valid@email.com", "1234567890")

    def login_as_admin(self):
        with patch('app.main.views.auth.data_api_client') as login_api_client:
            login_api_client.authenticate_user.return_value = self.user(
                123, "admin@email.com", None, None, 'Name', role='admin')

            self.get_user_patch = patch.object(
                data_api_client,
                'get_user',
                return_value=self.user(123, "admin@email.com", None, None, 'Some Admin', role='admin')
            )
            self.get_user_patch.start()

            self.client.post("/user/login", data={
                'email_address': 'valid@email.com',
                'password': '1234567890'
            })

            login_api_client.authenticate_user.assert_called_once_with(
                "valid@email.com", "1234567890")

    @staticmethod
    def get_cookie_by_name(response, name):
        cookies = response.headers.getlist('Set-Cookie')
        for cookie in cookies:
            if name in parse_cookie(cookie):
                return parse_cookie(cookie)
        return None

    @staticmethod
    def strip_all_whitespace(content):
        pattern = re.compile(r'\s+')
        return re.sub(pattern, '', content)

    # Method to test flashes taken from http://blog.paulopoiati.com/2013/02/22/testing-flash-messages-in-flask/
    def assert_flashes(self, expected_message, expected_category='message'):
        with self.client.session_transaction() as session:
            try:
                category, message = session['_flashes'][0]
            except KeyError:
                raise AssertionError('nothing flashed')
            assert expected_message in message, message
            assert expected_category == category

    def assert_breadcrumbs(self, response, extra_breadcrumbs=None):
        breadcrumbs = html.fromstring(response.get_data(as_text=True)).cssselect('.govuk-breadcrumbs ol li')

        breadcrumbs_we_expect = [('Digital Marketplace', '/')]
        if extra_breadcrumbs:
            breadcrumbs_we_expect.extend(extra_breadcrumbs)

        assert len(breadcrumbs) == len(breadcrumbs_we_expect)

        for index, link in enumerate(breadcrumbs_we_expect):
            if link[1] is None:
                # a non-link breadcrumb
                assert breadcrumbs[index].xpath("normalize-space(string())") == link[0]
                assert not breadcrumbs[index].find("a")
            else:
                assert breadcrumbs[index].find('a').xpath("normalize-space(string())") == link[0]
                assert breadcrumbs[index].find('a').get('href').strip() == link[1]


class MockMatcher(object):
    """A helper object that compares based on the function return value."""
    def __init__(self, fn):
        self.fn = fn

    def __eq__(self, other):
        return self.fn(other)
