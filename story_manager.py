#스토리 컨텍스트 관리모듈
# 스토리 연속성 강화 및 데이터 저장

from typing import Dict, List, Optional, Any
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from models import StoryContext, ReputationLevel
from reputation_system import ReputationManager
import json

class StoryManager:
    #스토리 컨텍스트 관리 클래스
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.reputation_manager = ReputationManager()
    
    def create_story_context(self, state: Dict) -> StoryContext:
        #스토리 컨텍스트 생성 
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        # DB나 player_id가 없으면 예외 발생 (게임이 제대로 초기화되지 않은 상태)
        if not main_db or not player_id:
            print(f"게임 초기화 오류 - DB: {main_db}, player_id: {player_id}")
            raise ValueError("게임이 제대로 초기화되지 않았습니다. 캐릭터 생성부터 다시 시작해주세요.")
        
        # 플레이어 데이터 조회
        player_data = main_db.get_character(player_id)
        if not player_data:
            print(f"플레이어 데이터 없음 - player_id: {player_id}")
            raise ValueError(f"플레이어 데이터를 찾을 수 없습니다. 새게임을 시작해주세요.")
        
        player_info = f"{player_data['name']} (레벨 {player_data['level']}, 명성 {player_data['reputation']})"
        
        # 파티 현황 (DB - 영구 저장)
        party_status = main_db.get_party_status()
        party_members = []
        
        for char in party_status:
            char_id, name, char_type, hp, max_hp, mp, max_mp, is_alive, relationship, reputation, gold = char
            if char_type != 'player':  # 플레이어 제외
                status = "생존" if is_alive else "위험"
                party_members.append(f"{name} (HP: {hp}/{max_hp}, 상태: {status})")
        
        # 동료가 없으면 혼자 모험 중
        if not party_members:
            party_members = ["혼자 모험 중"]
        
        # 세션별 데이터 (메모리에서 - 매번 새로움)
        current_location = state.get("current_location", "알 수 없는 곳")
        current_objective = state.get("current_objective", "새로운 모험 시작")
        
        # 이번 세션의 이벤트들 (메모리)
        recent_events = []
        messages = state.get("messages", [])
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
        
        for msg in ai_messages[-3:]:  # 최근 3개만
            content = msg.content
            if any(keyword in content for keyword in ["도착", "발견", "만남", "전투", "획득"]):
                recent_events.append(content[:100] + "...")
        
        # 장기적 성장 지표 (DB에서)
        total_adventures = main_db.get_adventure_count(player_id)
        session_turn_count = len(messages)
        
        # 명성 레벨
        reputation_level = self.reputation_manager.get_reputation_level(player_data['reputation'])
        
        return StoryContext(
            player_info=player_info,
            party_members=party_members,
            current_location=current_location,
            current_objective=current_objective,
            recent_events=recent_events,
            session_turn_count=session_turn_count,
            total_adventures=total_adventures,
            reputation_level=reputation_level
        )
    
    def update_story_context(self, state: Dict, new_location: str = None, 
                           new_objective: str = None, important_event: str = None,
                           reputation_change: int = 0, reputation_reason: str = "") -> Dict:
        #컨텍스트 업데이트 
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        # 메모리 업데이트 (항상)
        if new_location:
            state["current_location"] = new_location
        if new_objective:
            state["current_objective"] = new_objective
        
        # 명성 변화 처리
        if reputation_change != 0 and main_db and player_id:
            try:
                new_reputation = main_db.update_reputation(
                    player_id, reputation_change, reputation_reason, 
                    new_location or state.get("current_location", "알 수 없음")
                )
                
                # 명성 변화 기록을 상태에 추가
                if "reputation_changes" not in state:
                    state["reputation_changes"] = []
                
                state["reputation_changes"].append({
                    "change": reputation_change,
                    "reason": reputation_reason,
                    "new_reputation": new_reputation,
                    "location": new_location or state.get("current_location", "알 수 없음")
                })
            except Exception as e:
                print(f"명성 업데이트 실패: {e}")
        
        # 중요한 이벤트만 영구 저장
        if main_db and player_id and important_event:
            # 정말 중요한 이벤트만 영구 저장
            permanent_keywords = ["동료 영입", "동료 탈퇴", "보스 처치", "레벨업", "퀘스트 완료"]
            if any(keyword in important_event for keyword in permanent_keywords):
                try:
                    current_location = new_location or state.get("current_location", "알 수 없음")
                    turn_count = len(state.get("messages", []))
                    
                    main_db.add_story_event(
                        player_id,
                        "permanent_event",
                        important_event,
                        current_location,
                        turn_count,
                        reputation_change,
                        0  # gold_change
                    )
                    print(f"영구 이벤트 기록: {important_event}")
                except Exception as e:
                    print(f"이벤트 저장 실패: {e}")
        
        return state
    
    def extract_main_objective(self, first_ai_message: str) -> str:
        #초기 스토리에서 주요 목표 추출
        if not first_ai_message:
            return "모험 진행"
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="""
                다음 스토리에서 주요 목표나 임무를 1-2개 단어로 추출하세요.
                
                예시:
                - "빛의 성물을 되찾아라" → "빛의 성물"
                - "드래곤을 물리쳐라" → "드래곤 처치"
                - "공주를 구해라" → "공주 구출"
                - "보물을 찾아라" → "보물 탐색"
                
                목표만 간단히 답하세요. 설명 없이 목표만.
                """),
                HumanMessage(content=f"스토리: {first_ai_message}")
            ])
            
            extracted_goal = response.content.strip()
            if extracted_goal and len(extracted_goal) < 50:
                return extracted_goal
            return "모험 진행"
            
        except Exception as e:
            print(f"목표 추출 오류: {e}")
            return "모험 진행"
    
    def extract_main_objectives(self, first_ai_message: str) -> List[str]:
        #초기 스토리에서 주요 목표 키워드들 추출
        if not first_ai_message:
            return ["모험 진행"]
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="""
                다음 스토리에서 주요 목표나 키워드들을 찾아서 쉼표로 구분해서 나열하세요.
                
                예시:
                - "빛의 결정을 찾아 어둠의 군주를 물리쳐라" → "빛의 결정, 어둠의 군주"
                - "왕을 구하고 반역자를 처벌하라" → "왕 구출, 반역자 처벌"
                
                주요 목표 키워드들만 간단히 답하세요.
                """),
                HumanMessage(content=f"스토리: {first_ai_message}")
            ])
            
            extracted_objectives = response.content.strip()
            if extracted_objectives:
                return [obj.strip() for obj in extracted_objectives.split(',')]
            return ["모험 진행"]
            
        except Exception as e:
            print(f"목표 키워드 추출 오류: {e}")
            return ["모험 진행"]
    
    def get_story_summary(self, state: Dict, limit: int = 3) -> str:
        """스토리 요약 생성"""
        try:
            context = self.create_story_context(state)
            
            summary_parts = []
            
            # 기본 정보
            summary_parts.append(f"🎭 {context['player_info']}")
            summary_parts.append(f"📍 현재 위치: {context['current_location']}")
            summary_parts.append(f"🎯 목표: {context['current_objective']}")
            
            # 파티 정보
            if context['party_members'] and context['party_members'] != ["혼자 모험 중"]:
                summary_parts.append(f"👥 파티: {', '.join(context['party_members'])}")
            
            # 최근 사건
            if context['recent_events']:
                summary_parts.append(f"📜 최근 사건: {', '.join(context['recent_events'][:limit])}")
            
            # 명성 정보
            reputation_status = self.reputation_manager.get_reputation_status_message(
                self._get_current_reputation(state)
            )
            summary_parts.append(f"⭐ {reputation_status}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            print(f"스토리 요약 생성 오류: {e}")

    def _get_current_reputation(self, state: Dict) -> int:
        #현재 명성 조회
        main_db = state.get("main_story_db")
        player_id = state.get("main_story_player_id")
        
        if main_db and player_id:
            player_data = main_db.get_character(player_id)
            if player_data:
                return player_data['reputation']
        
        return 0
    
    def generate_situation_appropriate_content(self, state: Dict, situation_type: str, user_input: str = "") -> str:
        #상황에 맞는 컨텐츠 생성
        context = self.create_story_context(state)
        current_reputation = self._get_current_reputation(state)
        
        # 명성에 따른 세계의 반응
        reputation_response = self.reputation_manager.get_reputation_response(
            current_reputation, "세계", context['current_location']
        )
        
        sys_prompt = f"""
        현재 상황에 맞는 스토리를 생성해주세요.
        
        === 스토리 컨텍스트 ===
        {self.get_story_summary(state)}
        
        === 명성 정보 ===
        현재 명성: {current_reputation}
        명성 레벨: {reputation_response.level.value}
        세계의 태도: {reputation_response.tone}
        
        === 상황 타입 ===
        {situation_type}
        
        === 사용자 입력 ===
        {user_input}
        
        **지침:**
        1. 명성에 따른 세계의 반응을 자연스럽게 포함
        2. 이전 컨텍스트와 일관성 유지
        3. 상황 타입에 맞는 적절한 전개
        4. 250-300자 내외로 작성
        5. "어떻게 하시겠어요?"로 마무리
        
        명성이 높을수록 더 호의적인 반응을, 낮을수록 더 적대적인 반응을 보이도록 하세요.
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"상황: {situation_type}")
            ])
            
            return response.content
            
        except Exception as e:
            print(f"상황별 컨텐츠 생성 오류: {e}")
            return f"모험이 계속됩니다. 어떻게 하시겠어요?"
        
    def check_reputation_impact(self, state: Dict, action: str) -> Dict:
        #행동이 명성에 미치는 영향 분석
        current_reputation = self._get_current_reputation(state)
        reputation_change = self.reputation_manager.calculate_reputation_change(action)
        
        if reputation_change != 0:
            old_level = self.reputation_manager.get_reputation_level(current_reputation)
            new_level = self.reputation_manager.get_reputation_level(current_reputation + reputation_change)
            
            return {
                "has_change": True,
                "change": reputation_change,
                "old_level": old_level,
                "new_level": new_level,
                "level_changed": old_level != new_level,
                "action": action
            }
        
        return {"has_change": False}