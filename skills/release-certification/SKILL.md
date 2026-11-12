---
name: release-certification
description: Use this skill to plan, validate, and troubleshoot release certification workflows for Fusion Middleware products in Jira and Confluence.
---

# Release Certification Skill

## Purpose

This skill supports the end-to-end release certification process for Fusion Middleware (FMW) products. It helps a coding agent or assistant:

- interpret a certification request
- resolve product-to-POC information from Confluence
- create a parent Jira Story for the certification
- create per-product Jira Tasks and link them to the parent Story
- publish or update a Confluence certification summary page
- verify the created Jira and Confluence artifacts before reporting completion

## Scope

Use this skill for release certification planning, execution, validation, and debugging in this repository.

Relevant project files include:

- [README.md](../../README.md)
- [main.py](../../main.py)
- [app/agents/certification_agent.py](../../app/agents/certification_agent.py)
- [app/prompts/release_planning_prompt.py](../../app/prompts/release_planning_prompt.py)
- [app/tools/jira_tools.py](../../app/tools/jira_tools.py)
- [app/tools/confluence_tools.py](../../app/tools/confluence_tools.py)

## Workflow

1. Read and validate the request data.
   - certification
   - release
   - jira_project
   - confluence_space
   - parent_story_assignee
   - start_date
   - end_date

2. Resolve the source-of-truth product mapping from Confluence.
   - Search for the page titled "Product Contact Information for FMW Products".
   - Parse the product-to-POC mapping.
   - If a product has no valid POC, skip it and report the exception.

3. Create the parent certification Story in Jira.
   - Use the certification name as the summary.
   - Assign it to the requested owner.
   - Include release and date metadata.

4. Resolve each POC into a valid Jira user.
   - Do not guess or fabricate Jira users.
   - Skip unresolved entries and report them clearly.

5. Create one Jira Task per product.
   - Title pattern: "Certify <PRODUCT> for <CERTIFICATION>"
   - Assign each task to the matching POC.

6. Link every product Task to the parent Story.
   - Verify the parent-child relationship before concluding the step.

7. Create or update the Confluence certification summary page.
   - Use a title of the form: "<Certification> - <Release> - Certification Summary"
   - Include the purpose, certification details, live Jira link, and tracking table.

8. Verify the generated outputs.
   - Confirm Jira title, assignee, dates, release, and parent-child relationships.
   - Confirm Confluence content structure, table shape, and consistency with Jira data.

9. Return a structured execution report.
   - Status should be Completed, Partially Completed, or Failed.
   - Provide tool call evidence and any skipped or failed items.

## Safety rules

- Never invent missing product mappings, POCs, Jira users, or Confluence content.
- Never create a certification record with incomplete or unverified metadata.
- Skip problematic products instead of guessing.
- Treat the certification request as the authoritative source for project, release, and dates.
- Validate date ordering before creating issues.
- Keep Confluence content synchronized with the real Jira artifacts.

## Expected outcome

A successful execution should produce:

- one parent certification Story in Jira
- one product Task per valid product
- parent-child issue linking
- a Confluence certification summary page
- verification evidence for both Jira and Confluence
- a final report with status and exceptions

## Notes for agents

This repository’s certification workflow is deliberately strict about validation and evidence. If anything is missing, the correct action is to stop, report, or skip the item rather than proceed with assumptions.
