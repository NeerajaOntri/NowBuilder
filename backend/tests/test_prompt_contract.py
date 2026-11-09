"""The chat prompt has to send a build request to `propose_plan`.

nowBuilder's whole job is the plan card. The failure this guards against is the prompt growing
enough caution ("can't deploy flows", "never claim deployed", a list of unsupported types) that the
model answers a build request with careful prose instead of calling the tool — accurate, and
useless. These tests pin the contract that makes the tool the obvious move.
"""
from app.ai.planning import PROPOSAL_SCHEMA
from app.ai.skills import get_skills

BUILD_REQUEST = ("Create flow Incident Creation Notification that triggers when an incident is "
                 "created and sends an email notification to the incident creator (opened_by)")


def chat_prompt(text=BUILD_REQUEST):
    return get_skills().build_prompt("chat", text=text)


def test_the_plan_tool_is_offered_first():
    """Last in a seven-tool list is easy to overlook; the plan tool leads."""
    assert [t["name"] for t in chat_prompt().tools][0] == "propose_plan"


def test_the_plan_tool_says_it_is_how_a_build_request_is_answered():
    d = PROPOSAL_SCHEMA["description"]
    assert "HOW A BUILD OR CHANGE REQUEST IS ANSWERED" in d
    assert "instead" in d and "in your reply" in d


def test_the_process_the_model_reads_first_routes_to_the_plan():
    """`topic-knowledge.md` opens the prompt. Whatever else it says, it has to point at the tool
    before the model has read anything about what can't be deployed."""
    system = chat_prompt().system
    first_mention = system.find("propose_plan")
    cannot_build = system.find("What nowBuilder can't build")
    assert 0 < first_mention < cannot_build, "the plan tool must appear before the list of limits"
    opening = system[:first_mention + 400]
    assert "not by writing instructions in prose" in opening


def test_a_design_only_flow_still_belongs_in_the_plan():
    system = chat_prompt().system
    assert "Design-only types (a Flow Designer flow) are still plan rows" in system
    assert "never silently drop a requested artifact from the plan" in system


def test_the_limits_list_does_not_read_as_permission_to_skip_the_plan():
    limits = get_skills().limits()
    assert "still call `propose_plan`" in limits
    assert "not a reason to skip the plan" in limits


def test_documentation_search_is_optional_not_a_required_first_step():
    """Making a docs search mandatory for every request burns turns before any planning."""
    system = chat_prompt().system
    assert "only when the platform behaviour is genuinely in doubt" in system


def test_the_catalog_still_says_which_types_the_user_builds_by_hand():
    system = chat_prompt().system
    assert "deployed with the ServiceNow SDK" in system


def test_the_reply_after_a_plan_is_told_not_to_restate_the_card():
    """30 Oct: the plan card appeared and then the reply wrote the whole design out underneath it
    again — trigger, every step, every field checked. The card already shows all of that."""
    system = get_skills().build_prompt("chat").system
    after = system.split("## After you call it", 1)[1][:1200]
    assert "nothing else" in after
    assert "numbered steps" in after and "don't list what you checked" in after


def test_the_plan_summary_is_not_a_second_copy_of_the_rows():
    from app.ai.planning import PROPOSAL_SCHEMA
    desc = PROPOSAL_SCHEMA["input_schema"]["properties"]["summary"]["description"]
    assert "don't restate them" in desc
