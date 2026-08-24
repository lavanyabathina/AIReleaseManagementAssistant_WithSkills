"""
Authorization tests for the Confluence guardrails.

The write tools and the scoped search check the space allowlist before
calling Confluence. get_confluence_page_content is different: it reads the
page first, because only Confluence knows which space a page id belongs
to, then refuses to return the content if that space is not authorized.
"""
from unittest.mock import patch

import pytest

from app.security.confluence_security import authorize_confluence_space
from app.tools.confluence_tools import (
    search_confluence_page,
    create_confluence_page,
    update_confluence_page,
    get_confluence_page_content,
)

ALLOWED_SPACE = "lavanya bathina"
FORBIDDEN_SPACE = "engineering docs"


# --------------------------------------------------------------------
# the guard function itself
# --------------------------------------------------------------------

def test_allowed_space_passes():
    authorize_confluence_space(ALLOWED_SPACE)      # must not raise


def test_space_check_is_case_insensitive():
    authorize_confluence_space("Lavanya Bathina")  # must not raise


def test_unauthorized_space_is_rejected():
    with pytest.raises(PermissionError, match="not authorized"):
        authorize_confluence_space(FORBIDDEN_SPACE)


# --------------------------------------------------------------------
# enforcement at the tool boundary
# --------------------------------------------------------------------

def test_create_page_rejects_unauthorized_space():
    result = create_confluence_page.invoke({
        "title": "Anything",
        "space_name": FORBIDDEN_SPACE,
        "content": "<p>x</p>",
    })

    assert FORBIDDEN_SPACE in result["error"]
    assert "not authorized" in result["error"]


def test_update_page_rejects_unauthorized_space():
    result = update_confluence_page.invoke({
        "page_id": "123",
        "space_name": FORBIDDEN_SPACE,
        "title": "Anything",
        "body": "<p>x</p>",
    })

    assert "not authorized" in result["error"]


def test_scoped_search_rejects_unauthorized_space():
    result = search_confluence_page.invoke({
        "query": "anything",
        "space_name": FORBIDDEN_SPACE,
    })

    assert "not authorized" in result["error"]


# --------------------------------------------------------------------
# reads: the space comes from Confluence, not from the caller
# --------------------------------------------------------------------

def fake_page_response(payload):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    return Response()


def page_read(space_name):
    """Serve a page in the given space, and that space's name by id."""
    page = {
        "spaceId": "555",
        "title": "Product Contact Information",
        "body": {"storage": {"value": "<p>WLS owner is a@b.com</p>"}},
    }

    def handler(url, **kwargs):
        if "/spaces/" in url:
            return fake_page_response({"name": space_name})
        return fake_page_response(page)

    return handler


def test_page_content_returned_for_authorized_space():
    with patch("app.tools.confluence_tools.requests.get", page_read(ALLOWED_SPACE)):
        result = get_confluence_page_content.invoke("999")

    assert result["title"] == "Product Contact Information"
    assert "error" not in result


def test_page_content_withheld_for_unauthorized_space():
    with patch("app.tools.confluence_tools.requests.get", page_read(FORBIDDEN_SPACE)):
        result = get_confluence_page_content.invoke("999")

    assert "not authorized" in result["error"]
    assert "WLS" not in str(result)      # the content must not leak


def test_page_content_refused_when_space_cannot_be_determined():
    """Fails closed rather than returning content it could not authorize."""
    def handler(url, **kwargs):
        return fake_page_response({"title": "x", "body": {}})   # no spaceId

    with patch("app.tools.confluence_tools.requests.get", handler):
        result = get_confluence_page_content.invoke("999")

    assert "Refusing to return its content" in result["error"]


# --------------------------------------------------------------------
# refusal happens before any HTTP call
# --------------------------------------------------------------------

def test_rejected_create_never_calls_confluence():
    with patch("app.tools.confluence_tools.requests.post") as post:
        create_confluence_page.invoke({
            "title": "Anything",
            "space_name": FORBIDDEN_SPACE,
            "content": "<p>x</p>",
        })

    post.assert_not_called()
