#Langgraph 게임 노드 구현 모듈
#각 게임 상황에 대한 처리 노드들 정의

import json
import random
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from models import PlayerInitState, Player
from story_manager import StoryManager
from reputation_system import ReputationManager
from battle_system import BattleSystem
from inventory_system import InventorySystem, ShopSystem, ItemRewardSystem
from database import MainStoryDB
from character_creation import CharacterCreator, show_character_creation_help

class GameNodes:
    #게임 노드들 집합

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self.story_manager = StoryManager()
        self.reputation_manager = ReputationManager()
        self.battle_system = BattleSystem()
        self.inventory_system = InventorySystem()
        self.shop_system = ShopSystem()
        self.item_reward_system = ItemRewardSystem()
        self.character_creator = CharacterCreator()

    def user_input_node(self, state: PlayerInitState) -> PlayerInitState:
        #사용자 입력 대기
        result = {
            **state,
            "next_action": "analyze_intent"
        }
        return result
    
    def character_creation_node(self, state: PlayerInitState) -> PlayerInitState:
        #캐릭터 생성 노드

        if state.get("player") and hasattr(state['player'], 'name'):
            return {
                **state,
                "next_action": "main_story_start"
            }
        
        user_input = ""
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                user_input = message.content
                break
        
        #도움말 요청 처리
        if user_input.lower() in ['help', '도움말', '도움']:
            help_text = show_character_creation_help()
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content=help_text)],
                "next_action": "character_creation"
            }
        
        # 사용자 입력이 없으면 캐릭터 생성 안내 문구 출력
        if not user_input:
            creation_msg="""
캐릭터 생성

새로운 모험을 시작하기 위해 캐릭터를 생성해주세요!!!

입력 예시:
"내 이름은 아리아이고 종족은 인간, 직업은 마법사, 나이는 35살이야"
"나는 인간 전사 토르고 25살이다"

종족 : 인간, 엘프, 드워프, 오크, 하플링
직업 : 전사, 마법사, 도적, 궁수, 성직자

주의사항:
1. 시작 지점이 캐릭터에 맞게 자동 생성됩니다.
2. 배경 스토리는 개인화됩니다.
3. 직업에 맞는 초기 장비가 제공됩니다.

'help' 또는 '도움말'을 입력하면 자세하 가이드를 볼 수 있습니다.
"""

            return {
                **state,
                "messages": state["messages"]+[AIMessage(content = creation_msg)],
                "next_action": "character_creation"
            }
        

        #캐릭터 정보 파싱
        character_data = self.character_creator.parse_character_input(user_input)

        if not character_data:
            error_msg = """
캐릭터 정보가 부족합니다!!!

필요한 정보를 모두 포함해서 다시 입력해주세요:
- 이름
- 종족 (인간, 엘프, 드워프, 오크, 하플링)
- 직업 (전사, 마법사, 도적, 궁수, 성직자)
- 나이

예시: "내 이름은 린이고 종족은 엘프, 직업은 마법사, 나이는 25살이야"
            """

            return {
                **state,
                "messages": state["messages"] + [AIMessage(content=error_msg)],
                "next_action": "character_creation"
            }
        
        try:
            # 시작 지점 생성
            starting_location = self.character_creator.generate_starting_location(character_data)
            
            # 배경 스토리 생성
            backstory = self.character_creator.generate_character_backstory(character_data, starting_location)
            
            # 능력치 계산
            stats = self.character_creator.calculate_starting_stats(character_data)
            
            # 초기 아이템 생성
            items = self.character_creator.generate_starting_items(character_data)
            
            # 플레이어 객체 생성
            player = self.character_creator.create_player_object(
                character_data, starting_location, backstory, stats, items
            )

            #캐릭터 생성 완료 메시지
            creation_complete_msg = f"""
캐릭터 생성 완료!!!'

**기본 정보:**
• 이름: {player.name}
• 종족: {player.race}
• 직업: {player.class_type}
• 나이: {character_data['나이']}세

**능력치:**
• 힘: {stats['힘']}
• 민첩: {stats['민첩']}
• 지력: {stats['지력']}
• HP: {stats['hp']}
• MP: {stats['mp']}

**초기 장비:**
{chr(10).join([f"• {item['name']} - {item['description']}" for item in items[:3]])}

**시작 지점:** {starting_location}

**배경 스토리:**
{backstory}

**시작 골드:** {player.gold}골드
**시작 명성:** {player.reputation}

**게임이 곧 시작됩니다!**
            """

            return {
                **state,
                "messages": state["messages"] + [AIMessage(content=creation_complete_msg)],
                "player": player,
                "starting_location": starting_location,
                "backstory": backstory,
                "character_stats": stats,
                "starting_items": items,
                "next_action": "main_story_start"
            }
        
        except Exception as e:
            print(f"캐릭터 생성 노드에서 오류 {e}")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="캐릭터 생성 중 오류가 발생했습니다. 다시 시도해주세요.")],
                "next_action": "character_creation"
            }
        
    def main_story_start_node(self, state: PlayerInitState) -> PlayerInitState:
        #메인스토리 시작

        player = state ["player"]
        main_db = MainStoryDB()

        #캐릭터 생성 노드에서 받은 정보 활용
        starting_location = state.get("starting_location", "모험가의 마을")
        backstory = state.get("backstory", f"{player.name}의 모험이 시작됩니다.")
        character_stats = state.get("character_stats", {})
        starting_items = state.get("starting_items", [])

        #플레이어 정보를 DB에 등록
        player_data = {
            'name': player.name,
            'type': 'player',
            'race': player.race,
            'class': player.class_type,
            'level': player.level,
            'hp': player.hp,
            'max_hp': player.hp,
            'mp': player.mp,
            'max_mp': player.mp,
            'strength': character_stats.get('힘', 10),
            'agility': character_stats.get('민첩', 10),
            'intelligence': character_stats.get('지력', 10),
            'current_location': starting_location,
            'is_alive': True,
            'is_in_party': True,
            'relationship_level': 0,
            'reputation': player.reputation,
            'gold': player.gold,
            'backstory': backstory
        }
        
        player_id = main_db.create_character(player_data)

        # 초기 아이템 보급
        for item in starting_items:
            main_db.add_item(
                player_id,
                item['name'],
                item['type'],
                item.get('quantity', 1),
                item['description'],
                item.get('value', 0)
            )

        # 게임 시작 스토리 생성
        creation_story = self.character_creator.generate_creation_story(
            player, starting_location, backstory, character_stats, starting_items
        )
        
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=creation_story)],
            "main_story_db": main_db,
            "main_story_player_id": player_id,
            "companion_ids": [],
            "current_location": starting_location,
            "current_objective": "새로운 모험 시작",
            "player_gold": player.gold,
            "reputation_changes": [],
            "next_action": "wait_input"
        }
    
    def intent_analysis_node(self, state: PlayerInitState) -> PlayerInitState:
        #플레이어 응답 의도 분석

        #마지막 사용자 메시지
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        user_message = user_messages[-1].content if user_messages else ""

        #스토리 컨텍스트 생성
        story_context = self.story_manager.create_story_context(state)
        companion_count = len(state.get("companion_ids", []))

        #현재 명성 조회
        current_reputation = self._get_current_reputation(state)
        reputation_status = self.reputation_manager.get_reputation_status_message(current_reputation)

        first_ai_message = None
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                first_ai_message = msg.content
                break

        actual_goal = self.story_manager.extract_main_objective(first_ai_message)

        sys_prompt = f"""
            당신은 RPG 게임의 상황 분석 AI입니다.
            명성 시스템이 적용된 게임에서 사용자 입력을 분석하세요.
        
            === 현재 스토리 컨텍스트 ===
            플레이어: {story_context.get('player_info', '')}
            파티: {story_context.get('party_members', [])}
            현재 위치: {story_context.get('current_location', '미확인')}
            주요 목표: {actual_goal}
            현재 명성: {reputation_status}
        
            사용자 입력: "{user_message}"
        
            다음 중 하나를 JSON으로 답하세요:
            {{
                "next_action": "battle|companion_opportunity|story_continue|inventory|item_reward|shop_purchase|reputation_check",
                "reason": "판단 이유",
                "story_response": "이전 상황과 자연스럽게 이어지는 스토리 (200자 내외)",
                "location_update": "새로운 위치명 (이동 시에만)",
                "reputation_impact": "명성에 미치는 영향 (positive/negative/neutral)",
                "important_event": "중요한 사건 (있을 경우에만)"
            }}
        
            **판단 기준 (우선순위 순):**
            1. **shop_purchase**: 상점에서 구매 관련 ("~을 구입", "~을 산다", "구매")
            2. **reputation_check**: 명성 관련 질문 ("명성", "평판", "reputation")
            3. **companion_list**: 동료 목록 확인 ("동료 목록", "파티 확인", "동료 상태", "파티원")
            4. **companion_dismiss**: 동료 탈퇴 관련 ("동료 탈퇴", "동료 내보내기", "파티에서 제외", "동료 해고")
            5. **inventory**: 직접적인 인벤토리 명령 ("인벤토리", "가방", "아이템 사용")
            6. **battle**: 전투 관련 ("싸운다", "공격", "위험한 곳")
            7. **companion_opportunity**: 동료 영입 ("누군가 만나고 싶어", "동료 찾기", "새로운 동료") (현재 {companion_count}/2명)
            8. **story_continue**: 위치 이동, 탐험, 대화 등 일반 게임 진행
            9. **item_reward**: 전투/탐험 완료 후 보상 상황
        
            명성 시스템 고려사항:
            - 선한 행동 → positive 영향
            - 악한 행동 → negative 영향
            - 중립적 행동 → neutral 영향
            """
    
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"명성 시스템을 고려한 분석: {user_message}")
            ])
            
            analysis = json.loads(response.content)
            #명성 변화 처리
            reputation_change = 0
            reputation_reason = ""

            if analysis.get("reputation_impact") == "positive":
                reputation_change = 2
                reputation_reason = "선한 행동"
            elif analysis.get("reputation_impact") == "negative":
                reputation_change = -2
                reputation_reason = "의심스러운 행동"

            # 컨텍스트 업데이트
            updated_state = self.story_manager.update_story_context(
                state,
                new_location=analysis.get("location_update"),
                important_event=analysis.get("important_event"),
                reputation_change=reputation_change,
                reputation_reason=reputation_reason
            )

            result_state = {
                **updated_state,
                "messages": updated_state["messages"] + [AIMessage(content=analysis["story_response"])],
                "next_action": analysis["next_action"],
                "current_situation": f"다음 액션: {analysis['next_action']} - {analysis['reason']}"
            }
                
            return result_state

        except Exception as e:
            print(f"의도 분석에서 오류 발생 {e}")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="상황을 파악하고 있습니다...")],
                "next_action": "story_continue"
            }
        

    def story_continue_node(self, state: PlayerInitState) -> PlayerInitState:
        #일반적인 스토리 진행

        # 스토리 컨텍스트 가져오기
        story_context = self.story_manager.create_story_context(state)
        current_location = state.get("current_location", "알 수 없는 곳")

        # 최근 사용자 입력
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        last_user_input = user_messages[-1].content if user_messages else ""
        
        # 현재 명성 조회
        current_reputation = self._get_current_reputation(state)
        reputation_response = self.reputation_manager.get_reputation_response(
            current_reputation, "주민들", current_location
        )
        
        # 파티원 정보
        party_members = story_context.get('party_members', [])
        party_info = f"파티원: {party_members}" if party_members != ["혼자 모험 중"] else "혼자 모험 중"

        # 주요 목표 추출
        first_ai_message = None
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                first_ai_message = msg.content
                break

        main_objectives = self.story_manager.extract_main_objectives(first_ai_message)
        objective_info = f"주요 목표: {', '.join(main_objectives)}"

        sys_prompt = f"""
        명성 시스템이 적용된 RPG에서 사용자의 행동에 맞춰 스토리를 진행해주세요.
        
        === 현재 스토리 컨텍스트 ===
        플레이어: {story_context.get('player_info', '')}
        현재 위치: {current_location}
        {objective_info}
        {party_info}
        
        === 명성 정보 ===
        현재 명성: {current_reputation}
        명성 레벨: {reputation_response.level.value}
        주민들의 태도: {reputation_response.tone}
        협조 의지: {reputation_response.willingness_to_help * 100:.0f}%
        
        사용자의 최근 행동: "{last_user_input}"
        
        **핵심 원칙:**
        1. **명성에 따른 NPC 반응** - 명성이 높을수록 호의적, 낮을수록 적대적
        2. **실질적인 진전** - 사용자 행동에 대한 구체적이고 의미 있는 결과
        3. **정보는 충분히** - 묻는 것에 대해 유용한 정보를 제공
        4. **다음 단계 명확히** - 구체적인 선택지나 행동 방향 제시
        
        **명성별 NPC 반응 가이드:**
        - 영웅급(80+): 극도로 존경, 무료 도움, 특별 정보 제공
        - 매우 호의(60-79): 매우 친근, 할인 혜택, 추가 정보
        - 호의(20-59): 친근, 기본 협조
        - 평범(0-19): 중립적, 기본 서비스
        - 비호의(-1~-20): 경계, 정보 제한
        - 적대(-21~-40): 불쾌함, 높은 가격, 무례
        - 매우 적대(-41~-60): 두려움, 서비스 거부
        - 원수(-61 이하): 공격적, 도망 또는 싸움
        
        250-300자 내외로 작성하고 "어떻게 하시겠어요?"로 마무리하세요.
        """

        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"명성 기반 스토리 진행: {last_user_input}")
            ])

            result = {
                **state,
                "messages": state["messages"] + [AIMessage(content=response.content)],
                "next_action": "wait_input"
            }

            return result
        
        except Exception as e:
            print(f"스토리 진행+명성 영향 처리 오류")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="모험이 계속됩니다. 어떻게 하시겠어요?")],
                "next_action": "wait_input"
            }
        
    def battle_node(self, state: PlayerInitState) -> PlayerInitState:
        #전투 상황 처리

        # 전투 시뮬레이션
        battle_data = self.battle_system.simulate_battle(state)
        
        # 전투 장면 생성
        battle_scene = self.battle_system.generate_dynamic_battle_scene(state, battle_data)
        
        # 전투 통계 생성
        battle_summary = self.battle_system.create_battle_summary(battle_data)
        
        # 전투 결과 메시지
        battle_report = f"""
⚔️ **전투 발생!**

{battle_scene}

**📊 전투 통계**:
{chr(10).join(battle_summary)}
"""
        
        # 전투 결과 적용
        updated_state = self.battle_system.apply_battle_consequences(state, battle_data)
        
        # 전투 데이터를 상태에 저장 (아이템 보상용)
        updated_state["battle_data"] = battle_data
        
        result = {
            **updated_state,
            "messages": updated_state["messages"] + [AIMessage(content=battle_report)],
            "next_action": "item_reward"
        }
        return result
    
    def inventory_node(self, state: PlayerInitState) -> PlayerInitState:
        #인벤토리 노드

        inventory_display = self.inventory_system.get_inventory_display(state)

        result = {
            **state,
            "messages": state["messages"] + [AIMessage(content=inventory_display)],
            "next_action": "inventory_action"
        }
        
        return result
    
    def inventory_action_node(self, state: PlayerInitState) -> PlayerInitState:
        #인벤토리 및 힐, 물약 입력 처리

        # 사용자 입력 분석
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        user_input = user_messages[-1].content if user_messages else ""
        user_input_lower = user_input.lower()

        # 키워드 기반 분석
        if any(keyword in user_input_lower for keyword in ['닫기', '나가기', '종료', '밖으로', '마을', '광장']):
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="인벤토리를 닫았습니다. 어떻게 하시겠어요?")],
                "next_action": "wait_input"
            }
        elif any(keyword in user_input_lower for keyword in ['물약', '포션', '회복', 'hp', 'mp']):
            return {
                **state,
                "next_action": "use_potion"
            }
        elif any(keyword in user_input_lower for keyword in ['힐', '치유', '성직자', 'heal']):
            return {
                **state,
                "next_action": "use_heal"
            }
        else:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="인벤토리를 닫고 액션을 실행합니다.")],
                "next_action": "wait_input"
            }
        
    def use_potion_node(self, state: PlayerInitState) -> PlayerInitState:
        #물약 사용 처리

        result_msg = self.inventory_system.use_potion(state)

        result = {
            **state,
            "messages": state["messages"] + [AIMessage(content=result_msg + "\n\n다른 작업을 하시겠습니까?")],
            "next_action": "inventory_action"
        }

        return result
    
    def use_heal_node(self, state: PlayerInitState) -> PlayerInitState:
        #힐 사용 처리
        
        result_msg = self.inventory_system.use_heal_spell(state)

        result = {
            **state,
            "messages": state["messages"] + [AIMessage(content=result_msg + "\n\n다른 작업을 하시겠습니까?")],
            "next_action": "inventory_action"
        }

        return result
    
    def shop_purchase_node(self, state: PlayerInitState) -> PlayerInitState:
        #상점에서 구매 처리

        # 사용자 입력 분석
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        user_input = user_messages[-1].content if user_messages else ""

        #간단한 아이템 매칭
        item_mapping = {
            "물약": "치유 물약",
            "치유": "치유 물약",
            "체력": "치유 물약",
            "마나": "마나 물약",
            "mp": "마나 물약",
            "방패": "강화된 방패",
            "결정": "어둠의 결정",
            "어둠": "어둠의 결정"
        }

        item_to_buy = None
        for keyword, item_name in item_mapping.items():
            if keyword in user_input.lower():
                item_to_buy = item_name
                break
        
        if item_to_buy:
            result_msg = self.shop_system.process_purchase(state, item_to_buy)
        else:
            result_msg = "구매할 아이템을 명확히 말씀해 주세요. (예: '물약 구입', '방패 구입')"
        
        result = {
            **state,
            "messages": state["messages"] + [AIMessage(content=result_msg)],
            "next_action": "wait_input"
        }
        
        return result
    
    def item_reward_node(self, state = PlayerInitState) -> PlayerInitState:
        #아이템 보상 처리


        # 전투 데이터가 있는지 확인
        battle_data = state.get("battle_data", {})
        
        if battle_data:
            reward_msg = self.item_reward_system.generate_battle_rewards(state, battle_data)
        else:
            reward_msg = self.item_reward_system.generate_exploration_rewards(state)
        
        result = {
            **state,
            "messages": state["messages"] + [AIMessage(content=reward_msg)],
            "next_action": "wait_input"
        }

        return result
    
    def companion_opportunity_node(self, state: PlayerInitState) -> PlayerInitState:
        #동료 영입 기회 생성 노드

        companion_count = len(state.get("companion_ids", []))
        current_location = state.get("current_location", "마을")
        current_reputation = self._get_current_reputation(state)

        #동료 영입은 최대 2명, 초과하면 자동 거절 처리
        if companion_count >= 2:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="파티가 이미 가득 찬 상태입니다.")],
                "next_action": "wait_input"
            }
        
        # 명성에 따른 NPC 생성
        reputation_response = self.reputation_manager.get_reputation_response(current_reputation)
        
        # 최근 대화 컨텍스트
        recent_messages = [msg.content for msg in state["messages"][-5:] if isinstance(msg, AIMessage)]
        conversation_context = " ".join(recent_messages)
        
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        last_user_input = user_messages[-1].content if user_messages else ""
        
        sys_prompt = f"""
        현재 위치 "{current_location}"에서 동료 영입 상황을 생성해주세요.
        
        **플레이어 명성 정보:**
        - 현재 명성: {current_reputation}
        - 명성 레벨: {reputation_response.level.value}
        - NPC들의 태도: {reputation_response.tone}
        - 협조 의지: {reputation_response.willingness_to_help * 100:.0f}%
        
        **현재 파티:** {companion_count + 1}명/3명
        
        **최근 대화 컨텍스트:** {conversation_context}
        **사용자 발언:** "{last_user_input}"
        
        **명성에 따른 NPC 반응:**
        - 높은 명성(60+): 영광스럽게 생각하며 먼저 동료 신청
        - 보통 명성(0-59): 조심스럽게 제안하거나 조건부 동의
        - 낮은 명성(-1~-40): 의심스러워하며 거절하거나 높은 조건 요구
        - 매우 낮은 명성(-41 이하): 무서워하며 도망치거나 적대적
        
        **진행 방식:**
        1. 기존 NPC와 대화 중이라면 그 NPC 활용
        2. 명성에 맞는 NPC 태도 반영
        3. 자연스러운 동료 영입 제안
        
        200자 내외로 작성하고 "이 사람을 동료로 영입하시겠습니까?"로 마무리하세요.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"명성 {current_reputation}에 맞는 동료 영입 기회 생성")
            ])
            
            result = {
                **state,
                "messages": state["messages"] + [AIMessage(content=response.content)],
                "next_action": "companion_decision"
            }
            return result
            
        except Exception as e:
            print(f"동료 기회 생성 오류: {e}")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="새로운 사람을 만났습니다. 동료로 영입하시겠습니까?")],
                "next_action": "companion_decision"
            }
    
    def companion_decision_node(self, state: PlayerInitState) -> PlayerInitState:

        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        user_response = user_messages[-1].content if user_messages else ""

        # 간단한 답변 기반 분석
        positive_keywords = ['예', '네', '좋아', '승낙', '동의', '영입', '받아들', '함께']
        negative_keywords = ['아니', '싫어', '거절', '안 해', '필요없', '거부']
        
        user_lower = user_response.lower()

        if any(keyword in user_lower for keyword in positive_keywords):
            decision = "accept"
        elif any(keyword in user_lower for keyword in negative_keywords):
            decision = "reject"
        else:
            # 키워드 분석 실패 후, LLM 분석 시도
            try:
                analysis_response = self.llm.invoke([
                    SystemMessage(content=f"""
                    사용자 응답을 분석해서 동료 영입 의사를 판단하세요.
                    
                    사용자 응답: "{user_response}"
                    
                    JSON으로 답하세요:
                    {{"decision": "accept|reject"}}
                    """),
                    HumanMessage(content="결정 분석")
                ])
                
                decision_data = json.loads(analysis_response.content)
                decision = decision_data.get("decision", "reject")
                
            except Exception as e:
                print(f"결정 분석 오류: {e}")
                decision = "reject"
        
        result = {
            **state,
            "next_action": "companion_accept" if decision == "accept" else "companion_reject"
        }
        
        return result
    
    def companion_accept_node(self, state: PlayerInitState) -> PlayerInitState:
        #동료 영입 LLM 이용하여 생성
    
        main_db = state.get("main_story_db")
        companion_ids = state.get("companion_ids", [])
        current_location = state.get("current_location", "마을")
        current_reputation = self._get_current_reputation(state)

        #동료 최대 인원 자동 거절 처리
        if not main_db or len(companion_ids) >= 2:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="동료 영입에 실패했습니다.")],
                "next_action": "wait_input"
            }

        # 명성에 따른 기본 설정
        reputation_response = self.reputation_manager.get_reputation_response(current_reputation)

        # 최근 대화 컨텍스트에서 상황 파악(갑자기 상황에 맞지 않은 동료 생성 방지)
        recent_messages = [msg.content for msg in state["messages"][-5:] if isinstance(msg, AIMessage)]
        conversation_context = " ".join(recent_messages)

        # 플레이어 정보
        player = state.get("player")
        player_info = f"{player.name} ({player.race} {player.class_type})" if player else "모험가"

        # 명성에 따른 동료 타입 결정
        if current_reputation <= -20:
            companion_type = "악당/범죄자"
            moral_alignment = "악"
        elif current_reputation <= 0:
            companion_type = "회색지대 인물"
            moral_alignment = "중립"
        elif current_reputation <= 40:
            companion_type = "평범한 모험가"
            moral_alignment = "선량"
        else:
            companion_type = "정의로운 영웅"
            moral_alignment = "매우 선량"

        # LLM으로 동료 생성
        companion_prompt = f"""
        현재 상황에 맞는 동료 캐릭터를 생성해주세요.

        **현재 상황:**
        - 위치: {current_location}
        - 플레이어: {player_info}
        - 플레이어 명성: {current_reputation} ({reputation_response.level.value})
        - 최근 상황: {conversation_context}

        **명성에 따른 동료 타입:**
        - 매우 높은 명성(80+): 전설적인 정의의 영웅, 성기사, 현자 등
        - 높은 명성(40-79): 명예로운 기사, 정의로운 모험가
        - 보통 명성(1-39): 평범한 모험가, 선량한 시민
        - 낮은 명성(0 to -19): 회색지대 인물, 용병, 떠돌이
        - 악한 명성(-20 to -39): 도적, 암살자, 마법사(흑마법), 배신자
        - 매우 악한 명성(-40 이하): 살인자, 사이코패스, 악마술사, 타락한 기사

        **현재 동료 타입: {companion_type} (도덕성: {moral_alignment})**

        **위치별 특성:**
        - 마을/도시: 상인, 경비병, 도적, 암살자
        - 숲/자연: 사냥꾼, 드루이드, 산적, 밀렵꾼
        - 던전/유적: 탐험가, 도적, 보물사냥꾼, 고고학자
        - 술집/뒷골목: 용병, 암살자, 정보상, 사기꾼

        **능력치 가이드 (모든 명성에서 비슷한 수준 유지):**
        - 레벨: 1-3 (플레이어와 비슷한 수준)
        - HP: 80-120
        - MP: 20-60 (직업에 따라)
        - 능력치: 8-15 범위

        JSON 형식으로 답하세요:
        {{
            "name": "동료 이름",
            "race": "종족",
            "class": "직업 (악한 명성이면 도적/암살자/흑마법사 등)",
            "level": 레벨숫자,
            "hp": HP숫자,
            "max_hp": 최대HP숫자,
            "mp": MP숫자,
            "max_mp": 최대MP숫자,
            "strength": 힘수치,
            "agility": 민첩수치,
            "intelligence": 지력수치,
            "backstory": "배경 스토리 (명성에 맞는 어두운/밝은 과거)",
            "personality": "성격 (명성에 맞는 성향)",
            "special_ability": "특수 능력",
            "appearance": "외모 묘사",
            "reason_for_joining": "합류 이유 (명성 반영)",
            "moral_alignment": "{moral_alignment}",
            "dark_secret": "숨겨진 비밀이나 과거 (악한 동료인 경우)",
            "loyalty_risk": "배신 가능성 (높음/보통/낮음)"
        }}

        **중요:** 명성 {current_reputation}에 맞는 도덕성을 가진 동료를 만들어주세요!
        """

        try:
            response = self.llm.invoke([
                SystemMessage(content=companion_prompt),
                HumanMessage(content=f"명성 {current_reputation}에 맞는 {companion_type} 동료 생성")
            ])

            companion_data = json.loads(response.content)
        
            # DB에 저장 (능력치 균등화)
            companion_id = main_db.create_character({
                'name': companion_data.get('name', '신비한 동료'),
                'type': 'companion',
                'race': companion_data.get('race', '인간'),
                'class': companion_data.get('class', '전사'),
                'level': companion_data.get('level', 2),
                'hp': companion_data.get('hp', 100),
                'max_hp': companion_data.get('max_hp', 100),
                'mp': companion_data.get('mp', 30),
                'max_mp': companion_data.get('max_mp', 30),
                'strength': companion_data.get('strength', 10),
                'agility': companion_data.get('agility', 10),
                'intelligence': companion_data.get('intelligence', 10),
                'current_location': current_location,
                'is_alive': True,
                'is_in_party': True,
                'relationship_level': 0,
                'backstory': companion_data.get('backstory', '신비한 과거를 가진 동료')
            })

            companion_ids.append(companion_id)
            party_full = len(companion_ids) >= 2

            # 명성 변화 (악한 동료 영입 시 명성 하락 가능)
            if current_reputation <= -20:
                reputation_change = -2  # 악당 영입 시 명성 하락
                reputation_reason = "악한 동료 영입"
            elif current_reputation <= 0:
                reputation_change = 0  # 중립적
                reputation_reason = "회색지대 인물 영입"
            else:
                reputation_change = 3  # 선량한 동료 영입
                reputation_reason = "선량한 동료 영입"
            
            if reputation_change != 0:
                main_db.update_reputation(
                    state.get("main_story_player_id"),
                    reputation_change,
                    reputation_reason,
                    current_location
                )

            # 동적 환영 메시지 생성
            welcome_msg = f"""
            **{companion_data.get('name', '동료')}가 파티에 합류했습니다!** ✨

            **기본 정보:**
            • 이름: {companion_data.get('name', '동료')} ({companion_data.get('race', '인간')} {companion_data.get('class', '전사')})
            • 레벨: {companion_data.get('level', 2)}
            • 도덕성: {companion_data.get('moral_alignment', '중립')}
            • 영입 위치: {current_location}

            **외모:**
            {companion_data.get('appearance', '평범한 외모의 동료입니다.')}

            **능력치:**
            • HP: {companion_data.get('hp', 100)} | MP: {companion_data.get('mp', 30)}
            • 힘: {companion_data.get('strength', 10)} | 민첩: {companion_data.get('agility', 10)} | 지능: {companion_data.get('intelligence', 10)}

            **배경:**
            {companion_data.get('backstory', '신비한 과거를 가진 동료입니다.')}

            **성격:**
            {companion_data.get('personality', '복잡한 성격의 소유자입니다.')}

            **특수 능력:**
            {companion_data.get('special_ability', '특별한 능력을 지니고 있습니다.')}

            **합류 이유:**
            "{companion_data.get('reason_for_joining', '함께 모험하고 싶어서 합류했습니다.')}"
            """

            # 악한 동료의 경우 추가 정보
            if current_reputation <= -20:
                welcome_msg += f"""
                **위험 요소:**
                • 숨겨진 비밀: {companion_data.get('dark_secret', '알 수 없는 어두운 과거가 있습니다.')}
                • 배신 위험도: {companion_data.get('loyalty_risk', '보통')}
                • 악한 동료는 상황에 따라 배신할 가능성이 있습니다!
                """

            welcome_msg += f"""
            **현재 파티:** {len(companion_ids) + 1}명/3명 {"(파티 완성!)" if party_full else ""}
            """

            if reputation_change != 0:
                change_sign = "+" if reputation_change > 0 else ""
                welcome_msg += f"⭐ **명성 {change_sign}{reputation_change}** ({reputation_reason})\n"

            welcome_msg += """
            **동료 관리 명령어:**
            • '동료 목록' - 현재 동료들 확인
            • '동료 탈퇴' - 동료를 파티에서 내보내기

            어떻게 하시겠어요?
            """

            result = {
                **state,
                "messages": state["messages"] + [AIMessage(content=welcome_msg)],
                "companion_ids": companion_ids,
                "party_full": party_full,
                "next_action": "wait_input"
            }

            return result

        except json.JSONDecodeError as e:
            print(f"동료 생성 JSON 파싱 오류: {e}")
            return self._create_fallback_companion(state, main_db, companion_ids, current_location, current_reputation)
        except Exception as e:
            print(f"동료 생성 오류: {e}")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="동료 영입에 실패했습니다.")],
                "next_action": "wait_input"
            }
    def companion_dismiss_node(self, state: PlayerInitState) -> PlayerInitState:
        #동료 탈퇴 처리
     
        main_db = state.get("main_story_db")
        companion_ids = state.get("companion_ids", [])
    
        if not main_db or not companion_ids:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="탈퇴시킬 동료가 없습니다.")],
                "next_action": "wait_input"
            }
    
        # 현재 동료 목록 표시
        party_status = main_db.get_party_status()
        companions = []
    
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            if char_type == 'companion':
                companions.append({
                    "id": char_id,
                    "name": name,
                    "hp": hp,
                    "max_hp": max_hp,
                    "mp": mp,
                    "max_mp": max_mp,
                    "is_alive": is_alive
                })
    
        if not companions:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="동료가 없습니다.")],
                "next_action": "wait_input"
            }
    
        dismiss_msg = """
        **동료 탈퇴 관리**

        현재 파티 동료들:
        """
    
        for i, comp in enumerate(companions, 1):
            status = "생존" if comp["is_alive"] else "위험"
            dismiss_msg += f"{i}. {comp['name']} (HP: {comp['hp']}/{comp['max_hp']}, 상태: {status})\n"
    
        dismiss_msg += """
        탈퇴시킬 동료의 번호를 말하거나 '취소'라고 하세요.
        예: "1번 동료 탈퇴" 또는 "취소"
        """
    
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=dismiss_msg)],
            "next_action": "companion_dismiss_decision",
            "available_companions": companions
        }

    def companion_dismiss_decision_node(self, state: PlayerInitState) -> PlayerInitState:
        #동료 탈퇴 처리
        
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        user_input = user_messages[-1].content if user_messages else ""
    
        # 취소 확인
        if any(keyword in user_input.lower() for keyword in ['취소', '그만', '안해', '돌아가']):
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="동료 탈퇴를 취소했습니다. 어떻게 하시겠어요?")],
                "next_action": "wait_input"
            }
    
        # 번호 추출
        import re
        numbers = re.findall(r'\d+', user_input)
    
        if not numbers:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="올바른 번호를 입력해주세요. (예: '1번' 또는 '취소')")],
                "next_action": "companion_dismiss_decision"
            }
    
        try:
            companion_index = int(numbers[0]) - 1
            available_companions = state.get("available_companions", [])
        
            if 0 <= companion_index < len(available_companions):
                companion_to_dismiss = available_companions[companion_index]
                return self._execute_companion_dismiss(state, companion_to_dismiss)
            else:
                return {
                    **state,
                    "messages": state["messages"] + [AIMessage(content=f"1-{len(available_companions)} 범위의 번호를 입력해주세요.")],
                    "next_action": "companion_dismiss_decision"
                }
        except ValueError:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="올바른 숫자를 입력해주세요.")],
                "next_action": "companion_dismiss_decision"
            }
    def _execute_companion_dismiss(self, state: PlayerInitState, companion_info: Dict) -> PlayerInitState:
        #동료 탈퇴 처리 실행
        main_db = state.get("main_story_db")
        companion_ids = state.get("companion_ids", [])
        current_location = state.get("current_location", "알 수 없는 곳")
    
        companion_id = companion_info["id"]
        companion_name = companion_info["name"]
    
        try:
            # DB에서 동료를 파티에서 제거 (삭제하지 않고 is_in_party만 False로)
            cursor = main_db.conn.cursor()
            cursor.execute('''
                UPDATE main_story_characters 
                SET is_in_party = FALSE, current_location = ? 
                WHERE id = ?
            ''', (f"{current_location} 근처", companion_id))
            main_db.conn.commit()
        
            # 상태에서 동료 ID 제거
            if companion_id in companion_ids:
                companion_ids.remove(companion_id)
        
            # 명성에 따른 이별 메시지 생성
            current_reputation = self._get_current_reputation(state)
        
            if current_reputation <= -20:
                farewell_style = "차갑고 위협적인"
                farewell_msg = f"'{companion_name}'이 냉소적인 웃음을 지으며 떠났습니다. '언젠가 다시 만날 날이 있을 것이다...'"
            elif current_reputation <= 0:
                farewell_style = "담담한"
                farewell_msg = f"'{companion_name}'이 어깨를 으쓱하며 떠났습니다. '그럴 줄 알았어. 각자 길을 가자.'"
            else:
                farewell_style = "아쉬워하는"
                farewell_msg = f"'{companion_name}'이 아쉬운 표정으로 떠났습니다. '함께한 시간이 즐거웠습니다. 행운을 빕니다!'"
        
            dismiss_result = f"""
            **동료 탈퇴 완료**

            {farewell_msg}

            **파티 현황:**
            • 현재 파티: {len(companion_ids) + 1}명/3명
            • 새로운 동료 영입 가능: {'❌' if len(companion_ids) >= 2 else '✅'}

            탈퇴한 동료는 {current_location} 근처에서 각자의 길을 가게 됩니다.

            어떻게 하시겠어요?
            """
        
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content=dismiss_result)],
                "companion_ids": companion_ids,
                "party_full": len(companion_ids) >= 2,
                "next_action": "wait_input"
            }
        
        except Exception as e:
            print(f"동료 탈퇴 실행 오류: {e}")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="동료 탈퇴 중 오류가 발생했습니다.")],
                "next_action": "wait_input"
            }
        
    def companion_list_node(self, state: PlayerInitState) -> PlayerInitState:
        #동료 목록 표시
    
        main_db = state.get("main_story_db")
        companion_ids = state.get("companion_ids", [])
    
        if not main_db:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="동료 정보를 확인할 수 없습니다.")],
                "next_action": "wait_input"
            }
    
        if not companion_ids:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="현재 동료가 없습니다. '누군가 만나고 싶어'라고 말하면 동료 영입 기회가 생깁니다.")],
                "next_action": "wait_input"
            }
    
        # 파티 상태 조회
        party_status = main_db.get_party_status()
        companion_list = """
        **현재 파티 동료들**

        """
    
        companion_count = 0
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            if char_type == 'companion':
                companion_count += 1
                status = "💚 생존" if is_alive else "💀 위험"
            
                # 동료의 상세 정보 가져오기
                companion_data = main_db.get_character(char_id)
                backstory = companion_data.get('backstory', '알 수 없는 과거') if companion_data else '알 수 없는 과거'
            
                companion_list += f"""
                **{companion_count}. {name}**
                • 상태: {status}
                • HP: {hp}/{max_hp} | MP: {mp}/{max_mp}
                • 배경: {backstory}
                """
    
        companion_list += f"""
        **파티 현황:** {len(companion_ids) + 1}명/3명
        **관리 명령어:**
        • '동료 탈퇴' - 동료를 파티에서 내보내기

        어떻게 하시겠어요?
        """
    
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=companion_list)],
            "next_action": "wait_input"
        }
    
    def companion_reject_node(self, state: PlayerInitState) -> PlayerInitState:
        #동료 영입 거절
         
        current_location = state.get("current_location", "알 수 없는 곳")
        current_reputation = self._get_current_reputation(state)

        # 명성에 따른 NPC 반응
        reputation_response = self.reputation_manager.get_reputation_response(current_reputation)

        # 이전 메시지에서 NPC 정보 추출
        recent_messages = [msg.content for msg in state["messages"][-3:] if isinstance(msg, AIMessage)]
        npc_context = " ".join(recent_messages)

        sys_prompt = f"""
        현재 위치 {current_location}에서 플레이어가 동료 영입을 거절했습니다.
        
        **플레이어 명성:** {current_reputation} ({reputation_response.level.value})
        **NPC 태도:** {reputation_response.tone}
        **이전 상황:** {npc_context}
        
        **명성에 따른 NPC 반응:**
        - 높은 명성(60+): "영광이었습니다" (존경하며 이해)
        - 보통 명성(0-59): "아쉽지만 이해해요" (아쉬워하며)
        - 낮은 명성(-1~-40): "그럴 줄 알았어" (차가우게)
        - 매우 낮은 명성(-41 이하): "다행이야!" (안도하며)
        
        150-200자 내외로 생동감 있게 작성하고 "어떻게 하시겠어요?"로 마무리하세요.
        """

        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content="명성에 맞는 거절 반응 생성")
            ])
            
            result = {
                **state,
                "messages": state["messages"] + [AIMessage(content=response.content)],
                "next_action": "wait_input"
            }
            
            return result
            
        except Exception as e:
            print(f"동료 영입 거절 반응 생성 오류: {e}")
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="그 사람은 아쉬운 표정을 지으며 다른 길로 떠나갔습니다. 어떻게 하시겠어요?")],
                "next_action": "wait_input"
            }
        
    def reputation_check_node(self, state: PlayerInitState) -> PlayerInitState:
        #명성 상태 확인
        
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if not main_db or not player_id:
            return {
                **state,
                "messages": state["messages"] + [AIMessage(content="명성 정보를 확인할 수 없습니다.")],
                "next_action": "wait_input"
            }
        
        # 현재 명성 조회
        current_reputation = self._get_current_reputation(state)
        reputation_status = self.reputation_manager.get_reputation_status_message(current_reputation)
        
        # 명성 변화 기록 조회
        reputation_history = main_db.get_reputation_history(player_id, 5)
        
        reputation_msg = f"""
        **명성 현황**
        {reputation_status}

        **명성 효과:**
        • 상점 가격: {self.reputation_manager.get_reputation_response(current_reputation).price_modifier * 100:.0f}% (기본 100%)
        • NPC 호감도: {self.reputation_manager.get_reputation_response(current_reputation).willingness_to_help * 100:.0f}%
        • 태도: {self.reputation_manager.get_reputation_response(current_reputation).tone}

        **최근 명성 변화:**
        """
        
        if reputation_history:
            for old_rep, new_rep, change, reason, location, timestamp in reputation_history:
                change_sign = "+" if change > 0 else ""
                reputation_msg += f"• {reason}: {change_sign}{change} ({old_rep} → {new_rep}) - {location}\n"
        else:
            reputation_msg += "• 아직 명성 변화가 없습니다.\n"
        
        reputation_msg += """
        **명성 향상 방법:**
        • 선한 행동, 퀘스트 완료, 생명 구조
        • 마을 구원, 보스 처치, 동료 영입

        **명성 하락 요인:**
        • 악한 행동, 거짓말, 약속 위반
        • 민간인 공격, 도둑질, 배신

        어떻게 하시겠어요?
        """
        
        result = {
            **state,
            "messages": state["messages"] + [AIMessage(content=reputation_msg)],
            "next_action": "wait_input"
        }
        
        return result
    
    def _get_current_reputation(self, state: Dict) -> int:
        """현재 명성 조회"""
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if main_db and player_id:
            player_data = main_db.get_character(player_id)
            if player_data:
                return player_data['reputation']
        
        return 0