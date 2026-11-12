from app.models.certification_request import CertificationRequest

def cert_args(**overrides):
    args = {
        "certification": "SUSE16",
        "release": "14.1.2",
        "jira_project": "REL",
        "confluence_space": "lavanya bathina",
        "parent_story_assignee" : "lavanya.bathina@gmail.com",
        "start_date": "2026-08-13",
        "end_date": "2026-09-13",
    }
    print("BEFORE UPDATE:", args["confluence_space"])
    print("OVERRIDES:", overrides)

    args.update(overrides)
    print("AFTER UPDATE:", args["confluence_space"])

    return args


def make_request(**overrides):
    """
    Build the model, which is what run_certification expects.

    summary_page_title is a computed property, not a field, so it cannot
    be passed in. It is derived from certification and release.
    """
    return CertificationRequest(**cert_args(**overrides))
