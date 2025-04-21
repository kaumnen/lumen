import streamlit as st
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from src.agents.graph import aws_agent_graph
import uuid
import traceback
import json


st.title("💬 AWS Chat Assistant")
st.write("Ask me questions about AWS services. I can search local documentation.")


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    print(f"Initialized session_id: {st.session_state.session_id}")

    st.session_state.messages = []
    st.session_state.message_count = 0
    st.session_state.tool_calls_count = 0
    st.session_state.token_count = 0
    print("Initialized messages list and stats in session state.")


with st.sidebar:
    st.header("Session Info")
    st.write(f"Messages: {st.session_state.get('message_count', 0)}")
    st.write(f"Tool Calls: {st.session_state.get('tool_calls_count', 0)}")
    st.write(f"Total Tokens: {st.session_state.get('token_count', 0)}")

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.message_count = 0
        st.session_state.tool_calls_count = 0
        st.session_state.token_count = 0
        print("Chat history and stats cleared.")
        st.rerun()


print(f"Displaying {len(st.session_state.messages)} messages from history.")
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
                        except Exception:
                            st.write("Args:", activity["tool_call"]["args"])
                    elif "tool_result" in activity:
                        st.markdown(
                            f"**Tool Result (ID: `{activity['tool_result']['tool_call_id']}`):**"
                        )
                        st.write(activity["tool_result"]["content"])


if prompt := st.chat_input("Ask about AWS..."):
    print(f"User input received: {prompt}")

    user_message = HumanMessage(content=prompt)
    st.session_state.messages.append(user_message)
    st.session_state.message_count += 1
    st.chat_message("user").write(prompt)

    agent_input = {"messages": [user_message]}

    config = {"configurable": {"thread_id": st.session_state.session_id}}
    print(f"Invoking agent with config: {config}")

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response_state = aws_agent_graph.invoke(agent_input, config=config)
                print(f"Agent response state received: {response_state}")

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

                    st.session_state.messages.append(final_response_message)
                    st.session_state.message_count += 1

                    tool_calls_in_turn = sum(
                        1
                        for activity in tool_activity_details
                        if "tool_call" in activity
                    )
                    if tool_calls_in_turn > 0:
                        st.session_state.tool_calls_count += tool_calls_in_turn
                        print(
                            f"Added {tool_calls_in_turn} tool calls to session total."
                        )

                    try:
                        usage_metadata = getattr(
                            final_response_message, "usage_metadata", None
                        )
                        if usage_metadata:
                            call_tokens = usage_metadata.get("total_tokens", 0)
                            if call_tokens > 0:
                                st.session_state.token_count += call_tokens
                                print(f"Added {call_tokens} tokens to session total.")
                            else:
                                print(
                                    "Token usage information found but total_tokens is zero or missing."
                                )
                        else:
                            for msg in reversed(response_state["messages"]):
                                usage_metadata = getattr(msg, "usage_metadata", None)
                                if usage_metadata:
                                    call_tokens = usage_metadata.get("total_tokens", 0)
                                    if call_tokens > 0:
                                        st.session_state.token_count += call_tokens
                                        print(
                                            f"Added {call_tokens} tokens (from intermediate step) to session total."
                                        )
                                        break
                            if not usage_metadata or call_tokens == 0:
                                print(
                                    "usage_metadata not found on any relevant AIMessage in this turn."
                                )
                    except Exception as token_ex:
                        print(f"Could not extract token usage: {token_ex}")

                    st.write(final_response_message.content)
                    print(f"Added agent response to history: {final_response_message}")

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
                        st.session_state.messages.append(last_msg_in_state)
                        st.session_state.message_count += 1
                        st.write(last_msg_in_state.content)
                        print(
                            f"Warning: Agent ended with a HumanMessage: {last_msg_in_state}"
                        )
                    else:
                        response_content = f"Received unexpected final message type: {type(last_msg_in_state)}"
                        fallback_message = AIMessage(content=response_content)
                        st.session_state.messages.append(fallback_message)
                        st.session_state.message_count += 1
                        st.write(response_content)
                        print(
                            f"Warning: Last message was not AIMessage: {last_msg_in_state}"
                        )

                else:
                    response_content = (
                        "Sorry, I received an empty or invalid response state."
                    )
                    error_fallback_msg = AIMessage(content=response_content)
                    st.session_state.messages.append(error_fallback_msg)
                    st.session_state.message_count += 1
                    st.write(response_content)
                    print("Error: Empty or invalid response state from agent.")

            except Exception as e:
                error_message = f"An error occurred: {e}"
                error_details = traceback.format_exc()
                st.error(error_message)
                print(
                    f"Error during agent invocation: {error_message}\n{error_details}"
                )

                error_ai_message = AIMessage(
                    content="Sorry, an error occurred processing your request."
                )
                st.session_state.messages.append(error_ai_message)
                st.session_state.message_count += 1

    st.rerun()
