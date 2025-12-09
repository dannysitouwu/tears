import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../pages/login';
import * as api from '../services/api';

vi.mock('../services/api');

const MockedLogin = () => (
  <BrowserRouter>
    <Login />
  </BrowserRouter>
);

describe('Login Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders login form', () => {
    render(<MockedLogin />);
    
    expect(screen.getByPlaceholderText(/username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('shows error on failed login', async () => {
    const mockError = {
      response: {
        data: { detail: 'Invalid credentials' }
      }
    };
    api.authAPI.login.mockRejectedValue(mockError);
    
    render(<MockedLogin />);
    
    const usernameInput = screen.getByPlaceholderText(/username/i);
    const passwordInput = screen.getByPlaceholderText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });
    
    fireEvent.change(usernameInput, { target: { value: 'wronguser' } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpass' } });
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('successfully logs in and stores token', async () => {
    const mockToken = 'fake-jwt-token';
    api.authAPI.login.mockResolvedValue({ 
      data: { 
        access_token: mockToken,
        token_type: 'bearer'
      } 
    });
    
    render(<MockedLogin />);
    
    const usernameInput = screen.getByPlaceholderText(/username/i);
    const passwordInput = screen.getByPlaceholderText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'testpass' } });
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(localStorage.getItem('token')).toBe(mockToken);
    });
  });
});
