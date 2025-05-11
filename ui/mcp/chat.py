import streamlit as st
import pandas as pd
import json
from langchain_core.messages import HumanMessage, AIMessage
import uuid
import asyncio
from src.mcp.client import MCPChatClient
from loguru import logger


st.title("Chat with AWS MCP Servers")
st.success(
    "Ask me questions about AWS services. I can search online documentation. Powered by [AWS MCP Servers](https://github.com/awslabs/mcp)."
)


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    logger.info(f"Initialized new session: {st.session_state.session_id}")
    st.session_state.messages = []
    st.session_state.message_count = 0
    st.session_state.tool_calls_count = 0
    st.session_state.token_count = 0


if "mcp_client" not in st.session_state:
    st.session_state.mcp_client = MCPChatClient()
    logger.info("Initialized MCP client")


with st.sidebar:
    st.header("Model Settings")
    model_options = {
        "Amazon Nova Micro": "amazon.nova-micro-v1:0",
        "Amazon Nova Lite": "amazon.nova-lite-v1:0",
        "Amazon Nova Pro": "amazon.nova-pro-v1:0",
    }
    selected_model_name = st.selectbox(
        "Choose Model",
        list(model_options.keys()),
        help="Select the model to use for chat responses",
    )
    selected_model = model_options[selected_model_name]

    if (
        "selected_model" not in st.session_state
        or st.session_state.selected_model != selected_model
    ):
        st.session_state.selected_model = selected_model
        if len(st.session_state.messages) > 0:
            st.info("Model changed - Starting new conversation")
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.message_count = 0
            st.session_state.tool_calls_count = 0
            st.rerun()

    st.divider()

    st.header("Active MCP Servers")
    if "mcp_client" in st.session_state:
        server_urls = {
            "Core": "https://awslabs.github.io/mcp/servers/core-mcp-server/",
            "AWS Documentation": "https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/",
        }

        table = "| Server | Learn More |\n|--------|---------------|\n"
        for server in server_urls:
            table += f"| ✅ {server} | [Link]({server_urls[server]}) |\n"

        st.markdown(table)

    st.divider()

    st.header("Session Info")
    info_data = {
        "Metric": ["Messages", "Tool Calls"],
        "Value": [
            str(st.session_state.message_count),
            str(st.session_state.tool_calls_count),
        ],
    }
    info_df = pd.DataFrame(info_data)
    st.dataframe(
        info_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="medium"),
            "Value": st.column_config.TextColumn("Value", width="small"),
        },
    )

    if st.button("New Conversation"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.message_count = 0
        st.session_state.tool_calls_count = 0
        logger.info(
            f"Started new conversation with session ID: {st.session_state.session_id}"
        )
        st.rerun()


logger.debug(f"Displaying {len(st.session_state.messages)} messages from history")
for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.write(msg.content)
        if isinstance(msg, AIMessage) and msg.additional_kwargs.get("tool_activity"):
            with st.expander("Tool Activity"):
                for activity in msg.additional_kwargs["tool_activity"]:
                    if "tool_call" in activity:
                        st.markdown(f"**Tool Call:** `{activity['tool_call']['name']}`")
                        try:
                            args_str = json.dumps(
                                activity["tool_call"]["args"], indent=2
                            )
                            st.code(args_str, language="json")
                        except Exception as e:
                            logger.error(f"Error displaying tool args: {e}")
                            st.write("Args:", activity["tool_call"]["args"])
                    elif "tool_result" in activity:
                        st.markdown(
                            f"**Tool Result (ID: `{activity['tool_result']['tool_call_id']}`):**"
                        )
                        st.write(activity["tool_result"]["content"])


if prompt := st.chat_input("Ask a question..."):
    user_message = HumanMessage(content=prompt)
    st.session_state.messages.append(user_message)
    st.session_state.message_count += 1
    st.chat_message("user").write(prompt)
    logger.info(f"Received new message in session {st.session_state.session_id}")

    with st.chat_message("assistant"):
        with st.spinner("Processing with MCP tools..."):
            try:
                response_message, tool_activity = asyncio.run(
                    st.session_state.mcp_client.process_chat(
                        prompt=prompt,
                        session_id=st.session_state.session_id,
                        messages=st.session_state.messages[:-1],
                        model=st.session_state.selected_model,
                    )
                )

                st.session_state.messages.append(response_message)
                st.session_state.message_count += 1

                st.write(response_message.content)

                tool_calls_in_turn = sum(
                    1 for activity in tool_activity if "tool_call" in activity
                )
                if tool_calls_in_turn > 0:
                    st.session_state.tool_calls_count += tool_calls_in_turn
                    logger.info(
                        f"Added {tool_calls_in_turn} tool calls to session total"
                    )

                    with st.expander("Tool Activity"):
                        for activity in tool_activity:
                            if "tool_call" in activity:
                                st.markdown(
                                    f"**Tool Call:** `{activity['tool_call']['name']}`"
                                )
                                try:
                                    args_str = json.dumps(
                                        activity["tool_call"]["args"], indent=2
                                    )
                                    st.code(args_str, language="json")
                                except Exception as e:
                                    logger.error(f"Error displaying tool args: {e}")
                                    st.write("Args:", activity["tool_call"]["args"])
                            elif "tool_result" in activity:
                                st.markdown(
                                    f"**Tool Result (ID: `{activity['tool_result']['tool_call_id']}`):**"
                                )
                                st.write(activity["tool_result"]["content"])

            except Exception as e:
                logger.error(f"Error processing chat: {str(e)}")
                st.error(f"An error occurred: {str(e)}")

    st.rerun()
