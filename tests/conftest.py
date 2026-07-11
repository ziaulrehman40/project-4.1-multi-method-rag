import pytest
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="stage0-user",
        password="stage0-password",
    )


@pytest.fixture
def client(user):
    client = Client()
    client.force_login(user)
    return client

