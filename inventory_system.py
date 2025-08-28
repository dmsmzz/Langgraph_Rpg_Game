#인벤토리 및 상정 시스템 모듈
#아이템 관리, 상점 거래 등을 처리한다

import random
from typing import Dict, List, Optional, Tuple
from models import Item, ShopItem, GAME_CONSTANTS
from reputation_system import ReputationManager

class InventorySystem:
    #인벤토리 시스템 클래스

    def __init__(self):
        self.reputation_manager = ReputationManager()
    
    def get_inventory_display(self, state: Dict) -> str:
        #인벤토리 표시 생성
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        current_gold = state.get("player_gold", 0)
        
        if not main_db or not player_id:
            return "인벤토리에 접근할 수 없습니다."
        
        # 인벤토리 조회
        inventory = main_db.get_inventory(player_id)
        
        # 파티 HP/MP 상태 조회
        party_status = main_db.get_party_status()
        party_hp_info = []
        
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            party_hp_info.append({
                "id": char_id,
                "name": name,
                "hp": hp,
                "max_hp": max_hp,
                "mp": mp,
                "max_mp": max_mp,
                "is_alive": is_alive
            })
        
        # 치료사 확인
        healers = [char for char in party_hp_info 
                  if "성직자" in char.get("name", "") or "priest" in char.get("name", "").lower()]
        
        # 현재 명성 조회
        current_reputation = self._get_current_reputation(state)
        reputation_status = self.reputation_manager.get_reputation_status_message(current_reputation)
        
        inventory_display = f"""
        **인벤토리**
        """
        
        if inventory:
            # 아이템 타입별 분류
            items_by_type = {}
            for item in inventory:
                item_id, item_name, item_type, quantity, description, value = item
                if item_type not in items_by_type:
                    items_by_type[item_type] = []
                items_by_type[item_type].append({
                    "id": item_id,
                    "name": item_name,
                    "quantity": quantity,
                    "description": description,
                    "value": value
                })
            
            # 타입별로 표시
            for item_type, items in items_by_type.items():
                inventory_display += f"\n**{item_type.upper()}**:\n"
                for item in items:
                    inventory_display += f"• {item['name']} x{item['quantity']}"
                    if item['value'] > 0:
                        inventory_display += f" (가치: {item['value']}골드)"
                    inventory_display += "\n"
        else:
            inventory_display += "• 빈 인벤토리\n"
        
        inventory_display += f"""
        **골드**: {current_gold}
        **명성**: {reputation_status}

        **파티 상태**
        """
        
        for char in party_hp_info:
            status = "💀" if not char["is_alive"] else "❤️"
            inventory_display += f"{status} {char['name']}: HP {char['hp']}/{char['max_hp']}, MP {char['mp']}/{char['max_mp']}\n"
        
        if healers:
            inventory_display += f"\n✨ **치유 가능**: {', '.join([h['name'] for h in healers])}이 힐을 사용할 수 있습니다.\n"
        
        inventory_display += f"""
        **사용 가능한 명령어**:
        • "물약 사용" - HP/MP 회복
        • "힐 사용" - 성직자의 치유 마법 (성직자가 있을 경우)
        • "인벤토리 닫기" - 인벤토리 종료

        어떻게 하시겠습니까?
        """
        
        return inventory_display
    
    def use_potion(self, state: Dict) -> str:
        #물약 사용 처리
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if not main_db or not player_id:
            return "물약을 사용할 수 없습니다."
        
        # 물약 조회
        hp_potions = main_db.get_item_by_type(player_id, "hp_potion")
        mp_potions = main_db.get_item_by_type(player_id, "mp_potion")
        
        if not hp_potions and not mp_potions:
            return "사용할 수 있는 물약이 없습니다."
        
        # HP 물약 우선 사용
        if hp_potions:
            return self._use_hp_potion(main_db, player_id, hp_potions[0])
        elif mp_potions:
            return self._use_mp_potion(main_db, player_id, mp_potions[0])
        
    def _use_hp_potion(self, main_db, player_id: int, potion_info: Tuple) -> str:
        #HP 물약 사용
        item_id, item_name, item_type, quantity, description, value = potion_info
        
        # 파티원들의 HP 회복
        party_status = main_db.get_party_status()
        healed_members = []
        
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            if is_alive and hp < max_hp:
                heal_amount = min(GAME_CONSTANTS["HEALING_POTION_EFFECT"], max_hp - hp)
                new_hp, new_mp = main_db.heal_character(char_id, heal_amount, 0)
                healed_members.append(f"{name} (+{heal_amount} HP)")
        
        # 물약 소모
        main_db.use_item(player_id, item_id, 1)
        
        result_msg = f"✨ {item_name}을 사용했습니다!\n"
        if healed_members:
            result_msg += "💖 " + ", ".join(healed_members)
        else:
            result_msg += "모든 파티원이 이미 체력이 가득합니다."
        
        return result_msg
    
    def _use_mp_potion(self, main_db, player_id: int, potion_info: Tuple) -> str:
        #MP 물약 사용
        item_id, item_name, item_type, quantity, description, value = potion_info
        
        # 파티원들의 MP 회복
        party_status = main_db.get_party_status()
        healed_members = []
        
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            if is_alive and mp < max_mp:
                heal_amount = min(GAME_CONSTANTS["MANA_POTION_EFFECT"], max_mp - mp)
                new_hp, new_mp = main_db.heal_character(char_id, 0, heal_amount)
                healed_members.append(f"{name} (+{heal_amount} MP)")
        
        # 물약 소모
        main_db.use_item(player_id, item_id, 1)
        
        result_msg = f"✨ {item_name}을 사용했습니다!\n"
        if healed_members:
            result_msg += "💙 " + ", ".join(healed_members)
        else:
            result_msg += "모든 파티원이 이미 마나가 가득합니다."
        
        return result_msg
    
    def use_heal_spell(self, state: Dict) -> str:
        #성직자의 힐 사용
        main_db = state.get("main_story_db")
        
        if not main_db:
            return "힐을 사용할 수 없습니다."
        
        # 성직자 찾기
        healers = main_db.get_healers()
        
        if not healers:
            return "힐을 사용할 수 있는 성직자가 없거나 마나가 부족합니다."
        
        # 첫 번째 성직자가 힐 사용
        healer_id, healer_name, healer_hp, healer_max_hp, healer_mp, healer_max_mp, healer_class = healers[0]
        
        # 가장 체력이 낮은 파티원 치유
        party_status = main_db.get_party_status()
        lowest_hp_char = None
        lowest_hp_ratio = 1.0
        
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            if is_alive and hp < max_hp:
                hp_ratio = hp / max_hp
                if hp_ratio < lowest_hp_ratio:
                    lowest_hp_ratio = hp_ratio
                    lowest_hp_char = (char_id, name, hp, max_hp)
        
        if lowest_hp_char:
            char_id, name, current_hp, max_hp = lowest_hp_char
            heal_amount = min(GAME_CONSTANTS["HEAL_SPELL_EFFECT"], max_hp - current_hp)
            
            # 힐 실행
            main_db.heal_character(char_id, heal_amount, 0)
            # 성직자 MP 소모
            main_db.heal_character(healer_id, 0, -GAME_CONSTANTS["HEAL_SPELL_COST"])
            
            return f"✨ {healer_name}이 {name}에게 힐을 사용했습니다!\n💖 {name}이 {heal_amount} HP 회복했습니다!"
        else:
            return f"{healer_name}이 힐을 준비했지만 치유가 필요한 파티원이 없습니다."
        
    def _get_current_reputation(self, state: Dict) -> int:
        #현재 명성 조회
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if main_db and player_id:
            player_data = main_db.get_character(player_id)
            if player_data:
                return player_data['reputation']
        
        return 0
    
class ShopSystem:
    #상점 시스템 클래스
    
    def __init__(self):
        self.reputation_manager = ReputationManager()
        self.base_shop_items = {
            "치유 물약": ShopItem(
                name="치유 물약",
                price=50,
                type="hp_potion",
                description="HP를 50 회복시키는 물약",
                stock=10
            ),
            "마나 물약": ShopItem(
                name="마나 물약",
                price=50,
                type="mp_potion",
                description="MP를 30 회복시키는 물약",
                stock=10
            ),
            "강화된 방패": ShopItem(
                name="강화된 방패",
                price=200,
                type="shield",
                description="방어력을 증가시키는 방패",
                stock=3
            ),
            "어둠의 결정": ShopItem(
                name="어둠의 결정",
                price=100,
                type="crystal",
                description="어둠의 적에게 추가 피해를 주는 결정",
                stock=5
            )
        }

    def get_shop_display(self, state: Dict) -> str:
        #상점 표시 생성
        current_gold = state.get("player_gold", 0)
        current_reputation = self._get_current_reputation(state)
        
        # 명성에 따른 가격 조정
        reputation_response = self.reputation_manager.get_reputation_response(current_reputation)
        
        shop_display = f"""
        **상점**
        현재 골드: {current_gold}
        명성: {current_reputation} ({reputation_response.level.value})
        가격 조정: {int((reputation_response.price_modifier - 1) * 100):+d}%

        **상품 목록**:
        """
        
        for item_name, item_info in self.base_shop_items.items():
            adjusted_price = self.reputation_manager.apply_reputation_to_price(
                item_info["price"], current_reputation
            )
            
            shop_display += f"• {item_name}: {adjusted_price}골드"
            if adjusted_price != item_info["price"]:
                shop_display += f" (원가: {item_info['price']}골드)"
            shop_display += f" - {item_info['description']}\n"
        
        shop_display += f"""
        **구매 방법**: "물약 구입", "방패 구입" 등으로 말하세요.
        **나가기**: "상점 나가기" 또는 다른 행동을 말하세요.
        """
        
        return shop_display
    
    def process_purchase(self, state: Dict, item_name: str, quantity: int = 1) -> str:
        #구매 처리
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        current_gold = state.get("player_gold", 0)
        current_reputation = self._get_current_reputation(state)
        
        if not main_db or not player_id:
            return "구매할 수 없습니다."
        
        # 아이템 존재 확인
        if item_name not in self.base_shop_items:
            return "해당 아이템을 찾을 수 없습니다."
        
        item_info = self.base_shop_items[item_name]
        
        # 명성에 따른 가격 조정
        adjusted_price = self.reputation_manager.apply_reputation_to_price(
            item_info["price"], current_reputation
        )
        total_cost = adjusted_price * quantity
        
        # 골드 확인
        if current_gold < total_cost:
            return f"골드가 부족합니다! 현재 골드: {current_gold}, 필요한 골드: {total_cost}"
        
        # 서비스 접근 권한 확인
        if not self.reputation_manager.can_access_service(current_reputation, "기본_상점"):
            return "현재 명성으로는 이 상점을 이용할 수 없습니다."
        
        # 구매 처리
        new_gold = current_gold - total_cost
        state["player_gold"] = new_gold
        
        # 골드 DB 업데이트
        main_db.update_gold(player_id, -total_cost)
        
        # 아이템 추가
        main_db.add_item(
            player_id,
            item_name,
            item_info["type"],
            quantity,
            item_info["description"],
            item_info["price"]
        )
        
        # 거래 기록
        main_db.record_shop_transaction(
            player_id,
            item_name,
            quantity,
            adjusted_price,
            total_cost,
            "buy",
            state.get("current_location", "상점")
        )
        
        # 구매 완료 메시지
        purchase_msg = f"""
        **구매 완료!**
        • {item_name} x{quantity} 구매
        • 소모된 골드: {total_cost}
        • 남은 골드: {new_gold}
        """
        
        if adjusted_price != item_info["price"]:
            discount_percent = int((1 - adjusted_price / item_info["price"]) * 100)
            if discount_percent > 0:
                purchase_msg += f"• 명성 할인: {discount_percent}% 할인 적용!\n"
            else:
                purchase_msg += f"• 명성 할증: {abs(discount_percent)}% 할증 적용\n"
        
        purchase_msg += f"""
        아이템이 인벤토리에 추가되었습니다!
        '인벤토리'를 입력하여 확인할 수 있습니다.
        
        어떻게 하시겠어요?
        """
        
        return purchase_msg
    
    def _get_current_reputation(self, state: Dict) -> int:
        #현재 명성 조회
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if main_db and player_id:
            player_data = main_db.get_character(player_id)
            if player_data:
                return player_data['reputation']
        
        return 0

class ItemRewardSystem:
    #아이템 보상 시스템 클래스
        
    def __init__(self):
        self.possible_items = [
            ("체력 물약", "hp_potion", "체력을 50 회복시키는 물약", 50),
            ("마나 물약", "mp_potion", "마나를 30 회복시키는 물약", 50),
            ("고급 체력 물약", "hp_potion", "체력을 100 회복시키는 강력한 물약", 100),
            ("마법 두루마리", "scroll", "일회용 마법 아이템", 75),
            ("은화", "currency", "귀중한 화폐", 25),
            ("빵", "food", "허기를 달래는 음식", 10),
            ("철광석", "material", "무기 제작에 사용되는 재료", 30),
            ("마법 가루", "material", "마법 아이템 제작 재료", 40),
            ("낡은 지도", "misc", "보물의 위치를 알려주는 지도", 200),
            ("반지", "accessory", "능력을 향상시키는 반지", 150)
        ]
    
    def generate_battle_rewards(self, state: Dict, battle_data: Dict) -> str:
        #전투 후 아이템 보상 생성
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        current_location = state.get("current_location", "알 수 없는 곳")
        
        if not main_db or not player_id:
            return "보상을 받을 수 없습니다."
        
        # 전투 난이도에 따른 보상 수량 결정
        total_damage = battle_data.get("total_damage_dealt", 0)
        critical_hits = len(battle_data.get("critical_hits", []))
        
        # 1-3개 아이템 랜덤 획득
        base_item_count = 1
        if total_damage > 150:
            base_item_count = 3
        elif total_damage > 100:
            base_item_count = 2
        
        bonus_items = critical_hits // 2  # 크리티컬 히트 2개당 보너스 아이템 1개
        num_items = min(5, base_item_count + bonus_items)
        
        obtained_items = []
        
        for _ in range(num_items):
            item_name, item_type, description, value = random.choice(self.possible_items)
            quantity = random.randint(1, 3)
            
            # 희귀 아이템 확률 조정
            if item_type in ["accessory", "misc"] and random.random() > 0.3:
                continue  # 희귀 아이템은 30% 확률로만 획득
            
            # DB에 아이템 추가
            main_db.add_item(player_id, item_name, item_type, quantity, description, value)
            obtained_items.append(f"{item_name} x{quantity}")
        
        # 보상 메시지 생성
        reward_msg = f"""
        **아이템 획득!**
        {current_location}에서 다음 아이템을 발견했습니다:

        {chr(10).join(f"• {item}" for item in obtained_items)}

        인벤토리에 아이템이 추가되었습니다!
        '인벤토리'라고 말하면 언제든지 확인할 수 있습니다.

        어떻게 하시겠어요?
        """
        
        return reward_msg
    
    def generate_exploration_rewards(self, state: Dict) -> str:
        #탐험 중 아이템 발견
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        current_location = state.get("current_location", "알 수 없는 곳")
        
        if not main_db or not player_id:
            return "아이템을 발견할 수 없습니다."
        
        # 탐험 보상은 전투 보상보다 적음
        num_items = random.randint(1, 2)
        obtained_items = []
        
        for _ in range(num_items):
            # 탐험에서는 소모품과 재료 위주로 발견
            exploration_items = [item for item in self.possible_items 
                               if item[1] in ["hp_potion", "mp_potion", "food", "material", "currency"]]
            
            item_name, item_type, description, value = random.choice(exploration_items)
            quantity = random.randint(1, 2)
            
            # DB에 아이템 추가
            main_db.add_item(player_id, item_name, item_type, quantity, description, value)
            obtained_items.append(f"{item_name} x{quantity}")
        
        reward_msg = f"""
        **탐험 중 발견!**
        {current_location}을 탐험하던 중 다음 아이템을 발견했습니다:
        
        {chr(10).join(f"• {item}" for item in obtained_items)}
        
        인벤토리에 아이템이 추가되었습니다!
        
        어떻게 하시겠어요?
        """
        
        return reward_msg
    
    def give_quest_reward(self, state: Dict, quest_type: str) -> str:
        #퀘스트 완료 보상
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if not main_db or not player_id:
            return "보상을 받을 수 없습니다."
        
        # 퀘스트 타입별 보상 설정
        quest_rewards = {
            "main_quest": [
                ("전설의 검", "weapon", "고대의 힘이 깃든 검", 500),
                ("마법 갑옷", "armor", "마법 방어력을 제공하는 갑옷", 400),
                ("지혜의 반지", "accessory", "지능을 증가시키는 반지", 300)
            ],
            "side_quest": [
                ("고급 체력 물약", "hp_potion", "체력을 100 회복시키는 물약", 100),
                ("마법 두루마리", "scroll", "강력한 마법 두루마리", 75),
                ("은화", "currency", "퀘스트 보상금", 50)
            ],
            "rescue_quest": [
                ("감사의 목걸이", "accessory", "구조에 대한 감사의 표시", 200),
                ("축복의 물약", "hp_potion", "신의 축복이 깃든 물약", 150),
                ("희망의 결정", "crystal", "희망의 힘이 깃든 결정", 250)
            ]
        }
        
        reward_items = quest_rewards.get(quest_type, quest_rewards["side_quest"])
        selected_reward = random.choice(reward_items)
        
        item_name, item_type, description, value = selected_reward
        quantity = 1
        
        # DB에 아이템 추가
        main_db.add_item(player_id, item_name, item_type, quantity, description, value)
        
        # 명성 보상도 추가
        reputation_change = {"main_quest": 15, "side_quest": 5, "rescue_quest": 10}.get(quest_type, 5)
        main_db.update_reputation(
            player_id, 
            reputation_change, 
            f"{quest_type} 완료",
            state.get("current_location", "퀘스트 지역")
        )
        
        reward_msg = f"""
        🏆 **퀘스트 완료 보상!**
        • {item_name} x{quantity} 획득!
        • 명성 +{reputation_change}
        • 설명: {description}

        📦 인벤토리에 아이템이 추가되었습니다!
        ⭐ 명성이 증가했습니다!

        어떻게 하시겠어요?
        """
        
        return reward_msg