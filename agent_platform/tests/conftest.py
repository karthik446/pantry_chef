import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_rabbit():
    """Fixture for mocking RabbitMQ connections"""
    mock_conn = MagicMock()
    mock_channel = MagicMock()
    mock_conn.channel.return_value = mock_channel
    return mock_conn, mock_channel


@pytest.fixture
def mocker(monkeypatch):
    """Fixture that provides the mocker functionality"""

    class Mocker:
        def __init__(self, monkeypatch):
            self.monkeypatch = monkeypatch

        def patch(self, target, **kwargs):
            mock = MagicMock(**kwargs)
            self.monkeypatch.setattr(target, mock)
            return mock

    return Mocker(monkeypatch)
