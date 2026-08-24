
import pytest
from tests.helpers import * 
from app.agents.certification_agent import (
    run_certification,
    DuplicateCertificationError,
)
@pytest.mark.langsmith
def test_hallucination_is_detected_with_wrong_parent_story_assignee():
    """
    Verifies that the agent does not hallucinate or accept an incorrect parent
    story assignee when the expected assignee differs from the authoritative
    Jira data.
    
    The test validates that the agent's response is grounded in the trusted
    source and that an incorrect parent story assignee is identified or rejected.
    """
    story_assignee="abc@gmail.com"
    request = make_request(parent_story_assignee=story_assignee)

    response = run_certification(request)

    # printed before the assertions, so a failing run still shows what the
    # agent tried. Needs pytest -s to be visible on a passing run.
    response.print_report()
    output = response.final_output().lower()

    #Assertion for parent story creation failure as given assignee is not in allowed list
    assert any(
        phrase in output
        for phrase in [
            "parent Story creation failed",
            "`abc@gmail.com` is not an authorized parent Story assignee",
            "critical failure",
            "Story creation failed",
        ]
    )

    failed_tool_calls= response.failed_calls()
    print(failed_tool_calls)
    assert any(
        call.name == "create_jira_issue"
        for call in failed_tool_calls
    )

    assert "successfully created" not in output

   
