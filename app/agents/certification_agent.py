from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent

from app.llm.llm_factory import get_llm
from app.models.agent_response import AgentResponse
from app.models.certification_request import CertificationRequest
from app.prompts.release_planning_prompt import release_planning_prompt
from app.utils.load_config import load_config
from app.tools.confluence_tools import (
    search_confluence_page,
    get_confluence_page_content,
    get_confluence_space_details,
    create_confluence_page,
    update_confluence_page,
    find_confluence_page_by_title,
)
from app.tools.jira_tools import (
    get_jira_fields,
    get_jira_issue,
    get_jira_user,
    create_jira_issue,
    link_jira_issue,
    update_jira_issue,
    add_jira_comment,
)

# Resolved relative to this file so the config loads regardless of the
# working directory the caller was started from.
DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parents[1] / "config" / "application_config.yaml"
)

CERTIFICATION_TOOLS = [
    search_confluence_page,
    get_confluence_page_content,
    get_confluence_space_details,
    create_confluence_page,
    update_confluence_page,
    get_jira_fields,
    get_jira_issue,
    get_jira_user,
    create_jira_issue,
    link_jira_issue,
    update_jira_issue,
    add_jira_comment,
]


class DuplicateCertificationError(Exception):
    """
    Raised when a certification summary page already exists in Confluence.

    The certification has already been planned, so the workflow stops
    before creating any Jira or Confluence artifacts.
    """

    def __init__(self, title, page_url=None):
        self.title = title
        self.page_url = page_url

        super().__init__(
            f"Certification details are already present for "
            f"'{title}'. Existing page: {page_url}"
        )


def find_existing_summary_page(request):
    """
    Find the certification summary page for this request, if it exists.

    Looks the page up by its exact title. Confluence enforces unique
    titles per space, so this answers the question directly instead of
    relying on a fuzzy text search.

    Returns the matching page, or None.
    """
    title = request.summary_page_title

    print("\nChecking for an existing certification summary")
    print(f"  title : {title!r}")
    print(f"  space : {request.confluence_space!r}")

    space = get_confluence_space_details.invoke(request.confluence_space)
    space_key = space.get("space_key")

    if not space_key:
        print(
            f"  could not resolve the space: "
            f"{space.get('error', request.confluence_space)}"
        )
        return None

    print(f"  space key resolved: {space_key!r}")

    page = find_confluence_page_by_title(space_key, title)

    if page is None:
        print("  no page with that exact title -> continuing")
    else:
        print(f"  FOUND existing page: {page.get('url')}")

    return page


def build_certification_agent(
    model=None,
    tools=None,
    config_file=DEFAULT_CONFIG_FILE
):
    """
    Build the certification agent.

    Args:
        model: Chat model to use. Defaults to the provider configured in
            application_config.yaml.
        tools: Tools to register. Defaults to CERTIFICATION_TOOLS.
        config_file: Path to the application config.

    Returns:
        A configured LangChain agent.
    """

    if model is None:
        model = get_llm(load_config(config_file))

    return create_agent(
        model=model,
        tools=CERTIFICATION_TOOLS if tools is None else tools
    )


def run_certification(
    request: CertificationRequest,
    agent=None
) -> AgentResponse:
    """
    Run the certification workflow for a request.

    Reads no console input, so it can be called from tests and from the
    CLI alike.

    Args:
        request: A validated CertificationRequest.
        agent: Agent to run. Defaults to a freshly built one. Tests can
            pass a stub exposing invoke(payload) -> dict to avoid calling
            the model and the Jira and Confluence APIs.

    Returns:
        An AgentResponse wrapping the messages the agent produced.

    Raises:
        DuplicateCertificationError: If a certification summary page
            already exists for this certification and release.
    """

    load_dotenv()

    # Stop before anything is created if this certification was already
    # planned. Jira artifacts are created before the Confluence page, so
    # without this a rerun would duplicate the Jira issues first.
    existing_page = find_existing_summary_page(request)

    if existing_page is not None:
        raise DuplicateCertificationError(
            title=request.summary_page_title,
            page_url=existing_page.get("url"),
        )

    if agent is None:
        agent = build_certification_agent()


    messages = release_planning_prompt.format_messages(
        certification_request=request.model_dump(mode="json")
    )

    result = agent.invoke({"messages": messages})

    response = AgentResponse(
        messages=result.get("messages", [])
    )

    return response
