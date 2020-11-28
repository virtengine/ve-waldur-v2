import base64
import logging
import uuid

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import generics, response, status, views
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException, ValidationError

from waldur_core.core.models import SshPublicKey
from waldur_core.core.views import RefreshTokenMixin, validate_authentication_method

from . import tasks
from .log import event_logger, provider_event_type_mapping
from .models import AuthProfile
from .serializers import ActivationSerializer, AuthSerializer, RegistrationSerializer

logger = logging.getLogger(__name__)

auth_social_settings = getattr(settings, 'WALDUR_AUTH_SOCIAL', {})
FACEBOOK_SECRET = auth_social_settings.get('FACEBOOK_SECRET')
SMARTIDEE_SECRET = auth_social_settings.get('SMARTIDEE_SECRET')

TARA_CLIENT_ID = auth_social_settings.get('TARA_CLIENT_ID')
TARA_SECRET = auth_social_settings.get('TARA_SECRET')
TARA_SANDBOX = auth_social_settings.get('TARA_SANDBOX')

KEYCLOAK_CLIENT_ID = auth_social_settings.get('KEYCLOAK_CLIENT_ID')
KEYCLOAK_SECRET = auth_social_settings.get('KEYCLOAK_SECRET')
KEYCLOAK_TOKEN_URL = auth_social_settings.get('KEYCLOAK_TOKEN_URL')
KEYCLOAK_USERINFO_URL = auth_social_settings.get('KEYCLOAK_USERINFO_URL')

EDUTEAMS_CLIENT_ID = auth_social_settings.get('EDUTEAMS_CLIENT_ID')
EDUTEAMS_SECRET = auth_social_settings.get('EDUTEAMS_SECRET')
EDUTEAMS_TOKEN_URL = auth_social_settings.get('EDUTEAMS_TOKEN_URL')
EDUTEAMS_USERINFO_URL = auth_social_settings.get('EDUTEAMS_USERINFO_URL')

validate_social_signup = validate_authentication_method('SOCIAL_SIGNUP')
validate_local_signup = validate_authentication_method('LOCAL_SIGNUP')

User = get_user_model()


class AuthException(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED


class FacebookException(AuthException):
    def __init__(self, facebook_error):
        self.message_text = facebook_error.get('message', 'Undefined')
        self.message_type = facebook_error.get('type', 'Undefined')
        self.message_code = facebook_error.get('code', 'Undefined')
        self.message = 'Facebook error {} (code:{}): {}'.format(
            self.message_type, self.message_code, self.message_text
        )
        super(FacebookException, self).__init__(detail=self.message)

    def __str__(self):
        return self.message


class SmartIDeeException(AuthException):
    def __init__(self, error_message, error_description=None):
        self.message = 'SmartIDee error: %s' % error_message
        if error_description:
            self.message = '%s (%s)' % (self.message, error_description)
        super(SmartIDeeException, self).__init__(detail=self.message)

    def __str__(self):
        return self.message


class TARAException(AuthException):
    def __init__(self, error_message, error_description=None):
        self.message = 'TARA error: %s' % error_message
        if error_description:
            self.message = '%s (%s)' % (self.message, error_description)
        super(TARAException, self).__init__(detail=self.message)

    def __str__(self):
        return self.message


class KeycloakException(AuthException):
    def __init__(self, error_message, error_description=None):
        self.message = 'Keycloak error: %s' % error_message
        if error_description:
            self.message = '%s (%s)' % (self.message, error_description)
        super(KeycloakException, self).__init__(detail=self.message)

    def __str__(self):
        return self.message


class EduteamsException(AuthException):
    def __init__(self, error_message, error_description=None):
        self.message = 'Eduteams error: %s' % error_message
        if error_description:
            self.message = '%s (%s)' % (self.message, error_description)
        super(EduteamsException, self).__init__(detail=self.message)

    def __str__(self):
        return self.message


def generate_username():
    return uuid.uuid4().hex[:30]


class BaseAuthView(RefreshTokenMixin, views.APIView):
    permission_classes = []
    authentication_classes = []
    provider = None

    @validate_social_signup
    def post(self, request, format=None):
        if not self.request.user.is_anonymous:
            raise ValidationError('This view is for anonymous users only.')

        serializer = AuthSerializer(
            data={
                'client_id': request.data.get('clientId'),
                'redirect_uri': request.data.get('redirectUri'),
                'code': request.data.get('code'),
            }
        )
        serializer.is_valid(raise_exception=True)

        backend_user = self.get_backend_user(serializer.validated_data)
        user, created = self.create_or_update_user(backend_user)

        token = self.refresh_token(user)

        event_logger.auth_social.info(
            'User {user_username} with full name {user_full_name} authenticated successfully with {provider}.',
            event_type=provider_event_type_mapping[self.provider],
            event_context={'provider': self.provider, 'user': user,},
        )
        return response.Response(
            {'token': token.key},
            status=created and status.HTTP_201_CREATED or status.HTTP_200_OK,
        )

    def get_backend_user(self, validated_data):
        """
        It should return dictionary with fields 'name' and 'id'
        """
        raise NotImplementedError

    def create_or_update_user(self, backend_user):
        user_id, user_name = backend_user['id'], backend_user['name']
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=generate_username(),
                    full_name=user_name,
                    registration_method=self.provider,
                )
                user.set_unusable_password()
                user.save()
                setattr(user.auth_profile, self.provider, user_id)
                user.auth_profile.save()
                return user, True
        except IntegrityError:
            profile = AuthProfile.objects.get(**{self.provider: user_id})
            if profile.user.full_name != user_name:
                profile.user.full_name = user_name
                profile.user.save()
            return profile.user, False


class FacebookView(BaseAuthView):

    provider = 'facebook'

    def get_backend_user(self, validated_data):
        access_token_url = 'https://graph.facebook.com/oauth/access_token'
        graph_api_url = 'https://graph.facebook.com/me'

        params = {
            'client_id': validated_data['client_id'],
            'redirect_uri': validated_data['redirect_uri'],
            'client_secret': FACEBOOK_SECRET,
            'code': validated_data['code'],
        }

        # Step 1. Exchange authorization code for access token.
        r = requests.get(access_token_url, params=params)
        self.check_response(r)
        params = {'access_token': r.json()['access_token']}

        # Step 2. Retrieve information about the current user.
        r = requests.get(graph_api_url, params=params)
        self.check_response(r)
        response_data = r.json()

        return {'id': response_data['id'], 'name': response_data['name']}

    def check_response(self, r, valid_response=requests.codes.ok):
        if r.status_code != valid_response:
            try:
                data = r.json()
                error_message = data['error']
            except Exception:
                values = (r.reason, r.status_code)
                error_message = 'Message: %s, status code: %s' % values
            raise FacebookException(error_message)


class SmartIDeeView(BaseAuthView):
    provider = 'smartid.ee'

    def get_backend_user(self, validated_data):
        access_token_url = 'https://id.smartid.ee/oauth/access_token'
        user_data_url = 'https://id.smartid.ee/api/v2/user_data'

        data = {
            'client_id': validated_data['client_id'],
            'client_secret': SMARTIDEE_SECRET,
            'redirect_uri': validated_data['redirect_uri'],
            'code': validated_data['code'],
            'grant_type': 'authorization_code',
        }

        # Step 1. Exchange authorization code for access token.
        r = requests.post(access_token_url, data=data)
        self.check_response(r)
        access_token = r.json()['access_token']

        # Step 2. Retrieve information about the current user.
        r = requests.get(user_data_url, params={'access_token': access_token})
        self.check_response(r)
        return r.json()

    def check_response(self, r, valid_response=requests.codes.ok):
        if r.status_code != valid_response:
            try:
                data = r.json()
                error_message = data['error']
                error_description = data.get('error_description', '')
            except Exception:
                values = (r.reason, r.status_code)
                error_message = 'Message: %s, status code: %s' % values
                error_description = ''
            raise SmartIDeeException(error_message, error_description)

    def create_or_update_user(self, backend_user):
        """ Authenticate user by civil number """
        full_name = ('%s %s' % (backend_user['firstname'], backend_user['lastname']))[
            :100
        ]
        try:
            user = User.objects.get(civil_number=backend_user['idcode'])
        except User.DoesNotExist:
            created = True
            user = User.objects.create_user(
                username=generate_username(),
                # Ilja: disabling email update from smartid.ee as it comes in as a fake object for the moment.
                # email=backend_user['email'],
                full_name=full_name,
                civil_number=backend_user['idcode'],
                registration_method=self.provider,
            )
            user.set_unusable_password()
            user.save()
        else:
            created = False
            if user.full_name != full_name:
                user.full_name = full_name
                user.save()
        return user, created


class TARAView(BaseAuthView):
    """
    See also reference documentation for TARA authentication in Estonian language:
    https://e-gov.github.io/TARA-Doku/TehnilineKirjeldus#431-identsust%C3%B5end
    """

    provider = 'tara'

    def get_backend_user(self, validated_data):
        if TARA_SANDBOX:
            base_url = 'https://tara-test.ria.ee/oidc/'
        else:
            base_url = 'https://tara.ria.ee/oidc/'

        user_data_url = base_url + 'token'

        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': validated_data['redirect_uri'],
            'code': validated_data['code'],
        }

        raw_token = '%s:%s' % (TARA_CLIENT_ID, TARA_SECRET)
        auth_token = base64.b64encode(raw_token.encode('utf-8'))

        headers = {'Authorization': b'Basic %s' % auth_token}

        try:
            token_response = requests.post(user_data_url, data=data, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.warning('Unable to send authentication request. Error is %s', e)
            raise TARAException('Unable to send authentication request.')
        self.check_response(token_response)

        try:
            data = token_response.json()
            id_token = data['id_token']
            return jwt.decode(id_token, verify=False)
        except (ValueError, TypeError):
            raise TARAException('Unable to parse JSON in authentication response.')
        except KeyError:
            raise TARAException('Authentication response does not contain token.')
        except jwt.PyJWTError as e:
            logger.warning('Unable to decode authentication token. Error is %s', e)
            raise TARAException('Unable to decode authentication token.')

    def check_response(self, r, valid_response=requests.codes.ok):
        if r.status_code != valid_response:
            try:
                data = r.json()
                error_message = data['error']
                error_description = data.get('error_description', '')
            except Exception:
                values = (r.reason, r.status_code)
                error_message = 'Message: %s, status code: %s' % values
                error_description = ''
            raise TARAException(error_message, error_description)

    def create_or_update_user(self, backend_user):
        try:
            profile_attributes = backend_user['profile_attributes']
            full_name = (
                '%s %s'
                % (profile_attributes['given_name'], profile_attributes['family_name'])
            )[:100]
            civil_number = backend_user['sub']
            # AMR stands for Authentication Method Reference
            details = {
                'amr': backend_user.get('amr'),
                'profile_attributes_translit': backend_user.get(
                    'profile_attributes_translit'
                ),
            }
        except KeyError as e:
            logger.warning('Unable to parse identity certificate. Error is: %s', e)
            raise TARAException('Unable to parse identity certificate.')
        try:
            user = User.objects.get(civil_number=civil_number)
        except User.DoesNotExist:
            created = True
            user = User.objects.create_user(
                username=generate_username(),
                full_name=full_name,
                civil_number=civil_number,
                registration_method=self.provider,
                details=details,
            )
            user.set_unusable_password()
            user.save()
        else:
            created = False
            if user.full_name != full_name:
                user.full_name = full_name
                user.save()
            if user.details != details:
                user.details = details
                user.save()
        return user, created


class KeycloakView(BaseAuthView):
    provider = 'keycloak'

    def get_access_token(self, validated_data):
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': validated_data['redirect_uri'],
            'code': validated_data['code'],
            'client_id': KEYCLOAK_CLIENT_ID,
            'client_secret': KEYCLOAK_SECRET,
        }

        try:
            response = requests.post(KEYCLOAK_TOKEN_URL, data=data)
        except requests.exceptions.RequestException as e:
            logger.warning('Unable to send authentication request. Error is %s', e)
            raise KeycloakException('Unable to send authentication request.')
        self.check_response(response)

        try:
            return response.json()['access_token']
        except (ValueError, TypeError):
            raise KeycloakException('Unable to parse JSON in authentication response.')
        except KeyError:
            raise KeycloakException('Authentication response does not contain token.')

    def get_user_info(self, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(KEYCLOAK_USERINFO_URL, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.warning('Unable to send user info request. Error is %s', e)
            raise KeycloakException('Unable to send user info request.')
        self.check_response(response)

        try:
            return response.json()
        except (ValueError, TypeError):
            raise KeycloakException('Unable to parse JSON in user info response.')

    def get_backend_user(self, validated_data):
        access_token = self.get_access_token(validated_data)
        return self.get_user_info(access_token)

    def check_response(self, r, valid_response=requests.codes.ok):
        if r.status_code != valid_response:
            try:
                data = r.json()
                error_message = data['error']
                error_description = data.get('error_description', '')
            except Exception:
                values = (r.reason, r.status_code)
                error_message = 'Message: %s, status code: %s' % values
                error_description = ''
            raise KeycloakException(error_message, error_description)

    def create_or_update_user(self, backend_user):
        # Preferred username is not unique. Sub in UUID.
        username = f'keycloak_f{backend_user["sub"]}'
        email = backend_user.get('email')
        full_name = backend_user.get('name', '')
        try:
            user = User.objects.get(username=username)
            created = False
        except User.DoesNotExist:
            created = True
            user = User.objects.create_user(
                username=username,
                registration_method=self.provider,
                email=email,
                full_name=full_name,
            )
            user.set_unusable_password()
            user.save()
        return user, created


class EduteamsView(BaseAuthView):
    provider = 'eduteams'

    def get_access_token(self, validated_data):
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': validated_data['redirect_uri'],
            'code': validated_data['code'],
            'client_id': EDUTEAMS_CLIENT_ID,
            'client_secret': EDUTEAMS_SECRET,
        }

        try:
            response = requests.post(EDUTEAMS_TOKEN_URL, data=data)
        except requests.exceptions.RequestException as e:
            logger.warning('Unable to send authentication request. Error is %s', e)
            raise EduteamsException('Unable to send authentication request.')
        self.check_response(response)

        try:
            return response.json()['access_token']
        except (ValueError, TypeError):
            raise EduteamsException('Unable to parse JSON in authentication response.')
        except KeyError:
            raise EduteamsException('Authentication response does not contain token.')

    def get_user_info(self, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(EDUTEAMS_USERINFO_URL, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.warning('Unable to send user info request. Error is %s', e)
            raise EduteamsException('Unable to send user info request.')
        self.check_response(response)

        try:
            return response.json()
        except (ValueError, TypeError):
            raise EduteamsException('Unable to parse JSON in user info response.')

    def get_backend_user(self, validated_data):
        access_token = self.get_access_token(validated_data)
        return self.get_user_info(access_token)

    def check_response(self, r, valid_response=requests.codes.ok):
        if r.status_code != valid_response:
            try:
                data = r.json()
                error_message = data['error']
                error_description = data.get('error_description', '')
            except Exception:
                values = (r.reason, r.status_code)
                error_message = 'Message: %s, status code: %s' % values
                error_description = ''
            raise EduteamsException(error_message, error_description)

    def create_or_update_user(self, backend_user):
        username = backend_user["sub"]
        email = backend_user.get('email')
        full_name = backend_user.get('name', '')
        # https://wiki.geant.org/display/eduTEAMS/Attributes+available+to+Relying+Parties#AttributesavailabletoRelyingParties-Assurance
        details = {'eduperson_assurance': backend_user.get('eduperson_assurance', [])}
        try:
            user = User.objects.get(username=username)
            if user.details != details:
                user.details = details
                user.save(update_fields=['details'])
            created = False
        except User.DoesNotExist:
            created = True
            user = User.objects.create_user(
                username=username,
                registration_method=self.provider,
                email=email,
                full_name=full_name,
                details=details,
            )
            user.set_unusable_password()
            user.save()

        existing_keys_map = {
            key.public_key: key
            for key in SshPublicKey.objects.filter(
                user=user, name__startswith='eduteams_'
            )
        }
        eduteams_keys = backend_user.get('ssh_public_key', [])

        new_keys = set(eduteams_keys) - set(existing_keys_map.keys())
        stale_keys = set(existing_keys_map.keys()) - set(eduteams_keys)

        for key in new_keys:
            name = 'eduteams_key_{}'.format(uuid.uuid4().hex[:10])
            new_key = SshPublicKey(user=user, name=name, public_key=key)
            new_key.save()

        for key in stale_keys:
            existing_keys_map[key].delete()

        return user, created


class RegistrationView(generics.CreateAPIView):
    permission_classes = ()
    authentication_classes = ()
    serializer_class = RegistrationSerializer

    @validate_local_signup
    def post(self, request, *args, **kwargs):
        return super(RegistrationView, self).post(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = serializer.save()
        user.is_active = False
        user.save()
        transaction.on_commit(lambda: tasks.send_activation_email.delay(user.uuid.hex))


class ActivationView(views.APIView):
    permission_classes = ()
    authentication_classes = ()

    @validate_local_signup
    def post(self, request):
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.user.is_active = True
        serializer.user.save()

        token = Token.objects.get(user=serializer.user)
        return response.Response({'token': token.key}, status=status.HTTP_201_CREATED)
