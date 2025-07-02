import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Tuple
import os
import os.path
import requests
import json
import audio
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Configuration from environment
WHATSAPP_API_HOST = os.getenv('WHATSAPP_API_HOST', 'localhost')
WHATSAPP_API_PORT = os.getenv('WHATSAPP_API_PORT', '8080')
WHATSAPP_API_BASE_URL = os.getenv('WHATSAPP_API_BASE_URL', f'http://{WHATSAPP_API_HOST}:{WHATSAPP_API_PORT}/api')
MESSAGES_DB_NAME = os.getenv('MESSAGES_DB_NAME', 'messages.db')

# Database path
MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', MESSAGES_DB_NAME)

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

def get_sender_name(sender_jid: str) -> str:
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
        if not query or len(query.strip()) < 1:
            print("INFO: Query too short, returning empty results")
            return []
            
        # Check if database exists
        if not os.path.exists(MESSAGES_DB_PATH):
            print(f"WARNING: Database not found at {MESSAGES_DB_PATH}")
            return []
        
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Clean and prepare query
        clean_query = query.strip().lower()
        exact_pattern = clean_query
        starts_with_pattern = clean_query + '%'
        contains_pattern = '%' + clean_query + '%'
        word_boundary_pattern = f'% {clean_query}%'
        
        # Build simplified query with proper scoring
        group_filter = "" if include_groups else "AND jid NOT LIKE '%@g.us'"
        
        query_sql = f"""
            SELECT DISTINCT 
                jid,
                name,
                CASE 
                    WHEN LOWER(name) = ? THEN 100
                    WHEN LOWER(name) LIKE ? THEN 90
                    WHEN LOWER(jid) LIKE ? THEN 85
                    WHEN LOWER(name) LIKE ? THEN 80
                    WHEN LOWER(name) LIKE ? THEN 70
                    WHEN LOWER(jid) LIKE ? THEN 60
                    ELSE 40
                END as score,
                CASE WHEN name IS NOT NULL THEN 1 ELSE 0 END as has_name,
                LENGTH(name) as name_length
            FROM chats
            WHERE 
                (LOWER(name) LIKE ? OR LOWER(jid) LIKE ?)
                {group_filter}
                AND name IS NOT NULL
                AND TRIM(name) != ''
            ORDER BY 
                score DESC,
                has_name DESC,
                name_length ASC,
                name COLLATE NOCASE,
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
            if jid not in seen_jids:
                seen_jids.add(jid)
                contact = Contact(
                    phone_number=jid.split('@')[0],
                    name=contact_data[1],
                    jid=jid
                )
                result.append(contact)
        
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
def calculate_similarity(s1: str, s2: str) -> float:
    """Calculate similarity between two strings using Levenshtein distance."""
    if not s1 or not s2:
        return 0.0
    
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    
    if s1 == s2:
        return 1.0
    
    # If one string is contained in the other
    if s1 in s2 or s2 in s1:
        return 0.8
    
    # Levenshtein distance calculation
    m, n = len(s1), len(s2)
    if m == 0:
        return 0.0
    if n == 0:
        return 0.0
    
    # Create matrix
    d = [[0] * (n + 1) for _ in range(m + 1)]
    
    # Initialize first row and column
    for i in range(m + 1):
        d[i][0] = i
    for j in range(n + 1):
        d[0][j] = j
    
    # Fill the matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            d[i][j] = min(
                d[i-1][j] + 1,      # deletion
                d[i][j-1] + 1,      # insertion
                d[i-1][j-1] + cost  # substitution
            )
    
    # Convert distance to similarity (0-1)
    max_len = max(m, n)
    similarity = 1 - (d[m][n] / max_len)
    return similarity

def smart_search_contacts(query: str, limit: int = 25, include_groups: bool = False, similarity_threshold: float = 0.6) -> List[Contact]:
    """Advanced contact search with similarity scoring and smart ranking.
    
    This function provides more intelligent search capabilities:
    - Fuzzy string matching with configurable similarity threshold
    - Multiple search strategies (exact, partial, phonetic-like)
    - Smart ranking based on multiple factors
    - Handles common misspellings and variations
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
        
        clean_query = query.strip().lower()
        group_filter = "" if include_groups else "AND jid NOT LIKE '%@g.us'"
        
        # Get all potential matches for similarity analysis
        cursor.execute(f"""
            SELECT DISTINCT 
                jid,
                name
            FROM chats
            WHERE 
                name IS NOT NULL
                AND TRIM(name) != ''
                {group_filter}
            ORDER BY name COLLATE NOCASE
        """)
        
        all_contacts = cursor.fetchall()
        
        # Calculate similarity scores
        scored_contacts = []
        
        for contact_data in all_contacts:
            jid, name = contact_data
            if not name:
                continue
                
            # Calculate multiple similarity scores
            name_similarity = calculate_similarity(clean_query, name)
            
            # Check for partial matches
            partial_score = 0.0
            if clean_query in name.lower():
                partial_score = 0.9
            elif any(word.startswith(clean_query) for word in name.lower().split()):
                partial_score = 0.8
            elif any(clean_query in word for word in name.lower().split()):
                partial_score = 0.7
            
            # Check phone number match
            phone_score = 0.0
            phone_part = jid.split('@')[0]
            if clean_query in phone_part:
                phone_score = 0.85
            
            # Combined score
            final_score = max(name_similarity, partial_score, phone_score)
            
            # Apply threshold
            if final_score >= similarity_threshold:
                scored_contacts.append((contact_data, final_score, name_similarity, partial_score, phone_score))
        
        # Sort by score (descending) and name (ascending for ties)
        scored_contacts.sort(key=lambda x: (-x[1], x[0][1].lower()))
        
        # Convert to Contact objects
        result = []
        for i, (contact_data, final_score, name_sim, partial_sim, phone_sim) in enumerate(scored_contacts[:limit]):
            if i < 3:  # Show scoring details for top 3 results
                print(f"Match: {contact_data[1]} (Score: {final_score:.2f} - Name: {name_sim:.2f}, Partial: {partial_sim:.2f}, Phone: {phone_sim:.2f})")
            
            contact = Contact(
                phone_number=contact_data[0].split('@')[0],
                name=contact_data[1],
                jid=contact_data[0]
            )
            result.append(contact)
        
        # If no good matches found, fallback to basic search
        if not result:
            print(f"INFO: No matches above similarity threshold {similarity_threshold}. Trying basic search...")
            return search_contacts(query, limit, include_groups)
        
        return result
        
    except sqlite3.Error as e:
        print(f"Database error in smart search: {e}")
        # Fallback to basic search
        return search_contacts(query, limit, include_groups)
    except Exception as e:
        print(f"Unexpected error in smart search: {e}")
        # Fallback to basic search
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
