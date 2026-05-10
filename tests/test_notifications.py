import pytest
import httpx
from unittest.mock import MagicMock, patch
from app.notifications.whatsapp import WhatsAppClient

TOKEN = "test_bearer_token"
PHONE_NUMBER_ID = "123456789"
RECIPIENT = "+14379729046"
ANALYSIS = "Ran 5.02 km vs planned 4 km walk. Good effort overall."


@pytest.fixture
def client():
    return WhatsAppClient(TOKEN, PHONE_NUMBER_ID)


@pytest.fixture
def mock_post():
    with patch("app.notifications.whatsapp.httpx.post") as mock:
        mock.return_value = MagicMock(status_code=200)
        mock.return_value.raise_for_status = MagicMock()
        yield mock


class TestSendMessageRequest:
    def test_posts_to_correct_url(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        url = mock_post.call_args.args[0]
        assert f"/{PHONE_NUMBER_ID}/messages" in url
        assert "graph.facebook.com" in url

    def test_sends_bearer_auth_header(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer {TOKEN}"

    def test_sets_content_type_json(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        headers = mock_post.call_args.kwargs["headers"]
        assert "application/json" in headers["Content-Type"]

    def test_body_sets_messaging_product_whatsapp(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        body = mock_post.call_args.kwargs["json"]
        assert body["messaging_product"] == "whatsapp"

    def test_body_sets_type_text(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        body = mock_post.call_args.kwargs["json"]
        assert body["type"] == "text"

    def test_body_includes_recipient_number(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        body = mock_post.call_args.kwargs["json"]
        assert body["to"] == RECIPIENT

    def test_body_includes_message_text(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        body = mock_post.call_args.kwargs["json"]
        assert body["text"]["body"] == ANALYSIS

    def test_calls_raise_for_status(self, client, mock_post):
        client.send_message(RECIPIENT, ANALYSIS)

        mock_post.return_value.raise_for_status.assert_called_once()


class TestSendMessageErrorHandling:
    def test_raises_on_http_error(self, client):
        with patch("app.notifications.whatsapp.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=MagicMock(status_code=401),
            )
            mock_post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.send_message(RECIPIENT, ANALYSIS)
