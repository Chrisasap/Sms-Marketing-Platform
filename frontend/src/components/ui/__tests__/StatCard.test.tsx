import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatCard from '../StatCard';
import { Send, CheckCircle, XCircle } from 'lucide-react';

describe('StatCard', () => {
  it('renders title and value', () => {
    render(<StatCard title="Messages Sent" value={1234} icon={Send} />);
    expect(screen.getByText('Messages Sent')).toBeInTheDocument();
  });

  it('renders positive trend correctly', () => {
    render(<StatCard title="Delivered" value={100} icon={CheckCircle} trend={12.5} color="emerald" />);
    expect(screen.getByText('+12.5% from last period')).toBeInTheDocument();
    const trendEl = screen.getByText('+12.5% from last period');
    expect(trendEl).toHaveClass('text-emerald-400');
  });

  it('renders negative trend correctly', () => {
    render(<StatCard title="Failed" value={50} icon={XCircle} trend={-2.1} color="rose" />);
    expect(screen.getByText('-2.1% from last period')).toBeInTheDocument();
    const trendEl = screen.getByText('-2.1% from last period');
    expect(trendEl).toHaveClass('text-rose-400');
  });

  it('renders correct color icon container', () => {
    const { container } = render(<StatCard title="Test" value={42} icon={Send} color="amber" />);
    const iconContainer = container.querySelector('.from-amber-500');
    expect(iconContainer).toBeInTheDocument();
  });

  it('does not render trend when not provided', () => {
    render(<StatCard title="No Trend" value={99} icon={Send} />);
    expect(screen.queryByText(/from last period/)).not.toBeInTheDocument();
  });
});
