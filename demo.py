#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 작동하는 RPG 게임 포트폴리오 데모 - 오류 수정 버전
"""

import os
import sys
import time
import random
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
except ImportError:
    print("⚠️ LangChain 라이브러리가 설치되지 않았습니다.")
    print("pip install langchain langchain-openai 를 실행해주세요.")
    sys.exit(1)

class DemoDatabase:
    """데모용 간단 데이터베이스"""
    
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self._create_tables()
        
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE characters (
            id INTEGER PRIMARY KEY,
            name TEXT,
            race TEXT,
            class TEXT,
            level INTEGER,
            hp INTEGER,
            max_hp INTEGER,
            mp INTEGER,
            max_mp INTEGER,
            reputation INTEGER,
            gold INTEGER,
            is_player BOOLEAN,
            is_in_party BOOLEAN
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY,
            player_id INTEGER,
            item_name TEXT,
            item_type TEXT,
            quantity INTEGER,
            description TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE reputation_history (
            id INTEGER PRIMARY KEY,
            player_id INTEGER,
            old_reputation INTEGER,
            new_reputation INTEGER,
            change_amount INTEGER,
            reason TEXT,
            timestamp TEXT
        )
        ''')
        self.conn.commit()

class PortfolioDemo:
    """실제 작동하는 포트폴리오 데모"""
    
    def __init__(self, api_key: str):
        os.environ["OPENAI_API_KEY"] = api_key
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        self.db = DemoDatabase()
        
        # 데모 데이터 초기화
        self.player_id = self._create_demo_player()
        self._setup_demo_companions()
        self._setup_demo_inventory()
        
    def _create_demo_player(self) -> int:
        """데모 플레이어 생성"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        INSERT INTO characters 
        (name, race, class, level, hp, max_hp, mp, max_mp, reputation, gold, is_player, is_in_party)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("아리엘", "엘프", "마법사", 3, 105, 120, 65, 100, 47, 895, True, True))
        
        self.db.conn.commit()
        return cursor.lastrowid
        
    def _setup_demo_companions(self):
        """데모 동료들 설정"""
        companions = [
            ("가렌", "인간", "전사", 2, 155, 200, 20, 40, 0, 0),
            ("리나", "하플링", "도적", 2, 77, 120, 30, 60, 0, 0)
        ]
        
        cursor = self.db.conn.cursor()
        for comp in companions:
            cursor.execute('''
            INSERT INTO characters 
            (name, race, class, level, hp, max_hp, mp, max_mp, reputation, gold, is_player, is_in_party)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (*comp, False, True))
        self.db.conn.commit()
        
    def _setup_demo_inventory(self):
        """데모 인벤토리 설정"""
        items = [
            ("치유 물약", "hp_potion", 5, "HP 50 회복"),
            ("마나 물약", "mp_potion", 3, "MP 30 회복"),
            ("마법 두루마리", "scroll", 2, "파이어볼 마법"),
            ("은화", "currency", 25, "귀중한 화폐"),
            ("마법 지팡이", "weapon", 1, "마법력 증폭"),
            ("마법사 로브", "armor", 1, "마법 방어")
        ]
        
        cursor = self.db.conn.cursor()
        for item in items:
            cursor.execute('''
            INSERT INTO inventory (player_id, item_name, item_type, quantity, description)
            VALUES (?, ?, ?, ?, ?)
            ''', (self.player_id, *item))
        self.db.conn.commit()

    def print_header(self, title: str):
        """헤더 출력"""
        print("\n" + "="*80)
        print(f"🎮 {title}")
        print("="*80)

    def wait_for_demo(self, seconds: float = 1.5):
        """데모용 대기"""
        time.sleep(seconds)

    def demo_1_character_creation(self):
        """1. 캐릭터 생성 데모"""
        self.print_header("1. 실제 AI 기반 캐릭터 생성 시스템")
        
        print("🎭 캐릭터 생성 시스템 시연...")
        print("\n사용자 입력: \"내 이름은 아리엘이고 종족은 엘프, 직업은 마법사, 나이는 150살이야\"")
        
        self.wait_for_demo()
        
        # 실제 LLM으로 캐릭터 정보 파싱
        sys_prompt = """
        사용자 입력에서 캐릭터 정보를 추출해서 JSON으로 반환하세요.
        
        추출할 정보:
        - 이름 (string)
        - 종족 (string)
        - 직업 (string)
        - 나이 (integer)
        
        JSON 형식으로만 답변하세요:
        {"이름": "값", "종족": "값", "직업": "값", "나이": 값}
        """
        
        try:
            print("🤖 AI가 캐릭터 정보를 분석 중...")
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content="내 이름은 아리엘이고 종족은 엘프, 직업은 마법사, 나이는 150살이야")
            ])
            
            character_data = json.loads(response.content)
            print(f"✅ AI 분석 완료: {character_data}")
            
        except Exception as e:
            print(f"❌ AI 분석 실패: {e}")
            character_data = {"이름": "아리엘", "종족": "엘프", "직업": "마법사", "나이": 150}
        
        self.wait_for_demo()
        
        # 시작 지점 생성
        print("\n🤖 AI가 시작 지점을 생성 중...")
        location_prompt = f"""
        다음 캐릭터 정보를 바탕으로 흥미로운 시작 지점을 생성해주세요.
        
        캐릭터: {character_data['이름']} ({character_data['종족']} {character_data['직업']})
        
        창의적인 시작 지점 이름을 한 줄로만 답해주세요.
        """
        
        try:
            location_response = self.llm.invoke([
                SystemMessage(content=location_prompt),
                HumanMessage(content="시작 지점 생성")
            ])
            starting_location = location_response.content.strip()
            
        except Exception as e:
            print(f"❌ 시작 지점 생성 실패: {e}")
            starting_location = "고대 마법 도서관"
        
        print(f"✅ 시작 지점 생성: {starting_location}")
        
        self.wait_for_demo()
        
        # 배경 스토리 생성
        print("\n🤖 AI가 배경 스토리를 생성 중...")
        backstory_prompt = f"""
        다음 캐릭터의 배경 스토리를 생성해주세요.
        
        캐릭터: {character_data['이름']} ({character_data['종족']} {character_data['직업']}, {character_data['나이']}세)
        시작 지점: {starting_location}
        
        200-300자 내외로 흥미로운 배경 스토리를 작성해주세요.
        """
        
        try:
            backstory_response = self.llm.invoke([
                SystemMessage(content=backstory_prompt),
                HumanMessage(content="배경 스토리 생성")
            ])
            backstory = backstory_response.content.strip()
            
        except Exception as e:
            print(f"❌ 배경 스토리 생성 실패: {e}")
            backstory = f"{character_data['이름']}은 {starting_location}에서 모험을 시작하는 {character_data['종족']} {character_data['직업']}입니다."
        
        print("✅ 배경 스토리 생성 완료!")
        print(f"\n📖 {backstory}")
        
        # 최종 캐릭터 정보 표시
        print("\n🎭 GM: **캐릭터 생성 완료!**")
        print(f"\n**기본 정보:**")
        print(f"• 이름: {character_data['이름']}")
        print(f"• 종족: {character_data['종족']}")
        print(f"• 직업: {character_data['직업']}")
        print(f"• 나이: {character_data['나이']}세")
        print(f"\n**시작 지점:** {starting_location}")
        print("**초기 능력치:** HP: 120, MP: 100, 골드: 895")

    def demo_2_reputation_system(self):
        """2. 명성 시스템 데모"""
        self.print_header("2. 실시간 명성 시스템 - 8단계 명성 등급")
        
        print("📊 8단계 명성 시스템 시연...")
        
        # 8단계 명성 시스템
        def get_reputation_level_detailed(rep):
            if rep >= 80:
                return {"level": "🌟 영웅", "discount": 50, "attitude": "극도로 존경하며 경외", "service": "무료 서비스"}
            elif rep >= 60:
                return {"level": "😊 매우 호의적", "discount": 30, "attitude": "매우 친근하고 호의적", "service": "특별 할인"}
            elif rep >= 20:
                return {"level": "🙂 호의적", "discount": 10, "attitude": "친근하고 협조적", "service": "기본 할인"}
            elif rep >= 0:
                return {"level": "😐 평범", "discount": 0, "attitude": "중립적", "service": "정상 가격"}
            elif rep >= -20:
                return {"level": "😕 약간 비호의적", "discount": -20, "attitude": "경계하는", "service": "약간 할증"}
            elif rep >= -40:
                return {"level": "😠 적대적", "discount": -50, "attitude": "불쾌하고 무례", "service": "높은 할증"}
            elif rep >= -60:
                return {"level": "😨 매우 적대적", "discount": -100, "attitude": "두려워하며 적대", "service": "서비스 거부"}
            else:
                return {"level": "💀 원수", "discount": -200, "attitude": "극도로 적대적", "service": "전투 또는 도망"}
        
        # 현재 명성 조회
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT reputation FROM characters WHERE is_player = 1")
        current_reputation = cursor.fetchone()[0]
        
        current_level = get_reputation_level_detailed(current_reputation)
        
        print(f"⭐ 현재 명성: {current_reputation}")
        print(f"🎭 명성 등급: {current_level['level']}")
        print(f"💰 상점 가격: {current_level['discount']:+d}%")
        print(f"👥 NPC 태도: {current_level['attitude']}")
        print(f"🛍️ 서비스: {current_level['service']}")
        
        # 명성 등급별 비교 표시
        print(f"\n📊 명성 시스템 8단계 비교:")
        reputation_examples = [80, 65, 35, 10, -10, -30, -50, -70]
        for rep in reputation_examples:
            level_info = get_reputation_level_detailed(rep)
            print(f"• {rep:3d}: {level_info['level']} - {level_info['attitude']}")
        
        # 명성 변화 시뮬레이션
        print("\n🎬 명성 변화 시뮬레이션...")
        
        actions = [
            ("마을 사람 도움", 3),
            ("전투 승리", 2),
            ("보스 처치", 5)
        ]
        
        original_rep = current_reputation
        for action, change in actions:
            self.wait_for_demo()
            old_rep = current_reputation
            current_reputation += change
            old_level = get_reputation_level_detailed(old_rep)
            new_level = get_reputation_level_detailed(current_reputation)
            
            # DB 업데이트
            cursor.execute("UPDATE characters SET reputation = ? WHERE is_player = 1", (current_reputation,))
            cursor.execute('''
            INSERT INTO reputation_history (player_id, old_reputation, new_reputation, change_amount, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.player_id, old_rep, current_reputation, change, action, datetime.now().isoformat()))
            
            self.db.conn.commit()
            
            level_change = ""
            if old_level['level'] != new_level['level']:
                level_change = f" 🔄 등급 변화: {old_level['level']} → {new_level['level']}"
            
            print(f"✨ {action}: +{change} ({old_rep} → {current_reputation}){level_change}")
        
        final_level = get_reputation_level_detailed(current_reputation)
        print(f"\n🏆 최종 명성: {current_reputation} ({final_level['level']})")
        print(f"💡 명성 변화로 인한 혜택 증가: {final_level['discount'] - get_reputation_level_detailed(original_rep)['discount']:+d}%")

    def demo_3_npc_interaction(self):
        """3. AI 기반 NPC 상호작용 데모"""
        self.print_header("3. 명성 기반 AI NPC 상호작용 (실제 8단계 테스트)")
        
        print("🎬 명성별 NPC 반응 차이를 실제로 시연합니다!")
        print("📍 상황: 마을 광장에서 상인과 대화")
        print("💬 사용자 입력: \"안녕하세요, 물약을 좀 사고 싶어요\"")
        
        # 테스트할 명성 단계들 (대표적인 몇 개만)
        reputation_tests = [
            (85, "🌟 영웅급"),
            (45, "🙂 호의적"), 
            (5, "😐 평범"),
            (-35, "😠 적대적"),
            (-75, "💀 원수")
        ]
        
        cursor = self.db.conn.cursor()
        
        for reputation_value, reputation_name in reputation_tests:
            self.wait_for_demo()
            print(f"\n" + "="*50)
            print(f"🎭 **{reputation_name} ({reputation_value}) 테스트**")
            print("="*50)
            
            # 임시로 명성 변경
            cursor.execute("UPDATE characters SET reputation = ? WHERE is_player = 1", (reputation_value,))
            self.db.conn.commit()
            
            print(f"🤖 AI가 명성 {reputation_value}에 맞는 NPC 반응을 실제 생성 중...")
            
            # 실제 LLM으로 NPC 대화 생성
            npc_prompt = f"""
            당신은 마을 광장의 상인입니다. 플레이어의 명성이 {reputation_value}입니다.
            
            플레이어가 "안녕하세요, 물약을 좀 사고 싶어요"라고 말했습니다.
            
            **명성 {reputation_value}에 맞는 자연스러운 응답을 작성하세요:**
            
            **영웅급 (80+)**: 
            - 극도로 존경하며 떨리는 목소리로 "영웅님!"
            - 무료 제공을 당연하게 여기며 감격
            - 예: "영웅님! 저... 저희 마을의 구세주시군요! 물약이고 뭐고 모든 것을 무료로!"
            
            **호의적 (20-60)**: 
            - 밝고 친근하게 인사
            - 할인 혜택을 기꺼이 제공
            - 예: "어서오세요! 평판이 좋으시니 특별 할인 해드릴게요!"
            
            **평범 (0-19)**: 
            - 정중하지만 별다른 감정 없이
            - 사무적이고 기계적인 응답
            - 예: "어서오세요. 물약이 필요하시군요. 어떤 종류를 찾으시는지요?"
            
            **적대적 (-20 ~ -60)**: 
            - 불쾌한 표정으로 귀찮아함
            - 높은 가격을 부당하게 요구
            - 예: "흥! 당신 같은 놈한테 팔기 싫지만... 돈만 제대로 내면 주겠어!"
            
            **원수 (-60 이하)**: 
            - 극도로 적대적이고 공격적
            - 거래 완전 거부 또는 위협
            - 예: "감히 내 앞에 나타나다니! 당장 꺼져! 경비대를 부르기 전에!"
            
            150자 내외로 해당 명성에 맞는 생생하고 자연스러운 대화를 작성하세요.
            """
            
            try:
                npc_response = self.llm.invoke([
                    SystemMessage(content=npc_prompt),
                    HumanMessage(content=f"명성 {reputation_value}에 맞는 자연스러운 NPC 대화 생성")
                ])
                
                npc_dialogue = npc_response.content.strip()
                
            except Exception as e:
                print(f"❌ AI 생성 실패: {e}")
                # 더 자연스러운 백업 대화
                backup_dialogues = {
                    85: "영웅님! 어... 어떻게 저희 가게에! 물약이고 뭐고 모든 걸 무료로 드리겠습니다! 영광입니다!",
                    45: "어서오세요! 소문으로 들었는데 정말 훌륭한 분이시군요! 물약 10% 할인해드릴게요!",
                    5: "어서오세요. 물약을 찾으시는군요. 어떤 종류가 필요하신지 말씀해 주세요.",
                    -35: "어... 당신이군요. 팔기는 싫지만 장사니까... 2배 받을 거예요. 싫으면 다른 데 가세요.",
                    -75: "뭐? 당신이 감히 여기에! 당장 나가! 물약 따위 안 팔아! 경비대 부르기 전에 꺼져!"
                }
                npc_dialogue = backup_dialogues.get(reputation_value, "...")
            
            print(f"\n🎭 상인: {npc_dialogue}")
            
            # 가격 조정 계산
            base_price = 50
            if reputation_value >= 80:
                price_text = "무료! (영웅 대우)"
            elif reputation_value >= 20:
                final_price = int(base_price * 0.9)
                price_text = f"{final_price} 골드 (10% 할인)"
            elif reputation_value >= 0:
                price_text = f"{base_price} 골드 (정상가)"
            elif reputation_value >= -40:
                final_price = int(base_price * 2.0)
                price_text = f"{final_price} 골드 (100% 할증)"
            else:
                price_text = "거래 거부 또는 전투 위험!"
                
            print(f"💰 **가격**: {price_text}")
            print(f"📸 [명성 {reputation_value} 스크린샷 포인트]")
        
        # 원래 명성으로 복구
        cursor.execute("UPDATE characters SET reputation = 57 WHERE is_player = 1")
        self.db.conn.commit()
        
        print(f"\n🎉 **명성별 NPC 반응 시연 완료!**")

    def demo_4_battle_system(self):
        """4. 전투 시스템 데모"""
        self.print_header("4. AI 기반 동적 전투 시스템")
        
        print("⚔️ 전투 시뮬레이션 시작...")
        print("📍 상황: 어둠의 숲에서 그림자 늑대 무리 조우")
        
        self.wait_for_demo()
        print("\n🤖 AI가 전투 시나리오를 생성 중...")
        
        # 파티 상태 조회
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name, class, hp, max_hp, mp, max_mp FROM characters WHERE is_in_party = 1")
        party_members = cursor.fetchall()
        
        # 전투 계산
        battle_results = []
        for member in party_members:
            name, char_class, hp, max_hp, mp, max_mp = member
            
            # 랜덤 전투 결과
            damage_taken = random.randint(10, 25)
            mp_used = random.randint(5, 15)
            damage_dealt = random.randint(25, 50)
            is_critical = random.random() < 0.3
            
            if is_critical:
                damage_dealt = int(damage_dealt * 1.5)
                
            new_hp = max(0, hp - damage_taken)
            new_mp = max(0, mp - mp_used)
            
            battle_results.append({
                "name": name,
                "damage_taken": damage_taken,
                "mp_used": mp_used,
                "damage_dealt": damage_dealt,
                "new_hp": new_hp,
                "new_mp": new_mp,
                "critical": is_critical
            })
            
            # DB 업데이트
            cursor.execute("UPDATE characters SET hp = ?, mp = ? WHERE name = ?", (new_hp, new_mp, name))
        
        self.db.conn.commit()
        
        # 실제 LLM으로 전투 장면 생성
        battle_prompt = f"""
        다음 전투 결과를 바탕으로 생동감 있는 전투 장면을 생성하세요.
        
        **전투 참가자와 결과:**
        {json.dumps(battle_results, ensure_ascii=False, indent=2)}
        
        **위치:** 어둠의 숲
        **적:** 그림자 늑대 무리
        
        200-300자 내외로 극적이고 몰입감 있는 전투 장면을 만들어주세요.
        각 캐릭터의 행동과 크리티컬 히트를 포함하세요.
        """
        
        try:
            battle_response = self.llm.invoke([
                SystemMessage(content=battle_prompt),
                HumanMessage(content="전투 장면 생성")
            ])
            
            battle_scene = battle_response.content.strip()
            
        except Exception as e:
            print(f"❌ 전투 장면 생성 실패: {e}")
            battle_scene = "어둠의 숲에서 치열한 전투가 벌어졌습니다! 파티원들이 혼신의 힘을 다해 그림자 늑대 무리와 싸웠습니다."
        
        self.wait_for_demo(1)
        print(f"\n🎬 {battle_scene}")
        
        # 전투 통계 표시
        print(f"\n📊 전투 통계:")
        for result in battle_results:
            critical_text = " 🔥크리티컬!" if result["critical"] else ""
            print(f"• {result['name']}: -{result['damage_taken']}HP, -{result['mp_used']}MP, {result['damage_dealt']} 데미지{critical_text}")
        
        print("\n🏆 전투 승리!")

    def demo_5_inventory_system(self):
        """5. 인벤토리 시스템 데모"""
        self.print_header("5. 인벤토리 관리 시스템 (물약 사용 + 힐 마법)")
        
        print("🎒 인벤토리 시스템 실행...")
        
        # 인벤토리 조회
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT item_name, item_type, quantity, description FROM inventory WHERE player_id = ?", (self.player_id,))
        inventory_items = cursor.fetchall()
        
        # 파티 상태 조회
        cursor.execute("SELECT name, hp, max_hp, mp, max_mp, class FROM characters WHERE is_in_party = 1")
        party_status = cursor.fetchall()
        
        # 플레이어 골드 조회
        cursor.execute("SELECT gold, reputation FROM characters WHERE is_player = 1")
        player_data = cursor.fetchone()
        gold, reputation = player_data
        
        print("\n🎭 GM: **인벤토리**")
        
        # 아이템 타입별 분류
        items_by_type = {}
        for item_name, item_type, quantity, description in inventory_items:
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append((item_name, quantity, description))
        
        # 인벤토리 표시
        for item_type, items in items_by_type.items():
            print(f"\n**{item_type.upper()}**:")
            for name, qty, desc in items:
                print(f"• {name} x{qty} - {desc}")
        
        print(f"\n**골드**: {gold}")
        print(f"**명성**: {'🙂 호의적' if reputation >= 20 else '😐 평범'} ({reputation})")
        
        print(f"\n**파티 상태**")
        healers = []
        for name, hp, max_hp, mp, max_mp, char_class in party_status:
            status_icon = "❤️" if hp > max_hp * 0.7 else "💛" if hp > max_hp * 0.3 else "💔"
            print(f"{status_icon} {name}: HP {hp}/{max_hp}, MP {mp}/{max_mp}")
            
            # 성직자나 마법사 확인 (힐 사용 가능)
            if char_class in ["마법사", "성직자"] and mp >= 10:
                healers.append((name, char_class))
        
        if healers:
            healer_names = [f"{name}({char_class})" for name, char_class in healers]
            print(f"\n✨ **힐 사용 가능**: {', '.join(healer_names)}이 치유 마법을 사용할 수 있습니다.")
        
        # 물약 사용 시뮬레이션
        print("\n🎬 1. 물약 사용 시뮬레이션...")
        self.wait_for_demo()
        
        # 치유 물약 사용
        healing_amount = 50
        healed_members = []
        
        for name, hp, max_hp, mp, max_mp, char_class in party_status:
            if hp < max_hp:
                heal = min(healing_amount, max_hp - hp)
                new_hp = hp + heal
                healed_members.append(f"{name} (+{heal} HP)")
                
                # DB 업데이트
                cursor.execute("UPDATE characters SET hp = ? WHERE name = ?", (new_hp, name))
        
        # 물약 수량 감소
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE item_name = '치유 물약' AND player_id = ?", (self.player_id,))
        self.db.conn.commit()
        
        print("🎭 GM: ✨ 치유 물약을 사용했습니다!")
        if healed_members:
            print("💖 " + ", ".join(healed_members))
        else:
            print("모든 파티원이 이미 체력이 가득합니다.")
        
        # 힐 마법 사용 시뮬레이션 (성직자/마법사가 있을 경우)
        if healers:
            self.wait_for_demo(1)
            print(f"\n🎬 2. 힐 마법 시뮬레이션...")
            
            healer_name, healer_class = healers[0]  # 첫 번째 힐러 사용
            
            # 가장 체력이 낮은 파티원 찾기
            cursor.execute("SELECT name, hp, max_hp FROM characters WHERE is_in_party = 1 ORDER BY (hp * 1.0 / max_hp) ASC LIMIT 1")
            target_data = cursor.fetchone()
            target_name, target_hp, target_max_hp = target_data
            
            heal_amount = 70  # 힐 마법은 물약보다 강력
            mp_cost = 15
            
            actual_heal = min(heal_amount, target_max_hp - target_hp)
            new_target_hp = target_hp + actual_heal
            
            # DB 업데이트
            cursor.execute("UPDATE characters SET hp = ? WHERE name = ?", (new_target_hp, target_name))
            cursor.execute("UPDATE characters SET mp = mp - ? WHERE name = ?", (mp_cost, healer_name))
            self.db.conn.commit()
            
            print(f"🎭 GM: ✨ {healer_name}({healer_class})이 {target_name}에게 힐 마법을 사용했습니다!")
            print(f"💫 {target_name}이 {actual_heal} HP 회복! (MP -{mp_cost})")
            print(f"🔮 마법의 빛이 {target_name}을 감싸며 상처를 치유합니다.")
            
        else:
            print(f"\n💡 힐 마법: 성직자나 마법사가 파티에 있고 MP가 충분할 때 사용 가능합니다.")
        
        # 업데이트된 파티 상태 표시
        print(f"\n📊 **치료 후 파티 상태**")
        cursor.execute("SELECT name, hp, max_hp, mp, max_mp FROM characters WHERE is_in_party = 1")
        updated_party = cursor.fetchall()
        
        for name, hp, max_hp, mp, max_mp in updated_party:
            status_icon = "💚" if hp == max_hp else "❤️" if hp > max_hp * 0.8 else "💛"
            print(f"{status_icon} {name}: HP {hp}/{max_hp}, MP {mp}/{max_mp}")

    def demo_6_companion_system(self):
        """6. 동료 시스템 데모"""
        self.print_header("6. AI 기반 동료 영입 시스템 (실제 명성별 동료 타입)")
        
        print("🎬 명성별 동료 타입 차이를 실제로 시연합니다!")
        print("📍 상황: 마을 입구에서 새로운 인물 조우")
        
        # 테스트할 명성과 동료 타입들
        companion_tests = [
            (85, "🌟 전설적 영웅", "세라핀", "천사", "성기사"),
            (45, "⚔️ 정의로운 기사", "엘리아스", "인간", "기사"),
            (5, "🛡️ 평범한 모험가", "마르코", "인간", "전사"),
            (-35, "⚫ 위험한 인물", "바로크", "다크엘프", "암살자")
        ]
        
        cursor = self.db.conn.cursor()
        
        for rep_value, comp_type, name, race, job in companion_tests:
            self.wait_for_demo()
            print(f"\n" + "="*50)
            print(f"👥 **{comp_type} ({rep_value}) 테스트**")
            print("="*50)
            
            # 임시로 명성 변경
            cursor.execute("UPDATE characters SET reputation = ? WHERE is_player = 1", (rep_value,))
            self.db.conn.commit()
            
            print(f"⭐ 현재 명성: {rep_value}")
            print(f"🤖 AI가 명성 {rep_value}에 맞는 동료를 실제 생성 중...")
            
            # 실제 LLM으로 첫 만남 장면 생성
            companion_prompt = f"""
            명성 {rep_value}인 플레이어와 {name}({race} {job})의 첫 만남을 생성하세요.
            
            **중요: 플레이어의 명성에 따라 {name}의 태도가 달라져야 합니다!**
            
            **명성 {rep_value}에 맞는 자연스러운 상황:**
            
            **영웅급 (85)**: 
            - {name}이 떨리는 목소리로 극도로 존경
            - "영웅님! 저... 저 같은 자가 감히..."
            - 천상의 존재답게 겸손하고 경외심 표현
            
            **정의로운 (45)**: 
            - {name}이 감동받아 자발적으로 접근
            - "당신의 선행을 듣고 찾아왔습니다!"
            - 정의로운 기사답게 당당하고 진지한 태도
            
            **평범 (5)**: 
            - {name}이 실용적이고 현실적으로 접근
            - "서로에게 도움이 될 것 같은데요"
            - 평범한 모험가답게 거래적인 관계 제안
            
            **위험한 (-35)**: 
            - {name}이 음산하고 위협적으로 접근
            - "크크크... 당신 같은 자를 찾고 있었어"
            - 암살자답게 어둠 속에서 나타나 불길한 제안
            
            **중요사항:**
            - 플레이어를 지칭할 때는 "당신"이라고만 하세요
            - {name}이 플레이어의 명성에 반응하는 상황을 만드세요
            - 150자 내외로 간결하게 작성하세요
            - 대화는 {name}의 말만 포함하세요
            """
            
            try:
                companion_response = self.llm.invoke([
                    SystemMessage(content=companion_prompt),
                    HumanMessage(content=f"명성 {rep_value}에 맞는 {name}의 자연스러운 첫 대화")
                ])
                
                intro_scene = companion_response.content.strip()
                
            except Exception as e:
                print(f"❌ AI 생성 실패: {e}")
                # 더 자연스러운 백업 대화
                backup_scenes = {
                    85: f"빛이 내려오며 {name}이 나타납니다.\n\"{name}: \"영웅님... 저 같은 자가 감히 말을 걸어도 될까요? 천상계에서 당신을 도우라 하였습니다. 영광입니다...\"",
                    45: f"{name}이 결의에 찬 표정으로 다가옵니다.\n\"{name}: \"당신의 정의로운 행적을 듣고 찾아왔습니다! 저도 악과 싸우는 데 힘을 보태고 싶습니다. 함께 가주세요!\"",
                    5: f"{name}이 차분하게 말합니다.\n\"{name}: \"실력 있는 모험가를 찾고 있었습니다. 서로 도움이 될 것 같은데, 어떻습니까? 보상도 공평하게 나눠가지고요.\"",
                    -35: f"{name}이 그림자에서 나타나 음산하게 웃습니다.\n\"{name}: \"크크크... 당신 냄새가 나는군요. 악한 자의 냄새 말이에요. 함께하면 재미있는 일이 많을 것 같은데... 어떻습니까?\""
                }
                intro_scene = backup_scenes.get(rep_value, f"{name}을 만났습니다.")
            
            print(f"\n🎬 {intro_scene}")
            
            print(f"\n🎭 GM: **{name}이 파티에 합류하고 싶어합니다!**")
            print(f"• 이름: {name} ({race} {job})")
            print(f"• 타입: {comp_type}")
            
            # 명성별 특수 효과
            if rep_value >= 80:
                print(f"✨ **천상의 축복**: 무료 합류, 특별한 능력 보유")
            elif rep_value >= 40:
                print(f"⚔️ **정의의 맹세**: 충성도 높음, 배신 위험 없음")
            elif rep_value >= 0:
                print(f"🛡️ **실용적 계약**: 보상 기대, 기본적 신뢰")
            else:
                print(f"⚫ **위험한 동맹**: 높은 배신 위험, 숨겨진 목적")
                print(f"⚠️ **배신 확률**: {abs(rep_value)}%")
            
            print(f"📸 [명성 {rep_value} 동료 생성 스크린샷 포인트]")
        
        # 원래 명성으로 복구
        cursor.execute("UPDATE characters SET reputation = 57 WHERE is_player = 1")
        self.db.conn.commit()
        
        print(f"\n🎉 **명성별 동료 타입 시연 완료!**")

    def demo_7_complete_workflow(self):
        """7. 통합 워크플로우 데모"""
        self.print_header("7. 통합 게임 워크플로우")
        
        print("🔄 전체 게임 흐름 시연...")
        print("📝 시나리오: 플레이어가 마을에서 퀘스트를 받고 해결하는 과정")
        
        self.wait_for_demo()
        
        # 현재 상태 조회
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name, reputation, gold FROM characters WHERE is_player = 1")
        player_name, reputation, gold = cursor.fetchone()
        
        print(f"\n📊 현재 상태:")
        print(f"• 플레이어: {player_name}")
        print(f"• 명성: {reputation}")
        print(f"• 골드: {gold}")
        
        # 1단계: 퀘스트 수주
        print(f"\n🎬 1단계: 퀘스트 수주")
        print("🎭 GM: 마을 촌장이 다가옵니다.")
        
        quest_prompt = f"""
        마을 촌장이 명성 {reputation}인 플레이어에게 퀘스트를 제안합니다.
        
        명성에 따른 퀘스트 난이도:
        - 높은 명성(40+): 중요하고 어려운 퀘스트
        - 보통 명성(20-39): 적당한 난이도의 퀘스트  
        - 낮은 명성(0-19): 간단한 심부름
        
        촌장의 대사와 퀘스트 내용을 150자 내외로 작성하세요.
        """
        
        try:
            quest_response = self.llm.invoke([
                SystemMessage(content=quest_prompt),
                HumanMessage(content="퀘스트 제안")
            ])
            quest_dialogue = quest_response.content.strip()
        except Exception as e:
            quest_dialogue = "마을을 위협하는 몬스터들을 물리쳐 주세요!"
        
        print(f"🎭 촌장: {quest_dialogue}")
        
        # 2단계: 전투 발생
        self.wait_for_demo(1)
        print(f"\n🎬 2단계: 퀘스트 수행 중 전투 발생")
        
        # 간단한 전투 시뮬레이션
        total_damage = random.randint(80, 120)
        critical_hits = random.randint(0, 2)
        
        print(f"⚔️ 전투 결과: 총 {total_damage} 데미지, 크리티컬 {critical_hits}회")
        
        # 명성 보상
        reputation_gain = 5 if reputation < 50 else 3
        gold_gain = 100 + random.randint(0, 50)
        
        new_reputation = reputation + reputation_gain
        new_gold = gold + gold_gain
        
        # DB 업데이트
        cursor.execute("UPDATE characters SET reputation = ?, gold = ? WHERE is_player = 1", 
                      (new_reputation, new_gold))
        self.db.conn.commit()
        
        # 3단계: 보상 및 결과
        self.wait_for_demo()
        print(f"\n🎬 3단계: 퀘스트 완료 및 보상")
        
        completion_prompt = f"""
        플레이어가 퀘스트를 성공적으로 완료했습니다.
        
        **결과:**
        - 명성 증가: +{reputation_gain} ({reputation} → {new_reputation})
        - 골드 획득: +{gold_gain}
        
        촌장의 감사 인사와 마을 사람들의 반응을 150자 내외로 작성하세요.
        """
        
        try:
            completion_response = self.llm.invoke([
                SystemMessage(content=completion_prompt),
                HumanMessage(content="퀘스트 완료")
            ])
            completion_scene = completion_response.content.strip()
        except Exception as e:
            completion_scene = "마을 사람들이 환호하며 감사를 표합니다!"
        
        print(f"🎭 GM: {completion_scene}")
        
        print(f"\n🏆 퀘스트 완료 보상:")
        print(f"• 명성 +{reputation_gain} ({reputation} → {new_reputation})")
        print(f"• 골드 +{gold_gain} ({gold} → {new_gold})")
        
        # 4단계: 상점에서 아이템 구매
        self.wait_for_demo()
        print(f"\n🎬 4단계: 명성 기반 상점 이용")
        
        base_price = 50
        if new_reputation >= 40:
            discount = 0.7  # 30% 할인
        elif new_reputation >= 20:
            discount = 0.9  # 10% 할인
        else:
            discount = 1.0
        
        final_price = int(base_price * discount)
        
        print(f"🏪 상점 이용:")
        print(f"• 기본 가격: {base_price} 골드")
        print(f"• 명성 할인: {final_price} 골드 ({int((1-discount)*100)}% 할인)")
        print(f"• 구매 후 잔액: {new_gold - final_price} 골드")
        
        print(f"\n✅ 전체 워크플로우 완료!")
        print(f"📈 성장 결과: 명성 {reputation} → {new_reputation}, 골드 {gold} → {new_gold-final_price}")


def get_api_key():
    """API 키 입력 받기"""
    print("🔑 OpenAI API 키 설정")
    print("💡 API 키는 https://platform.openai.com/api-keys 에서 발급받을 수 있습니다.")
    
    # 환경변수에서 먼저 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"✅ 환경변수에서 API 키를 찾았습니다: {api_key[:8]}...")
        return api_key
    
    while True:
        try:
            api_key = input("\nOpenAI API 키를 입력하세요 (sk-로 시작): ").strip()
            
            if not api_key:
                print("❌ API 키를 입력해주세요.")
                continue
            
            if not api_key.startswith("sk-"):
                print("❌ 올바른 API 키 형식이 아닙니다. (sk-로 시작해야 합니다)")
                continue
            
            if len(api_key) < 20:
                print("❌ API 키가 너무 짧습니다.")
                continue
            
            print(f"✅ API 키가 설정되었습니다: {api_key[:8]}...")
            return api_key
            
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            continue


def main():
    """메인 함수"""
    print("="*80)
    print("🎮 LangGraph RPG 게임 포트폴리오 데모")
    print("="*80)
    print("🚀 모든 주요 기능을 실제 AI와 연동하여 시연합니다!")
    print("📸 각 단계별로 스크린샷을 찍어서 포트폴리오에 활용하세요.")
    print()
    
    # API 키 설정
    api_key = get_api_key()
    
    try:
        # 데모 초기화
        print("\n🔧 데모 시스템 초기화 중...")
        demo = PortfolioDemo(api_key)
        print("✅ 초기화 완료!")
        
        # 데모 메뉴
        demos = [
            ("1. AI 기반 캐릭터 생성", demo.demo_1_character_creation),
            ("2. 실시간 명성 시스템", demo.demo_2_reputation_system),
            ("3. 명성 기반 NPC 상호작용", demo.demo_3_npc_interaction),
            ("4. AI 동적 전투 시스템", demo.demo_4_battle_system),
            ("5. 인벤토리 관리 시스템", demo.demo_5_inventory_system),
            ("6. AI 동료 영입 시스템", demo.demo_6_companion_system),
            ("7. 통합 게임 워크플로우", demo.demo_7_complete_workflow),
            ("8. 전체 데모 실행", None)
        ]
        
        while True:
            print("\n" + "="*60)
            print("📋 데모 메뉴 - 각 기능별로 실행 가능")
            print("="*60)
            
            for i, (title, _) in enumerate(demos, 1):
                print(f"{i}. {title}")
            print("9. 종료")
            
            try:
                choice = input("\n실행할 데모를 선택하세요 (1-9): ").strip()
                
                if choice == "9":
                    print("데모를 종료합니다. 포트폴리오 제작에 활용하세요! 🎯")
                    break
                elif choice == "8":
                    print("\n🎬 전체 데모 실행 - 모든 기능을 순차적으로 시연합니다!")
                    input("준비되면 Enter를 눌러주세요...")
                    
                    for title, func in demos[:-1]:  # 마지막 "전체 실행" 제외
                        if func:
                            func()
                            input("\n📸 스크린샷을 찍은 후 Enter를 눌러 다음으로...")
                    
                    print("\n🎉 전체 데모 완료! 모든 기능이 성공적으로 시연되었습니다!")
                    
                elif choice.isdigit() and 1 <= int(choice) <= 7:
                    title, func = demos[int(choice) - 1]
                    if func:
                        func()
                        input("\n📸 스크린샷을 찍은 후 Enter를 눌러 메뉴로...")
                else:
                    print("❌ 올바른 번호를 입력해주세요.")
                    
            except KeyboardInterrupt:
                print("\n\n데모를 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                print("계속 진행합니다...")
                
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        print("데모를 종료합니다.")


if __name__ == "__main__":
    main()