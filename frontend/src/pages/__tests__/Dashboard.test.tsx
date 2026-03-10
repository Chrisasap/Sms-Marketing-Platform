import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Dashboard from '../Dashboard';

describe('Dashboard', () => {
  it('renders stat cards', () => {
    render(<Dashboard />);
    expect(screen.getByText('Messages Sent')).toBeInTheDocument();
    expect(screen.getByText('Delivered')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Responses')).toBeInTheDocument();
  });

  it('renders page heading', () => {
    render(<Dashboard />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText("Welcome back. Here's your messaging overview.")).toBeInTheDocument();
  });

  it('renders quick stats section', () => {
    render(<Dashboard />);
    expect(screen.getByText('Quick Stats')).toBeInTheDocument();
    expect(screen.getByText('Delivery Rate')).toBeInTheDocument();
    expect(screen.getByText('94.9%')).toBeInTheDocument();
    expect(screen.getByText('Active Contacts')).toBeInTheDocument();
    expect(screen.getByText('24,891')).toBeInTheDocument();
    expect(screen.getByText('Active Numbers')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Spent Today')).toBeInTheDocument();
    expect(screen.getByText('$142.30')).toBeInTheDocument();
  });

  it('renders message volume section', () => {
    render(<Dashboard />);
    expect(screen.getByText('Message Volume')).toBeInTheDocument();
  });

  it('renders trend indicators', () => {
    render(<Dashboard />);
    expect(screen.getByText('+12.5% from last period')).toBeInTheDocument();
    expect(screen.getByText('+8.3% from last period')).toBeInTheDocument();
    expect(screen.getByText('-2.1% from last period')).toBeInTheDocument();
    expect(screen.getByText('+15.7% from last period')).toBeInTheDocument();
  });
});
