from app.inputs.certification_input import get_certification_request
from app.agents.certification_agent import (
    run_certification,
    DuplicateCertificationError,
)
from dotenv import load_dotenv
from app.tools.confluence_tools import *
from app.tools.jira_tools import *
import sys
import os


def test_tools():
    """
    Test method to invoke individual tools and verify they work correctly.
    """
    print("\n" + "="*60)
    print("TESTING INDIVIDUAL TOOLS")
    print("="*60 + "\n")

    # Test 1: Get Jira Issue
    print("\n[TEST 1] Get Jira Issue")
    print("-" * 60)
    get_jira_issue_response = get_jira_issue.invoke("REL-15")
    print("Get Jira issue result is:****")
    print(get_jira_issue_response)

    # Test 2: Get Jira User
    print("\n[TEST 2] Get Jira User")
    print("-" * 60)
    assignee = get_jira_user.invoke("lavanya.bathina@gmail.com")
    account_id = assignee["account_id"]
    print("Account id of lavanya.bathina@gmail.com:", account_id)

    # Test 3: Create Jira Story
    print("\n[TEST 3] Create Jira Story")
    print("-" * 60)
    create_story_issue_result = create_jira_issue.invoke({
        "project_key": "REL",
        "issue_type": "Story",
        "summary": "Oracle Linux6",
        "description": "Certification Activity for Oracle Linux6",
        "start_date": "2026-08-13",
        "end_date": "2026-09-13",
        "assignee_email": "lavanya.bathina@gmail.com"
    })
    print("Create issue(story) result is:*****")
    print(create_story_issue_result)
    story_issue_key = create_story_issue_result.get("issue_key")

    # Test 4: Create Jira Task
    print("\n[TEST 4] Create Jira Task")
    print("-" * 60)
    create_task_issue_result = create_jira_issue.invoke({
        "project_key": "REL",
        "issue_type": "Task",
        "summary": "Certify WLS with Oracle Linux6",
        "description": "Certification Activity for WLS with Oracle Linux6",
        "start_date": "2026-08-13",
        "end_date": "2026-09-13",
        "assignee_email": "lavanya.bathina@gmail.com"
    })
    print("Create issue(task) result is:*****")
    print(create_task_issue_result)
    task_issue_key = create_task_issue_result.get("issue_key")

    # Test 5: Link Jira Issues
    print("\n[TEST 5] Link Jira Issues")
    print("-" * 60)
    link_issues_result = link_jira_issue.invoke({
        "inward_issue_key": story_issue_key,
        "outward_issue_key": task_issue_key,
        "link_type": "Relates"
    })
    print("Link issues result:")
    print(link_issues_result)

    # Test 6: Get Confluence Space Details
    print("\n[TEST 6] Get Confluence Space Details")
    print("-" * 60)
    space_details = get_confluence_space_details.invoke("lavanya bathina")
    space_id = space_details.get("space_id")
    print("Space id is:", space_id)

    # Test 7: Create Confluence Page
    print("\n[TEST 7] Create Confluence Page")
    print("-" * 60)
    create_page_result = create_confluence_page.invoke({
        "title": "Test Certification Page3",
        "space_name": "lavanya bathina",
        "content": "<p>Hello from API V2</p>"
    })
    print("Create page result:")
    print(create_page_result)

    print("\n" + "="*60)
    print("TOOL TESTING COMPLETE")
    print("="*60 + "\n")


def run_certification_agent():
    print("Loading .env file")
    load_dotenv()

    request = get_certification_request()

    # Convert Pydantic model to a json compatible dictionary
    print("\nCertification Request:")
    print(request.model_dump(mode="json"))

    try:
        response = run_certification(request)
    except DuplicateCertificationError as error:
        print(f"\n{error}")
        return None

    response.print_report()

    return response

if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "certification":
            run_certification_agent()
        elif sys.argv[1] == "releasereadiness":
            run_releasereadiness_agent()
    else:
        run_certification_agent()  # default