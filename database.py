# 게임 데이터베이스 관리 모듈
# 캐릭터 정보, 인벤토리, 이벤트 등 게임 데이터 관리

import sqlite3
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from models import Player, NPC, Item

class MainStoryDB:
    #메인스토리 데이터베이스 클래스

    def __init__(self, db_path: str = "main_story.db"):
        #데이터베이스 초기화
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        #테이블 생성
        cursor = self.conn.cursor()
        
        # 캐릭터 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS main_story_characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            race TEXT,
            class TEXT,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            mp INTEGER DEFAULT 50,
            max_mp INTEGER DEFAULT 50,
            strength INTEGER DEFAULT 10,
            agility INTEGER DEFAULT 10,
            intelligence INTEGER DEFAULT 10,
            current_location TEXT DEFAULT '마을',
            is_alive BOOLEAN DEFAULT TRUE,
            is_in_party BOOLEAN DEFAULT FALSE,
            relationship_level INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 300,
            backstory TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 인벤토리 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            description TEXT,
            value INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES main_story_characters (id)
        )
        ''')
        
        # 스토리 이벤트 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_description TEXT,
            location TEXT,
            turn_number INTEGER,
            reputation_change INTEGER DEFAULT 0,
            gold_change INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES main_story_characters (id)
        )
        ''')
        
        # 명성 변화 기록 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reputation_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            old_reputation INTEGER,
            new_reputation INTEGER,
            change_amount INTEGER,
            reason TEXT,
            location TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES main_story_characters (id)
        )
        ''')
        
        # 상점 거래 기록 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER,
            unit_price INTEGER,
            total_price INTEGER,
            transaction_type TEXT, -- 'buy' or 'sell'
            location TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES main_story_characters (id)
        )
        ''')

        self.conn.commit()

    def create_character(self, char_data: Dict) -> int:
        #캐릭터 생성
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO main_story_characters
            (name, type, race, class, level, hp, max_hp, mp, max_mp,
             strength, agility, intelligence, current_location, is_alive,
             is_in_party, relationship_level, reputation, gold, backstory)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            char_data['name'], char_data['type'], char_data.get('race', '인간'),
            char_data.get('class', '전사'), char_data.get('level', 1),
            char_data.get('hp', 100), char_data.get('max_hp', 100),
            char_data.get('mp', 50), char_data.get('max_mp', 50),
            char_data.get('strength', 10), char_data.get('agility', 10),
            char_data.get('intelligence', 10), char_data.get('current_location', '마을'),
            char_data.get('is_alive', True), char_data.get('is_in_party', False),
            char_data.get('relationship_level', 0), char_data.get('reputation', 0),
            char_data.get('gold', 300), char_data.get('backstory', '')
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_character(self, char_id: int) -> Optional[Dict]:
        #캐릭터 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM main_story_characters WHERE id = ?
        ''', (char_id,))
        
        result = cursor.fetchone()
        if result:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        return None
    
    def get_party_status(self) -> List[Tuple]:
        #파티 상태 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, type, hp, max_hp, mp, max_mp, is_alive, 
                   relationship_level, reputation, gold
            FROM main_story_characters 
            WHERE is_in_party = 1
            ORDER BY type, name
        ''')
        return cursor.fetchall()
    
    def apply_damage(self, char_id: int, damage: int) -> Tuple[int, bool]:
        #캐릭터에게 데미지 적용
        cursor = self.conn.cursor()
        cursor.execute("SELECT hp, max_hp FROM main_story_characters WHERE id = ?", (char_id,))
        result = cursor.fetchone()
        
        if not result:
            return 0, False
        
        current_hp, max_hp = result
        new_hp = max(0, current_hp - damage)
        is_alive = new_hp > 0
        
        cursor.execute('''
            UPDATE main_story_characters
            SET hp = ?, is_alive = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_hp, is_alive, char_id))
        
        self.conn.commit()
        return new_hp, is_alive
    
    def heal_character(self, char_id: int, hp_heal: int, mp_heal: int) -> Tuple[int, int]:
        #캐릭터 HP/MP 회복
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT hp, max_hp, mp, max_mp FROM main_story_characters WHERE id = ?
        ''', (char_id,))
        result = cursor.fetchone()
        
        if not result:
            return 0, 0
        
        current_hp, max_hp, current_mp, max_mp = result
        new_hp = min(max_hp, max(0, current_hp + hp_heal))
        new_mp = min(max_mp, max(0, current_mp + mp_heal))
        
        cursor.execute('''
            UPDATE main_story_characters
            SET hp = ?, mp = ?, is_alive = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_hp, new_mp, new_hp > 0, char_id))
        
        self.conn.commit()
        return new_hp, new_mp
    
    def update_reputation(self, char_id: int, reputation_change: int, reason: str = "", location: str = "") -> int:
        #캐릭터 명성 업데이트
        cursor = self.conn.cursor()
        
        # 현재 명성 조회
        cursor.execute("SELECT reputation FROM main_story_characters WHERE id = ?", (char_id,))
        result = cursor.fetchone()
        
        if not result:
            return 0
        
        old_reputation = result[0]
        new_reputation = max(-100, min(100, old_reputation + reputation_change))
        
        # 명성 업데이트
        cursor.execute('''
            UPDATE main_story_characters
            SET reputation = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_reputation, char_id))
        
        # 명성 변화 기록
        cursor.execute('''
            INSERT INTO reputation_changes
            (player_id, old_reputation, new_reputation, change_amount, reason, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (char_id, old_reputation, new_reputation, reputation_change, reason, location))
        
        self.conn.commit()
        return new_reputation
    
    def update_gold(self, char_id: int, gold_change: int) -> int:
        #캐릭터 골드 업데이트
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT gold FROM main_story_characters WHERE id = ?", (char_id,))
        result = cursor.fetchone()
        
        if not result:
            return 0
        
        current_gold = result[0]
        new_gold = max(0, current_gold + gold_change)
        
        cursor.execute('''
            UPDATE main_story_characters
            SET gold = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_gold, char_id))
        
        self.conn.commit()
        return new_gold
    
    def add_item(self, player_id: int, item_name: str, item_type: str, quantity: int, description: str = "", value: int = 0) -> int:
        #인벤토리에 아이템 추가
        cursor = self.conn.cursor()
        
        # 기존 아이템 확인
        cursor.execute('''
            SELECT id, quantity FROM inventory
            WHERE player_id = ? AND item_name = ? AND item_type = ?
        ''', (player_id, item_name, item_type))
        
        existing_item = cursor.fetchone()
        
        if existing_item:
            # 기존 아이템 수량 증가
            item_id, current_quantity = existing_item
            new_quantity = current_quantity + quantity
            cursor.execute('''
                UPDATE inventory SET quantity = ? WHERE id = ?
            ''', (new_quantity, item_id))
            result_id = item_id
        else:
            # 새 아이템 추가
            cursor.execute('''
                INSERT INTO inventory (player_id, item_name, item_type, quantity, description, value)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (player_id, item_name, item_type, quantity, description, value))
            result_id = cursor.lastrowid
        
        self.conn.commit()
        return result_id
    
    def get_inventory(self, player_id: int) -> List[Tuple]:
        #플레이어 인벤토리 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, item_name, item_type, quantity, description, value
            FROM inventory
            WHERE player_id = ? AND quantity > 0
            ORDER BY item_type, item_name
        ''', (player_id,))
        return cursor.fetchall()
    
    def get_item_by_type(self, player_id: int, item_type: str) -> List[Tuple]:
        #특정 타입의 아이템 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, item_name, item_type, quantity, description, value
            FROM inventory
            WHERE player_id = ? AND item_type = ? AND quantity > 0
            ORDER BY item_name
        ''', (player_id, item_type))
        return cursor.fetchall()
    
    def use_item(self, player_id: int, item_id: int, quantity_used: int) -> bool:
        #아이템 사용 (수량 차감)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT quantity FROM inventory WHERE id = ? AND player_id = ?
        ''', (item_id, player_id))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        current_quantity = result[0]
        if current_quantity < quantity_used:
            return False
        
        new_quantity = current_quantity - quantity_used
        
        if new_quantity <= 0:
            cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
        else:
            cursor.execute('''
                UPDATE inventory SET quantity = ? WHERE id = ?
            ''', (new_quantity, item_id))
        
        self.conn.commit()
        return True
    
    def add_story_event(self, player_id: int, event_type: str, description: str, location: str = "", turn_number: int = 0, reputation_change: int = 0, gold_change: int = 0):
        #스토리 이벤트 기록
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO story_events
            (player_id, event_type, event_description, location, turn_number, 
             reputation_change, gold_change)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, event_type, description, location, turn_number, 
              reputation_change, gold_change))
        self.conn.commit()

    def get_adventure_count(self, player_id: int) -> int:
        #모험 횟수 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM story_events 
            WHERE player_id = ? AND event_type = 'permanent_event'
        ''', (player_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def get_recent_events(self, player_id: int, limit: int = 5) -> List[Tuple]:
        #최근 이벤트 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT event_type, event_description, location, timestamp
            FROM story_events
            WHERE player_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (player_id, limit))
        return cursor.fetchall()
    
    def get_reputation_history(self, player_id: int, limit: int = 10) -> List[Tuple]:
        #명성 변화 기록 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT old_reputation, new_reputation, change_amount, reason, location, timestamp
            FROM reputation_changes
            WHERE player_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (player_id, limit))
        return cursor.fetchall()
    
    def record_shop_transaction(self, player_id: int, item_name: str, quantity: int, unit_price: int, total_price: int, transaction_type: str, location: str = ""):
        #상점 거래 기록
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO shop_transactions
            (player_id, item_name, quantity, unit_price, total_price, 
             transaction_type, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, item_name, quantity, unit_price, total_price, 
              transaction_type, location))
        self.conn.commit()

    def get_character_by_name(self, name: str) -> Optional[Tuple]:
        #이름으로 캐릭터 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, type, hp, max_hp, mp, max_mp, is_alive, class, reputation
            FROM main_story_characters
            WHERE name = ? AND is_in_party = 1
        ''', (name,))
        return cursor.fetchone()
    
    def get_healers(self) -> List[Tuple]:
        #파티 내 치유사 조회
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, hp, max_hp, mp, max_mp, class
            FROM main_story_characters
            WHERE is_in_party = 1 AND is_alive = 1
            AND (class LIKE '%성직자%' OR class LIKE '%priest%' OR class LIKE '%cleric%')
            AND mp >= 10
        ''')
        return cursor.fetchall()
    
    def backup_database(self, backup_path: str = None):
        #데이터베이스 백업
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{timestamp}.db"
        
        backup_conn = sqlite3.connect(backup_path)
        self.conn.backup(backup_conn)
        backup_conn.close()
        print(f"데이터베이스가 {backup_path}에 백업되었습니다.")
    
    def reset_database(self):
        #데이터베이스 초기화
        cursor = self.conn.cursor()
        
        # 모든 테이블 삭제
        cursor.execute("DROP TABLE IF EXISTS reputation_changes")
        cursor.execute("DROP TABLE IF EXISTS shop_transactions")
        cursor.execute("DROP TABLE IF EXISTS story_events")
        cursor.execute("DROP TABLE IF EXISTS inventory")
        cursor.execute("DROP TABLE IF EXISTS main_story_characters")
        
        self.conn.commit()
        
        # 테이블 재생성
        self._create_tables()
        print("데이터베이스가 초기화되었습니다.")
    
    def close(self):
        #데이터베이스 연결 종료
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        #소멸자
        self.close()



def reset_database(db_path: str = "main_story.db"):
    #새게임 시작을 위한 DB 초기화
    if os.path.exists(db_path):
        os.remove(db_path)
        print("기존 게임 데이터가 삭제되었습니다.")
    
    main_db = MainStoryDB(db_path)
    print("새로운 게임 데이터베이스가 생성되었습니다.")
    return main_db