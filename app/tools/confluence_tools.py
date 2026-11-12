import os
import requests
from typing import Optional
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from app.security.confluence_security import authorize_confluence_space

load_dotenv()

CONFLUENCE_API_BASE_URL= os.getenv("CONFLUENCE_API_BASE_URL")
CONFLUENCE_EMAIL= os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN= os.getenv("CONFLUENCE_API_TOKEN")


@tool
def search_confluence_page(
    query: str,
    space_name: str,
    limit: int = 5
) -> dict:
    """
    Search Confluence pages using the page title or page content.

    Args:
        query: Text to search for in Confluence.
        space_name: Optional Confluence space name, for example
            'lavanya bathina', used to restrict the search to that space.
            The name is resolved to a space key internally. Do not pass a
            space key or a space ID. Omit it to search all spaces.
        limit: Maximum number of pages to return.

    Returns:
        Matching Confluence pages with title, URL, space and content, or
        a dictionary containing an "error" key if the space cannot be
        resolved or the Confluence API call fails.
    """

    if not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
        return {
            "error": "Confluence credentials are not configured."
        }

    # Search page title/content
    cql = f'type=page AND text ~ "{query}"'

    if space_name:
        try:
            authorize_confluence_space(space_name)
        except PermissionError as e:
            return {
                "error": str(e)
            }

        space = get_confluence_space_details.invoke(space_name)
        space_key = space.get("space_key")

        if not space_key:
            return {
                "error": space.get(
                    "error",
                    f"Could not resolve Confluence space: {space_name}"
                )
            }

        cql += f' AND space="{space_key}"'

    cql += " ORDER BY lastmodified DESC"

    url = f"{CONFLUENCE_API_BASE_URL}/rest/api/search"

    params = {
        "cql": cql,
        "limit": limit,
        "expand": "body.storage"
    }

    try:
        response = requests.get(
            url,
            params=params,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        #print("Response json is:" ,data )
        results = []

        results = []

        for result in data.get("results", []):

            page = result.get("content", {})

            page_id = page.get("id")

            page_url = (
            CONFLUENCE_API_BASE_URL
            + page.get("_links", {}).get("webui", "")
            )

            result_space_name = (
                result.get("resultGlobalContainer", {})
            .get("title")
            )

            results.append({
                "page_id": page_id,
                "title": page.get("title"),
                "space": result_space_name,
                "url": page_url
            })

        return {
            "query": query,
            "count": len(results),
            "results": results
        }

    except requests.exceptions.RequestException as e:

        return {
        "error": f"Confluence API request failed: {str(e)}"
        }

def find_confluence_page_by_title(space_key: str, title: str) -> Optional[dict]:
    """
    Look up a Confluence page by its exact title within a space.

    Internal helper, deliberately not exposed to the agent as a tool.

    Uses the content API's exact title filter rather than a CQL search.
    CQL 'text ~' is a fuzzy full text match that tokenizes the query, so
    titles containing punctuation such as '-' or '.' do not match
    reliably. Confluence enforces unique titles per space, so an exact
    title lookup is the correct way to ask whether a page exists.

    Returns the page, or None when no page has that title.
    """

    url = f"{CONFLUENCE_API_BASE_URL}/rest/api/content"

    params = {
        "spaceKey": space_key,
        "title": title,
        "type": "page",
        "limit": 1
    }

    try:
        response = requests.get(
            url,
            params=params,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"  title lookup failed: {e}")
        return None

    results = response.json().get("results", [])

    print(f"  title lookup returned {len(results)} page(s)")

    if not results:
        return None

    page = results[0]

    return {
        "page_id": page.get("id"),
        "title": page.get("title"),
        "url": (
            CONFLUENCE_API_BASE_URL
            + page.get("_links", {}).get("webui", "")
        )
    }


def get_confluence_space_name_by_id(space_id: str) -> Optional[str]:
    """
    Look up a Confluence space name from its space ID.

    Internal helper, deliberately not exposed to the agent as a tool so
    that space authorization cannot be influenced by the caller.

    Returns the space name, or None if it cannot be determined.
    """

    url = f"{CONFLUENCE_API_BASE_URL}/api/v2/spaces/{space_id}"

    response = requests.get(
        url,
        auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
        headers={
            "Accept": "application/json"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json().get("name")


@tool
def get_confluence_page_content(page_id : str)-> dict :
    """
        Retrieve the complete content and metadata of a Confluence page.

        The space the page belongs to is read back from Confluence and
        checked against the authorized Confluence spaces. Content is only
        returned for pages in an authorized space.

        Args:
            page_id: The Confluence page ID.

        Returns:
            Page metadata and content, or a dictionary containing an
            "error" key if the page's space is not authorized, the space
            cannot be determined, or the Confluence API call fails.
    """

    try :
        url = f"{CONFLUENCE_API_BASE_URL}/api/v2/pages/{page_id}"
        params = {
            "body-format": "storage"
        }
        response = requests.get(
                    url,
                    params=params,
                    auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
                    headers={
                    "Accept": "application/json"
                    },
                    timeout=30
            )

        response.raise_for_status()

        data = response.json()

        # Authorize using the space Confluence reports for this page, not
        # a value supplied by the caller, then return the content only if
        # that space is authorized.
        space_id = data.get("spaceId")

        if not space_id:
            return {
                "error": (
                    f"Could not determine the Confluence space for page "
                    f"{page_id}. Refusing to return its content."
                )
            }

        space_name = get_confluence_space_name_by_id(space_id)

        if not space_name:
            return {
                "error": (
                    f"Could not determine the Confluence space name for "
                    f"space ID {space_id}. Refusing to return the content "
                    f"of page {page_id}."
                )
            }

        try:
            authorize_confluence_space(space_name)
        except PermissionError as e:
            return {
                "error": str(e)
            }

        title = data.get("title", "")

        html_content = data.get("body", {}).get("storage", {}).get("value", "")
        soup = BeautifulSoup(html_content, "html.parser")

        lines = []

        for table in soup.find_all("table"):
            rows = table.find_all("tr")

            for row in rows:
                cells = row.find_all(["th", "td"])
                values = [cell.get_text(" ", strip=True) for cell in cells]

                if values:
                    lines.append(" | ".join(values))

        content = "\n".join(lines)

        return {
            "title": title,
            "content": content
        }


    except requests.exceptions.RequestException as e:

        return {
        "error": f"Confluence API request failed: {str(e)}"
        }
from langchain_core.tools import tool
import requests


@tool
def get_confluence_space_details(space_name: str) -> dict:
    """
    Find Confluence space details using the space Name.

    Args:
        space_name: Confluence space name, for example 'lavanya bathina'.

    Returns:
        Space ID, space key, and space name.
    """

    if not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
        return {
            "error": "Confluence credentials are not configured."
        }

    url = f"{CONFLUENCE_API_BASE_URL}/api/v2/spaces"

    params = {
        "limit": 100
    }

    try:
        response = requests.get(
            url,
            params=params,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        #print("Get Confluence Spaces API result is:" , data)

        for space in data.get("results", []):

            if space.get("name") == space_name:

                result= {
                    "space_id": space.get("id"),
                    "space_key": space.get("key"),
                    "space_name": space.get("name")
                }
                return result
        return {
            "error": f"Confluence space with name '{space_name}' was not found."
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"Confluence API request failed: {str(e)}"
        }

@tool
def create_confluence_page(
    title: str,
    space_name: str,
    content: str,
    parent_page_id: Optional[str] = None
) -> dict:
    """
    Create a new Confluence page.

    Args:
        title: Title of the page.
        space_name: Confluence space name, for example 'lavanya bathina'.
            The name is resolved to a Confluence space ID internally.
            Do not pass a space ID or a space key.
        content: Page content in storage format.
        parent_page_id: Optional parent page ID.

    Returns:
        Details of the created page including page_id, title, space_id
        and url, or a dictionary containing an "error" key if the space
        cannot be resolved, a page with the same title already exists,
        or the Confluence API call fails.
    """

    if not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
        return {
            "error": "Confluence credentials are not configured."
        }

    try:
        authorize_confluence_space(space_name)
    except PermissionError as e:
        return {
            "error": str(e)
        }

    space = get_confluence_space_details.invoke(space_name)
    space_id = space.get("space_id")

    if not space_id:
        return {
            "error": space.get(
                "error",
                f"Could not resolve Confluence space: {space_name}"
            )
        }

    url = f"{CONFLUENCE_API_BASE_URL}/api/v2/pages"

    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": content
        }
    }

    if parent_page_id:
        payload["parentId"] = parent_page_id

    try:
        response = requests.post(
            url,
            json=payload,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        #print("Create page response:", data)

        page_id = data.get("id")

        result= {
            "page_id": page_id,
            "title": data.get("title"),
            "space_id": data.get("spaceId"),
            "url": (
                CONFLUENCE_API_BASE_URL
                + data.get("_links", {}).get("webui", "")
            )
        }
        return result

    except requests.exceptions.RequestException as e:

        print("Status code:", response.status_code)
        print("Response body:", response.text)

        if response.status_code == 400 and "already exists" in response.text:
            return {
                "error": "A Confluence page with this title already exists in this space.",
                "status_code": 400,
                "duplicate_page": True
            }

        return {
            "error": f"Confluence API request failed: {str(e)}",
            "status_code": response.status_code,
            "response": response.text
        }



@tool
def update_confluence_page(
    page_id: str,
    space_name: str,
    title: str,
    body: str
) -> dict:
    """
    Update an existing Confluence page.

    Args:
        page_id: Confluence page ID.
        space_name: Confluence space name the page belongs to, for
            example 'lavanya bathina'. Checked against the authorized
            Confluence spaces before the page is updated.
        title: New page title.
        body: Page content in Confluence storage format.

    Returns:
        Updated page information including page_id, title, version and
        url, or a dictionary containing an "error" key if the space is
        not authorized or the Confluence API call fails.
    """

    if not CONFLUENCE_EMAIL or not CONFLUENCE_API_TOKEN:
        return {
            "error": "Confluence credentials are not configured."
        }

    try:
        authorize_confluence_space(space_name)
    except PermissionError as e:
        return {
            "error": str(e)
        }

    url = f"{CONFLUENCE_API_BASE_URL}/rest/api/content/{page_id}"

    try:
        # Get current page version
        params = {
            "expand": "version"
        }

        get_response = requests.get(
            url,
            params=params,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        get_response.raise_for_status()

        page_data = get_response.json()

        current_version = page_data.get("version", {}).get("number")

        if current_version is None:
            return {
                "error": "Unable to determine current Confluence page version"
            }

        new_version = current_version + 1

        # Update page
        payload = {
            "version": {
                "number": new_version
            },
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage"
                }
            }
        }

        response = requests.put(
            url,
            json=payload,
            auth=(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        result= {
            "page_id": data.get("id"),
            "title": data.get("title"),
            "version": data.get("version", {}).get("number"),
            "url": data.get("_links", {}).get("webui")
        }
        return result
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Confluence API request failed: {str(e)}"
        }