#RPG 게임 데이터 모델 및 타입 정의

from typing import TypedDict, Annotated, List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum
import operator

class ReputationLevel(Enum):
    #명성 레벨 정의
    HEROIC = "heroic"           # 80+: 영웅적 대우
    VERY_FRIENDLY = "very_friendly"  # 60-79: 매우 호의적
    FRIENDLY = "friendly"       # 20-59: 호의적
    NEUTRAL = "neutral"         # 0-19: 평범
    SLIGHTLY_HOSTILE = "slightly_hostile"  # -1 to -20: 약간 비호의적
    HOSTILE = "hostile"         # -21 to -40: 혐악
    VERY_HOSTILE = "very_hostile"  # -41 to -60: 매우 험악/무서워함
    ENEMY = "enemy"             # -61 이하: 적대적/시비

@dataclass
class Player:
    #플레이어 정보
    name: str
    race: str
    class_type: str
    level: int
    hp: int
    mp: int
    reputation: int = 0
    gold: int = 300
    weapon: str = "기본 무기"
    armor: str = "기본 방어구"

@dataclass
class NPC:
    #NPC 정보
    name: str
    race: str
    class_type: str
    level: int
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    strength: int
    agility: int
    intelligence: int
    backstory: str
    personality: str
    special_ability: str
    location: str

@dataclass
class Item:
    #아이템 정보
    name: str
    type: str
    quantity: int
    description: str
    value: int = 0

class PlayerInitState(TypedDict):
    #LangGraph 상태 정의
    messages: Annotated[List, operator.add]
    player: Player
    companion_ids: List[int]
    current_situation: str
    game_active: bool
    main_story_db: object
    main_story_player_id: int
    party_full: bool
    next_action: str
    current_location: str
    current_objective: str
    player_gold: int
    reputation_changes: List[Dict]  # 명성 변화 기록

@dataclass
class ReputationResponse:
    #명성 기반 응답 정보
    level: ReputationLevel
    greeting: str
    tone: str
    willingness_to_help: float  # 0.0 ~ 1.0
    price_modifier: float  # 0.5 ~ 2.0
    special_actions: List[str]


class ShopItem(TypedDict):
    #상점 아이템 정보
    name: str
    price: int
    type: str
    description: str
    stock: int

class BattleResult(TypedDict):
    #전투 결과 정보
    participant_name: str
    damage_taken: int
    mp_used: int
    damage_dealt: int
    hp_after: Union[int, str]
    mp_after: Union[int, str]
    alive: bool
    critical: bool
    special_action: bool


class StoryContext(TypedDict):
    #스토리 컨텍스트 정보
    player_info: str
    party_members: List[str]
    current_location: str
    current_objective: str
    recent_events: List[str]
    session_turn_count: int
    total_adventures: int
    reputation_level: ReputationLevel


# 게임 상수
GAME_CONSTANTS = {
    "MAX_PARTY_SIZE": 3,
    "MAX_COMPANION_COUNT": 2,
    "DEFAULT_GOLD": 300,
    "BATTLE_CRITICAL_CHANCE": 0.15,
    "BATTLE_SPECIAL_CHANCE": 0.20,
    "HEALING_POTION_EFFECT": 50,
    "MANA_POTION_EFFECT": 30,
    "HEAL_SPELL_EFFECT": 70,
    "HEAL_SPELL_COST": 10
}

# 명성 시스템 설정
REPUTATION_THRESHOLDS = {
    ReputationLevel.HEROIC: 80,
    ReputationLevel.VERY_FRIENDLY: 60,
    ReputationLevel.FRIENDLY: 20,
    ReputationLevel.NEUTRAL: 0,
    ReputationLevel.SLIGHTLY_HOSTILE: -1,
    ReputationLevel.HOSTILE: -21,
    ReputationLevel.VERY_HOSTILE: -41,
    ReputationLevel.ENEMY: -61
}