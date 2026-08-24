"""
Authorization tests for the Jira guardrails.

These need no network. Every guard runs before the HTTP call, so a
rejected operation never reaches Jira. The tests assert exactly that.
"""
from unittest.mock import patch

import pytest

from app.security.jira_security import (
    authorize_jira_action,
    authorize_jira_task_assignee,
    authorize_jira_story_assignee,
)
from app.tools.jira_tools import (
    create_jira_issue,
    update_jira_issue,
    add_jira_comment,
)

TASK_ASSIGNEE = "lakumabathina@gmail.com"          # tasks only
STORY_ASSIGNEE = "lavanya.bathina@gmail.com"       # tasks and parent stories
OUTSIDER = "attacker@evil.com"


def story_args(**overrides):
    args = {
        "project_key": "REL",
        "issue_type": "Story",
        "summary": "OL10",
        "description": "Certification activity",
        "start_date": "2026-08-13",
        "end_date": "2026-09-13",
        "assignee_email": STORY_ASSIGNEE,
    }
    args.update(overrides)
    return args


# --------------------------------------------------------------------
# the guard functions themselves
# --------------------------------------------------------------------

def test_allowed_project_and_action_pass():
    authorize_jira_action("REL", "create")      # must not raise


def test_unauthorized_project_is_rejected():
    with pytest.raises(PermissionError, match="not an authorized project"):
        authorize_jira_action("HACK", "create")


def test_unauthorized_action_is_rejected():
    with pytest.raises(PermissionError, match="not authorized"):
        authorize_jira_action("REL", "delete")


def test_task_assignee_allowlist():
    authorize_jira_task_assignee(TASK_ASSIGNEE)

    with pytest.raises(PermissionError, match="not an authorized task assignee"):
        authorize_jira_task_assignee(OUTSIDER)


def test_story_assignee_allowlist():
    """
    An allowed parent story assignee must be accepted.

    Without this, STORY_ASSIGNEE could hold any value and the suite would
    still pass, because every other test that uses it is rejected by an
    earlier guard before the assignee is ever checked.
    """
    authorize_jira_story_assignee(STORY_ASSIGNEE)      # must not raise

    with pytest.raises(PermissionError, match="not an authorized parent story assignee"):
        authorize_jira_story_assignee(OUTSIDER)


def test_story_assignee_list_is_narrower_than_task_list():
    """A task assignee is not automatically allowed to own a parent story."""
    authorize_jira_task_assignee(TASK_ASSIGNEE)

    with pytest.raises(PermissionError, match="not an authorized parent story assignee"):
        authorize_jira_story_assignee(TASK_ASSIGNEE)


# --------------------------------------------------------------------
# enforcement at the tool boundary
# --------------------------------------------------------------------

def test_create_rejects_unauthorized_project():
    result = create_jira_issue.invoke(story_args(project_key="HACK"))

    assert "HACK" in result["error"]
    assert "not an authorized project" in result["error"]


def test_create_rejects_unauthorized_assignee():
    result = create_jira_issue.invoke(
        story_args(issue_type="Task", assignee_email=OUTSIDER)
    )

    assert "not an authorized task assignee" in result["error"]


def test_create_rejects_task_assignee_on_a_story():
    result = create_jira_issue.invoke(story_args(assignee_email=TASK_ASSIGNEE))

    assert "not an authorized parent story assignee" in result["error"]


def test_create_rejects_invalid_issue_type():
    result = create_jira_issue.invoke(story_args(issue_type="Epic"))

    assert "issue_type must be either" in result["error"]


def test_update_derives_project_from_issue_key():
    result = update_jira_issue.invoke({"issue_key": "HACK-1", "summary": "x"})

    assert "HACK" in result["error"]


def test_add_comment_is_currently_blocked_by_config():
    """
    add_jira_comment authorizes the action 'add_comment', which is absent
    from authorized_jira_actions in application_config.yaml. This test
    documents that. Add 'add_comment' to the config and flip the assertion
    if commenting is meant to be allowed.
    """
    result = add_jira_comment.invoke({"issue_key": "REL-15", "comment": "hi"})

    assert "add_comment is not authorized" in result["error"]


# --------------------------------------------------------------------
# the property that matters most: refusal happens before any HTTP call
# --------------------------------------------------------------------

def test_rejected_create_never_calls_jira():
    with patch("app.tools.jira_tools.requests.post") as post:
        create_jira_issue.invoke(story_args(project_key="HACK"))

    post.assert_not_called()


def test_rejected_update_never_calls_jira():
    with patch("app.tools.jira_tools.requests.put") as put:
        update_jira_issue.invoke({"issue_key": "HACK-1", "summary": "x"})

    put.assert_not_called()
