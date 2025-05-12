import streamlit as st
import pandas as pd
from loguru import logger
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from src.agents.graph import aws_agent_graph
import uuid
import traceback
import json


st.title("Chat with local AWS Docs")
st.success(
    "Ask me questions about AWS services. I can search local documentation. You can [submit PDFs](/add_pdf) to the local vector database."
)


if "rag_session_id" not in st.session_state:
    st.session_state.rag_session_id = str(uuid.uuid4())
    logger.info(f"Initialized rag_session_id: {st.session_state.rag_session_id}")

    st.session_state.rag_messages = []
    st.session_state.rag_message_count = 0
    st.session_state.rag_tool_calls_count = 0
    st.session_state.rag_token_count = 0
    logger.info("Initialized messages list and stats in rag_session state.")


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
        "rag_selected_model" not in st.session_state
        or st.session_state.rag_selected_model != selected_model
    ):
        st.session_state.rag_selected_model = selected_model
        if len(st.session_state.rag_messages) > 0:
            st.info("Model changed - Starting new conversation")
            st.session_state.rag_session_id = str(uuid.uuid4())
            st.session_state.rag_messages = []
            st.session_state.rag_message_count = 0
            st.session_state.rag_tool_calls_count = 0
            st.session_state.rag_token_count = 0
            st.rerun()

    st.divider()
    st.header("Session Info")

    info_data = {
        "Metric": ["Messages", "Tool Calls", "Total Tokens"],
        "Value": [
            str(st.session_state.get("rag_message_count", 0)),
            str(st.session_state.get("rag_tool_calls_count", 0)),
            str(st.session_state.get("rag_token_count", 0)),
        ],
    }
    info_df = pd.DataFrame(info_data)

    st.dataframe(
        info_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn(
                "Metric",
                width="medium",
            ),
            "Value": st.column_config.TextColumn(
                "Value",
                width="small",
            ),
        },
    )

    if st.button("New Conversation"):
        st.session_state.rag_messages = []
        st.session_state.rag_session_id = str(uuid.uuid4())
        st.session_state.rag_message_count = 0
        st.session_state.rag_tool_calls_count = 0
        st.session_state.rag_token_count = 0
        logger.info("Chat history and stats cleared for rag_session.")
        st.rerun()


logger.debug(f"Displaying {len(st.session_state.rag_messages)} messages from history.")
for msg in st.session_state.rag_messages:
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
                        except Exception:
                            st.write("Args:", activity["tool_call"]["args"])
                    elif "tool_result" in activity:
                        st.markdown(
                            f"**Tool Result (ID: `{activity['tool_result']['tool_call_id']}`):**"
                        )
                        st.write(activity["tool_result"]["content"])


if prompt := st.chat_input("Ask about AWS..."):
    logger.debug(f"User input received: {prompt}")

    user_message = HumanMessage(content=prompt)
    st.session_state.rag_messages.append(user_message)
    st.session_state.rag_message_count += 1
    st.chat_message("user").write(prompt)

    agent_input = {"messages": [user_message]}

    config = {
        "configurable": {
            "thread_id": st.session_state.rag_session_id,
            "model": st.session_state.rag_selected_model,
        }
    }
    logger.debug(f"Invoking agent with config: {config}")

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response_state = aws_agent_graph.invoke(agent_input, config=config)
                logger.debug(f"Agent response state received: {response_state}")

                final_response_message = None
                tool_activity_details = []

                if response_state and "messages" in response_state:
                    for msg in response_state["messages"]:
                        if isinstance(msg, AIMessage) and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tool_activity_details.append({"tool_call": tool_call})
                        elif isinstance(msg, ToolMessage):
                            tool_activity_details.append(
                                {
                                    "tool_result": {
                                        "content": msg.content,
                                        "tool_call_id": msg.tool_call_id,
                                    }
                                }
                            )

                    for msg in reversed(response_state["messages"]):
                        if isinstance(msg, AIMessage):
                            final_response_message = msg
                            break

                if final_response_message:
                    final_response_message.additional_kwargs["tool_activity"] = (
                        tool_activity_details
                    )

                    st.session_state.rag_messages.append(final_response_message)
                    st.session_state.rag_message_count += 1

                    tool_calls_in_turn = sum(
                        1
                        for activity in tool_activity_details
                        if "tool_call" in activity
                    )
                    if tool_calls_in_turn > 0:
                        st.session_state.rag_tool_calls_count += tool_calls_in_turn
                        logger.debug(
                            f"Added {tool_calls_in_turn} tool calls to rag_session total."
                        )

                    try:
                        usage_metadata = getattr(
                            final_response_message, "usage_metadata", None
                        )
                        if usage_metadata:
                            input_tokens = usage_metadata.get("input_tokens", 0)
                            output_tokens = usage_metadata.get("output_tokens", 0)
                            total_tokens = usage_metadata.get("total_tokens", 0)
                            st.session_state.rag_token_count += total_tokens
                            logger.info(
                                f"Tokens used: Input={input_tokens}, Output={output_tokens}, Total={total_tokens}. Session total: {st.session_state.rag_token_count}"
                            )
                        else:
                            logger.warning("Usage metadata not found on the message.")
                    except Exception as token_ex:
                        logger.warning(f"Could not extract token usage: {token_ex}")

                    st.write(final_response_message.content)
                    logger.debug(
                        f"Added agent response to history: {final_response_message}"
                    )

                    if tool_activity_details:
                        with st.expander("Tool Activity (Current Turn)"):
                            for activity in tool_activity_details:
                                if "tool_call" in activity:
                                    st.markdown(
                                        f"**Tool Call:** `{activity['tool_call']['name']}`"
                                    )

                                    try:
                                        args_str = json.dumps(
                                            activity["tool_call"]["args"], indent=2
                                        )
                                        st.code(args_str, language="json")
                                    except Exception:
                                        st.write("Args:", activity["tool_call"]["args"])
                                elif "tool_result" in activity:
                                    st.markdown(
                                        f"**Tool Result (ID: `{activity['tool_result']['tool_call_id']}`):**"
                                    )
                                    st.write(activity["tool_result"]["content"])

                elif (
                    not final_response_message
                    and response_state
                    and "messages" in response_state
                    and response_state["messages"]
                ):
                    last_msg_in_state = response_state["messages"][-1]
                    if isinstance(last_msg_in_state, HumanMessage):
                        st.session_state.rag_messages.append(last_msg_in_state)
                        st.session_state.rag_message_count += 1
                        st.write(last_msg_in_state.content)
                        logger.warning(
                            f"Agent ended with a HumanMessage: {last_msg_in_state}"
                        )
                    else:
                        response_content = f"Received unexpected final message type: {type(last_msg_in_state)}"
                        fallback_message = AIMessage(content=response_content)
                        st.session_state.rag_messages.append(fallback_message)
                        st.session_state.rag_message_count += 1
                        st.write(response_content)
                        logger.warning(
                            f"Last message was not AIMessage: {last_msg_in_state}"
                        )

                else:
                    response_content = (
                        "Sorry, I received an empty or invalid response state."
                    )
                    error_fallback_msg = AIMessage(content=response_content)
                    st.session_state.rag_messages.append(error_fallback_msg)
                    st.session_state.rag_message_count += 1
                    st.write(response_content)
                    logger.error("Error: Empty or invalid response state from agent.")

            except Exception as e:
                error_message = f"An error occurred: {e}"
                error_details = traceback.format_exc()
                st.error(error_message)
                logger.error(
                    f"Error during agent invocation: {error_message}\n{error_details}"
                )

                error_ai_message = AIMessage(
                    content="Sorry, an error occurred processing your request."
                )
                st.session_state.rag_messages.append(error_ai_message)
                st.session_state.rag_message_count += 1

    st.rerun()
