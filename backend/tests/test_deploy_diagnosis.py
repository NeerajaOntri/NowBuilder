"""What a deployment tells the user when the instance doesn't behave.

These are the cases a real PDI hits and the fake instance previously didn't: the current update set
refusing to move, and the update set capturing nothing. Each has to say what actually happened,
because the user can only act on a specific message.
"""
import pytest

from app.services.deploy import DeployError, Deployer

from .test_chat import ready, send, text_turn, use_llm  # noqa: F401
from .test_deploy import approve, built_plan, deploy, final_plan


def _deployer(client, snow):
    from app.models import Instance
    from app.security import encrypt

    inst = Instance(url="https://dev410284.service-now.com", auth_method="basic", username="admin",
                    password_enc=encrypt("pw"), user_sys_id=snow.user_sys_id, is_admin=True)
    from app.services.servicenow import ServiceNowClient
    return Deployer(ServiceNowClient(inst, None, transport=snow.transport), inst)


def test_nothing_is_written_when_the_current_update_set_will_not_move(client, ready, snow, monkeypatch):
    """The instance accepts the preference write but reports a different value back."""
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)

    real_set_current = Deployer.set_current

    def set_then_change_it_back(self, update_set_sys_id):
        out = real_set_current(self, update_set_sys_id)
        pref = self._preference()                      # another session moves it away
        self.client.update("sys_user_preference", pref["sys_id"], {"value": "someone-elses-set"})
        return out

    monkeypatch.setattr(Deployer, "set_current", set_then_change_it_back)
    _, evs = deploy(client, ready, plan["id"])

    [error] = [e["message"] for e in evs if e["type"] == "error"]
    assert "current update set didn't move" in error
    assert "someone-elses-set" in error and "Nothing was written" in error
    assert snow.tables["sys_script"] == []             # it stopped before writing
    assert final_plan(evs)["deployment"]["status"] == "failed"


def test_a_missing_preference_names_the_user_and_the_table(client, ready, snow, monkeypatch):
    deployer = _deployer(client, snow)
    with pytest.raises(DeployError) as caught:
        deployer.verify_current("some-update-set")
    message = str(caught.value)
    assert "sys_update_set" in message and "admin" in message and "sys_user_preference" in message


def test_artifacts_that_landed_are_not_called_a_partial_deployment(client, ready, snow, monkeypatch):
    """Capture is about promoting the change onward. The artifacts are live either way, so the
    deployment is "deployed" with a warning — not "partial", which would say rows are missing and
    push the user to roll back something that worked."""
    snow.captures = False
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    _, evs = deploy(client, ready, plan["id"])

    out = final_plan(evs)
    assert out["deployment"]["status"] == "deployed" and out["status"] == "deployed"
    assert out["components"][0]["deploy"]["status"] == "deployed"
    assert len(snow.tables["sys_script"]) == 1
    assert "records are live in this instance" in out["deployment"]["message"]
    assert [e for e in evs if e["type"] == "warning"] and not [e for e in evs if e["type"] == "error"]


def test_an_unreadable_update_set_log_is_a_warning_not_a_failure(client, ready, snow, monkeypatch):
    plan = built_plan(client, ready, monkeypatch)
    approve(client, ready, plan)
    snow.forbidden.add("sys_update_xml")
    _, evs = deploy(client, ready, plan["id"])

    out = final_plan(evs)
    assert out["deployment"]["status"] == "deployed" and out["deployment"]["captured"] == -1
    assert "can't read sys_update_xml" in out["deployment"]["message"]
    assert len(snow.tables["sys_script"]) == 1
