import os
import sys
import random

# Find the folder this file lives in
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Find the main project folder (one level up from this file)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Make sure Python can find our other project files when importing
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class ElementComponent:
    # This is the list of the 4 elements that exist in our game
    ELEMENTS = ["Fire", "Wind", "Earth", "Water"]

    # This dictionary tells us which element beats which other element.
    # Fire beats Wind, Wind beats Earth, Earth beats Water, Water beats Fire.
    # It goes in a circle, like Rock-Paper-Scissors but with 4 elements instead of 3.
    ADVANTAGES = {
        "Fire": "Wind",
        "Wind": "Earth",
        "Earth": "Water",
        "Water": "Fire"
    }

    def __init__(self, element_type="random"):
        # If someone asks for a random element, pick one from the list above
        if element_type.lower() == "random":
            self.element_type = random.choice(self.ELEMENTS)
        else:
            # Otherwise, use the specific element they asked for
            # .capitalize() makes sure "fire" becomes "Fire" so it matches our dictionary keys
            self.element_type = element_type.capitalize()

    def get_damage_multiplier(self, target_element):
        # If the target has no element at all, just deal normal damage (no bonus, no penalty)
        if not target_element:
            return 1.0

        # target_element might be a whole ElementComponent object, or just a plain string.
        # This line tries to grab ".element_type" off of it, but if that doesn't exist,
        # it just uses target_element directly as the string itself.
        target_type = getattr(target_element, "element_type", target_element)

        # Check: does MY element beat the TARGET's element?
        # Example: I am Fire, target is Wind. Fire beats Wind. So I deal STRONG damage.
        if self.ADVANTAGES.get(self.element_type) == target_type:
            return 1.5  # Strong against target: deal 1.5x damage

        # Check: does the TARGET's element beat MY element?
        # Example: I am Fire, target is Water. Water beats Fire. So I deal WEAK damage.
        if self.ADVANTAGES.get(target_type) == self.element_type:
            return 0.5  # Weak against target: deal 0.5x damage (FIXED: was 0.75, now correctly 0.5)

        # Neither element beats the other, so it's a neutral matchup
        return 1.0  # Neutral: deal normal 1.0x damage