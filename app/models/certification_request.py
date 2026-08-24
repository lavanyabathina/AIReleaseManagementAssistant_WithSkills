from pydantic import BaseModel,model_validator
from datetime import date

class CertificationRequest(BaseModel):
    certification : str
    release : str
    jira_project : str
    confluence_space: str
    parent_story_assignee : str
    start_date : date
    end_date : date 



    @property
    def summary_page_title(self) -> str:
        """Title of the Confluence certification summary page."""
        return f"{self.certification} - {self.release} - Certification Summary"

    @model_validator(mode='after')
    def validate_dates(self):
        print("validate_dates() called")
        if self.start_date > self.end_date:
            raise ValueError("Start date can't be after End Date")
        else:
            return self
    