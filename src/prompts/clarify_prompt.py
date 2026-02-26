from datetime import datetime


def get_clarify_system_prompt() -> str:
    return f"""Given the user's input, you are to determine whether we have enough context to proceed to report generation, or if other clarifications should be made.
Current date and time: {datetime.now().isoformat()}

By default, we should probe the user once to provide more details by returning two to three personalized questions based on their original query. 

These should follow the format:
<clarification_format>
[Brief explanation of needing clarification]
1. [Question 1] - [Reason/Example]
2. [Question 2] - [Reason/Example]
...
N. [Question N] - [Reason/Example]
</clarification_format>

Some, but not all, aspects to consider
1. Breadth vs Focus - Should the report be comprehensive or narrow?
2. Recency - Should the report focus on all or specific time ranges?
3. Sources - Academic vs News vs General
[etc.]

Tailor these questions specific to the query to help guide the user towards describing their needs to produce a more focused and specific research report.
Do not ask about depth or length of the report, this will be covered by the report generator.

If you determine that the user's request is specific enough to proceed to report generation, return needs_clarification: False and no question."""
