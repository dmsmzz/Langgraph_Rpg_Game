#전투 시스템 모듈
#동적 전투 시뮬레이션이지만 아직 구체적인 배틀노드 구현X
#배틀 시스템 초기 구현 (배틀 상황을 제시 하지만 무조건 승리)

import random
from typing import List, Dict, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from models import BattleResult, GAME_CONSTANTS
from reputation_system import ReputationManager

class BattleSystem:
    #전투 시스템 클래스
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
        self.reputation_manager = ReputationManager()
    
    def simulate_battle(self, state: Dict) -> Dict:
        #전투 시뮬레이션 실행
        main_db = state.get("main_story_db")
        companion_ids = state.get("companion_ids", [])
        current_location = state.get("current_location", "알 수 없는 곳")
        
        # 전투 참가자 확인
        has_companions = companion_ids and len(companion_ids) > 0 and main_db is not None
        
        if has_companions:
            return self._simulate_party_battle(state, main_db, companion_ids)
        else:
            return self._simulate_solo_battle(state)
        
    def _simulate_party_battle(self, state: Dict, main_db, companion_ids: List[int]) -> Dict:
        #파티 전투

        battle_results = []
        total_damage_dealt = 0
        critical_hits = []
        special_actions = []

        # 파티 상태 조회
        party_status = main_db.get_party_status()

        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char

            if not is_alive:
                print(f"{name}은 이미 쓰러진 상태, 전투 불참")
                continue
            
            # 전투 계산
            battle_result = self._calculate_character_battle(char_id, name, char_type, main_db)
            battle_results.append(battle_result)
            
            total_damage_dealt += battle_result['damage_dealt']
            
            if battle_result['critical']:
                critical_hits.append(name)
            
            if battle_result['special_action']:
                special_actions.append(name)
        
        return {
            "battle_results": battle_results,
            "total_damage_dealt": total_damage_dealt,
            "critical_hits": critical_hits,
            "special_actions": special_actions,
            "battle_type": "party"
        }
    
    def _simulate_solo_battle(self, state: Dict) -> Dict:
        #솔로 전투 시뮬레이션
        
        player = state["player"]
        player_name = player.name if hasattr(player, 'name') else player.get('이름', '테스트용사')
                
        # 솔로 전투 계산
        damage_taken = random.randint(10, 30)
        mp_used = random.randint(5, 20)
        damage_dealt = random.randint(30, 60)  # 솔로는 더 높은 데미지
        
        # 크리티컬 히트 확률
        is_critical = random.random() < GAME_CONSTANTS["BATTLE_CRITICAL_CHANCE"]
        if is_critical:
            damage_dealt = int(damage_dealt * 1.5)
        
        # 특수 행동 확률
        special_action_used = random.random() < GAME_CONSTANTS["BATTLE_SPECIAL_CHANCE"]
        if special_action_used:
            damage_dealt += random.randint(15, 25)
        
        battle_result = BattleResult(
            participant_name=player_name,
            damage_taken=damage_taken,
            mp_used=mp_used,
            damage_dealt=damage_dealt,
            hp_after='solo_player',
            mp_after='solo_player',
            alive=True,
            critical=is_critical,
            special_action=special_action_used
        )
        
        return {
            "battle_results": [battle_result],
            "total_damage_dealt": damage_dealt,
            "critical_hits": [player_name] if is_critical else [],
            "special_actions": [player_name] if special_action_used else [],
            "battle_type": "solo"
        }
    
    def _calculate_character_battle(self, char_id: int, name: str, char_type: str, main_db) -> BattleResult:
        #개별 캐릭터 전투 계산

        # 데미지 받기
        damage_taken = random.randint(5, 35)
        new_hp, still_alive = main_db.apply_damage(char_id, damage_taken)
        
        # MP 소모 (직업별 차등)
        if "성직자" in name:
            mp_used = random.randint(8, 20)
        elif "마법사" in name:
            mp_used = random.randint(10, 25)
        else:
            mp_used = random.randint(3, 15)
        
        # MP 차감
        new_hp_after_heal, new_mp = main_db.heal_character(char_id, 0, -mp_used)
        
        # 적에게 입힌 데미지 (직업별 차등)
        if "전사" in name or "테스트용사" in name:
            damage_dealt = random.randint(25, 50)
        elif "성직자" in name:
            damage_dealt = random.randint(15, 30)
        elif "마법사" in name:
            damage_dealt = random.randint(30, 55)
        else:
            damage_dealt = random.randint(20, 40)
        
        # 크리티컬 히트 확률
        is_critical = random.random() < GAME_CONSTANTS["BATTLE_CRITICAL_CHANCE"]
        if is_critical:
            damage_dealt = int(damage_dealt * 1.5)
        
        # 특수 행동 확률
        special_action_used = random.random() < GAME_CONSTANTS["BATTLE_SPECIAL_CHANCE"]
        if special_action_used:
            damage_dealt += random.randint(10, 20)
        
        return BattleResult(
            participant_name=name,
            damage_taken=damage_taken,
            mp_used=mp_used,
            damage_dealt=damage_dealt,
            hp_after=new_hp,
            mp_after=new_mp,
            alive=still_alive,
            critical=is_critical,
            special_action=special_action_used
        )
    
    def create_battle_summary(self, battle_data: Dict) -> List[str]:
        #전투 결과 요약 생성
        battle_results = battle_data["battle_results"]
        battle_summary = []
        
        for result in battle_results:
            summary_line = f"{result['participant_name']}: -{result['damage_taken']}HP, -{result['mp_used']}MP"
            
            if result['critical']:
                summary_line += f", 🔥크리티컬 {result['damage_dealt']} 데미지!"
            else:
                summary_line += f", {result['damage_dealt']} 데미지"
            
            if result['special_action']:
                summary_line += " (특수 기술 사용)"
            
            if not result['alive']:
                summary_line += " ⚠️쓰러짐!"
            
            battle_summary.append(summary_line)
        
        return battle_summary
    
    def generate_dynamic_battle_scene(self, state: Dict, battle_data: Dict) -> str:
        #동적 전투 장면 생성
        current_location = state.get("current_location", "알 수 없는 곳")
        battle_results = battle_data["battle_results"]
        total_damage_dealt = battle_data["total_damage_dealt"]
        critical_hits = battle_data["critical_hits"]
        special_actions = battle_data["special_actions"]
        
        # 참가자 이름 추출
        battle_participants = [result['participant_name'] for result in battle_results]
        
        # 전투 요약
        battle_summary = self.create_battle_summary(battle_data)
        
        # 최근 스토리 컨텍스트
        recent_ai_messages = [msg.content for msg in state["messages"][-3:] 
                             if hasattr(msg, 'content') and hasattr(msg, '__class__') 
                             and 'AIMessage' in str(msg.__class__)]
        story_context = " ".join(recent_ai_messages)
        
        # 명성 정보
        current_reputation = self._get_current_reputation(state)
        reputation_response = self.reputation_manager.get_reputation_response(current_reputation)
        
        sys_prompt = f"""
        현재 위치 "{current_location}"에서 전투가 발생했습니다!
        
        **최근 스토리 컨텍스트**: {story_context}
        
        **플레이어 명성**: {current_reputation} ({reputation_response.level.value})
        - 명성에 따라 적들의 반응이 달라집니다
        - 높은 명성: 적들이 두려워하거나 존경
        - 낮은 명성: 적들이 만만히 보거나 더 공격적
        
        **전투 참가자**: {', '.join(battle_participants)}
        **전투 통계**:
        {chr(10).join(battle_summary)}
        **총 적에게 입힌 데미지**: {total_damage_dealt}
        **크리티컬 히트**: {', '.join(critical_hits) if critical_hits else "없음"}
        **특수 기술 사용자**: {', '.join(special_actions) if special_actions else "없음"}
        
        다음 요소들을 모두 포함하여 완전한 전투 장면을 만들어주세요:
        
        1. **적 정보 생성**:
           - 현재 위치와 스토리 컨텍스트에 어울리는 적
           - 플레이어의 명성에 따른 적의 태도
           - 적의 이름, 외모, 특징, 위험 요소
        
        2. **전투 시작**:
           - 적과의 첫 조우 상황
           - 명성에 따른 적의 초기 반응
        
        3. **구체적인 전투 액션**:
           - 각 참가자의 개별적이고 구체적인 공격 묘사
           - 각 캐릭터의 직업과 성격에 맞는 전투 스타일
        
        4. **적의 반격**:
           - 적의 고유한 공격 기술과 위협적인 반격
           - 참가자들이 입은 피해에 대한 생생한 묘사
        
        5. **특수 순간들**:
           - 크리티컬 히트 순간의 극적 묘사
           - 특수 기술 사용 시의 화려한 액션
        
        6. **승리의 순간**:
           - 어떻게 적을 처치했는지 구체적이고 극적으로
           - 전투 후 참가자들의 상태와 감정
        
        **중요 요구사항**:
        - 현재 위치와 스토리 맥락에 완벽히 어울리는 적 창조
        - 플레이어의 명성에 따른 적의 반응 차별화
        - 실제 전투 통계를 자연스럽게 스토리에 녹여넣기
        - 각 참가자의 개성과 능력을 살린 전투 묘사
        - 300-400자 내외의 몰입감 있는 전투 장면
        
        마지막에 "전투에서 승리했습니다! 어떻게 하시겠어요?"로 마무리하세요.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content="현재 상황에 맞는 적과 전투 장면을 창조적으로 생성해주세요")
            ])
            return response.content
            
        except Exception as e:
            print(f"전투 장면 생성 오류: {e}")
            return self._generate_basic_battle_scene(current_location, battle_participants, battle_summary)
    
    def _generate_basic_battle_scene(self, location: str, participants: List[str], battle_summary: List[str]) -> str:
        #기본 전투 장면 생성 (백업용)
        return f"""
        **{location}에서 치열한 전투!**

        갑작스럽게 나타난 적과 목숨을 건 전투를 벌였습니다!
        {', '.join(participants)}이 혼신의 힘을 다해 싸운 결과:

        **전투 결과**:
        {chr(10).join(battle_summary)}

        피와 땀으로 얼룩진 치열한 혈투 끝에 승리했습니다! 어떻게 하시겠어요?
        """
    
    def _get_current_reputation(self, state: Dict) -> int:
        #현재 명성 조회
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if main_db and player_id:
            player_data = main_db.get_character(player_id)
            if player_data:
                return player_data['reputation']
        
        return 0
    
    def calculate_battle_rewards(self, battle_data: Dict, state: Dict) -> Dict:
        #전투 후 보상 계산
        total_damage = battle_data["total_damage_dealt"]
        critical_hits = len(battle_data["critical_hits"])
        special_actions = len(battle_data["special_actions"])
        
        # 기본 보상
        base_exp = 20 + (total_damage // 10)
        base_gold = 10 + (total_damage // 20)
        
        # 보너스 계산
        critical_bonus = critical_hits * 5
        special_bonus = special_actions * 3
        
        # 명성 보너스
        reputation = self._get_current_reputation(state)
        reputation_multiplier = 1.0
        if reputation >= 60:
            reputation_multiplier = 1.5
        elif reputation >= 20:
            reputation_multiplier = 1.2
        elif reputation <= -40:
            reputation_multiplier = 0.8
        
        final_exp = int((base_exp + critical_bonus + special_bonus) * reputation_multiplier)
        final_gold = int((base_gold + critical_bonus + special_bonus) * reputation_multiplier)
        
        return {
            "experience": final_exp,
            "gold": final_gold,
            "reputation_change": 2 if total_damage > 100 else 1,
            "reputation_reason": "전투 승리"
        }
    
    def apply_battle_consequences(self, state: Dict, battle_data: Dict) -> Dict:
        #전투 결과 적용
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if not main_db or not player_id:
            return state
        
        # 보상 계산
        rewards = self.calculate_battle_rewards(battle_data, state)
        
        # 골드 업데이트
        current_gold = state.get("player_gold", 0)
        new_gold = current_gold + rewards["gold"]
        state["player_gold"] = new_gold
        
        # 명성 업데이트
        main_db.update_reputation(
            player_id, 
            rewards["reputation_change"], 
            rewards["reputation_reason"],
            state.get("current_location", "전투지역")
        )
        
        # 전투 이벤트 기록
        main_db.add_story_event(
            player_id,
            "battle_victory",
            f"전투 승리 - 총 데미지: {battle_data['total_damage_dealt']}",
            state.get("current_location", "전투지역"),
            len(state.get("messages", [])),
            rewards["reputation_change"],
            rewards["gold"]
        )
        
        return state