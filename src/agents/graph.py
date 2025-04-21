from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, ToolMessage, AIMessage, SystemMessage
from langchain_aws import ChatBedrock
from langgraph.checkpoint.memory import InMemorySaver

from .state import AgentState
from .tools.qdrant import search_local_aws_docs

import json
import re
from typing import Literal, List


def should_continue(state: AgentState) -> Literal["continue", "end"]:
    last_message: BaseMessage = state["messages"][-1]

    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        print("--- Agent decided to END ---")
        return "end"

    else:
        print("--- Agent decided to CONTINUE with tools---")
        return "continue"


def call_model(state: AgentState, config: RunnableConfig):
    print("--- Calling Bedrock Model ---")
    model = ChatBedrock(
        model_id="amazon.nova-micro-v1:0",
    )
    model_with_tools = model.bind_tools([search_local_aws_docs])

    system_prompt = """You are an expert AWS assistant. Your goal is to answer user questions about AWS services accurately.
You have access to a tool that searches locally stored AWS documentation PDFs. Use this tool ('search_local_aws_docs') when the user asks specific questions about AWS features, configuration, or procedures that might be detailed in documentation.
When you use the tool, clearly state that you are searching the local documents and summarize the findings from the tool's output in your response.
If the tool returns 'No relevant documents found', inform the user you couldn't find the information in the local store.
If you don't know the answer and the tool doesn't help, say so clearly. Do not make up information.
Keep your answers focused on the user's question.
"""

    messages = state["messages"]

    messages_with_prompt = [SystemMessage(content=system_prompt)] + messages

    response = model_with_tools.invoke(messages_with_prompt, config=config)

    if hasattr(response, "content"):
        if isinstance(response.content, list):
            content = " ".join(str(item) for item in response.content)
        else:
            content = str(response.content)

        pattern = r"<thinking>.*?</thinking>\s*"
        response.content = re.sub(pattern, "", content, flags=re.DOTALL).strip()

    print(f"--- Bedrock Model Response --- \n{response.content}")
    if response.tool_calls:
        print(f"Tool Calls: {response.tool_calls}")

    return {"messages": [response]}


def call_tools(state: AgentState) -> dict[str, List[ToolMessage]]:
    print("--- Calling Tools ---")

    last_message: BaseMessage = state["messages"][-1]

    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        raise ValueError("Last message is not an AIMessage with tool calls.")

    tool_messages: List[ToolMessage] = []

    available_tools = {search_local_aws_docs.name: search_local_aws_docs}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get("name")

        if tool_name not in available_tools:
            print(f"Warning: Tool '{tool_name}' called by LLM but not available.")

            tool_messages.append(
                ToolMessage(
                    content=f"Error: Tool '{tool_name}' not found.",
                    tool_call_id=tool_call["id"],
                )
            )
            continue

        selected_tool = available_tools[tool_name]
        tool_input_args = tool_call.get("args", {})

        try:
            print(f"Executing tool: {tool_name} with args: {tool_input_args}")
            tool_output = selected_tool.invoke(tool_input_args)

            if not isinstance(tool_output, str):
                tool_output = json.dumps(tool_output)

            tool_messages.append(
                ToolMessage(content=tool_output, tool_call_id=tool_call["id"])
            )

        except Exception as e:
            print(f"Error executing tool {tool_name}: {e}")
            tool_messages.append(
                ToolMessage(
                    content=f"Error executing tool {tool_name}: {str(e)}",
                    tool_call_id=tool_call["id"],
                )
            )

    print(f"--- Tools Results --- \n{tool_messages}")

    return {"messages": tool_messages}


workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END,
    },
)

workflow.add_edge("tools", "agent")

checkpointer = InMemorySaver()

aws_agent_graph = workflow.compile(checkpointer=checkpointer)

print(f"langgraph mermaid diagram: \n{aws_agent_graph.get_graph().draw_mermaid()}")

print("AWS Agent Graph Compiled!")
