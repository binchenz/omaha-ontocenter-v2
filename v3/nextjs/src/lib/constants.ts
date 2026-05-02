export const DEFAULT_TENANT_ID = "default";
export const DEFAULT_USER_ID = "demo";
export const DEFAULT_SESSION_TITLE = "新对话";

/** Prior-turn cap sent to the LLM. Too long → cost + context pollution. */
export const MAX_HISTORY_MESSAGES = 12;

/** Upper bound on messages returned from the /messages list endpoint. */
export const MAX_MESSAGES_PER_SESSION_FETCH = 500;
