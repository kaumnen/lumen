import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from src.agents.graph import aws_agent_graph
import uuid
import traceback


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
    st.chat_message(role).write(msg.content)


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

                if (
                    response_state
                    and "messages" in response_state
                    and response_state["messages"]
                ):
                    final_response_message = response_state["messages"][-1]

                    if isinstance(final_response_message, AIMessage):
                        st.session_state.messages.append(final_response_message)
                        st.session_state.message_count += 1

                        if final_response_message.tool_calls:
                            st.session_state.tool_calls_count += len(
                                final_response_message.tool_calls
                            )

                        try:
                            usage_metadata = getattr(
                                final_response_message, "usage_metadata", None
                            )
                            if usage_metadata:
                                call_tokens = usage_metadata.get("total_tokens", 0)
                                if call_tokens > 0:
                                    st.session_state.token_count += call_tokens
                                    print(
                                        f"Added {call_tokens} tokens to session total."
                                    )
                                else:
                                    print(
                                        "Token usage information found but total_tokens is zero or missing."
                                    )
                            else:
                                print("usage_metadata not found on AIMessage.")
                        except Exception as token_ex:
                            print(f"Could not extract token usage: {token_ex}")

                        st.write(final_response_message.content)
                        print(
                            f"Added agent response to history: {final_response_message}"
                        )
                    elif isinstance(final_response_message, HumanMessage):
                        st.session_state.messages.append(final_response_message)
                        st.session_state.message_count += 1
                        st.write(final_response_message.content)
                        print(
                            f"Added human message from agent state (unexpected): {final_response_message}"
                        )
                    else:
                        response_content = f"Received unexpected message type: {type(final_response_message)}"
                        st.session_state.messages.append(
                            AIMessage(content=response_content)
                        )
                        st.session_state.message_count += 1
                        st.write(response_content)
                        print(
                            f"Warning: Last message was not AIMessage or HumanMessage: {final_response_message}"
                        )

                else:
                    response_content = (
                        "Sorry, I received an empty or invalid response state."
                    )
                    st.session_state.messages.append(
                        AIMessage(content=response_content)
                    )
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
