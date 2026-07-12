import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_confirms_database_connection(client):
    client.logout()

    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
