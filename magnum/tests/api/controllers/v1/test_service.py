# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
from magnum.conductor import api
from magnum import objects
from magnum.tests.db import base as db_base
from magnum.tests.db import utils as db_utils

from mock import patch


class TestServiceController(db_base.DbTestCase):

    def mock_service_create(self, service):
        service.create()
        return service

    def mock_service_destroy(self, uuid):
        service = objects.Service.get_by_uuid({}, uuid)
        service.destroy()

    @patch('magnum.common.context.RequestContext')
    def test_service_api(self, mock_RequestContext):
        with patch.object(api.API, 'service_create') as mock_method:
            mock_method.side_effect = self.mock_service_create
            mock_auth_token = mock_RequestContext.auth_token_info['token']
            mock_auth_token['project']['id'].return_value = 'fake_project'
            mock_auth_token['user']['id'].return_value = 'fake_user'
            # Create a bay
            bay = db_utils.create_test_bay()

            # Create a service
            params = '''
            {
                "bay_uuid": "%s",
                "manifest": "\
                {\
                  \\"id\\": \\"service_foo\\",\
                  \\"kind\\": \\"Service\\",\
                  \\"apiVersion\\": \\"v1beta1\\",\
                  \\"port\\": 88,\
                  \\"selector\\": {\
                    \\"bar\\": \\"foo\\"\
                  },\
                  \\"labels\\": {\
                    \\"bar\\": \\"foo\\"\
                  }\
                }\
                \"
            }
            ''' % bay.uuid
            response = self.app.post('/v1/services',
                                     params=params,
                                     content_type='application/json')
            self.assertEqual(response.status_int, 201)
            # Get all services
            response = self.app.get('/v1/services')
            self.assertEqual(response.status_int, 200)
            self.assertEqual(1, len(response.json))
            c = response.json['services'][0]
            self.assertIsNotNone(c.get('uuid'))
            self.assertEqual('service_foo', c.get('name'))
            self.assertEqual(bay.uuid, c.get('bay_uuid'))
            self.assertEqual('foo', c.get('labels')['bar'])
            self.assertEqual('foo', c.get('selector')['bar'])
            self.assertEqual(88, c.get('port'))

            # Get just the one we created
            response = self.app.get('/v1/services/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 200)

            # Update the description
            params = [{'path': '/name',
                       'value': 'service_bar',
                       'op': 'replace'}]
            response = self.app.patch_json('/v1/services/%s' % c.get('uuid'),
                                           params=params)
            self.assertEqual(response.status_int, 200)

        with patch.object(api.API, 'service_delete') as mock_method:
            mock_method.side_effect = self.mock_service_destroy
            # Delete the service we created
            response = self.app.delete('/v1/services/%s' % c.get('uuid'))
            self.assertEqual(response.status_int, 204)

            response = self.app.get('/v1/services')
            self.assertEqual(response.status_int, 200)
            c = response.json['services']
            self.assertEqual(0, len(c))
