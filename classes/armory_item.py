import os
import random


DEFAULT_BURST = {
    "name": "Elemental Burst", "type": "aoe", "damage_mult": 1.5,
    "status": None, "desc": "A pulse of raw elemental force.",
}


BURST_GROUNDBREAKING = {
    "name": "Groundbreaking", "type": "aoe", "damage_mult": 2.0,
    "status": None,
    "desc": "Slams the ground, sending a shockwave through every enemy.",
}
BURST_THORN_BLOOM = {
    "name": "Thornbloom", "type": "aoe", "damage_mult": 2.2,
    "status": ("poison", 3),
    "desc": "Thorny vines burst from the earth and poison every foe.",
}
BURST_VERDANT_RUPTURE = {
    "name": "Verdant Rupture", "type": "aoe", "damage_mult": 2.2,
    "status": None,
    "desc": "Roots and stone erupt upward beneath every enemy.",
}
BURST_FEATHER_BURST = {
    "name": "Feather Burst", "type": "aoe", "damage_mult": 2.5,
    "status": ("bleed", 3),
    "desc": "A storm of shimmering feathers pierces every enemy, inflicting Bleed.",
}
BURST_GALE_SLASH = {
    "name": "Gale Slash", "type": "aoe", "damage_mult": 1.5,
    "status": None,
    "desc": "A wide wind slash. Off-hand passive weapon.",
}
BURST_HEAVENLY_GALE = {
    "name": "Heavenly Gale", "type": "aoe", "damage_mult": 2.5,
    "status": None,
    "desc": "An upward wind burst launches every enemy skyward.",
}
BURST_FERAL_INFERNO = {
    "name": "Feral Inferno", "type": "aoe", "damage_mult": 2.0,
    "status": ("burn", 3),
    "desc": "A beast-shaped wave of flame scorches the field.",
}
BURST_AZURE_PYRE = {
    "name": "Azure Pyre", "type": "aoe", "damage_mult": 2.5,
    "status": ("blue_flame", 5),
    "desc": "Blue flames cling to every enemy.",
}
BURST_BLAZING_DETONATION = {
    "name": "Blazing Detonation", "type": "aoe", "damage_mult": 3.0,
    "status": None,
    "desc": "A ground-strike that detonates outward in all directions.",
}
BURST_SINNERS_PUNISHMENT = {
    "name": "Sinners Punishment", "type": "single", "damage_mult": 3.8,
    "status": None,
    "desc": "Burning ash and rock rain down on the target.",
}
BURST_TIDAL_CRESCENT = {
    "name": "Tidal Crescent", "type": "aoe", "damage_mult": 2.0,
    "status": ("weak", 2),
    "desc": "A crescent wave of water weakens every enemy.",
}
BURST_SERAPHIC_TORRENT = {
    "name": "Seraphic Torrent", "type": "aoe", "damage_mult": 2.0,
    "status": None,
    "desc": "A concentrated torrent rushes every enemy.",
}
BURST_RAINBOW_MAELSTROM = {
    "name": "Rainbow Maelstrom", "type": "aoe", "damage_mult": 2.8,
    "status": None,
    "desc": "A swirling vortex of water hurls every enemy outward.",
}
BURST_CRIMSON_WALTZ = {
    "name": "Crimson Waltz", "type": "aoe", "damage_mult": 2.0,
    "status": ("bleed", 2),
    "desc": "A spinning arc that leaves deep cuts on every foe.",
}
BURST_ECLIPSE_END = {
    "name": "Eclipse End", "type": "single", "damage_mult": 2.0,
    "status": None,
    "desc": "Reality folds. MOON DAMAGE: ignores DEF and enemy element, "
            "and deals DOUBLE damage to Gorgona.",
}


class Item:
    def __init__(self, id_name, name, item_type, image_path,
                 description="", is_permanent=False):
        self.id_name = id_name
        self.name = name
        self.item_type = item_type
        self.image_path = image_path
        self.description = description
        self.is_permanent = is_permanent

    @property
    def is_stackable(self):
        return False

    @property
    def is_unique(self):
        return False


class Consumable(Item):
    MAX_STACK_DEFAULT = 99

    def __init__(self, id_name, name, image_path, effect_type, effect_value,
                 description="", is_permanent=False, max_stack=None,
                 duration=0, extra_status=None):
        super().__init__(id_name, name, "consumable", image_path,
                         description, is_permanent)
        self.effect_type = effect_type
        self.effect_value = effect_value
        self.count = 1
        self.max_stack = max_stack if max_stack is not None else self.MAX_STACK_DEFAULT
        self.duration = duration
        self.extra_status = extra_status

    @property
    def is_stackable(self):
        return True

    def use(self, player):
        if self.effect_type == "heal_percent":
            max_hp = int(getattr(player, "max_hp", 0))
            cur_hp = int(getattr(player, "hp", 0))
            missing = max(0, max_hp - cur_hp)
            healed = int(missing * (self.effect_value / 100.0))
            player.hp = min(max_hp, cur_hp + healed)

            if self.extra_status:
                try:
                    status_name, stacks = self.extra_status
                    apply = getattr(player, "_battle_apply_self_status", None)
                    if callable(apply):
                        apply(status_name, stacks)
                except Exception as e:
                    print(f"[Consumable] extra_status failed: {e}")

            return (True, f"Used {self.name}! Restored {healed} HP.")

        if self.effect_type == "boost_def":
            if getattr(player, "temp_def_bonus", 0) > 0:
                return (False, f"{self.name} is already active this battle!")
            player.temp_def_bonus = self.effect_value
            player.temp_def_bonus_turns = self.duration if self.duration > 0 else 0
            return (True, f"Used {self.name}! +{self.effect_value} DEF "
                          f"for {self.duration} turns.")

        if self.effect_type == "boost_atk":
            if getattr(player, "temp_atk_bonus", 0) > 0:
                return (False, f"{self.name} is already active this battle!")
            player.temp_atk_bonus = self.effect_value
            player.temp_atk_bonus_turns = self.duration if self.duration > 0 else 0
            return (True, f"Used {self.name}! +{self.effect_value} ATK "
                          f"for {self.duration} turns.")

        if self.effect_type == "boost_elem_atk":
            if hasattr(player, "elemental_attack"):
                player.elemental_attack += self.effect_value
            return (True, f"Used {self.name}! +{self.effect_value} "
                          f"Elemental ATK.")

        return (True, f"Used {self.name}!")


class Accessory(Item):
    def __init__(self, id_name, name, image_path, description="",
                 is_permanent=False, hp_bonus=0, atk_bonus=0,
                 elem_atk_bonus=0):
        super().__init__(id_name, name, "accessory", image_path,
                         description, is_permanent)
        self.hp_bonus = hp_bonus
        self.atk_bonus = atk_bonus
        self.elem_atk_bonus = elem_atk_bonus

        self._roll_key = None
        self._roll_amount = 0

    def _roll_golden_ring(self):
        if self._roll_key is None:
            self._roll_key = random.choice(["hp", "atk", "elem_atk"])
            self._roll_amount = random.randint(5, 10)

    def _apply_golden_ring(self, player, sign=1):
        if self._roll_key == "hp":
            delta = self._roll_amount * sign
            player.max_hp = max(1, player.max_hp + delta)
            player.hp = max(1, player.hp + delta)
            if player.hp > player.max_hp:
                player.hp = player.max_hp
        elif self._roll_key == "atk":
            player.atk = max(0, player.atk + self._roll_amount * sign)
        elif self._roll_key == "elem_atk":
            if hasattr(player, "elemental_attack"):
                player.elemental_attack = max(
                    0, player.elemental_attack + self._roll_amount * sign)

    def equip(self, player):
        if self.id_name == "golden_ring":
            self._roll_golden_ring()
            self._apply_golden_ring(player, sign=1)
            return

        if self.hp_bonus:
            player.max_hp += self.hp_bonus
            player.hp += self.hp_bonus
        if self.atk_bonus:
            player.atk += self.atk_bonus
        if self.elem_atk_bonus and hasattr(player, "elemental_attack"):
            player.elemental_attack += self.elem_atk_bonus

    def unequip(self, player):
        if self.id_name == "golden_ring":
            self._apply_golden_ring(player, sign=-1)
            return

        if self.hp_bonus:
            player.max_hp = max(1, player.max_hp - self.hp_bonus)
            if player.hp > player.max_hp:
                player.hp = player.max_hp
        if self.atk_bonus:
            player.atk = max(0, player.atk - self.atk_bonus)
        if self.elem_atk_bonus and hasattr(player, "elemental_attack"):
            player.elemental_attack = max(0, player.elemental_attack - self.elem_atk_bonus)


class Armor(Item):
    def __init__(self, id_name, name, image_path, def_boost=0,
                 hp_bonus=0,
                 description="", is_permanent=False):
        super().__init__(id_name, name, "armor", image_path,
                         description, is_permanent)
        self.def_boost = def_boost
        self.hp_bonus = hp_bonus

    def equip(self, player):
        player.defense += self.def_boost
        if self.hp_bonus:
            player.max_hp += self.hp_bonus
            player.hp += self.hp_bonus

    def unequip(self, player):
        player.defense = max(0, player.defense - self.def_boost)
        if self.hp_bonus:
            player.max_hp = max(1, player.max_hp - self.hp_bonus)
            if player.hp > player.max_hp:
                player.hp = player.max_hp


class Weapon(Item):
    def __init__(self, id_name, name, image_path, min_atk, max_atk,
                 min_elem_atk=0, max_elem_atk=0, element="Neutral",
                 description="", special_effects=None, is_permanent=False,
                 burst=None, off_hand_only=False, passive=None):
        super().__init__(id_name, name, "weapon", image_path,
                         description, is_permanent)

        self.is_permanent = True

        self.min_atk = min_atk
        self.max_atk = max_atk
        self.min_elem_atk = min_elem_atk
        self.max_elem_atk = max_elem_atk
        self.element = element
        self.special_effects = special_effects if special_effects else {}
        self.burst = dict(burst) if burst else None
        self.off_hand_only = off_hand_only
        self.passive = dict(passive) if passive else {}
        self._applied = {}

    @property
    def is_unique(self):
        return True

    def get_damage(self):
        phys = random.randint(self.min_atk, self.max_atk)
        elem = random.randint(self.min_elem_atk, self.max_elem_atk) if self.max_elem_atk > 0 else 0
        return phys, elem

    def get_total_damage(self):
        phys, elem = self.get_damage()
        return phys + elem

    def equip(self, player):
        self._applied = {}
        p = self.passive
        if not p:
            return

        if "defense" in p:
            amt = p["defense"]
            player.defense = getattr(player, "defense", 0) + amt
            self._applied["defense"] = amt

        if "atk_mult" in p:
            amt = p["atk_mult"]
            player.atk_mult = getattr(player, "atk_mult", 0.0) + amt
            self._applied["atk_mult"] = amt

        if "elem_atk_mult" in p:
            amt = p["elem_atk_mult"]
            player.elem_atk_mult = getattr(player, "elem_atk_mult", 0.0) + amt
            self._applied["elem_atk_mult"] = amt

        if "elem_dmg_bonus" in p:
            for element, amt in p["elem_dmg_bonus"].items():
                bonuses = getattr(player, "elem_dmg_bonus", None)
                if bonuses is None:
                    bonuses = {}
                    player.elem_dmg_bonus = bonuses
                bonuses[element] = bonuses.get(element, 0.0) + amt
                self._applied.setdefault("elem_dmg_bonus", {})[element] = amt

        if "status_dmg_bonus" in p:
            for status_key, amt in p["status_dmg_bonus"].items():
                bonuses = getattr(player, "status_dmg_bonus", None)
                if bonuses is None:
                    bonuses = {}
                    player.status_dmg_bonus = bonuses
                bonuses[status_key] = bonuses.get(status_key, 0.0) + amt
                self._applied.setdefault("status_dmg_bonus", {})[status_key] = amt

    def unequip(self, player):
        a = self._applied
        if not a:
            return

        if "defense" in a:
            player.defense = max(0, getattr(player, "defense", 0) - a["defense"])
        if "atk_mult" in a:
            player.atk_mult = max(0.0, getattr(player, "atk_mult", 0.0) - a["atk_mult"])
        if "elem_atk_mult" in a:
            player.elem_atk_mult = max(0.0, getattr(player, "elem_atk_mult", 0.0) - a["elem_atk_mult"])
        if "elem_dmg_bonus" in a:
            bonuses = getattr(player, "elem_dmg_bonus", None)
            if bonuses:
                for element, amt in a["elem_dmg_bonus"].items():
                    bonuses[element] = max(0.0, bonuses.get(element, 0.0) - amt)

        if "status_dmg_bonus" in a:
            bonuses = getattr(player, "status_dmg_bonus", None)
            if bonuses:
                for status_key, amt in a["status_dmg_bonus"].items():
                    bonuses[status_key] = max(0.0, bonuses.get(status_key, 0.0) - amt)

        self._applied = {}


class Inventory:
    INVENTORY_SIZE = 45
    PAGE_SIZE = 15

    def __init__(self, player):
        self.player = player
        self.fixed_items = [None] * self.INVENTORY_SIZE
        self.items = self.fixed_items
        self.current_page = 0

        self.equipped_weapon = None
        self.equipped_weapon_off = None
        self.equipped_helmet = None
        self.equipped_chestplate = None
        self.equipped_accessory = None

        crescent = ItemDatabase.get_item("crescent_necklace")
        if crescent:
            self.add_item(crescent)

        starter = ItemDatabase.get_item("crimson_petal_katana")
        if starter:
            self.add_item(starter)

    def add_item(self, item):
        if not item:
            return
        empty = next((i for i, x in enumerate(self.fixed_items) if x is None), None)
        if empty is not None:
            self.fixed_items[empty] = item
        else:
            self.fixed_items.extend([None] * self.PAGE_SIZE)
            self.fixed_items[-self.PAGE_SIZE] = item
        self.items = self.fixed_items


class ItemDatabase:
    BASE_DIR = os.path.join("asset", "items")
    WEAPON_DIR = os.path.join(BASE_DIR, "Weapon")

    _FACTORIES = {}
    _NAME_TO_ID = {}

    @staticmethod
    def _register(id_name, factory):
        ItemDatabase._FACTORIES[id_name] = factory
        probe = factory()
        if probe is not None:
            ItemDatabase._NAME_TO_ID[probe.name] = id_name

    @staticmethod
    def get_item(id_name, saved_data=None):
        factory = ItemDatabase._FACTORIES.get(id_name.lower())
        if not factory:
            return None
        item = factory()
        if item is not None and saved_data:
            if "def_boost" in saved_data and hasattr(item, "def_boost"):
                item.def_boost = saved_data["def_boost"]
            if "hp_bonus" in saved_data and hasattr(item, "hp_bonus"):
                item.hp_bonus = saved_data["hp_bonus"]
            if "_roll_key" in saved_data and hasattr(item, "_roll_key"):
                key = saved_data["_roll_key"]
                if key == "elem_def":
                    key = "hp"
                item._roll_key = key
                item._roll_amount = saved_data.get("_roll_amount", 0)
        return item

    @staticmethod
    def get_item_by_name(display_name, saved_data=None):
        id_name = ItemDatabase._NAME_TO_ID.get(display_name)
        return ItemDatabase.get_item(id_name, saved_data) if id_name else None

    @staticmethod
    def has_item(id_name):
        return id_name.lower() in ItemDatabase._FACTORIES

    @staticmethod
    def get_save_data(item):
        if item is None:
            return {}
        data = {}
        if hasattr(item, "def_boost"):
            if item.def_boost or getattr(item, "hp_bonus", 0):
                data["def_boost"] = item.def_boost
                if getattr(item, "hp_bonus", 0):
                    data["hp_bonus"] = item.hp_bonus
        if hasattr(item, "_roll_key") and item._roll_key:
            data["_roll_key"] = item._roll_key
            data["_roll_amount"] = item._roll_amount
        return data


def _register_items():
    B = ItemDatabase.BASE_DIR
    W = ItemDatabase.WEAPON_DIR
    reg = ItemDatabase._register

    def _make_golden_ring():
        ring = Accessory(
            "golden_ring", "Golden Ring", os.path.join(B, "golden_ring.png"),
            "Chest drop. z")
        ring._roll_golden_ring()
        return ring

    reg("golden_ring", _make_golden_ring)

    reg("crescent_necklace", lambda: Accessory(
        "crescent_necklace", "Crescent Necklace",
        os.path.join(B, "crescent_necklace.png"),
        "Lunaire's gift. Equip: +10 HP, +2 ATK. Cannot be dropped.",
        is_permanent=True, hp_bonus=10, atk_bonus=2))

    reg("heal_pot", lambda: Consumable(
        "heal_pot", "Healing Potion", os.path.join(B, "heal_pot.png"),
        "heal_percent", 55,
        "Restores 55% of missing HP. Also grants Healing x3 "
        "(2% missing HP per stack per turn, 3 turns).",
        extra_status=("healing", 3)))

    reg("def_pot", lambda: Consumable(
        "def_pot", "Defense Potion", os.path.join(B, "def_pot.png"),
        "boost_def", 10,
        "Boosts Defense by 10 for 5 turns.",
        duration=5))

    reg("attk_pot", lambda: Consumable(
        "attk_pot", "Attack Potion", os.path.join(B, "attk_pot.png"),
        "boost_atk", 10,
        "Boosts Attack by 10 for 5 turns.",
        duration=5))

    reg("chestplate_1", lambda: Armor(
        "chestplate_1", "Oz's Chestplate", os.path.join(B, "chestplate_1.png"),
        def_boost=random.randint(5, 10),
        description="Chest drop. Random DEF 5-10."))

    reg("helmet_1", lambda: Armor(
        "helmet_1", "Tiny Orc Helmet", os.path.join(B, "helmet_1.png"),
        def_boost=random.randint(5, 10),
        description="Chest drop. Random DEF 5-10."))

    reg("chestplate_2", lambda: Armor(
        "chestplate_2", "Iron Dragon Chestplate",
        os.path.join(B, "chestplate_2.png"),
        def_boost=20,
        description="Oz's gift. +20 DEF. Cannot be dropped.",
        is_permanent=True))

    reg("helmet_2", lambda: Armor(
        "helmet_2", "Iron Dragon Helmet",
        os.path.join(B, "helmet_2.png"),
        def_boost=20,
        description="Oz's gift. +20 DEF. Cannot be dropped.",
        is_permanent=True))

    reg("crimson_petal_katana", lambda: Weapon(
        "crimson_petal_katana", "Crimson Petal Katana",
        os.path.join(W, "Crimson_Petal_Katana.png"),
        5, 7, 0, 0, "Neutral",
        "Your father's blade. Inflicts Bleed. Cannot be dropped.",
        {"inflict_bleed": True},
        is_permanent=True,
        burst=None))

    reg("earth_sword", lambda: Weapon(
        "earth_sword", "Earth Sword", os.path.join(W, "Earth_Sword.png"),
        5, 5, 0, 0, "Earth",
        "A sturdy earth blade. Given by Oz. +5 DEF when equipped.",
        is_permanent=True,
        passive={"defense": 5},
        burst=BURST_GROUNDBREAKING))

    reg("flaming_saber", lambda: Weapon(
        "flaming_saber", "Flaming Saber", os.path.join(W, "Flaming_Saber.png"),
        4, 4, 0, 0, "Fire",
        "A saber wreathed in flame. Given by Oz.",
        {"inflict_burn": 3},
        is_permanent=True,
        burst=BURST_FERAL_INFERNO))

    reg("water_spike", lambda: Weapon(
        "water_spike", "Water Spike", os.path.join(W, "Water_Spike.png"),
        4, 4, 0, 0, "Water",
        "A needle of frozen water. Given by Oz.",
        {"inflict_weak": 2},
        is_permanent=True,
        burst=BURST_TIDAL_CRESCENT))

    reg("dual_rapier", lambda: Weapon(
        "dual_rapier", "Dual Rapier", os.path.join(W, "Dual_Rapier.png"),
        0, 0, 0, 0, "Neutral",
        "Oz's reward. OFF-HAND only. +5% elemental ATK to main weapon.",
        off_hand_only=True,
        passive={"elem_atk_mult": 0.05},
        burst=None))

    reg("thorny_vines", lambda: Weapon(
        "thorny_vines", "Thorny Vines", os.path.join(W, "Thorny_Vines.png"),
        3, 5, 0, 0, "Earth",
        "Slime drop. Poison is permanent when in the OFF-HAND slot.",
        {"inflict_poison": True, "permanent_poison_off_hand": True},
        burst=BURST_THORN_BLOOM))

    reg("dinosaur_tooth", lambda: Weapon(
        "dinosaur_tooth", "Dinosaur Tooth", os.path.join(W, "Dinosaur_Tooth.png"),
        4, 8, 0, 0, "Earth",
        "Earth Orc drop. Ignores Earth immunity.",
        {"ignore_earth_immunity": True},
        burst=BURST_VERDANT_RUPTURE))

    reg("broken_feather", lambda: Weapon(
        "broken_feather", "Broken Feather", os.path.join(W, "Broken_Feather.png"),
        3, 8, 0, 0, "Wind",
        "Wind Orc drop. Feather Burst inflicts Bleed (3 stacks).",
        burst=BURST_FEATHER_BURST))

    reg("water_bearer", lambda: Weapon(
        "water_bearer", "Water Bearer", os.path.join(W, "Water_Bearer.png"),
        3, 6, 0, 0, "Water",
        "Water Orc drop. 15% chance to stun.",
        {"stun_chance": 0.15},
        burst=BURST_SERAPHIC_TORRENT))

    reg("steel_feather", lambda: Weapon(
        "steel_feather", "Steel Feather", os.path.join(W, "Steel Feather.png"),
        4, 7, 0, 0, "Wind",
        "Rare chest drop. +5% Wind and Bleed damage.",
        passive={
            "elem_dmg_bonus":   {"Wind":  0.05},
            "status_dmg_bonus": {"bleed": 0.05},
        },
        burst=BURST_HEAVENLY_GALE))

    reg("blueflame_katana", lambda: Weapon(
        "blueflame_katana", "Blueflame Katana",
        os.path.join(W, "Blueflame_Katana.png"),
        1, 2, 0, 0, "Fire",
        "Kitsune drop. OFF-HAND only. Applies Burn 2. "
        "Transforms existing Burn into Blue Flame when paired "
        "with another Burn source.",
        {"inflict_burn": 2, "transform_blue_flame": True},
        off_hand_only=True,
        burst=None))

    reg("the_suns_ray", lambda: Weapon(
        "the_suns_ray", "The Suns Ray", os.path.join(W, "The_Suns_Ray.png"),
        5, 10, 0, 0, "Fire",
        "Oz's future reward. +20% Fire damage. "
        "Applies Burn 3 and instantly triggers Burn damage on hit.",
        {"inflict_burn": 3, "trigger_burn_instantly": True},
        passive={"elem_dmg_bonus": {"Fire": 0.20}},
        burst=BURST_BLAZING_DETONATION))

    reg("demon_blade", lambda: Weapon(
        "demon_blade", "Demon Blade", os.path.join(W, "Demon_Blade.png"),
        5, 10, 0, 0, "Neutral",
        "Tiny Devil drop. +20% ATK.",
        passive={"atk_mult": 0.20},
        burst=BURST_SINNERS_PUNISHMENT))

    reg("rainbow_water_blade", lambda: Weapon(
        "rainbow_water_blade", "Rainbow Water Blade",
        os.path.join(W, "Rainbow_Water_Blade.png"),
        8, 15, 0, 0, "Water",
        "Hidden in the Mystic Forest. OFF-HAND only. Pure damage.",
        {"true_damage": True},
        off_hand_only=True,
        burst=None))

    reg("eclipsis_dagger", lambda: Weapon(
        "eclipsis_dagger", "Eclipsis Dagger",
        os.path.join(W, "Eclipsis_Dagger.png"),
        20, 40, 0, 0, "Moon",
        "Wizard Oz's trial reward. MOON DAMAGE: ignores enemy DEF "
        "AND the element wheel, so it always deals 100% (or more) "
        "of its damage. Deals DOUBLE damage to Gorgona on BASIC, "
        "ELEMENTAL SLASH, and ELEMENTAL BURST.",
        {"true_damage": True, "moon_damage": True},
        burst=BURST_ECLIPSE_END))


_register_items()