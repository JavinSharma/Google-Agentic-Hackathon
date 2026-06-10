from elastic.client import ingest_event


async def log_user_action(user_id: str, action_type: str, topic: str, session_id: str = "default") -> str:
    """
    Logs a user behavioral action to Elasticsearch for tracking and analysis.
    
    This tool should be called when a user performs any action that indicates their interests,
    such as searching for a topic, viewing content, or dismissing a suggestion.
    
    Args:
        user_id: The unique identifier of the user performing the action
        action_type: The type of action performed. Must be one of: "search", "view", "dismiss"
        topic: The topic or subject matter the action relates to
        session_id: The unique identifier for the current user session (defaults to "default")
    
    Returns:
        A confirmation message indicating the action was logged
    """
    event_dict = {
        "user_id": user_id,
        "action_type": action_type,
        "topic": topic,
        "session_id": session_id
    }
    
    await ingest_event(event_dict)
    
    return f"Logged action: {action_type} on {topic} for user {user_id}"
