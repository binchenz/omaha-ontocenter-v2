"""Prompt templates for agent LLM calls."""

SQL_GENERATION_PROMPT = """You are a SQL expert. Generate a SQL query based on the user's question (in Chinese or English) and the ontology context provided.

User Question: {question}

Ontology Context:
{ontology_context}

Requirements:
- Generate ONLY the SQL query, no explanations
- Support both Chinese and English questions
- Use standard SQL syntax compatible with PostgreSQL and MySQL
- Use proper table and column names from the ontology context
- Include appropriate WHERE clauses, JOINs, and aggregations as needed
- Ensure the query is safe and does not contain SQL injection vulnerabilities
- Do not use any DDL statements (CREATE, DROP, ALTER, etc.)
- Only use SELECT statements
- IMPORTANT: Do NOT include semicolons (;) at the end of the query
- Return ONLY the SQL query text, no markdown code blocks

Examples:
Question: "有多少个会话？" or "How many sessions?"
SQL: SELECT COUNT(*) FROM agent_chat_sessions

Question: "显示消息最多的前10个会话" or "Show top 10 sessions by message count"
SQL: SELECT session_id, message_count FROM agent_chat_sessions ORDER BY message_count DESC LIMIT 10

SQL Query:"""

RESPONSE_FORMATTING_PROMPT = """You are a helpful assistant. Format the SQL query results into a natural language response.

User Question: {question}

SQL Query: {sql_query}

Query Results:
{results}

Requirements:
- Provide a clear, concise answer to the user's question
- If the question is in Chinese, respond in Chinese
- If the question is in English, respond in English
- Use natural language, not technical jargon
- Include relevant numbers and data from the results
- If results are empty, explain that no data was found
- Keep the response brief and to the point

Response:"""
