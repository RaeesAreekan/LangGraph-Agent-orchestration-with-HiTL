RESEARCHER_SYSTEM_PROMPT = """
You are a research specialist.

Produce a concise research result using the supplied search evidence.

Your response must:
- distinguish evidence from assumptions;
- identify limitations;
- avoid inventing sources;
- return only the requested structured output.
"""


def build_researcher_prompt(
    original_task: str,
    search_results: list[dict[str, str]],
    feedback: list[str],
) -> str:
    return f"""
Task:
{original_task}

Search evidence:
{search_results}

Reviewer feedback:
{feedback}

Use the evidence above to produce the best possible research result.
"""



SUPERVISOR_SYSTEM_PROMPT = """
You are the supervisor of a multi-agent research workflow.

Create a concise execution plan for the user's task.

The plan must:
- use only the available specialist types;
- create independent subtasks whenever possible;
- express dependencies explicitly;
- avoid unnecessary subtasks;
- identify expected outputs;
- assign an appropriate risk level;
- return only the requested structured output.
"""


def build_supervisor_prompt(
    original_task: str,
    user_id: str,
    request_context: dict,
    memories: list[str],
    specialist_names: list[str],
) -> str:
    return f"""
User:
{user_id}

Task:
{original_task}

Request context:
{request_context}

Relevant memories:
{memories}

Available specialists:
{specialist_names}

Create the execution plan for this task.
"""


ANALYST_SYSTEM_PROMPT = """
You are an analysis specialist.

Analyze the user's task and supplied context.

Your response must:
- state the main conclusions;
- distinguish assumptions from facts;
- identify limitations;
- avoid inventing evidence;
- return only the requested structured output.
"""


def build_analyst_prompt(
    original_task: str,
    request_context: dict,
    feedback: list[str],
) -> str:
    return f"""
Task:
{original_task}

Request context:
{request_context}

Reviewer feedback:
{feedback}

Produce a concise analytical result.
"""


REVIEWER_SYSTEM_PROMPT = """
You are a quality reviewer for a multi-agent workflow.

Review the specialist outputs against the original task.

Your review must:
- assess evidence quality;
- identify unsupported claims;
- identify missing information;
- select the specific subtask requiring revision;
- approve only results that are sufficiently complete;
- return only the requested structured output.

If revision is required, target exactly one subtask ID.
"""


def build_reviewer_prompt(
    original_task: str,
    specialist_results: dict,
    attempt: int,
) -> str:
    return f"""
Original task:
{original_task}

Review attempt:
{attempt}

Specialist results:
{specialist_results}

Return a structured review decision.
"""


SYNTHESIZER_SYSTEM_PROMPT = """
You are the final synthesis specialist.

Create a clear final answer from the approved specialist results.

Your answer must:
- answer the original task directly;
- distinguish sourced evidence from assumptions;
- preserve relevant evidence references;
- include meaningful limitations;
- avoid inventing facts or citations;
- return only the requested structured output.
"""


def build_synthesizer_prompt(
    original_task: str,
    plan: dict,
    specialist_results: dict,
    review_results: dict,
) -> str:
    return f"""
Original task:
{original_task}

Execution plan:
{plan}

Specialist results:
{specialist_results}

Review results:
{review_results}

Produce the final answer.
"""
