# game_enums.py
from enum import Enum


class TimeOfDay(Enum):
    MORNING = 0
    AFTERNOON = 1
    EVENING = 2
    NIGHT = 3


class Weather(Enum):
    CLEAR = 0
    CLOUDY = 1
    RAINY = 2
    FOGGY = 3
    STORMY = 4


class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3


class EventType(Enum):
    FIRST_MEETING = "first_meeting"
    CONVERSATION = "conversation"
    QUEST_ACCEPTED = "quest_accepted"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    ITEM_GIFTED = "item_gifted"
    OBSERVED_COMBAT = "observed_combat"
    HELPED_IN_DANGER = "helped_in_danger"
    VISITED_LOCATION = "visited_location"
    SHARED_SECRET = "shared_secret"
    BETRAYAL = "betrayal"
