import math
import random


MAX_STATUS_STACKS = {
    "burn":       5,
    "bleed":      3,
    "poison":     5,
    "blue_flame": 5,
    "weak":       5,
    "stun":       2,
    "healing":    3,
}

STATUS_DAMAGE_MIN = 1
STATUS_DAMAGE_MAX = 4

WEAK_REDUCTION_PER_STACK = 5

HEALING_PERCENT_PER_STACK = 0.02


class StatusManager:

    def __init__(self):
        self.stacks = {
            "burn": 0,
            "bleed": 0,
            "poison": 0,
            "blue_flame": 0,
            "weak": 0,
            "stun": 0,
            "healing": 0,
        }
        self.permanent_poison = False

    def add_status(self, status_type, stacks=1, permanent=False):
        status_key = status_type.lower().replace(" ", "_")
        if status_key not in self.stacks:
            return

        if status_key == "burn" and self.stacks.get("blue_flame", 0) > 0:
            status_key = "blue_flame"

        cap = MAX_STATUS_STACKS.get(status_key, 99)
        self.stacks[status_key] = min(cap, self.stacks[status_key] + max(1, stacks))

        if status_key == "poison" and permanent:
            self.permanent_poison = True

    def convert_burn_to_blue_flame(self):

        burn_before = self.stacks.get("burn", 0)
        if burn_before <= 0:
            return 0

        cap = MAX_STATUS_STACKS["blue_flame"]
        self.stacks["blue_flame"] = min(
            cap, self.stacks["blue_flame"] + burn_before)
        self.stacks["burn"] = 0
        return burn_before

    def get_damage_reduction(self):
        return self.stacks.get("weak", 0) * WEAK_REDUCTION_PER_STACK

    def _decay_stacks(self):
        for key in list(self.stacks.keys()):
            if self.stacks[key] <= 0:
                continue
            if key == "poison" and self.permanent_poison:
                continue
            if key == "stun":
                continue
            self.stacks[key] = max(0, self.stacks[key] - 1)

    def process_turn_damage(self, target, attacker_atk=0, bonuses=None,
                            breakdown=None, heal_breakdown=None):
        if not hasattr(target, "hp") or not hasattr(target, "max_hp"):
            return 0

        if bonuses is None:
            bonuses = {}
        if breakdown is not None:
            breakdown.clear()
        if heal_breakdown is not None:
            heal_breakdown.clear()

        total_damage = 0

        if self.stacks["burn"] > 0:
            dmg = max(STATUS_DAMAGE_MIN, min(STATUS_DAMAGE_MAX, self.stacks["burn"]))
            dmg = int(dmg * (1.0 + bonuses.get("burn", 0.0)))
            total_damage += dmg
            if breakdown is not None:
                breakdown["burn"] = breakdown.get("burn", 0) + dmg

        if self.stacks["bleed"] > 0:
            dmg = math.ceil(target.hp * 0.03)
            dmg = max(STATUS_DAMAGE_MIN, min(STATUS_DAMAGE_MAX, dmg))
            dmg = int(dmg * (1.0 + bonuses.get("bleed", 0.0)))
            total_damage += dmg
            if breakdown is not None:
                breakdown["bleed"] = breakdown.get("bleed", 0) + dmg

        if self.stacks["poison"] > 0:
            dmg = math.ceil(target.max_hp * (0.005 * self.stacks["poison"]))
            dmg = max(STATUS_DAMAGE_MIN, min(STATUS_DAMAGE_MAX, dmg))
            dmg = int(dmg * (1.0 + bonuses.get("poison", 0.0)))
            total_damage += dmg
            if breakdown is not None:
                breakdown["poison"] = breakdown.get("poison", 0) + dmg

        if self.stacks["blue_flame"] > 0:
            dmg = math.ceil(target.max_hp * (0.01 * self.stacks["blue_flame"]))
            dmg = max(STATUS_DAMAGE_MIN, min(STATUS_DAMAGE_MAX, dmg))
            dmg = int(dmg * (1.0 + bonuses.get("blue_flame", 0.0)))
            total_damage += dmg
            if breakdown is not None:
                breakdown["blue_flame"] = breakdown.get("blue_flame", 0) + dmg

        final_dmg = int(total_damage)
        target.hp = max(0, int(target.hp) - final_dmg)

        if self.stacks.get("healing", 0) > 0:
            max_hp = int(target.max_hp)
            cur_hp = int(target.hp)
            missing = max(0, max_hp - cur_hp)
            if missing > 0:
                heal = math.ceil(missing * (HEALING_PERCENT_PER_STACK
                                            * self.stacks["healing"]))
                heal = max(1, heal)
                target.hp = min(max_hp, cur_hp + heal)
                if heal_breakdown is not None:
                    heal_breakdown["healing"] = (
                        heal_breakdown.get("healing", 0) + heal)

        self._decay_stacks()
        return final_dmg

    @staticmethod
    def calculate_attack_hit(attacker, defender, weapon=None):
        defender_evade = getattr(defender, "evade", 0.02)
        if random.random() < defender_evade:
            return {"hit": False, "damage": 0, "type": "EVADED"}

        raw_damage = attacker.atk

        special = {}
        if weapon and hasattr(weapon, "special_effects"):
            special = weapon.special_effects

        if weapon:
            if hasattr(weapon, "get_total_damage"):
                raw_damage += weapon.get_total_damage()
            else:
                phys, elem = weapon.get_damage()
                raw_damage += phys + elem

        if special.get("true_damage", False):
            final_dmg = int(raw_damage)
            defender.hp = max(0, int(defender.hp) - final_dmg)
            return {"hit": True, "damage": final_dmg, "type": "TRUE DAMAGE"}

        defender_def = getattr(defender, "defense", 0)
        if special.get("ignore_def_chance", 0) > 0:
            if random.random() < special["ignore_def_chance"]:
                defender_def = 0

        final_dmg = int(max(1, raw_damage - defender_def))
        defender.hp = max(0, int(defender.hp) - final_dmg)
        return {"hit": True, "damage": final_dmg, "type": "PHYSICAL"}