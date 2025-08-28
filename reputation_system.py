# 명성 시스템 관리
# NPC와의 상호작용에서 명성에 따른 태도 변화 처리
import random
from typing import Dict, List, Optional
from models import ReputationLevel, ReputationResponse, REPUTATION_THRESHOLDS
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

class ReputationManager:
    #명성 시스템 관리 클래스"

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    def get_reputation_level(self, reputation: int) -> ReputationLevel:
        #명성에 따른 등급 처리
        #HEROIC>=80
        #VERY_FRIENDLY >=60
        #FRIENDLY >=20
        #NEUTRAL >=0
        #SLIGHTLY_HOSTILE >= -20
        #HOSTILE >= -60
        #VERY_HOSTILE >=-80
        #ENEMY < -80
        if reputation >= REPUTATION_THRESHOLDS[ReputationLevel.HEROIC]:
            return ReputationLevel.HEROIC
        elif reputation >= REPUTATION_THRESHOLDS[ReputationLevel.VERY_FRIENDLY]:
            return ReputationLevel.VERY_FRIENDLY
        elif reputation >= REPUTATION_THRESHOLDS[ReputationLevel.FRIENDLY]:
            return ReputationLevel.FRIENDLY
        elif reputation >= REPUTATION_THRESHOLDS[ReputationLevel.NEUTRAL]:
            return ReputationLevel.NEUTRAL
        elif reputation >= REPUTATION_THRESHOLDS[ReputationLevel.SLIGHTLY_HOSTILE]:
            return ReputationLevel.SLIGHTLY_HOSTILE
        elif reputation >= REPUTATION_THRESHOLDS[ReputationLevel.HOSTILE]:
            return ReputationLevel.HOSTILE
        elif reputation >= REPUTATION_THRESHOLDS[ReputationLevel.VERY_HOSTILE]:
            return ReputationLevel.VERY_HOSTILE
        else:
            return ReputationLevel.ENEMY
        
    def get_reputation_response(self, reputation: int, npc_name: str = "NPC", location: str = "마을") -> ReputationResponse:
        #명성에 따른 NPC 응답 성향 변화

        level = self.get_reputation_level(reputation)
        
        response_configs = {
            ReputationLevel.HEROIC: {
                "greeting": f"영웅님! {npc_name}입니다. 당신의 명성은 온 대륙에 울려 퍼지고 있습니다!",
                "tone": "극도로 존경스럽고 경외심 가득한",
                "willingness_to_help": 1.0,
                "price_modifier": 0.5,
                "special_actions": ["무료_서비스", "특별_정보_제공", "귀중한_선물"]
            },
            ReputationLevel.VERY_FRIENDLY: {
                "greeting": f"오, {npc_name}입니다! 당신의 업적은 정말 훌륭합니다!",
                "tone": "매우 친근하고 호의적인",
                "willingness_to_help": 0.9,
                "price_modifier": 0.7,
                "special_actions": ["할인_제공", "추가_정보", "친절한_조언"]
            },
            ReputationLevel.FRIENDLY: {
                "greeting": f"안녕하세요! {npc_name}입니다. 좋은 평판을 들었습니다.",
                "tone": "친근하고 협조적인",
                "willingness_to_help": 0.8,
                "price_modifier": 0.9,
                "special_actions": ["약간_할인", "기본_정보_제공"]
            },
            ReputationLevel.NEUTRAL: {
                "greeting": f"안녕하세요. {npc_name}입니다.",
                "tone": "평범하고 중립적인",
                "willingness_to_help": 0.6,
                "price_modifier": 1.0,
                "special_actions": ["기본_서비스"]
            },
            ReputationLevel.SLIGHTLY_HOSTILE: {
                "greeting": f"음... {npc_name}입니다. 당신에 대한 이야기를 들었는데...",
                "tone": "약간 경계하는",
                "willingness_to_help": 0.4,
                "price_modifier": 1.2,
                "special_actions": ["정보_제한", "경계"]
            },
            ReputationLevel.HOSTILE: {
                "greeting": f"흥! {npc_name}다. 당신 같은 자와는 거래하기 싫지만...",
                "tone": "적대적이고 불쾌한",
                "willingness_to_help": 0.2,
                "price_modifier": 1.5,
                "special_actions": ["높은_가격", "무례한_태도", "정보_거부"]
            },
            ReputationLevel.VERY_HOSTILE: {
                "greeting": f"당신이... {npc_name}은 당신을 경계하고 있습니다.",
                "tone": "매우 적대적이고 두려워하는",
                "willingness_to_help": 0.1,
                "price_modifier": 2.0,
                "special_actions": ["서비스_거부", "도망_시도", "경비_호출"]
            },
            ReputationLevel.ENEMY: {
                "greeting": f"감히 여기에 나타나다니! {npc_name}이 당신을 용서하지 않겠다!",
                "tone": "극도로 적대적이고 공격적인",
                "willingness_to_help": 0.0,
                "price_modifier": 3.0,
                "special_actions": ["전투_시작", "도망", "경비_호출", "위협"]
            }
        }

        config = response_configs[level]
        
        return ReputationResponse(
            level=level,
            greeting=config["greeting"],
            tone=config["tone"],
            willingness_to_help=config["willingness_to_help"],
            price_modifier=config["price_modifier"],
            special_actions=config["special_actions"]
        )
    def generate_npc_dialogue(self, reputation: int, npc_name: str, location: str, context: str, user_input: str) -> str:
        #명성에 따른 NPC 대화 생성
        response_info = self.get_reputation_response(reputation, npc_name, location)

        # 특별한 행동 결정
        special_action = None
        if response_info.special_actions:
            if response_info.level == ReputationLevel.ENEMY:
                # 적대적인 경우 높은 확률로 특별 행동
                if random.random() < 0.7:
                    special_action = random.choice(response_info.special_actions)
            elif response_info.level == ReputationLevel.VERY_HOSTILE:
                if random.random() < 0.5:
                    special_action = random.choice(response_info.special_actions)
            elif response_info.level == ReputationLevel.HEROIC:
                if random.random() < 0.8:
                    special_action = random.choice(response_info.special_actions)
        
        sys_prompt = f"""
        당신은 {location}에 있는 {npc_name}입니다.
        
        **명성 정보:**
        - 플레이어의 명성: {reputation}
        - 명성 레벨: {response_info.level.value}
        - 당신의 태도: {response_info.tone}
        - 협조 의지: {response_info.willingness_to_help * 100:.0f}%
        
        **상황 컨텍스트:**
        {context}
        
        **플레이어 말:**
        "{user_input}"
        
        **특별 행동:** {special_action if special_action else "없음"}
        
        **지침:**
        1. 명성에 따른 태도를 일관되게 유지
        2. {response_info.tone} 톤으로 대화
        3. 협조 의지({response_info.willingness_to_help * 100:.0f}%)에 맞게 도움 제공
        4. 특별 행동이 있다면 자연스럽게 포함
        5. 150-200자 내외로 응답
        
        **명성별 행동 가이드:**
        - 영웅급(80+): 극도로 존경, 무료 서비스, 특별 정보
        - 매우 호의(60-79): 매우 친근, 할인, 추가 정보
        - 호의(20-59): 친근, 기본 할인, 협조적
        - 평범(0-19): 중립적, 정상 가격, 기본 서비스
        - 약간 적대(-1~-20): 경계, 약간 비싼 가격
        - 적대(-21~-40): 불쾌함, 높은 가격, 무례
        - 매우 적대(-41~-60): 두려움, 서비스 거부
        - 원수(-61 이하): 공격적, 전투 또는 도망
        
        자연스럽고 몰입감 있는 대화를 생성하세요.
        """

        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"명성 {reputation}에 맞는 대화 생성")
            ])
            
            return response.content
            
        except Exception as e:
            print(f"NPC 대화 생성 오류: {e}")
            # 기본 응답
            return f"{npc_name}: {response_info.greeting}"
        
    def calculate_reputation_change(self, action: str, context: str = "") -> int:
        #행동에 따른 명성 변화 
        reputation_changes = {
            "퀘스트_완료": 10,
            "선한_행동": 5,
            "생명_구조": 15,
            "마을_구원": 25,
            "보스_처치": 20,
            "동료_배신": -30,
            "민간인_공격": -40,
            "도둑질": -15,
            "거짓말": -5,
            "약속_위반": -10,
            "폭력_행위": -20,
            "마을_파괴": -50
        }
        
        return reputation_changes.get(action, 0)
    
    def update_reputation(self, current_reputation: int, change: int, reason: str = "") -> Dict:
        #명성 업데이트 및 변화 기록
        new_reputation = max(-100, min(100, current_reputation + change))
        old_level = self.get_reputation_level(current_reputation)
        new_level = self.get_reputation_level(new_reputation)
        
        change_info = {
            "old_reputation": current_reputation,
            "new_reputation": new_reputation,
            "change": change,
            "reason": reason,
            "old_level": old_level,
            "new_level": new_level,
            "level_changed": old_level != new_level
        }
        
        return change_info
    
    def get_reputation_status_message(self, reputation: int) -> str:
        #현재 명성 상태 메시지
        level = self.get_reputation_level(reputation)
        
        status_messages = {
            ReputationLevel.HEROIC: f"🌟 영웅 ({reputation}) - 모든 이들이 당신을 경외합니다!",
            ReputationLevel.VERY_FRIENDLY: f"😊 매우 호의적 ({reputation}) - 사람들이 당신을 매우 좋아합니다!",
            ReputationLevel.FRIENDLY: f"🙂 호의적 ({reputation}) - 사람들이 당신을 좋아합니다.",
            ReputationLevel.NEUTRAL: f"😐 평범 ({reputation}) - 보통의 평판입니다.",
            ReputationLevel.SLIGHTLY_HOSTILE: f"😕 약간 비호의적 ({reputation}) - 사람들이 당신을 경계합니다.",
            ReputationLevel.HOSTILE: f"😠 적대적 ({reputation}) - 사람들이 당신을 싫어합니다.",
            ReputationLevel.VERY_HOSTILE: f"😨 매우 적대적 ({reputation}) - 사람들이 당신을 무서워합니다!",
            ReputationLevel.ENEMY: f"💀 원수 ({reputation}) - 사람들이 당신을 증오합니다!"
        }

        return status_messages[level]
    
    def apply_reputation_to_price(self, base_price: int, reputation: int) -> int:
        #명성에 따른 가격 조정
        response_info = self.get_reputation_response(reputation)
        adjusted_price = int(base_price * response_info.price_modifier)
        return max(1, adjusted_price)  # 최소 1골드
    
    def can_access_service(self, reputation: int, service_type: str) -> bool:
        #명성에 따른 서비스 접근 가능 여부
        level = self.get_reputation_level(reputation)
        
        service_requirements = {
            "기본_상점": ReputationLevel.VERY_HOSTILE,
            "특별_아이템": ReputationLevel.FRIENDLY,
            "고급_서비스": ReputationLevel.VERY_FRIENDLY,
            "영웅_전용": ReputationLevel.HEROIC,
            "정보_수집": ReputationLevel.NEUTRAL,
            "퀘스트_수주": ReputationLevel.SLIGHTLY_HOSTILE
        }
        
        required_level = service_requirements.get(service_type, ReputationLevel.NEUTRAL)
        player_level_value = list(REPUTATION_THRESHOLDS.keys()).index(level)
        required_level_value = list(REPUTATION_THRESHOLDS.keys()).index(required_level)
        
        return player_level_value <= required_level_value
    