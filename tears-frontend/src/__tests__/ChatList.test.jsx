import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ChatList from '../pages/chat_list';
import * as api from '../services/api';

vi.mock('../services/api');

const MockedChatList = () => (
  <BrowserRouter>
    <ChatList />
  </BrowserRouter>
);

describe('ChatList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('token', 'fake-token');
  });

  it('renders chat list', async () => {
    const mockUserInfo = {
      data: { id: 1, username: 'testuser', email: 'test@example.com' }
    };
    const mockChats = {
      data: {
        items: [
          { id: 1, name: 'Test Chat 1', message_count: 10, member_count: 5 },
          { id: 2, name: 'Test Chat 2', message_count: 20, member_count: 3 }
        ]
      }
    };
    
    api.authAPI.me.mockResolvedValue(mockUserInfo);
    api.chatsAPI.list.mockResolvedValue(mockChats);
    
    render(<MockedChatList />);
    
    await waitFor(() => {
      expect(screen.getByText('Test Chat 1')).toBeInTheDocument();
      expect(screen.getByText('Test Chat 2')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    api.authAPI.me.mockReturnValue(new Promise(() => {}));
    api.chatsAPI.list.mockReturnValue(new Promise(() => {}));
    
    render(<MockedChatList />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('handles empty chat list', async () => {
    api.authAPI.me.mockResolvedValue({ 
      data: { id: 1, username: 'testuser', email: 'test@example.com' } 
    });
    api.chatsAPI.list.mockResolvedValue({ data: { items: [] } });
    
    render(<MockedChatList />);
    
    await waitFor(() => {
      expect(screen.getByText(/no chats/i)).toBeInTheDocument();
    });
  });
});
