#실행부
import os
import sys
import pickle
import json
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

# 모듈 imports
from models import Player, PlayerInitState
from database import MainStoryDB, reset_database
from game_graph import create_game_graph, visualize_game_graph
from game_nodes import GameNodes
from reputation_system import ReputationManager
from character_creation import show_character_creation_help


def setup_openai_api():
    #OpenAI API 키 설정
    # 환경변수에서 먼저 확인
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        print(f"✅ 환경변수에서 API 키를 찾았습니다: {api_key[:8]}...")
        return api_key
    
    # 환경변수에 없으면 사용자 입력 받기
    print("🔑 OpenAI API 키가 필요합니다.")
    print("💡 API 키는 https://platform.openai.com/api-keys 에서 발급받을 수 있습니다.")
    
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
            
            # 환경변수에 설정
            os.environ["OPENAI_API_KEY"] = api_key
            
            # 간단한 테스트 (선택사항)
            test_api = input("API 키를 테스트하시겠습니까? (y/n): ").lower()
            if test_api in ['y', 'yes', '예']:
                try:
                    from langchain_openai import ChatOpenAI
                    test_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
                    test_response = test_llm.invoke([{"role": "user", "content": "Hello"}])
                    print("✅ API 키 테스트 성공!")
                except Exception as e:
                    print(f"❌ API 키 테스트 실패: {e}")
                    continue
            
            print(f"✅ API 키가 설정되었습니다: {api_key[:8]}...")
            return api_key
            
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            continue


def save_game_state(state: PlayerInitState, filename: str = None):
    #게임 상태 저장
    try:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"savegame_{timestamp}.pkl"
        
        # 저장할 수 없는 객체들 제거
        save_state = {}
        for key, value in state.items():
            if key == "main_story_db":
                # DB 객체는 저장하지 않고 DB 파일 경로만 저장
                save_state["db_path"] = "main_story.db"
            elif key == "messages":
                # 메시지는 직렬화 가능한 형태로 변환
                serializable_messages = []
                for msg in value:
                    if isinstance(msg, HumanMessage):
                        serializable_messages.append({"type": "human", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        serializable_messages.append({"type": "ai", "content": msg.content})
                save_state[key] = serializable_messages
            else:
                save_state[key] = value
        
        # 데이터베이스 백업
        main_db = state.get("main_story_db")
        if main_db:
            db_backup_name = filename.replace(".pkl", "_db.db")
            main_db.backup_database(db_backup_name)
        
        # 상태 저장
        with open(filename, 'wb') as f:
            pickle.dump(save_state, f)
        
        print(f"✅ 게임이 저장되었습니다: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ 게임 저장 실패: {e}")
        return None


def load_game_state(filename: str) -> PlayerInitState:
    #게임 상태 로드
    try:
        if not os.path.exists(filename):
            print(f"❌ 저장 파일을 찾을 수 없습니다: {filename}")
            return None
        
        with open(filename, 'rb') as f:
            save_state = pickle.load(f)
        
        # DB 복원
        db_backup_name = filename.replace(".pkl", "_db.db")
        if os.path.exists(db_backup_name):
            # 기존 DB 파일 교체
            if os.path.exists("main_story.db"):
                os.remove("main_story.db")
            os.rename(db_backup_name, "main_story.db")
        
        # DB 객체 재생성
        main_db = MainStoryDB()
        save_state["main_story_db"] = main_db
        
        # 메시지 복원
        if "messages" in save_state:
            restored_messages = []
            for msg_data in save_state["messages"]:
                if msg_data["type"] == "human":
                    restored_messages.append(HumanMessage(content=msg_data["content"]))
                elif msg_data["type"] == "ai":
                    restored_messages.append(AIMessage(content=msg_data["content"]))
            save_state["messages"] = restored_messages
        
        print(f"✅ 게임이 로드되었습니다: {filename}")
        return save_state
        
    except Exception as e:
        print(f"❌ 게임 로드 실패: {e}")
        return None


def get_save_files():
    #저장 파일 목록 조회
    save_files = []
    for file in os.listdir("."):
        if file.startswith("savegame_") and file.endswith(".pkl"):
            try:
                # 파일 생성 시간 확인
                stat = os.stat(file)
                created_time = datetime.fromtimestamp(stat.st_ctime)
                
                # 파일 크기 확인
                file_size = stat.st_size
                size_str = f"{file_size:,} bytes"
                
                save_files.append({
                    "filename": file,
                    "created": created_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size": size_str
                })
            except:
                continue
    
    # 최신 파일 순으로 정렬
    save_files.sort(key=lambda x: x["created"], reverse=True)
    return save_files


def select_save_file():
    #저장 파일 선택
    save_files = get_save_files()
    
    if not save_files:
        print("💾 저장된 게임 파일이 없습니다.")
        return None
    
    print("\n💾 저장된 게임 파일 목록:")
    print("-" * 60)
    for i, save_file in enumerate(save_files, 1):
        print(f"{i}. {save_file['filename']}")
        print(f"   생성시간: {save_file['created']}")
        print(f"   파일크기: {save_file['size']}")
        print()
    
    while True:
        try:
            choice = input(f"로드할 파일을 선택하세요 (1-{len(save_files)}, 0: 취소): ").strip()
            
            if choice == "0":
                return None
            
            file_index = int(choice) - 1
            if 0 <= file_index < len(save_files):
                return save_files[file_index]["filename"]
            else:
                print(f"❌ 1-{len(save_files)} 사이의 숫자를 입력해주세요.")
                
        except ValueError:
            print("❌ 올바른 숫자를 입력해주세요.")
        except KeyboardInterrupt:
            print("\n취소되었습니다.")
            return None


def handle_inventory_flow(state: PlayerInitState) -> PlayerInitState:
    #인벤토리 플로우 처리
    print("[DEBUG] 인벤토리 플로우 시작")
    
    game_nodes = GameNodes()
    
    # 인벤토리 진입 전 상황 저장
    ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
    last_situation = ai_messages[-1].content if ai_messages else ""
    current_location = state.get("current_location", "알 수 없는 곳")
    current_gold = state.get("player_gold", 0)
    
    # 인벤토리 화면 표시
    state = game_nodes.inventory_node(state)
    
    # 인벤토리 화면 출력
    ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
    if ai_messages:
        print("\n🎭 GM:", ai_messages[-1].content)
    
    # 인벤토리 액션 루프
    while state.get("next_action") == "inventory_action":
        try:
            user_input = input("\n당신: ")
            
            if user_input.lower() in ['quit', '종료', 'exit']:
                print("게임을 종료합니다!")
                state["game_active"] = False
                break
            
            # 사용자 입력 추가
            state["messages"].append(HumanMessage(content=user_input))
            
            # 인벤토리 액션 처리
            state = game_nodes.inventory_action_node(state)
            next_action = state.get("next_action")
            
            if next_action == "use_potion":
                state = game_nodes.use_potion_node(state)
                state["next_action"] = "inventory_action"
            elif next_action == "use_heal":
                state = game_nodes.use_heal_node(state)
                state["next_action"] = "inventory_action"
            elif next_action == "wait_input":
                # 인벤토리 종료 - 이전 상황 복원
                restore_msg = f"""
📍 **{current_location}로 돌아왔습니다**

{last_situation}

💰 골드: {state.get('player_gold', current_gold)}
"""
                state["messages"].append(AIMessage(content=restore_msg))
                print(f"\n🎭 GM: {restore_msg}")
                break
            
            # 결과 메시지 출력
            ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                print("\n🎭 GM:", ai_messages[-1].content)
                
        except Exception as e:
            print(f"[ERROR] 인벤토리 플로우 오류: {e}")
            state["next_action"] = "wait_input"
            break
    
    print("[DEBUG] 인벤토리 플로우 종료")
    return state


def run_game(initial_state: PlayerInitState = None):
    #게임 실행 - 캐릭터 생성 시스템 포함
    print("🎮 명성 시스템 적용 RPG 게임 시작!")
    print("=" * 50)
    
    # 초기 상태 설정
    if initial_state:
        print("📁 저장된 게임을 이어서 진행합니다...")
        current_state = initial_state
    else:
        # 새 게임 시작 - 캐릭터 생성부터
        current_state = {
            "messages": [],
            "player": None,  # 캐릭터 생성에서 설정
            "companion_ids": [],
            "current_situation": "캐릭터 생성",
            "game_active": True,
            "main_story_db": None,
            "main_story_player_id": 0,
            "party_full": False,
            "current_location": "시작 지점",
            "current_objective": "새로운 모험 시작",
            "player_gold": 300,
            "reputation_changes": [],
            "next_action": "character_creation"
        }
    
    try:
        # 게임 노드 초기화
        game_nodes = GameNodes()
        
        # 새 게임인 경우 캐릭터 생성부터 시작
        if not initial_state:
            print("🎭 캐릭터 생성을 시작합니다...")
            
            # 캐릭터 생성 루프
            while current_state.get("next_action") == "character_creation":
                try:
                    current_state = game_nodes.character_creation_node(current_state)
                    
                    if current_state.get("next_action") == "character_creation":
                        # 마지막 AI 메시지 출력
                        ai_messages = [msg for msg in current_state["messages"] if isinstance(msg, AIMessage)]
                        if ai_messages:
                            print("\n🎭 GM:", ai_messages[-1].content)
                        
                        # 사용자 입력 받기
                        user_input = input("\n당신: ")
                        
                        if user_input.lower() in ['quit', '종료', 'exit']:
                            print("게임을 종료합니다!")
                            return
                        
                        current_state["messages"].append(HumanMessage(content=user_input))
                        
                except Exception as e:
                    print(f"[ERROR] 캐릭터 생성 오류: {e}")
                    continue
            
            # 캐릭터 생성 완료 후 메인 스토리 시작
            if current_state.get("next_action") == "main_story_start":
                current_state = game_nodes.main_story_start_node(current_state)
        
        # 게임 상태 출력
        print("\n🎭 GM:", current_state["messages"][-1].content)
        
        if not initial_state:
            print("\n" + "="*60)
            print("🌟 명성 시스템 적용 RPG 게임!")
            print("💡 새로운 기능:")
            print("  - 🎭 개성 있는 캐릭터 생성 시스템")
            print("  - 🗺️ 캐릭터에 맞는 동적 시작 지점 생성")
            print("  - ⭐ 명성에 따른 NPC 태도 변화")
            print("  - 💰 명성 기반 상점 가격 조정")
            print("  - 👥 명성별 동료 영입 난이도 차이")
            print("  - 📊 '명성 확인' → 현재 명성 상태 조회")
            print("💡 게임 관리:")
            print("  - 'save' 또는 '저장' → 게임 저장")
            print("  - 'load' 또는 '로드' → 게임 불러오기")
            print("💡 기존 기능:")
            print("  - '인벤토리' → 가방 확인 및 아이템 사용")
            print("  - '물약 구입' → 상점에서 아이템 구매")
            print("  - '숲을 탐험하고 싶어' → 자동 상황 생성")
            print("  - '누군가 만나고 싶어' → 동료 영입 기회")
            print("  - '위험한 곳에 가보자' → 전투 발생")
            print("  - '종료' → 게임 종료")
            print("="*60)
        
        # 메인 게임 루프
        while current_state.get("game_active", True):
            try:
                user_input = input("\n당신: ")
                
                # 게임 종료
                if user_input.lower() in ['quit', '종료', 'exit']:
                    save_choice = input("게임을 저장하시겠습니까? (y/n): ").lower()
                    if save_choice in ['y', 'yes', '예']:
                        save_game_state(current_state)
                    print("게임을 종료합니다!")
                    break
                
                # 게임 저장
                if user_input.lower() in ['save', '저장']:
                    filename = save_game_state(current_state)
                    if filename:
                        print("게임이 저장되었습니다. 계속 플레이하세요!")
                    continue
                
                # 게임 로드
                if user_input.lower() in ['load', '로드']:
                    selected_file = select_save_file()
                    if selected_file:
                        loaded_state = load_game_state(selected_file)
                        if loaded_state:
                            current_state = loaded_state
                            print("게임이 로드되었습니다. 계속 플레이하세요!")
                            
                            # 현재 상태 출력
                            ai_messages = [msg for msg in current_state["messages"] if isinstance(msg, AIMessage)]
                            if ai_messages:
                                print(f"\n🎭 GM: {ai_messages[-1].content}")
                                print(f"📍 현재 위치: {current_state.get('current_location', '알 수 없음')}")
                                print(f"💰 골드: {current_state.get('player_gold', 0)}")
                                
                                # 명성 상태 표시
                                reputation_manager = ReputationManager()
                                current_reputation = game_nodes._get_current_reputation(current_state)
                                reputation_status = reputation_manager.get_reputation_status_message(current_reputation)
                                print(f"⭐ {reputation_status}")
                    continue
                
                # 캐릭터 생성 도움말
                if user_input.lower() in ['help character', 'character help', '캐릭터 도움말']:
                    help_text = show_character_creation_help()
                    print(f"\n{help_text}")
                    continue
                
                # 사용자 입력을 상태에 추가
                current_state["messages"].append(HumanMessage(content=user_input))
                
                # 직접 노드 실행 방식
                try:
                    # 의도 분석
                    current_state = game_nodes.intent_analysis_node(current_state)
                    
                    # next_action에 따른 노드 실행
                    next_action = current_state.get("next_action")
                    print(f"[DEBUG] 다음 액션: {next_action}")
                    
                    if next_action == "story_continue":
                        current_state = game_nodes.story_continue_node(current_state)
                        
                    elif next_action == "battle":
                        current_state = game_nodes.battle_node(current_state)
                        # 전투 결과 출력
                        ai_messages = [msg for msg in current_state["messages"] if isinstance(msg, AIMessage)]
                        if ai_messages:
                            print("\n🎭 GM:", ai_messages[-1].content)
                            print(f"📍 현재 위치: {current_state.get('current_location', '알 수 없음')}")
                            print(f"💰 골드: {current_state.get('player_gold', 0)}")
                            
                            # 명성 상태 표시
                            reputation_manager = ReputationManager()
                            current_reputation = game_nodes._get_current_reputation(current_state)
                            reputation_status = reputation_manager.get_reputation_status_message(current_reputation)
                            print(f"⭐ {reputation_status}")
                        
                        # 아이템 보상 처리
                        if current_state.get("next_action") == "item_reward":
                            current_state = game_nodes.item_reward_node(current_state)
                            
                    elif next_action == "shop_purchase":
                        current_state = game_nodes.shop_purchase_node(current_state)
                        
                    elif next_action == "inventory":
                        current_state = handle_inventory_flow(current_state)
                        continue
                        
                    elif next_action == "reputation_check":
                        current_state = game_nodes.reputation_check_node(current_state)
                        
                    elif next_action == "item_reward":
                        current_state = game_nodes.item_reward_node(current_state)
                        
                    elif next_action == "companion_opportunity":
                        current_state = game_nodes.companion_opportunity_node(current_state)
                        
                        # 동료 영입 기회 후 사용자 응답 대기
                        if current_state.get("next_action") == "companion_decision":
                            ai_messages = [msg for msg in current_state["messages"] if isinstance(msg, AIMessage)]
                            if ai_messages:
                                print("\n🎭 GM:", ai_messages[-1].content)
                            
                            # 사용자 응답 받기
                            companion_response = input("\n당신: ")
                            if companion_response.lower() in ['quit', '종료', 'exit']:
                                save_choice = input("게임을 저장하시겠습니까? (y/n): ").lower()
                                if save_choice in ['y', 'yes', '예']:
                                    save_game_state(current_state)
                                print("게임을 종료합니다!")
                                break
                            
                            current_state["messages"].append(HumanMessage(content=companion_response))
                            
                            # 결정 처리
                            current_state = game_nodes.companion_decision_node(current_state)
                            companion_decision = current_state.get("next_action")
                            
                            if companion_decision == "companion_accept":
                                current_state = game_nodes.companion_accept_node(current_state)
                            elif companion_decision == "companion_reject":
                                current_state = game_nodes.companion_reject_node(current_state)
                            
                            # 결과 출력
                            ai_messages = [msg for msg in current_state["messages"] if isinstance(msg, AIMessage)]
                            if ai_messages:
                                print("\n🎭 GM:", ai_messages[-1].content)
                                print(f"📍 현재 위치: {current_state.get('current_location', '알 수 없음')}")
                                print(f"💰 골드: {current_state.get('player_gold', 0)}")
                                
                                # 명성 상태 표시
                                reputation_manager = ReputationManager()
                                current_reputation = game_nodes._get_current_reputation(current_state)
                                reputation_status = reputation_manager.get_reputation_status_message(current_reputation)
                                print(f"⭐ {reputation_status}")
                            continue
                    
                    # 마지막 AI 메시지 출력 (companion_opportunity가 아닌 경우)
                    if next_action != "companion_opportunity":
                        ai_messages = [msg for msg in current_state["messages"] if isinstance(msg, AIMessage)]
                        if ai_messages and len(ai_messages) >= 2:
                            print("\n🎭 GM:", ai_messages[-1].content)
                            print(f"📍 현재 위치: {current_state.get('current_location', '알 수 없음')}")
                            print(f"💰 골드: {current_state.get('player_gold', 0)}")
                            
                            # 명성 상태 표시
                            reputation_manager = ReputationManager()
                            current_reputation = game_nodes._get_current_reputation(current_state)
                            reputation_status = reputation_manager.get_reputation_status_message(current_reputation)
                            print(f"⭐ {reputation_status}")
                
                except Exception as e:
                    print(f"\n❌ 실행 오류: {e}")
                    print("기본 스토리로 진행합니다...")
                    print("\n🎭 GM: 모험이 계속됩니다. 어떻게 하시겠어요?")
                    
            except Exception as e:
                print(f"\n❌ 게임 루프 오류: {e}")
                print("게임을 계속 진행합니다...")
                
    except KeyboardInterrupt:
        print("\n\n게임이 중단되었습니다.")
        save_choice = input("게임을 저장하시겠습니까? (y/n): ").lower()
        if save_choice in ['y', 'yes', '예']:
            save_game_state(current_state)
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        print("게임을 종료합니다.")
    finally:
        # 데이터베이스 정리
        if current_state.get("main_story_db"):
            current_state["main_story_db"].close()


def main():
    #메인 함수
    print("=== 🎮 명성 시스템 적용 LangGraph RPG ===")
    print("📍 GitHub 포트폴리오용 모듈화 버전")
    print("⭐ 명성 시스템으로 더욱 몰입감 있는 RPG 경험!")
    print("💾 저장/로드 기능으로 언제든지 게임 중단 가능!")
    print()
    
    # OpenAI API 키 설정
    api_key = setup_openai_api()
    if not api_key:
        print("❌ API 키가 설정되지 않았습니다. 프로그램을 종료합니다.")
        return
    
    print("\n게임 옵션을 선택하세요:")
    print("1. 새게임 시작")
    print("2. 저장된 게임 이어하기")
    print("3. 그래프 구조 시각화")
    print("4. 시스템 정보")
    print("5. 저장 파일 관리")
    print("6. 종료")
    
    while True:
        try:
            choice = input("\n선택 (1-6): ").strip()
            
            if choice == "1":
                print("\n🆕 새게임을 시작합니다...")
                print("⚠️ 기존 게임 데이터가 모두 삭제됩니다.")
                confirm = input("계속하시겠습니까? (y/n): ").lower()
                
                if confirm in ['y', 'yes', '예', '']:
                    print("\n🔧 시스템 기능:")
                    print("✅ 명성 시스템 - NPC 태도 변화")
                    print("✅ 동적 가격 조정 시스템")
                    print("✅ 명성 기반 동료 영입")
                    print("✅ 전투 시스템")
                    print("✅ 인벤토리 관리")
                    print("✅ 상점 시스템")
                    print("✅ 아이템 보상 시스템")
                    print("✅ 저장/로드 시스템")
                    print("✅ 모듈화된 코드 구조")
                    print("\n🎮 자연스럽게 대화하듯 게임을 즐기세요!")
                    print("💡 게임 중 'save' 또는 '저장'으로 언제든지 저장 가능!")
                    
                    # 데이터베이스 초기화
                    reset_database()
                    
                    # 게임 시작
                    run_game()
                    break
                else:
                    print("게임 시작이 취소되었습니다.")
                    continue
                    
            elif choice == "2":
                print("\n💾 저장된 게임 이어하기...")
                selected_file = select_save_file()
                if selected_file:
                    loaded_state = load_game_state(selected_file)
                    if loaded_state:
                        print("\n🎮 게임을 이어서 진행합니다!")
                        print("💡 게임 중 'save' 또는 '저장'으로 언제든지 저장 가능!")
                        run_game(loaded_state)
                        break
                    else:
                        print("게임 로드에 실패했습니다.")
                        continue
                else:
                    print("게임 로드가 취소되었습니다.")
                    continue
                    
            elif choice == "3":
                print("\n📊 그래프 구조 시각화...")
                visualize_game_graph()
                continue
                
            elif choice == "4":
                print("\n💻 시스템 정보:")
                print("- 언어: Python")
                print("- 프레임워크: LangGraph, LangChain")
                print("- AI 모델: GPT-4o-mini")
                print("- 데이터베이스: SQLite")
                print("- 아키텍처: 모듈화된 객체지향 설계")
                print("- 주요 기능: 명성 시스템, 동적 스토리, 전투, 인벤토리, 저장/로드")
                print("\n📁 모듈 구조:")
                print("1. models.py - 데이터 모델")
                print("2. reputation_system.py - 명성 시스템")
                print("3. database.py - 데이터베이스 관리")
                print("4. story_manager.py - 스토리 관리")
                print("5. battle_system.py - 전투 시스템")
                print("6. inventory_system.py - 인벤토리/상점")
                print("7. character_creation.py - 캐릭터 생성")
                print("8. game_nodes.py - 게임 노드")
                print("9. game_graph.py - 워크플로우")
                print("10. main.py - 메인 실행")
                continue
                
            elif choice == "5":
                print("\n💾 저장 파일 관리...")
                save_files = get_save_files()
                if not save_files:
                    print("저장된 파일이 없습니다.")
                    continue
                
                print(f"총 {len(save_files)}개의 저장 파일이 있습니다:")
                for i, save_file in enumerate(save_files, 1):
                    print(f"{i}. {save_file['filename']} ({save_file['created']}, {save_file['size']})")
                
                manage_choice = input("\n작업을 선택하세요 (1: 삭제, 2: 상세정보, 0: 돌아가기): ").strip()
                
                if manage_choice == "1":
                    try:
                        file_num = int(input("삭제할 파일 번호: ")) - 1
                        if 0 <= file_num < len(save_files):
                            filename = save_files[file_num]["filename"]
                            confirm = input(f"'{filename}'을 삭제하시겠습니까? (y/n): ").lower()
                            if confirm in ['y', 'yes', '예']:
                                os.remove(filename)
                                # DB 백업 파일도 삭제
                                db_file = filename.replace(".pkl", "_db.db")
                                if os.path.exists(db_file):
                                    os.remove(db_file)
                                print("파일이 삭제되었습니다.")
                        else:
                            print("잘못된 파일 번호입니다.")
                    except ValueError:
                        print("올바른 숫자를 입력해주세요.")
                
                elif manage_choice == "2":
                    try:
                        file_num = int(input("정보를 볼 파일 번호: ")) - 1
                        if 0 <= file_num < len(save_files):
                            filename = save_files[file_num]["filename"]
                            # 저장 파일 정보 로드
                            with open(filename, 'rb') as f:
                                save_data = pickle.load(f)
                            
                            print(f"\n📄 {filename} 상세 정보:")
                            print(f"생성시간: {save_files[file_num]['created']}")
                            print(f"파일크기: {save_files[file_num]['size']}")
                            print(f"플레이어: {save_data.get('player', {}).get('name', 'N/A')}")
                            print(f"현재 위치: {save_data.get('current_location', 'N/A')}")
                            print(f"골드: {save_data.get('player_gold', 0)}")
                            print(f"동료 수: {len(save_data.get('companion_ids', []))}")
                            print(f"메시지 수: {len(save_data.get('messages', []))}")
                        else:
                            print("잘못된 파일 번호입니다.")
                    except ValueError:
                        print("올바른 숫자를 입력해주세요.")
                    except Exception as e:
                        print(f"파일 정보 로드 실패: {e}")
                
                continue
                
            elif choice == "6":
                print("게임을 종료합니다. 감사합니다! 🎮")
                break
                
            else:
                print("잘못된 선택입니다. 1-6 중에서 선택해주세요.")
                continue
                
        except KeyboardInterrupt:
            print("\n\n게임이 중단되었습니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            print("다시 시도해주세요.")
            continue


if __name__ == "__main__":
    main()