import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Login from '../Login';

function renderLogin() {
  return render(
    <BrowserRouter>
      <Login />
    </BrowserRouter>
  );
}

describe('Login', () => {
  it('renders login form', () => {
    renderLogin();
    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByText('Sign in to BlastWave SMS')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
    expect(screen.getByText('Forgot password?')).toBeInTheDocument();
    expect(screen.getByText('Sign up')).toBeInTheDocument();
  });

  it('shows/hides password', async () => {
    const user = userEvent.setup();
    renderLogin();

    const passwordInput = screen.getByPlaceholderText('Password');
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Find the toggle button (the one containing the Eye icon)
    // It's the button with type="button" inside the password field area
    const toggleButtons = screen.getAllByRole('button');
    const eyeToggle = toggleButtons.find((btn) => btn.getAttribute('type') === 'button');
    expect(eyeToggle).toBeTruthy();

    // Click to show password
    await user.click(eyeToggle!);
    expect(passwordInput).toHaveAttribute('type', 'text');

    // Click again to hide password
    await user.click(eyeToggle!);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('form submission with email and password', async () => {
    const user = userEvent.setup();
    renderLogin();

    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');

    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');
  });

  it('links to register page', () => {
    renderLogin();
    const signUpLink = screen.getByText('Sign up');
    expect(signUpLink).toHaveAttribute('href', '/register');
  });
});
