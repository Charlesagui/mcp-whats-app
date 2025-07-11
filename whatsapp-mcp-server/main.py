from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from whatsapp_contacts import (
    search_contacts as whatsapp_search_contacts,
    search_contacts_enhanced as whatsapp_search_contacts_enhanced,
    smart_search_contacts as whatsapp_smart_search_contacts,
    smart_search_contacts_enhanced as whatsapp_smart_search_contacts_enhanced,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_send_audio_message,
    download_media as whatsapp_download_media
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str, limit: int = 25, include_groups: bool = False) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number with advanced fuzzy matching.
    
    Args:
        query: Search term to match against contact names or phone numbers
        limit: Maximum number of results to return (default 25)
        include_groups: Whether to include group chats in results (default False)
    """
    # Try enhanced search first (using real WhatsApp contact names)
    try:
        contacts = whatsapp_search_contacts_enhanced(query, limit, include_groups)
        if contacts:
            return [
                {
                    "phone_number": contact.phone_number,
                    "name": contact.name,
                    "jid": contact.jid
                }
                for contact in contacts
            ]
    except Exception as e:
        print(f"Enhanced search failed, falling back to basic search: {e}")
    
    # Fallback to basic search
    contacts = whatsapp_search_contacts(query, limit, include_groups)
    return [
        {
            "phone_number": contact.phone_number,
            "name": contact.name,
            "jid": contact.jid
        }
        for contact in contacts
    ]

@mcp.tool()
def smart_search_contacts(query: str, limit: int = 25, include_groups: bool = False, similarity_threshold: float = 0.6) -> List[Dict[str, Any]]:
    """Advanced contact search with AI-like similarity matching and typo tolerance.
    
    This function provides intelligent search capabilities:
    - Handles misspellings and typos using similarity algorithms
    - Smart ranking based on multiple factors
    - Configurable similarity threshold for precision control
    - Better than basic search for complex names or unclear spelling
    
    Args:
        query: Search term to match against contact names or phone numbers
        limit: Maximum number of results to return (default 25)
        include_groups: Whether to include group chats in results (default False)
        similarity_threshold: Minimum similarity score (0.0-1.0, default 0.6)
    """
    # Try enhanced smart search first (using real WhatsApp contact names)
    try:
        contacts = whatsapp_smart_search_contacts_enhanced(query, limit, include_groups, similarity_threshold)
        if contacts:
            return [
                {
                    "phone_number": contact.phone_number,
                    "name": contact.name,
                    "jid": contact.jid
                }
                for contact in contacts
            ]
    except Exception as e:
        print(f"Enhanced smart search failed, falling back to basic smart search: {e}")
    
    # Fallback to basic smart search
    contacts = whatsapp_smart_search_contacts(query, limit, include_groups, similarity_threshold)
    return [
        {
            "phone_number": contact.phone_number,
            "name": contact.name,
            "jid": contact.jid
        }
        for contact in contacts
    ]

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1,
    max_results: int = 100,
    force_load: bool = False
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
        max_results: Maximum number of total results to return (default 100)
        force_load: Force loading messages even without filters (default False)
    
    Note: To prevent loading entire history, at least one filter must be specified or force_load=True.
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after,
        max_results=max_results,
        force_load=force_load
    )
    return messages

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_send_audio_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
