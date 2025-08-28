#Langgraph 연결 노드 선언 및 그래프 엣지 생성
from langgraph.graph import START, END, StateGraph
from models import PlayerInitState
from game_nodes import GameNodes


class GameGraph:
    #게임 그래프 관리 클래스
    
    def __init__(self):
        self.game_nodes = GameNodes()
    
    def create_game_workflow(self) -> StateGraph:
        #게임 워크플로우 생성
        
        def route_by_next_action(state):
            #next_action 기반 라우팅 노드
            next_action = state.get("next_action", "wait_input")
            
            action_mapping = {
                "analyze_intent": "intent_analysis",
                "character_creation": "character_creation",  # 캐릭터 생성 추가
                "main_story_start": "main_story_start",      # 메인 스토리 시작 추가
                "battle": "battle",
                "companion_opportunity": "companion_opportunity",
                "companion_decision": "companion_decision",
                "companion_accept": "companion_accept",
                "companion_reject": "companion_reject",
                "companion_list": "companion_list",         # 동료 목록 추가
                "companion_dismiss": "companion_dismiss",   # 동료 탈퇴 추가
                "companion_dismiss_decision": "companion_dismiss_decision",  # 탈퇴 결정 추가
                "story_continue": "story_continue",
                "inventory": "inventory",
                "inventory_action": "inventory_action",
                "use_potion": "use_potion",
                "use_heal": "use_heal",
                "item_reward": "item_reward",
                "shop_purchase": "shop_purchase",
                "reputation_check": "reputation_check",
                "wait_input": "user_input"
            }
            
            return action_mapping.get(next_action, "user_input")
        
        def always_to_user_input(state):
            #항상 user_input으로 복귀
            return "user_input"
        
        # 워크플로우 생성
        workflow = StateGraph(PlayerInitState)
        
        # 기존 노드들
        workflow.add_node("character_creation", self.game_nodes.character_creation_node)
        workflow.add_node("main_story_start", self.game_nodes.main_story_start_node)
        workflow.add_node("user_input", self.game_nodes.user_input_node)
        workflow.add_node("intent_analysis", self.game_nodes.intent_analysis_node)
        workflow.add_node("story_continue", self.game_nodes.story_continue_node)
        workflow.add_node("battle", self.game_nodes.battle_node)
        
        # 동료 관리 노드들 (기존 + 새로 추가)
        workflow.add_node("companion_opportunity", self.game_nodes.companion_opportunity_node)
        workflow.add_node("companion_decision", self.game_nodes.companion_decision_node)
        workflow.add_node("companion_accept", self.game_nodes.companion_accept_node)
        workflow.add_node("companion_reject", self.game_nodes.companion_reject_node)
        workflow.add_node("companion_list", self.game_nodes.companion_list_node)           # 새로 추가
        workflow.add_node("companion_dismiss", self.game_nodes.companion_dismiss_node)     # 새로 추가
        workflow.add_node("companion_dismiss_decision", self.game_nodes.companion_dismiss_decision_node)  # 새로 추가
        
        # 인벤토리 및 기타 노드들
        workflow.add_node("inventory", self.game_nodes.inventory_node)
        workflow.add_node("inventory_action", self.game_nodes.inventory_action_node)
        workflow.add_node("use_potion", self.game_nodes.use_potion_node)
        workflow.add_node("use_heal", self.game_nodes.use_heal_node)
        workflow.add_node("item_reward", self.game_nodes.item_reward_node)
        workflow.add_node("shop_purchase", self.game_nodes.shop_purchase_node)
        workflow.add_node("reputation_check", self.game_nodes.reputation_check_node)
        
        # 시작점 연결 (캐릭터 생성부터)
        workflow.add_edge(START, "character_creation")
        
        # 캐릭터 생성 → 메인 스토리 시작 → 사용자 입력
        workflow.add_conditional_edges(
            "character_creation",
            route_by_next_action,
            {
                "character_creation": "character_creation",  # 생성 중이면 계속
                "main_story_start": "main_story_start"       # 완료되면 스토리 시작
            }
        )
        
        workflow.add_edge("main_story_start", "user_input")
        
        # 사용자 입력 후 의도 분석
        workflow.add_edge("user_input", "intent_analysis")
        
        # intent_analysis에서 상황별 분기 (새 노드들 추가)
        workflow.add_conditional_edges(
            "intent_analysis",
            route_by_next_action,
            {
                "story_continue": "story_continue",
                "battle": "battle",
                "companion_opportunity": "companion_opportunity",
                "companion_list": "companion_list",           # 동료 목록
                "companion_dismiss": "companion_dismiss",     # 동료 탈퇴
                "inventory": "inventory",
                "item_reward": "item_reward",
                "shop_purchase": "shop_purchase",
                "reputation_check": "reputation_check"
            }
        )
        
        # 동료 영입 플로우 (기존)
        workflow.add_edge("companion_opportunity", "companion_decision")
        workflow.add_conditional_edges(
            "companion_decision",
            route_by_next_action,
            {
                "companion_accept": "companion_accept",
                "companion_reject": "companion_reject"
            }
        )
        
        # 동료 탈퇴 플로우 (새로 추가)
        workflow.add_edge("companion_dismiss", "companion_dismiss_decision")
        workflow.add_conditional_edges(
            "companion_dismiss_decision",
            route_by_next_action,
            {
                "companion_dismiss_decision": "companion_dismiss_decision",  # 계속 선택 중
                "user_input": "user_input"                                  # 완료 또는 취소
            }
        )
        
        # 인벤토리 관련 플로우
        workflow.add_edge("inventory", "inventory_action")
        workflow.add_conditional_edges(
            "inventory_action",
            route_by_next_action,
            {
                "use_potion": "use_potion",
                "use_heal": "use_heal",
                "user_input": "user_input"
            }
        )
        
        # 물약/힐 사용 후 인벤토리 액션으로 복귀
        workflow.add_edge("use_potion", "inventory_action")
        workflow.add_edge("use_heal", "inventory_action")
        
        # 전투 후 아이템 보상
        workflow.add_edge("battle", "item_reward")
        
        # 대부분의 노드에서 user_input으로 복귀 (새 노드들 추가)
        for node in ["story_continue", "companion_accept", "companion_reject", 
                     "companion_list", "item_reward", "shop_purchase", "reputation_check"]:
            workflow.add_conditional_edges(
                node,
                always_to_user_input,
                {"user_input": "user_input"}
            )
        
        return workflow.compile()
    
    def visualize_graph(self):
        #그래프 시각화
        workflow = self.create_game_workflow()
        mermaid_code = workflow.get_graph().draw_mermaid()
            
        print("=== Mermaid Graph Code ===")
        print(mermaid_code)
        print("\n=== 시각화 방법 ===")
        print("1. 위 코드를 복사")
        print("2. https://mermaid.live 접속")
        print("3. 코드 붙여넣기")
            
        return mermaid_code


def create_game_graph():
    #게임 그래프 생성 (외부 호출용)
    game_graph = GameGraph()
    return game_graph.create_game_workflow()


def visualize_game_graph():
    #게임 그래프 시각화 (외부 호출용)
    game_graph = GameGraph()
    return game_graph.visualize_graph()