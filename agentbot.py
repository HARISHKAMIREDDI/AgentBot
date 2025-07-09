import streamlit as st
from openai import OpenAI

# ---------------- Session State Initialization ---------------- #

for key, default in {
    "chat_history": [],
    "assigned_agent": None,
    "show_goodbye": False,
    "email": "",
    "language": "English",
    "user_prompt": "",
    "last_agent": None,
    "last_language": "English"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------- Mock Order DB ---------------- #

mock_order_db = {
    "john@example.com": {
        "order_id": "ORD12345",
        "status": "Out for Delivery",
        "expected_delivery": "2025-07-06",
        "carrier": "BlueDart",
        "tracking_link": "https://track.bluedart.com/ORD12345",
        "amount": 1299
    },
    "alice@example.com": {
        "order_id": "ORD67890",
        "status": "Shipped",
        "expected_delivery": "2025-07-08",
        "carrier": "Delhivery",
        "tracking_link": "https://track.delhivery.com/ORD67890",
        "amount": 899
    },
    "bob@example.com": {
        "order_id": "ORD54321",
        "status": "Delivered",
        "expected_delivery": "2025-07-02",
        "carrier": "Xpressbees",
        "tracking_link": "https://xpressbees.com/track/ORD54321",
        "amount": 1549
    },
    "sara@example.com": {
        "order_id": "ORD98765",
        "status": "Processing",
        "expected_delivery": "2025-07-10",
        "carrier": "Ecom Express",
        "tracking_link": "https://ecomexpress.in/track/ORD98765",
        "amount": 2199
    }
}

# ---------------- OpenAI Client ---------------- #

client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# ---------------- Utility Functions ---------------- #

def assign_agent(user_prompt, language="English"):
    routing_prompt = f"""
    You are a routing assistant. Detect the correct agent from the following:

    - Order Tracking Agent
    - Refund Agent
    - Return Agent
    - General Support agent

    User prompt (in {language}): {user_prompt}
    """
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": routing_prompt}]
    )
    return res.choices[0].message.content.strip()

def handle_agent_conversation(agent, email, messages, language):
    order = mock_order_db.get(email, {})

    system_prompt = {
        "Order Tracking Agent": f"You are an order tracking assistant. Use this order info: {order}",
        "Refund Agent": f"You are a refund assistant. Use this order info: {order}",
        "Return Agent": f"You are a return assistant. Use this order info: {order}",
        "General Support agent": "You are a general support assistant. Help the user with their request."
    }.get(agent, "You are a helpful assistant.")

    if language != "English":
        system_prompt += f" Respond in {language} using its native writing script. Do not translate the user's query; instead, give a helpful response in that language."

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model="gpt-4",
        messages=full_messages
    )

    return response.choices[0].message.content.strip()

def get_agent_based_goodbye(agent, language):
    base_messages = {
        "Order Tracking Agent": "Glad I could help you track your order today.",
        "Refund Agent": "Your refund request is in good hands. Thank you for your patience!",
        "Return Agent": "Hope we made your return process easier!",
        "General Support agent": "Thanks for reaching out. We’re always here for any help!"
    }

    agent_emojis = {
        "Order Tracking Agent": "📦",
        "Refund Agent": "💸",
        "Return Agent": "🔄",
        "General Support agent": "🤝"
    }

    fallback = "It was a pleasure assisting you today. Take care!"
    message = base_messages.get(agent, fallback)
    emoji = agent_emojis.get(agent, "💬")

    if language == "English":
        return f"{emoji} {message} 💬✨"

    translation_prompt = f'Translate this message into {language} using its native script:\n\n"{message}"'
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": translation_prompt}]
    )
    translated = res.choices[0].message.content.strip()
    return f"{emoji} {translated} 💬✨"

# ---------------- Streamlit UI ---------------- #

st.set_page_config("📦 Smart Support Assistant")
st.title("📦 Smart Customer Support Assistant")

language_options = ["English", "Telugu", "Hindi"]

# Ensure selected language is valid
if st.session_state.language not in language_options:
    st.session_state.language = "English"

st.session_state.email = st.text_input("Enter your Email", value=st.session_state.email)
st.session_state.language = st.selectbox(
    "Preferred Language", language_options,
    index=language_options.index(st.session_state.language)
)
st.session_state.user_prompt = st.text_area("Enter your query here", value=st.session_state.user_prompt)

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    submitted = st.button("Submit")
with col2:
    clear_chat = st.button("Clear Chat")
with col3:
    end_chat = st.button("❌ End Conversation")

# Clear
if clear_chat:
    st.session_state.chat_history = []
    st.rerun()

# End Conversation
if end_chat:
    st.session_state.last_agent = st.session_state.assigned_agent
    st.session_state.last_language = st.session_state.language
    st.session_state.show_goodbye = True
    st.session_state.email = ""
    st.session_state.language = "English"
    st.session_state.user_prompt = ""
    st.session_state.assigned_agent = None
    st.rerun()

# Goodbye (after rerun)
if st.session_state.show_goodbye:
    goodbye_text = get_agent_based_goodbye(st.session_state.last_agent, st.session_state.last_language)
    st.success(goodbye_text)
    st.session_state.show_goodbye = False

# Submit Handler
if submitted and st.session_state.user_prompt:
    with st.spinner("🔍 Processing..."):
        if st.session_state.assigned_agent is None:
            agent = assign_agent(st.session_state.user_prompt, st.session_state.language)
            st.session_state.assigned_agent = agent
        else:
            agent = st.session_state.assigned_agent

        messages = []
        for turn in st.session_state.chat_history:
            messages.append({"role": "user", "content": turn["query"]})
            messages.append({"role": "assistant", "content": turn["response"]})
        messages.append({"role": "user", "content": st.session_state.user_prompt})

        response = handle_agent_conversation(agent, st.session_state.email, messages, st.session_state.language)

        st.session_state.chat_history.append({
            "query": st.session_state.user_prompt,
            "response": response
        })

# Chat History
if st.session_state.chat_history:
    st.subheader("💬 Conversation")
    st.markdown(f"**Agent Assigned**: `{st.session_state.assigned_agent}`")
    for msg in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {msg['query']}")
        st.markdown(f"**Agent:** {msg['response']}")
        st.markdown("---")
