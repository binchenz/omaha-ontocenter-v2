/**
 * Action triggers for structured panels.
 *
 * IMPORTANT: These string literals are also referenced by the LLM system
 * prompt in `backend/app/services/chat.py`. Changing one without the other
 * will silently break the modeling-confirm flow.
 */
export const MODELING_CONFIRM_TRIGGER = '确认建模';
export const MODELING_RETRY_TRIGGER = '重新分析建模';
