

def get_quests(player):

    if player is None:
        return ["Explore Aurelia."]

    scene = getattr(player, "last_scene", "castle")

    if scene == "castle":
        return _castle(player)
    if scene == "village":
        return _village(player)
    if scene == "outskirts":
        return _outskirts(player)
    if scene == "mystic":
        return _mystic(player)
    if scene == "deeper":
        return _deeper(player)
    if scene == "curse":
        return _curse(player)
    if scene == "wizardoz":
        return _wizardoz(player)
    if scene == "kitsune":
        return _kitsune(player)
    if scene == "wizard3":
        return _wizard3(player)
    if scene == "final":
        return _final(player)

    return ["Explore Aurelia."]


def _castle(player):
    village_done = bool(getattr(player, "village_orc_reward_done", False))
    state = getattr(player, "wizard_dialogue_state", "PART_1")

    if state in ("PART_1", "WAITING_BATTLE") and not village_done:
        return ["Speak with Wizard Oz"]
    if village_done:
        return ["Head west to the Outskirts"]
    return ["Travel east to the village"]


def _village(player):
    reward_done = bool(getattr(player, "village_orc_reward_done", False))
    orc_defeated = bool(getattr(player, "village_orc_defeated", False))

    if reward_done:
        return ["Return to the Castle"]
    if orc_defeated:
        return ["Return to Wizard Oz"]
    return ["Defeat the Orc in the north-east"]


def _outskirts(player):
    if getattr(player, "outskirts_horde_defeated", False):
        return ["Find the forest path"]
    if getattr(player, "outskirts_wizard_state", "NEW") == "NEW":
        return ["Speak with Wizard Oz"]
    return ["Defeat the hordes"]


def _mystic(player):
    if getattr(player, "has_seen_deeper_intro", False):
        return [
            "Explore the deeper forest",
            "Beware of what stirs within",
        ]
    return [
        "Go deeper in the forest",
        "Beware of strong opponents",
    ]


def _deeper(player):
    defeated = getattr(player, "deeper_horde_defeated_list", [False] * 3)
    try:
        cleared = sum(1 for x in defeated if x)
    except TypeError:
        cleared = 0

    if cleared >= 3:
        return ["The forest darkens ahead"]
    return [f"Silence the three hordes ({cleared}/3)"]


def _curse(player):
    return [
        "escape the curse part of the mystic forest",
        "any form of healing will revive the enemies",
        "unlimited chest...",
    ]


def _wizardoz(player):
    if not getattr(player, "wizardoz_reward_given", False):
        return [
            "Go find Wizard Oz",
            "Talk to Wizard Oz",
        ]
    return ["The Kitsune's flame awaits ahead"]


def _kitsune(player):
    if getattr(player, "kitsune_defeated", False):
        return [
            "continue to the forest and meet wizard oz",
            "farm now or regret later",
            "be prepared",
        ]
    if getattr(player, "has_seen_kitsune_dialogue", False):
        return ["Defeat the Kitsune"]
    return ["Face the fox spirit"]


def _wizard3(player):
    if getattr(player, "wizard3_reward_given", False):
        return ["Gorgona's castle lies west"]
    return ["Speak with Wizard Oz"]


def _final(player):
    if getattr(player, "gorgona_defeated", False):
        return ["Aurelia is at peace"]
    if not getattr(player, "final_horde_1_defeated", False) \
            or not getattr(player, "final_horde_2_defeated", False):
        return ["Silence the Empress's pets"]
    return ["Face Gorgona, the Vain Empress"]