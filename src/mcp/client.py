from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
from langchain_aws import ChatBedrock
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from typing import List, Dict, Any, Optional
from loguru import logger
import traceback
import re


class MCPChatClient:
    def __init__(self):
        self.mcp_servers = {
            "awslabs.core": {
                "command": "uvx",
                "args": ["awslabs.core-mcp-server@latest"],
                "env": {"FASTMCP_LOG_LEVEL": "ERROR"},
                "transport": "stdio",
            },
            "awslabs.aws-docs": {
                "command": "uvx",
                "args": ["awslabs.aws-documentation-mcp-server@latest"],
                "env": {"FASTMCP_LOG_LEVEL": "ERROR"},
                "transport": "stdio",
            },
        }
        self._initialize_model()

    def _initialize_model(self, model_id: str = "amazon.nova-pro-v1:0"):
        logger.info(f"Initializing model: {model_id}")
        self.model = ChatBedrock(
            model_id=model_id,
            streaming=True,
            model_kwargs={"temperature": 0.7},
        )

    async def process_chat(
        self,
        prompt: str,
        session_id: str,
        messages: Optional[List[Any]] = None,
        model: str = "amazon.nova-pro-v1:0",
    ) -> tuple[AIMessage, List[Dict]]:
        """Process a chat message with full conversation history."""
        if messages is None:
            messages = []

        logger.info(f"Processing chat for session {session_id} with model {model}")

        self._initialize_model(model_id=model)

        async with MultiServerMCPClient(self.mcp_servers) as client:
            try:
                tools = client.get_tools()
                logger.info(f"Retrieved {len(tools)} tools from MCP servers")

                tool_descriptions = "\n".join(
                    [f"- {tool.name}: {tool.description}" for tool in tools]
                )

                system_prompt = f"""You are an expert AI assistant with access to various MCP (Model Context Protocol) tools.
Available tools:
{tool_descriptions}

When a user asks a question, think about which tools might help answer it. You can use multiple tools if needed.
ALWAYS use tools when they can help answer the question - don't try to answer without tools unless the question is purely conversational.
After using tools, summarize what you found and provide a clear response to the user's question.
"""

                self.model = self.model.bind(stop=["\nHuman:", "\nAssistant:"])

                all_messages = (
                    [SystemMessage(content=system_prompt)]
                    + messages
                    + [HumanMessage(content=prompt)]
                )

                agent = create_react_agent(self.model, tools)

                response_state = await agent.ainvoke(
                    {"messages": all_messages},
                    config={
                        "configurable": {"thread_id": session_id, "history": messages}
                    },
                )

                tool_activity_details = []
                final_response_message = None

                if response_state and "messages" in response_state:
                    for msg in response_state["messages"]:
                        if isinstance(msg, AIMessage):
                            if hasattr(msg, "content"):
                                content = str(msg.content)
                                pattern = r"<thinking>.*?</thinking>\s*"
                                msg.content = re.sub(
                                    pattern, "", content, flags=re.DOTALL
                                ).strip()

                            if msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    tool_activity_details.append(
                                        {"tool_call": tool_call}
                                    )

                            elif msg.content and msg.content.strip():
                                final_response_message = msg
                        elif isinstance(msg, ToolMessage):
                            tool_activity_details.append(
                                {
                                    "tool_result": {
                                        "content": msg.content,
                                        "tool_call_id": msg.tool_call_id,
                                    }
                                }
                            )

                    if not final_response_message:
                        for msg in reversed(response_state["messages"]):
                            if (
                                isinstance(msg, AIMessage)
                                and msg.content
                                and msg.content.strip()
                            ):
                                final_response_message = msg
                                break

                if final_response_message:
                    if (
                        not final_response_message.content
                        or not final_response_message.content.strip()
                    ):
                        final_response_message = AIMessage(
                            content="Here are the results of my investigation.",
                        )
                    final_response_message.additional_kwargs["tool_activity"] = (
                        tool_activity_details
                    )
                    logger.info(
                        f"Successfully generated response for session {session_id}"
                    )
                    return final_response_message, tool_activity_details

                logger.warning(
                    f"No final response message generated for session {session_id}"
                )
                return AIMessage(
                    content="I have completed the task but didn't generate a final response. Here are the tool activities I performed."
                ), tool_activity_details

            except Exception as e:
                logger.error(f"Error in process_chat: {str(e)}")
                logger.error(traceback.format_exc())
                return AIMessage(content=f"An error occurred: {str(e)}"), []
