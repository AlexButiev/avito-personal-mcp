import pytest

from avito_personal_mcp.profile import ProfileDiscoveryError, select_current_profile


def test_selects_current_profile():
    payload = {
        "result": {
            "count": 2,
            "profiles": [
                {
                    "profileId": 10,
                    "name": "Old profile",
                    "title": "Private",
                    "entity": "person",
                    "status": "active",
                    "isCurrent": False,
                },
                {
                    "profileId": 20,
                    "name": "Current profile",
                    "title": "Private",
                    "entity": "person",
                    "status": "active",
                    "isCurrent": True,
                },
            ],
        }
    }

    profile = select_current_profile(payload)

    assert profile == {
        "profile_id": 20,
        "name": "Current profile",
        "title": "Private",
        "entity": "person",
        "status": "active",
    }


def test_single_profile_is_safe_fallback():
    payload = {
        "result": {
            "count": 1,
            "profiles": [
                {
                    "profileId": "abc",
                    "name": "Only profile",
                    "title": None,
                    "entity": None,
                    "status": None,
                }
            ],
        }
    }

    assert select_current_profile(payload)["profile_id"] == "abc"


def test_rejects_missing_profiles():
    with pytest.raises(ProfileDiscoveryError, match="No Avito profiles"):
        select_current_profile({"result": {"profiles": []}})


def test_rejects_ambiguous_profiles_without_current_marker():
    payload = {
        "result": {
            "profiles": [
                {"profileId": 1, "name": "One"},
                {"profileId": 2, "name": "Two"},
            ]
        }
    }

    with pytest.raises(ProfileDiscoveryError, match="Could not determine"):
        select_current_profile(payload)
