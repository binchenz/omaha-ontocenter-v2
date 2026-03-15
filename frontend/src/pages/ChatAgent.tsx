/**
 * ChatAgent page - main chat interface.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { chatApi } from '@/services/chatApi';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { DataTable } from '@/components/chat/DataTable';
import { ChartRenderer } from '@/components/chat/ChartRenderer';
import type { ChatMessage as ChatMessageType, SendMessageResponse } from '@/types/chat';

export const ChatAgent: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<SendMessageResponse | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      if (!projectId) return;

      try {
        const session = await chatApi.createSession(Number(projectId), {
          user_id: 1, // TODO: Get from auth context
          title: 'New Chat',
        });
        setSessionId(session.id);
      } catch (err) {
        setError('Failed to create chat session');
        console.error(err);
      }
    };

    initSession();
  }, [projectId]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || !projectId) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setError(null);

    // Add user message to UI
    const tempUserMsg: ChatMessageType = {
      id: Date.now(),
      session_id: sessionId,
      role: 'user',
      content: userMessage,
      tool_calls: null,
      chart_config: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await chatApi.sendMessage(
        Number(projectId),
        sessionId,
        { message: userMessage }
      );

      // Add assistant message to UI
      const assistantMsg: ChatMessageType = {
        id: Date.now() + 1,
        session_id: sessionId,
        role: 'assistant',
        content: response.message,
        tool_calls: null,
        chart_config: response.chart_config ? JSON.stringify(response.chart_config) : null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setLastResponse(response);
    } catch (err) {
      setError('Failed to send message');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!sessionId) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Initializing chat...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Chat Agent
      </Typography>

      {/* Messages */}
      <Paper
        elevation={2}
        sx={{
          height: '500px',
          overflowY: 'auto',
          p: 2,
          mb: 2,
          bgcolor: 'grey.50',
        }}
      >
        {messages.length === 0 && (
          <Typography color="text.secondary" textAlign="center" sx={{ mt: 4 }}>
            Start a conversation by typing a message below
          </Typography>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {/* Data Table */}
      {lastResponse?.data_table && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Query Results
          </Typography>
          <DataTable data={lastResponse.data_table} />
        </Box>
      )}

      {/* Chart */}
      {lastResponse?.chart_config && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Visualization
          </Typography>
          <ChartRenderer config={lastResponse.chart_config} />
        </Box>
      )}

      {/* SQL */}
      {lastResponse?.sql && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Generated SQL
          </Typography>
          <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
            <Typography
              component="pre"
              sx={{ fontFamily: 'monospace', fontSize: '0.875rem', m: 0 }}
            >
              {lastResponse.sql}
            </Typography>
          </Paper>
        </Box>
      )}

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Input */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={loading}
        />
        <Button
          variant="contained"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          endIcon={<SendIcon />}
        >
          Send
        </Button>
      </Box>
    </Container>
  );
};
