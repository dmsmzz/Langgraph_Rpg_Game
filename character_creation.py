#캐릭터 생성 시스템 모듈
#플레이어 캐릭터 생성 및 설정

import json
import random
from typing import Dict, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from models import Player

class CharacterCreator:
    #캐릭터 생성 관리 클래스
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    def parse_character_input(self, user_input: str) -> Optional[Dict]:
        #사용자 입력에서 캐릭터 정보 파싱
        sys_prompt = """
        사용자 입력에서 캐릭터 정보를 추출해서 JSON으로 반환하세요.
        
        추출할 정보:
        - 이름 (string)
        - 종족 (string, [인간, 엘프, 드워프, 오크, 하플링] 중 하나 또는 사용자 창의적 선택)
        - 직업 (string, [전사, 마법사, 도적, 궁수, 성직자] 중 하나 또는 사용자 창의적 선택)
        - 나이 (integer)
        
        만약 정보가 부족하면 해당 항목을 null로 설정하세요.
        
        JSON 형식으로만 답변하세요:
        {"이름": "값", "종족": "값", "직업": "값", "나이": 값}
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=user_input)
            ])
            
            character_data = json.loads(response.content)
            
            # 필수 정보 확인
            required_fields = ["이름", "종족", "직업", "나이"]
            missing_fields = [field for field in required_fields if not character_data.get(field)]
            
            if missing_fields:
                return None
            
            return character_data
            
        except Exception as e:
            print(f"캐릭터 정보 파싱 오류: {e}")
            return None
        
    def generate_starting_location(self, character_data: Dict) -> str:
        #캐릭터 정보를 바탕으로 시작 지점 생성
        name = character_data.get("이름", "모험가")
        race = character_data.get("종족", "인간")
        job = character_data.get("직업", "전사")
        age = character_data.get("나이", 20)
        
        sys_prompt = f"""
        다음 캐릭터 정보를 바탕으로 흥미로운 시작 지점을 생성해주세요.
        
        캐릭터 정보:
        - 이름: {name}
        - 종족: {race}
        - 직업: {job}
        - 나이: {age}세
        
        **시작 지점 생성 가이드라인:**
        1. 캐릭터의 종족과 직업에 어울리는 장소
        2. 모험을 시작하기에 적합한 환경
        3. 창의적이고 흥미로운 설정
        4. 너무 위험하지 않은 초심자 적합 지역
        
        **예시:**
        - 고대 도서관 (마법사에게 적합)
        - 번화한 상업도시 (도적에게 적합)
        - 평화로운 대도시 (전사에게 적합)
        - 신비로운 숲의 오두막 (엘프에게 적합)
        - 산악 지대의 광산 마을 (드워프에게 적합)
        
        창의적인 시작 지점 이름을 한 줄로만 답해주세요.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"{name}의 시작 지점 생성")
            ])
            
            starting_location = response.content.strip()
            return starting_location
            
        except Exception as e:
            print(f"시작 지점 생성 오류: {e}")
            return "모험가의 마을"
        
    def generate_character_backstory(self, character_data: Dict, starting_location: str) -> str:
        #캐릭터 배경 스토리 생성
        name = character_data.get("이름", "모험가")
        race = character_data.get("종족", "인간")
        job = character_data.get("직업", "전사")
        age = character_data.get("나이", 20)
        
        sys_prompt = f"""
        다음 캐릭터의 배경 스토리를 생성해주세요.
        
        캐릭터 정보:
        - 이름: {name}
        - 종족: {race}
        - 직업: {job}
        - 나이: {age}세
        - 시작 지점: {starting_location}
        
        **배경 스토리 가이드라인:**
        1. 캐릭터가 왜 모험을 시작하게 되었는지
        2. 어떤 과거를 가지고 있는지
        3. 시작 지점과 어떤 연관이 있는지
        4. 앞으로의 목표나 꿈
        5. "1. 주점으로 간다 2. 동료에게 대화를 한다" 같은 번호가 매겨진 선택지를 제시하지 마세요
        6. 대신 열린 상황을 만들어 플레이어가 자유롭게 행동할 수 있도록 하세요
        7. "무엇을 하고 싶나요?" 또는 "어떤 행동을 취하시겠어요?" 같은 열린 질문으로 마무리
        
        200-300자 내외로 흥미로운 배경 스토리를 작성해주세요.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"{name}의 배경 스토리 생성")
            ])
            
            return response.content.strip()
            
        except Exception as e:
            print(f"배경 스토리 생성 오류: {e}")
            return f"{name}은 {starting_location}에서 모험을 시작하는 {race} {job}입니다."
        
    def calculate_starting_stats(self, character_data: Dict) -> Dict:
        #직업에 따른 초기 능력치 계산
        job = character_data.get("직업", "전사")
        race = character_data.get("종족", "인간")
        
        # 기본 능력치 (직업별)
        job_stats = {
            "전사": {"힘": 12, "민첩": 8, "지력": 6, "hp_bonus": 20, "mp_bonus": 0},
            "마법사": {"힘": 6, "민첩": 8, "지력": 12, "hp_bonus": 0, "mp_bonus": 30},
            "도적": {"힘": 8, "민첩": 12, "지력": 6, "hp_bonus": 10, "mp_bonus": 10},
            "궁수": {"힘": 8, "민첩": 11, "지력": 7, "hp_bonus": 15, "mp_bonus": 5},
            "성직자": {"힘": 7, "민첩": 7, "지력": 11, "hp_bonus": 15, "mp_bonus": 25}
        }
        
        # 종족 보정
        race_modifiers = {
            "인간": {"힘": 0, "민첩": 0, "지력": 0},
            "엘프": {"힘": -1, "민첩": +2, "지력": +1},
            "드워프": {"힘": +2, "민첩": -1, "지력": 0},
            "오크": {"힘": +2, "민첩": 0, "지력": -1},
            "하플링": {"힘": -1, "민첩": +2, "지력": 0}
        }
        
        base_stats = job_stats.get(job, job_stats["전사"])
        race_modifier = race_modifiers.get(race, race_modifiers["인간"])
        
        final_stats = {
            "힘": base_stats["힘"] + race_modifier["힘"],
            "민첩": base_stats["민첩"] + race_modifier["민첩"],
            "지력": base_stats["지력"] + race_modifier["지력"],
            "hp": 80 + base_stats["hp_bonus"] + (base_stats["힘"] * 2),
            "mp": 40 + base_stats["mp_bonus"] + (base_stats["지력"] * 3)
        }
        
        return final_stats
    
    def generate_starting_items(self, character_data: Dict) -> list:
        #직업에 따른 초기 아이템 생성
        job = character_data.get("직업", "전사")
        
        starting_items = {
            "전사": [
                {"name": "철검", "type": "weapon", "description": "견고한 철로 만든 검"},
                {"name": "가죽 갑옷", "type": "armor", "description": "기본적인 방어구"},
                {"name": "나무 방패", "type": "shield", "description": "튼튼한 나무 방패"},
                {"name": "체력 물약", "type": "potion", "description": "HP 50 회복", "quantity": 3}
            ],
            "마법사": [
                {"name": "마법 지팡이", "type": "weapon", "description": "마법력을 증폭시키는 지팡이"},
                {"name": "마법사 로브", "type": "armor", "description": "마법 방어력을 제공하는 로브"},
                {"name": "마법서: 파이어볼", "type": "spellbook", "description": "화염 마법서"},
                {"name": "마나 물약", "type": "potion", "description": "MP 30 회복", "quantity": 5}
            ],
            "도적": [
                {"name": "단검", "type": "weapon", "description": "날카로운 단검"},
                {"name": "가죽 갑옷", "type": "armor", "description": "조용한 가죽 갑옷"},
                {"name": "도구 세트", "type": "tool", "description": "자물쇠 따개와 각종 도구"},
                {"name": "독 바르기", "type": "consumable", "description": "무기에 독을 바르는 도구"}
            ],
            "궁수": [
                {"name": "장궁", "type": "weapon", "description": "정확한 장거리 활"},
                {"name": "화살통", "type": "ammunition", "description": "화살 30발", "quantity": 30},
                {"name": "가죽 갑옷", "type": "armor", "description": "가벼운 가죽 갑옷"},
                {"name": "체력 물약", "type": "potion", "description": "HP 50 회복", "quantity": 2}
            ],
            "성직자": [
                {"name": "성스러운 지팡이", "type": "weapon", "description": "치유 마법이 깃든 지팡이"},
                {"name": "성직자 로브", "type": "armor", "description": "신성한 힘을 담은 로브"},
                {"name": "성수", "type": "consumable", "description": "언데드에게 효과적", "quantity": 3},
                {"name": "치유 물약", "type": "potion", "description": "HP 80 회복", "quantity": 4}
            ]
        }
        
        return starting_items.get(job, starting_items["전사"])
    

    def create_player_object(self, character_data: Dict, starting_location: str, backstory: str, stats: Dict, items: list) -> Player:
        #완성된 플레이어 객체 생성
        return Player(
            name=character_data["이름"],
            race=character_data["종족"],
            class_type=character_data["직업"],
            level=1,
            hp=stats["hp"],
            mp=stats["mp"],
            reputation=0,
            gold=300,
            weapon=items[0]["name"] if items else "맨손",
            armor=items[1]["name"] if len(items) > 1 else "평복"
        )
    
    def generate_creation_story(self, player: Player, starting_location: str, backstory: str, stats: Dict, items: list) -> str:
        #캐릭터 생성 완료 스토리 생성
        sys_prompt = f"""
        캐릭터 생성이 완료되었습니다. 게임 시작 장면을 생성해주세요.
        
        캐릭터 정보:
        - 이름: {player.name}
        - 종족: {player.race}
        - 직업: {player.class_type}
        - 레벨: {player.level}
        - HP: {player.hp}
        - MP: {player.mp}
        - 시작 지점: {starting_location}
        - 배경 스토리: {backstory}
        - 주요 장비: {items[0]['name'] if items else '없음'}
        
        **게임 시작 장면 생성 가이드:**
        1. 시작 지점의 분위기와 환경 묘사
        2. 캐릭터가 어떤 상황에 놓여있는지
        3. 첫 번째 선택지나 행동 기회 제시
        4. 명성 시스템 간단히 언급
        
        300-400자 내외로 몰입감 있는 시작 장면을 만들어주세요.
        "어떻게 하시겠어요?"로 마무리해주세요.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"{player.name}의 게임 시작 장면 생성")
            ])
            
            return response.content.strip()
            
        except Exception as e:
            print(f"생성 스토리 오류: {e}")
            return f"{player.name}님의 모험이 {starting_location}에서 시작됩니다. 어떻게 하시겠어요?"
 
def show_character_creation_help():
    #캐릭터 생성 도움말
    help_text = """
        **캐릭터 생성 가이드**

        **입력 예시:**
        "내 이름은 아리아이고 종족은 엘프, 직업은 마법사, 나이는 120살이야"
        "나는 인간 전사 토르고 25살이다"
        "엘린이라는 하플링 도적으로 18살"

        **사용 가능한 종족:**
        • 인간 - 균형잡힌 능력치
        • 엘프 - 민첩성과 지력 보정
        • 드워프 - 힘 보정, 내구성 우수
        • 오크 - 높은 힘, 전투 특화
        • 하플링 - 민첩성 우수, 작고 빠름

        **사용 가능한 직업:**
        • 전사 - 높은 HP, 근접 전투 특화
        • 마법사 - 높은 MP, 마법 공격 특화
        • 도적 - 높은 민첩, 은신과 기술 특화
        • 궁수 - 원거리 공격, 정확성 특화
        • 성직자 - 치유 마법, 보조 특화

        **특별한 점:**
        • 시작 지점이 캐릭터에 맞게 자동 생성됩니다
        • 배경 스토리가 개인화됩니다
        • 직업에 맞는 초기 장비가 제공됩니다
        • 종족과 직업 조합으로 고유한 플레이 경험
        """
    return help_text