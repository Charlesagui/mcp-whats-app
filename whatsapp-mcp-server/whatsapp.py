import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Tuple
import os
import os.path
import requests
import json
import audio
import unicodedata
from dotenv import load_dotenv
from unidecode import unidecode
from fuzzywuzzy import process, fuzz

# Import optimized contact search functions
from whatsapp_contacts import (
    search_contacts as optimized_search_contacts,
    search_contacts_enhanced as optimized_search_contacts_enhanced,
    smart_search_contacts as optimized_smart_search_contacts,
    smart_search_contacts_enhanced as optimized_smart_search_contacts_enhanced
)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def normalize(text):
    """Normaliza el texto eliminando acentos y convirtiéndolo a minúsculas."""
    if not text:
        return ""
    return unidecode(text).lower()

# Configuration from environment
WHATSAPP_API_HOST = os.getenv('WHATSAPP_API_HOST', 'localhost')
WHATSAPP_API_PORT = os.getenv('WHATSAPP_API_PORT', '8080')
WHATSAPP_API_BASE_URL = os.getenv('WHATSAPP_API_BASE_URL', f'http://{WHATSAPP_API_HOST}:{WHATSAPP_API_PORT}/api')
MESSAGES_DB_NAME = os.getenv('MESSAGES_DB_NAME', 'messages.db')

# Database paths
MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', MESSAGES_DB_NAME)
WHATSAPP_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'whatsapp.db')

@dataclass
class Message:
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_jid: str
    id: str
    chat_name: Optional[str] = None
    media_type: Optional[str] = None

@dataclass
class Chat:
    jid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None

    @property
    def is_group(self) -> bool:
        """Determine if chat is a group based on JID pattern."""
        return self.jid.endswith("@g.us")

@dataclass
class Contact:
    phone_number: str
    name: Optional[str]
    jid: str

@dataclass
class MessageContext:
    message: Message
    before: List[Message]
    after: List[Message]

def get_real_contact_name(jid: str) -> Optional[str]:
    """Get the real contact name from whatsapp.db"""
    try:
        conn = sqlite3.connect(WHATSAPP_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT full_name, first_name, push_name
            FROM whatsmeow_contacts
            WHERE their_jid = ?
            ORDER BY 
                CASE WHEN full_name IS NOT NULL AND TRIM(full_name) != '' THEN 1 ELSE 0 END DESC,
                CASE WHEN first_name IS NOT NULL AND TRIM(first_name) != '' THEN 1 ELSE 0 END DESC,
                CASE WHEN push_name IS NOT NULL AND TRIM(push_name) != '' THEN 1 ELSE 0 END DESC
            LIMIT 1
        """, (jid,))
        
        result = cursor.fetchone()
        
        if result:
            # Return the first non-empty name in order of preference: full_name, first_name, push_name
            for name in result:
                if name and name.strip():
                    return name.strip()
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error while getting real contact name: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def search_contacts_enhanced(query: str, limit: int = 25, include_groups: bool = False) -> List[Contact]:
    """Enhanced contact search using both messages.db and whatsapp.db for complete contact info."""
    try:
        # Enhanced validation
        if query is None:
            print("INFO: Query is None, returning empty results")
            return []
        
        clean_query = query.strip().lower()
        if len(clean_query) == 0:
            # For empty queries, return all contacts
            clean_query = ""
        elif len(clean_query) < 1:
            print("INFO: Query too short, returning empty results")
            return []
            
        # Check if databases exist
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Messages database not found at {MESSAGES_DB_PATH}")
            return []
            
        if not os.path.exists(WHATSAPP_DB_PATH):
            print(f"WARNING: WhatsApp database not found at {WHATSAPP_DB_PATH}")
            return []
        
        # Connect to both databases
        messages_conn = sqlite3.connect(MESSAGES_DB_PATH)
        whatsapp_conn = sqlite3.connect(WHATSAPP_DB_PATH)
        
        messages_cursor = messages_conn.cursor()
        whatsapp_cursor = whatsapp_conn.cursor()
        
        # Get all contacts from whatsapp.db with real names
        whatsapp_cursor.execute("""
            SELECT DISTINCT 
                their_jid,
                COALESCE(
                    NULLIF(TRIM(full_name), ''),
                    NULLIF(TRIM(first_name), ''),
                    NULLIF(TRIM(push_name), '')
                ) as display_name,
                full_name,
                first_name, 
                push_name
            FROM whatsmeow_contacts
            WHERE their_jid IS NOT NULL
            ORDER BY display_name COLLATE NOCASE
        """)
        
        whatsapp_contacts = whatsapp_cursor.fetchall()
        
        # Also get chats that might not be in contacts
        group_filter = "" if include_groups else "AND jid NOT LIKE '%@g.us'"
        
        messages_cursor.execute(f"""
            SELECT DISTINCT 
                jid,
                name
            FROM chats
            WHERE jid != '0@s.whatsapp.net'
                {group_filter}
        """)
        
        chat_contacts = messages_cursor.fetchall()
        
        # Combine and deduplicate
        all_contacts = {}
        
        # First add WhatsApp contacts (priority)
        for contact in whatsapp_contacts:
            jid, display_name, full_name, first_name, push_name = contact
            if jid and not (not include_groups and jid.endswith('@g.us')):
                all_contacts[jid] = {
                    'jid': jid,
                    'name': display_name,
                    'full_name': full_name,
                    'first_name': first_name,
                    'push_name': push_name,
                    'source': 'whatsapp'
                }
        
        # Then add chat contacts (if not already present)
        for chat in chat_contacts:
            jid, name = chat
            if jid not in all_contacts and jid:
                all_contacts[jid] = {
                    'jid': jid,
                    'name': name,
                    'source': 'messages'
                }
        
        # Filter by query if provided
        result = []
        if clean_query == "":
            # Return all contacts
            for contact_data in all_contacts.values():
                jid = contact_data['jid']
                name = contact_data['name']
                phone_number = jid.split('@')[0] if '@' in jid else jid
                
                contact = Contact(
                    phone_number=phone_number,
                    name=name if name and name != phone_number else None,
                    jid=jid
                )
                result.append(contact)
        else:
            # Search with scoring
            scored_contacts = []
            
            for contact_data in all_contacts.values():
                jid = contact_data['jid']
                name = contact_data['name'] or ''
                
                # Score calculation
                score = 0
                if name:
                    name_lower = name.lower()
                    if name_lower == clean_query:
                        score = 100
                    elif name_lower.startswith(clean_query):
                        score = 90
                    elif clean_query in name_lower:
                        score = 80
                    elif any(word.startswith(clean_query) for word in name_lower.split()):
                        score = 70
                
                # Also check phone number
                phone_number = jid.split('@')[0] if '@' in jid else jid
                if clean_query in phone_number:
                    score = max(score, 60)
                
                if score > 0:
                    scored_contacts.append((score, contact_data))
            
            # Sort by score and limit
            scored_contacts.sort(key=lambda x: x[0], reverse=True)
            
            for score, contact_data in scored_contacts[:limit]:
                jid = contact_data['jid']
                name = contact_data['name']
                phone_number = jid.split('@')[0] if '@' in jid else jid
                
                contact = Contact(
                    phone_number=phone_number,
                    name=name if name and name != phone_number else None,
                    jid=jid
                )
                result.append(contact)
        
        # If no results and we had a query, try fuzzy matching
        if not result and clean_query and len(clean_query) >= 2:
            fuzzy_result = smart_search_contacts_enhanced(query, limit, include_groups)
            if fuzzy_result:
                return fuzzy_result
        
        return result[:limit]
        
    except sqlite3.Error as e:
        print(f"Database error in enhanced search: {e}")
        return search_contacts(query, limit, include_groups)
    except Exception as e:
        print(f"Unexpected error in enhanced search: {e}")
        return search_contacts(query, limit, include_groups)
    finally:
        if 'messages_conn' in locals():
            messages_conn.close()
        if 'whatsapp_conn' in locals():
            whatsapp_conn.close()

def smart_search_contacts_enhanced(query: str, limit: int = 25, include_groups: bool = False, similarity_threshold: float = 0.6) -> List[Contact]:
    """Enhanced smart search using both databases with fuzzy matching."""
    try:
        if not query or len(query.strip()) < 1:
            print("INFO: Query too short, returning empty results")
            return []
            
        # Check if databases exist
        if not os.path.exists(WHATSAPP_DB_PATH):
            print(f"WARNING: WhatsApp database not found at {WHATSAPP_DB_PATH}")
            return smart_search_contacts(query, limit, include_groups, similarity_threshold)
        
        # Connect to WhatsApp database
        whatsapp_conn = sqlite3.connect(WHATSAPP_DB_PATH)
        whatsapp_cursor = whatsapp_conn.cursor()
        
        # Get all contacts with names from whatsapp.db
        whatsapp_cursor.execute("""
            SELECT DISTINCT 
                their_jid,
                COALESCE(
                    NULLIF(TRIM(full_name), ''),
                    NULLIF(TRIM(first_name), ''),
                    NULLIF(TRIM(push_name), '')
                ) as display_name
            FROM whatsmeow_contacts
            WHERE their_jid IS NOT NULL
                AND display_name IS NOT NULL
        """)
        
        all_contacts = whatsapp_cursor.fetchall()
        
        # Filter groups if needed
        if not include_groups:
            all_contacts = [(jid, name) for jid, name in all_contacts if not jid.endswith('@g.us')]
        
        # Prepare data for fuzzywuzzy
        normalized_query = normalize(query)
        contact_choices = []
        contact_map = {}
        
        for jid, display_name in all_contacts:
            if display_name:
                normalized_name = normalize(display_name)
                contact_choices.append(normalized_name)
                contact_map[normalized_name] = (jid, display_name)
        
        if not contact_choices:
            print("INFO: No contacts with names found in WhatsApp database")
            return []
        
        # Use fuzzywuzzy for intelligent matching
        fuzzy_threshold = int(similarity_threshold * 100)
        best_matches = process.extract(normalized_query, contact_choices, limit=limit)
        
        # Build results
        result = []
        for match_name, score in best_matches:
            if score >= fuzzy_threshold:
                jid, original_name = contact_map[match_name]
                phone_number = jid.split('@')[0] if '@' in jid else jid
                
                contact = Contact(
                    phone_number=phone_number,
                    name=original_name,
                    jid=jid
                )
                result.append(contact)
                
                # Show match details for debugging
                if len(result) <= 3:
                    print(f"Enhanced fuzzy match: {original_name} (Score: {score})")
        
        return result
        
    except sqlite3.Error as e:
        print(f"Database error in enhanced smart search: {e}")
        return smart_search_contacts(query, limit, include_groups, similarity_threshold)
    except Exception as e:
        print(f"Unexpected error in enhanced smart search: {e}")
        return smart_search_contacts(query, limit, include_groups, similarity_threshold)
    finally:
        if 'whatsapp_conn' in locals():
            whatsapp_conn.close()
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # First try matching by exact JID
        cursor.execute("""
            SELECT name
            FROM chats
            WHERE jid = ?
            LIMIT 1
        """, (sender_jid,))
        
        result = cursor.fetchone()
        
        # If no result, try looking for the number within JIDs
        if not result:
            # Extract the phone number part if it's a JID
            if '@' in sender_jid:
                phone_part = sender_jid.split('@')[0]
            else:
                phone_part = sender_jid
                
            cursor.execute("""
                SELECT name
                FROM chats
                WHERE jid LIKE ?
                LIMIT 1
            """, (f"%{phone_part}%",))
            
            result = cursor.fetchone()
        
        if result and result[0]:
            return result[0]
        else:
            return sender_jid
        
    except sqlite3.Error as e:
        print(f"Database error while getting sender name: {e}")
        return sender_jid
    finally:
        if 'conn' in locals():
            conn.close()
def format_message(message: Message, show_chat_info: bool = True) -> None:
    """Print a single message with consistent formatting."""
    output = ""
    
    if show_chat_info and message.chat_name:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] Chat: {message.chat_name} "
    else:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] "
        
    content_prefix = ""
    if hasattr(message, 'media_type') and message.media_type:
        content_prefix = f"[{message.media_type} - Message ID: {message.id} - Chat JID: {message.chat_jid}] "
    
    try:
        sender_name = get_sender_name(message.sender) if not message.is_from_me else "Me"
        output += f"From: {sender_name}: {content_prefix}{message.content}\n"
    except Exception as e:
        print(f"Error formatting message: {e}")
    return output

def format_messages_list(messages: List[Message], show_chat_info: bool = True) -> None:
    output = ""
    if not messages:
        output += "No messages to display."
        return output
    
    for message in messages:
        output += format_message(message, show_chat_info)
    return output

def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = False,
    context_before: int = 1,
    context_after: int = 1,
    max_results: int = 100,
    force_load: bool = False
) -> List[Message]:
    """Get messages matching the specified criteria with optional context.
    
    To prevent loading entire history, at least one filter must be specified or force_load=True.
    """
    try:
        # Check if at least one filter is specified or load is forced
        if not any([after, before, sender_phone_number, chat_jid, query, force_load]):
            print("WARNING: No filters specified and force_load=False. No messages will be loaded.")
            return []
        
        # Quick connection test - if DB doesn't exist, return empty
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Database not found at {MESSAGES_DB_PATH}")
            return []
        
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query with optimized indexes
        query_parts = ["SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type FROM messages"]
        query_parts.append("JOIN chats ON messages.chat_jid = chats.jid")
        where_clauses = []
        params = []
        
        # Add filters with proper indexing
        if after:
            try:
                after_date = datetime.fromisoformat(after) if isinstance(after, str) else after
            except ValueError:
                raise ValueError(f"Invalid date format for 'after': {after}. Please use ISO-8601 format.")
            
            where_clauses.append("messages.timestamp > ?")
            params.append(after_date)

        if before:
            try:
                before_date = datetime.fromisoformat(before) if isinstance(before, str) else before
            except ValueError:
                raise ValueError(f"Invalid date format for 'before': {before}. Please use ISO-8601 format.")
            
            where_clauses.append("messages.timestamp < ?")
            params.append(before_date)

        if sender_phone_number:
            where_clauses.append("messages.sender = ?")
            params.append(sender_phone_number)
            
        if chat_jid:
            where_clauses.append("messages.chat_jid = ?")
            params.append(chat_jid)
            
        if query:
            where_clauses.append("LOWER(messages.content) LIKE LOWER(?)")
            params.append(f"%{query}%")
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add pagination with stricter limits for performance
        offset = page * limit
        actual_limit = min(limit, max_results, 50)  # Hard cap at 50 for performance
        query_parts.append("ORDER BY messages.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([actual_limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        messages = cursor.fetchall()
        
        result = []
        for msg in messages:
            message = Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7]
            )
            result.append(message)
        
        # Context loading only if explicitly requested and limited
        if include_context and result:
            context_limit = min(len(result), 5)  # Max 5 messages with context
            if context_limit < len(result):
                print(f"INFO: Limiting context to first {context_limit} messages for performance")
                
            messages_with_context = []
            for msg in result[:context_limit]:
                try:
                    context = get_message_context(msg.id, context_before, context_after)
                    messages_with_context.extend(context.before)
                    messages_with_context.append(context.message)
                    messages_with_context.extend(context.after)
                except Exception as e:
                    print(f"Warning: Could not load context for message {msg.id}: {e}")
                    messages_with_context.append(msg)
            
            # Add remaining messages without context
            if context_limit < len(result):
                messages_with_context.extend(result[context_limit:])
                
            return format_messages_list(messages_with_context, show_chat_info=True)
            
        # Return formatted messages without context
        return format_messages_list(result, show_chat_info=True)    
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> MessageContext:
    """Get context around a specific message."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Get the target message first
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.chat_jid, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.id = ?
        """, (message_id,))
        msg_data = cursor.fetchone()
        
        if not msg_data:
            raise ValueError(f"Message with ID {message_id} not found")
            
        target_message = Message(
            timestamp=datetime.fromisoformat(msg_data[0]),
            sender=msg_data[1],
            chat_name=msg_data[2],
            content=msg_data[3],
            is_from_me=msg_data[4],
            chat_jid=msg_data[5],
            id=msg_data[6],
            media_type=msg_data[8]
        )
        
        # Get messages before
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.chat_jid = ? AND messages.timestamp < ?
            ORDER BY messages.timestamp DESC
            LIMIT ?
        """, (msg_data[7], msg_data[0], before))
        
        before_messages = []
        for msg in cursor.fetchall():
            before_messages.append(Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7]
            ))
        
        # Get messages after
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.chat_jid = ? AND messages.timestamp > ?
            ORDER BY messages.timestamp ASC
            LIMIT ?
        """, (msg_data[7], msg_data[0], after))
        
        after_messages = []
        for msg in cursor.fetchall():
            after_messages.append(Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7]
            ))
        
        return MessageContext(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Chat]:
    """Get chats matching the specified criteria."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query
        query_parts = ["""
            SELECT 
                chats.jid,
                chats.name,
                chats.last_message_time,
                messages.content as last_message,
                messages.sender as last_sender,
                messages.is_from_me as last_is_from_me
            FROM chats
        """]
        
        if include_last_message:
            query_parts.append("""
                LEFT JOIN messages ON chats.jid = messages.chat_jid 
                AND chats.last_message_time = messages.timestamp
            """)
            
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append("(LOWER(chats.name) LIKE LOWER(?) OR chats.jid LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add sorting
        order_by = "chats.last_message_time DESC" if sort_by == "last_active" else "chats.name"
        query_parts.append(f"ORDER BY {order_by}")
        
        # Add pagination
        offset = (page ) * limit
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        chats = cursor.fetchall()
        
        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5]
            )
            result.append(chat)
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def search_contacts(query: str, limit: int = 25, include_groups: bool = False) -> List[Contact]:
    """Search contacts by name or phone number with advanced fuzzy matching."""
    try:
        # Enhanced validation
        if query is None:
            print("INFO: Query is None, returning empty results")
            return []
        
        clean_query = query.strip().lower()
        if len(clean_query) == 0:
            # For empty queries, return all contacts
            clean_query = ""
            exact_pattern = ""
            starts_with_pattern = "%"
            contains_pattern = "%"
            word_boundary_pattern = "%"
        elif len(clean_query) < 1:
            print("INFO: Query too short, returning empty results")
            return []
        else:
            exact_pattern = clean_query
            starts_with_pattern = clean_query + '%'
            contains_pattern = '%' + clean_query + '%'
            word_boundary_pattern = f'% {clean_query}%'
            
        # Check if database exists
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Database not found at {MESSAGES_DB_PATH}")
            return []
        
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build simplified query with proper scoring
        group_filter = "" if include_groups else "AND jid NOT LIKE '%@g.us'"
        
        if clean_query == "":
            # For empty queries, return all contacts ordered by name
            query_sql = f"""
                SELECT DISTINCT 
                    jid,
                    COALESCE(name, SUBSTR(jid, 1, INSTR(jid, '@') - 1)) as display_name,
                    50 as score,
                    CASE WHEN name IS NOT NULL AND TRIM(name) != '' THEN 1 ELSE 0 END as has_name,
                    LENGTH(COALESCE(name, '')) as name_length
                FROM chats
                WHERE jid != '0@s.whatsapp.net'
                    {group_filter}
                ORDER BY 
                    has_name DESC,
                    display_name COLLATE NOCASE,
                    jid
                LIMIT ?
            """
            params = [limit]
        else:
            query_sql = f"""
                SELECT DISTINCT 
                    jid,
                    COALESCE(name, SUBSTR(jid, 1, INSTR(jid, '@') - 1)) as display_name,
                    CASE 
                        WHEN LOWER(COALESCE(name, '')) = ? THEN 100
                        WHEN LOWER(COALESCE(name, '')) LIKE ? THEN 90
                        WHEN LOWER(jid) LIKE ? THEN 85
                        WHEN LOWER(COALESCE(name, '')) LIKE ? THEN 80
                        WHEN LOWER(COALESCE(name, '')) LIKE ? THEN 70
                        WHEN LOWER(jid) LIKE ? THEN 60
                        ELSE 40
                    END as score,
                    CASE WHEN name IS NOT NULL AND TRIM(name) != '' THEN 1 ELSE 0 END as has_name,
                    LENGTH(COALESCE(name, '')) as name_length
                FROM chats
                WHERE 
                    (LOWER(COALESCE(name, '')) LIKE ? OR LOWER(jid) LIKE ?)
                    {group_filter}
                    AND jid != '0@s.whatsapp.net'
                ORDER BY 
                    score DESC,
                    has_name DESC,
                    name_length ASC,
                    display_name COLLATE NOCASE,
                    jid
                LIMIT ?
            """
            # Prepare parameters in correct order
            params = [
                exact_pattern,              # Exact match
                starts_with_pattern,        # Starts with
                starts_with_pattern,        # Phone starts with  
                word_boundary_pattern,      # Word boundary
                contains_pattern,           # Contains anywhere
                contains_pattern,           # JID contains
                contains_pattern,           # Main WHERE name
                contains_pattern,           # Main WHERE jid
                limit
            ]
        
        cursor.execute(query_sql, params)
        contacts = cursor.fetchall()
        
        result = []
        seen_jids = set()  # Prevent duplicates
        
        for contact_data in contacts:
            jid = contact_data[0]
            display_name = contact_data[1]
            if jid not in seen_jids:
                seen_jids.add(jid)
                # Extract phone number from JID
                phone_number = jid.split('@')[0] if '@' in jid else jid
                # Use name if available, otherwise use phone number
                contact_name = display_name if display_name and display_name != phone_number else None
                
                contact = Contact(
                    phone_number=phone_number,
                    name=contact_name,
                    jid=jid
                )
                result.append(contact)
        
        # If no results and query has potential accent issues, try normalized search
        if not result and len(clean_query) >= 2:
            normalized_query = normalize(clean_query)
            if normalized_query != clean_query or True:  # Always try normalized search as fallback
                # Try search with normalized query on all contacts
                cursor.execute(f"""
                    SELECT DISTINCT jid, COALESCE(name, SUBSTR(jid, 1, INSTR(jid, '@') - 1)) as display_name
                    FROM chats
                    WHERE jid != '0@s.whatsapp.net'
                        {group_filter}
                    ORDER BY 
                        CASE WHEN name IS NOT NULL AND TRIM(name) != '' THEN 1 ELSE 0 END DESC,
                        display_name COLLATE NOCASE
                """)
                
                all_contacts = cursor.fetchall()
                for contact_data in all_contacts:
                    jid = contact_data[0]
                    display_name = contact_data[1]
                    
                    # Check if normalized name contains normalized query
                    if display_name and normalize(display_name).find(normalized_query) >= 0:
                        if jid not in seen_jids:
                            seen_jids.add(jid)
                            phone_number = jid.split('@')[0] if '@' in jid else jid
                            contact_name = display_name if display_name and display_name != phone_number else None
                            
                            contact = Contact(
                                phone_number=phone_number,
                                name=contact_name,
                                jid=jid
                            )
                            result.append(contact)
                            
                            if len(result) >= limit:
                                break
        
        # If no results and query looks like a phone number, suggest direct JID
        if not result and (clean_query.isdigit() or clean_query.replace('+', '').replace('-', '').replace(' ', '').isdigit()):
            print(f"INFO: No contacts found. For direct messaging, try JID format: {clean_query.replace('+', '').replace('-', '').replace(' ', '')}@s.whatsapp.net")
        
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error in contact search: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()
def search_contacts_fuzzy(contacts, query, limit=5):
    """
    Busca contactos usando coincidencias aproximadas.
    :param contacts: Un diccionario de contactos donde las claves son JIDs y los valores son objetos ContactInfo.
    :param query: La cadena de búsqueda.
    :param limit: El número máximo de resultados a devolver.
    :return: Una lista de tuplas (JID, ContactInfo) para las mejores coincidencias.
    """
    normalized_query = normalize(query)
    contact_names = [(jid, normalize(contact['FullName'])) for jid, contact in contacts.items()]
    best_matches = process.extract(normalized_query, [name for jid, name in contact_names], limit=limit)
    results = []
    for match in best_matches:
        jid = [jid for j, name in contact_names if name == match[0]][0]
        if match[1] > 60:  # Umbral de similitud del 60%
            results.append((jid, contacts[jid]))
    return results

def smart_search_contacts(query: str, limit: int = 25, include_groups: bool = False, similarity_threshold: float = 0.6) -> List[Contact]:
    """Advanced contact search with AI-like similarity matching and typo tolerance.
    
    This function provides intelligent search capabilities:
    - Handles misspellings and typos using similarity algorithms
    - Smart ranking based on multiple factors
    - Configurable similarity threshold for precision control
    - Better than basic search for complex names or unclear spelling
    """
    try:
        # Enhanced validation
        if not query or len(query.strip()) < 1:
            print("INFO: Query too short, returning empty results")
            return []
            
        # Check if database exists
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Database not found at {MESSAGES_DB_PATH}")
            return []
        
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        group_filter = "" if include_groups else "AND jid NOT LIKE '%@g.us'"
        
        # Get all contacts for fuzzy matching
        cursor.execute(f"""
            SELECT DISTINCT 
                jid,
                COALESCE(name, SUBSTR(jid, 1, INSTR(jid, '@') - 1)) as display_name
            FROM chats
            WHERE 
                jid != '0@s.whatsapp.net'
                {group_filter}
            ORDER BY display_name COLLATE NOCASE
        """)
        
        all_contacts = cursor.fetchall()
        
        # Prepare data for fuzzywuzzy
        normalized_query = normalize(query)
        contact_choices = []
        contact_map = {}
        
        for jid, display_name in all_contacts:
            if display_name:
                normalized_name = normalize(display_name)
                contact_choices.append(normalized_name)
                contact_map[normalized_name] = (jid, display_name)
        
        # Use fuzzywuzzy for intelligent matching
        # Convert similarity_threshold from 0-1 to 0-100 scale for fuzzywuzzy
        fuzzy_threshold = int(similarity_threshold * 100)
        best_matches = process.extract(normalized_query, contact_choices, limit=limit)
        
        # Build results
        result = []
        for match_name, score in best_matches:
            if score >= fuzzy_threshold:
                jid, original_name = contact_map[match_name]
                phone_number = jid.split('@')[0] if '@' in jid else jid
                contact_name = original_name if original_name != phone_number else None
                
                contact = Contact(
                    phone_number=phone_number,
                    name=contact_name,
                    jid=jid
                )
                result.append(contact)
                
                # Show match details for debugging
                if len(result) <= 3:
                    print(f"Fuzzy match: {original_name} (Score: {score})")
        
        # If no good matches found, fallback to basic search
        if not result:
            print(f"INFO: No fuzzy matches above threshold {fuzzy_threshold}. Trying basic search...")
            return search_contacts(query, limit, include_groups)
        
        return result
        
    except sqlite3.Error as e:
        print(f"Database error in smart search: {e}")
        return search_contacts(query, limit, include_groups)
    except Exception as e:
        print(f"Unexpected error in smart search: {e}")
        return search_contacts(query, limit, include_groups)
    finally:
        if 'conn' in locals():
            conn.close()


    """Get all chats involving the contact."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            JOIN messages m ON c.jid = m.chat_jid
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY c.last_message_time DESC
            LIMIT ? OFFSET ?
        """, (jid, jid, limit, page * limit))
        
        chats = cursor.fetchall()
        
        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5]
            )
            result.append(chat)
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Chat]:
    """Get all chats involving the contact."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            JOIN messages m ON c.jid = m.chat_jid
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY c.last_message_time DESC
            LIMIT ? OFFSET ?
        """, (jid, jid, limit, page * limit))
        
        chats = cursor.fetchall()
        
        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5]
            )
            result.append(chat)
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


    """Get most recent message involving the contact."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.timestamp,
                m.sender,
                c.name,
                m.content,
                m.is_from_me,
                c.jid,
                m.id,
                m.media_type
            FROM messages m
            JOIN chats c ON m.chat_jid = c.jid
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY m.timestamp DESC
            LIMIT 1
        """, (jid, jid))
        
        msg_data = cursor.fetchone()
        
        if not msg_data:
            return None
            
        message = Message(
            timestamp=datetime.fromisoformat(msg_data[0]),
            sender=msg_data[1],
            chat_name=msg_data[2],
            content=msg_data[3],
            is_from_me=msg_data[4],
            chat_jid=msg_data[5],
            id=msg_data[6],
            media_type=msg_data[7]
        )
        
        return format_message(message)
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def get_chat(chat_jid: str, include_last_message: bool = True) -> Optional[Chat]:
    """Get chat metadata by JID."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
        """
        
        if include_last_message:
            query += """
                LEFT JOIN messages m ON c.jid = m.chat_jid 
                AND c.last_message_time = m.timestamp
            """
            
        query += " WHERE c.jid = ?"
        
        cursor.execute(query, (chat_jid,))
        chat_data = cursor.fetchone()
        
        if not chat_data:
            return None
            
        return Chat(
            jid=chat_data[0],
            name=chat_data[1],
            last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
            last_message=chat_data[3],
            last_sender=chat_data[4],
            last_is_from_me=chat_data[5]
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def get_direct_chat_by_contact(sender_phone_number: str) -> Optional[Chat]:
    """Get chat metadata by sender phone number."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            LEFT JOIN messages m ON c.jid = m.chat_jid 
                AND c.last_message_time = m.timestamp
            WHERE c.jid LIKE ? AND c.jid NOT LIKE '%@g.us'
            LIMIT 1
        """, (f"%{sender_phone_number}%",))
        
        chat_data = cursor.fetchone()
        
        if not chat_data:
            return None
            
        return Chat(
            jid=chat_data[0],
            name=chat_data[1],
            last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
            last_message=chat_data[3],
            last_sender=chat_data[4],
            last_is_from_me=chat_data[5]
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "message": message,
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_file(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        if not media_path.endswith(".ogg"):
            try:
                media_path = audio.convert_to_opus_ogg_temp(media_path)
            except Exception as e:
                return False, f"Error converting file to opus ogg. You likely need to install ffmpeg: {str(e)}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def download_media(message_id: str, chat_jid: str) -> Optional[str]:
    """Download media from a message and return the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        The local file path if download was successful, None otherwise
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/download"
        payload = {
            "message_id": message_id,
            "chat_jid": chat_jid
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                path = result.get("path")
                print(f"Media downloaded successfully: {path}")
                return path
            else:
                print(f"Download failed: {result.get('message', 'Unknown error')}")
                return None
        else:
            print(f"Error: HTTP {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except json.JSONDecodeError:
        print(f"Error parsing response: {response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None
