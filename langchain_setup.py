from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import os
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    user_prompt: str
    generated_code: Annotated[str, lambda x, _: x]
    execution_result: dict
    error_context: str
    retry_count: int

class ManimAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.1,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("generate", self.generate_code)
        workflow.add_node("execute", self.execute_code)
        workflow.add_node("correct", self.correct_code)

        workflow.set_entry_point("generate")
        workflow.add_edge("generate", "execute")
        workflow.add_conditional_edges(
            "execute",
            self.decide_next_step,
            {
                "retry": "correct",
                "success": END,
                "failure": END
            }
        )
        workflow.add_edge("correct", "generate")
        
        return workflow.compile()
    
    def generate_code(self, state: AgentState):
        system_prompt = f"""You are a Manim animation expert. Your task is to create engaging mathematical animations based on user prompts. Follow these guidelines:

1. Code Requirements:
   - Use Manim Community Edition syntax (v0.18.0+)
   - Class name must be AnimationScene
   - Animation duration: 10-15 seconds total
   - Include appropriate self.wait() calls between animations
   - Add descriptive comments in the code

2. Animation Best Practices:
   - Use simple colors: BLUE, RED, GREEN, YELLOW
   - Add smooth transitions between animations
   - Include transformations (rotate, scale, shift)
   - Use run_time parameter to control animation speed

3. Example Animation:
```python
from manim import *

class AnimationScene(Scene):
    def construct(self):
        # Create initial shape
        square = Square(side_length=2)
        square.set_color(BLUE)
        
        # Animate creation
        self.play(Create(square), run_time=1)
        self.wait(0.5)
        
        # Transform to circle
        circle = Circle(radius=1)
        circle.set_color(RED)
        self.play(Transform(square, circle), run_time=2)
        self.wait(1)
        
        # Add rotation
        self.play(circle.animate.rotate(PI), run_time=2)
        self.wait(1)
```

Previous error (if any): {state.get('error_context', 'None')}

Generate code that follows these patterns and matches the user's request exactly. Make sure to:
1. Use descriptive variable names
2. Add comments explaining each step
3. Include appropriate wait times between animations
4. Use smooth transitions and transformations
5. Set colors using set_color() method
6. Keep animations simple and focused"""

        response = self.llm.invoke([
            ("system", system_prompt),
            ("user", state["user_prompt"])
        ])
        
        return {
            **state, 
            "generated_code": response.content,
            "retry_count": state.get("retry_count", 0) + 1
        }

    def execute_code(self, state: AgentState):
        from run_manim import run_manim_code
        result = run_manim_code(state["generated_code"])
        return {**state, "execution_result": result}

    def correct_code(self, state: AgentState):
        error = state["execution_result"].get("error", "")
        return {**state, "error_context": error}

    def decide_next_step(self, state: AgentState):
        if state["execution_result"]["success"]:
            return "success"
        elif state["retry_count"] < 3:
            return "retry"
        else:
            return "failure"

manim_agent = ManimAgent()
